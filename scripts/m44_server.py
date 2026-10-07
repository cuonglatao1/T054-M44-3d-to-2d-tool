"""Local M44 service: a bookmarklet in the browser bar checks the CVAT task you are looking at.

  python scripts/m44_server.py            (or double-click m44_server.bat)
  then open http://localhost:8765 and drag the "M44 Check" button to the bookmarks bar.

On a CVAT task/job page, clicking the bookmark opens /check?task=<id> (or ?job=<id>): the task is checked
(same as scripts/cvat_check.py: qc + Score written back to CVAT) while a progress page polls /status, then
the HTML report is shown from /report/<task id>/. Only the standard library is used for the server.
"""
import html
import json
import mimetypes
import os
import sys
import threading
import traceback
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from cvat_check import check_task  # noqa: E402
from cvat_create_task import create_nusc_task  # noqa: E402
from m44 import cvat_io  # noqa: E402
from m44.loader import load_frames_nusc  # noqa: E402

PORT = int(os.environ.get('M44_PORT', 8765))
RUNS: dict[int, dict] = {}            # task id -> {state, log, summary, error, started}
RUNS_LOCK = threading.Lock()
CHECK_LOCK = threading.Lock()         # one check / task creation at a time: they share CPU, GPU and disk
CREATES: dict[str, dict] = {}         # creation job id -> {state, log, results, error, title}
# must stay identical to pilot_setup.bat so every reviewer gets the same frames and the same injected errors
PILOT_SPECS = [{'name': 'PILOT A', 'start': 10, 'count': 5, 'labels': 'noisy', 'expect': 25},
               {'name': 'PILOT B', 'start': 60, 'count': 5, 'labels': 'noisy', 'expect': 18}]
# pilot part 2: one empty frame (Boston, 10 cars + 7 pedestrians within 30 m) labelled from scratch
LABEL_SPECS = [{'name': 'PILOT GAN NHAN', 'start': 25, 'count': 1, 'labels': 'none'}]


def nusc_root() -> str:
    return os.environ.get('NUSC_ROOT', str(ROOT / 'data' / 'nuscenes'))


def existing_tasks(names: set[str]) -> list[dict]:
    """Tasks created earlier from this machine (out/cvat_tasks/task_*/task.json) with one of these names
    that still exist in CVAT (people delete tasks in the CVAT UI)."""
    found = []
    for p in sorted((ROOT / 'out' / 'cvat_tasks').glob('task_*/task.json')):
        info = json.loads(p.read_text(encoding='utf-8'))
        if info.get('name') in names:
            found.append(info)
    if not found:
        return []
    cvat_io.load_env(ROOT / '.cvat.env')
    with cvat_io.connect() as client:
        alive = {t.id for t in client.tasks.list()}
    return [t for t in found if t['task_id'] in alive]


def start_create(title: str, specs: list[dict]) -> str:
    job_id = datetime.now().strftime('%H%M%S%f')
    job = CREATES[job_id] = {'state': 'running', 'log': [], 'results': [], 'error': None, 'title': title}

    def work():
        with CHECK_LOCK:
            try:
                for s in specs:
                    job['log'].append(f"Đọc {s['count']} frame nuScenes (val, từ frame {s['start']})…")
                    frames = load_frames_nusc(nusc_root(), 'val', max_frames=s['start'] + s['count'])[s['start']:]
                    res = create_nusc_task(frames, s['name'], s['labels'], seed=s.get('seed', 0),
                                           log=job['log'].append)
                    job['results'].append({**res, 'expect': s.get('expect')})
                job['state'] = 'done'
            except BaseException as e:  # SystemExit from cvat_io carries a readable message
                traceback.print_exc()
                job['error'] = f'{type(e).__name__}: {e}'
                job['state'] = 'error'

    threading.Thread(target=work, daemon=True).start()
    return job_id

PAGE = """<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;margin:24px;max-width:860px;color:#222;background:#fafafa}}
.btn{{display:inline-block;padding:10px 16px;background:#1f6feb;color:#fff;border-radius:6px;text-decoration:none;
font-weight:600}} code{{background:#eee;padding:1px 4px;border-radius:3px}} pre{{background:#111;color:#ddd;
padding:12px;border-radius:6px;white-space:pre-wrap}} td,th{{padding:4px 10px;border-bottom:1px solid #ddd;text-align:left}}
.err{{color:#b00020}}</style></head><body>{body}</body></html>"""


def bookmarklet() -> str:
    js = ("(function(){var p=location.pathname,t=p.match(/\\/tasks\\/(\\d+)/),j=p.match(/\\/jobs\\/(\\d+)/);"
          "if(!t&&!j){alert('M44: hãy mở một task hoặc job CVAT trước');return;}"
          f"window.open('http://localhost:{PORT}/check?'+(t?'task='+t[1]:'job='+j[1]),'_blank');}})();")
    return 'javascript:' + urllib.parse.quote(js, safe="(){};:=,+'/?!&|.[]")


def start_check(task_id: int) -> None:
    with RUNS_LOCK:
        run = RUNS.get(task_id)
        if run and run['state'] in ('queued', 'running'):
            return
        run = RUNS[task_id] = {'state': 'queued', 'log': ['Đang chờ lượt kiểm tra…'], 'summary': None,
                               'error': None, 'started': datetime.now().strftime('%H:%M:%S')}

    def work():
        with CHECK_LOCK:
            run['state'] = 'running'
            try:
                run['summary'] = check_task(task_id, log=run['log'].append)
                run['state'] = 'done'
            except Exception as e:  # shown to the user on the progress page
                traceback.print_exc()
                run['error'] = f'{type(e).__name__}: {e}'
                run['state'] = 'error'

    threading.Thread(target=work, daemon=True).start()


def task_of_job(job_id: int) -> int:
    cvat_io.load_env(ROOT / '.cvat.env')
    with cvat_io.connect() as client:
        return client.jobs.retrieve(job_id).task_id


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype='text/html; charset=utf-8', code=200, headers=None):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _page(self, title, body, code=200):
        self._send(PAGE.format(title=html.escape(title), body=body).encode('utf-8'), code=code)

    def log_message(self, fmt, *args):  # keep the console quiet except for errors
        if args and str(args[1]).startswith(('4', '5')):
            super().log_message(fmt, *args)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        try:
            if url.path == '/':
                return self.home()
            if url.path == '/check':
                return self.check(q)
            if url.path == '/status':
                run = RUNS.get(int(q['task'][0]))
                return self._send(json.dumps(run or {'state': 'unknown'}, ensure_ascii=False).encode('utf-8'),
                                  'application/json; charset=utf-8')
            if url.path == '/create':
                return self.create(q)
            if url.path == '/cstatus':
                job = CREATES.get(q['id'][0])
                return self._send(json.dumps(job or {'state': 'unknown'}, ensure_ascii=False).encode('utf-8'),
                                  'application/json; charset=utf-8')
            if url.path.startswith('/report/'):
                return self.report(url.path)
            self._page('Không tìm thấy', '<p>Không có trang này.</p>', 404)
        except Exception as e:
            traceback.print_exc()
            self._page('Lỗi', f'<p class="err">{html.escape(f"{type(e).__name__}: {e}")}</p>', 500)

    def home(self):
        rows = ''.join(
            f"<tr><td>{tid}</td><td>{html.escape((r['summary'] or {}).get('name', ''))}</td><td>{r['started']}</td>"
            f"<td>{r['state']}</td><td>{'<a href=/report/%d/>Báo cáo</a>' % tid if r['state'] == 'done' else ''}</td></tr>"
            for tid, r in sorted(RUNS.items()))
        body = f"""<h1>M44 – Kiểm tra nhãn 3D</h1>
<p>Dịch vụ đang chạy. Kéo nút dưới đây lên <b>thanh dấu trang</b> của trình duyệt (làm một lần):</p>
<p><a class="btn" href="{html.escape(bookmarklet())}">M44 Check</a></p>
<p>Cách dùng: mở một task hoặc job trên CVAT → bấm <b>M44 Check</b> trên thanh dấu trang → tool kiểm tra task đó,
ghi cờ vào CVAT và mở danh sách lỗi. Không thấy thanh dấu trang: <code>Ctrl+Shift+B</code>.</p>
<h2>Tạo task trên CVAT</h2>
<p><a class="btn" href="/create?preset=pilot">Tạo task pilot (A + B)</a>
&nbsp;phần 1: PILOT A (25 lỗi cài) và PILOT B (18 lỗi cài) – giống hệt máy các bạn khác.</p>
<p><a class="btn" href="/create?preset=label">Tạo task gán nhãn</a>
&nbsp;phần 2: 1 frame trống (Boston) để tự gán ô tô + người đi bộ rồi bấm M44 Check.</p>
<form action="/create" method="get" style="margin-top:12px">
<b>Tạo task khác:</b> tên <input name="name" value="M44 task" size="14">
· từ frame <input name="start" type="number" value="0" min="0" max="80" style="width:4em">
· số frame <input name="count" type="number" value="10" min="1" max="81" style="width:4em">
· nhãn <select name="labels"><option value="none">trống (tự gán)</option><option value="gt">nhãn gốc</option>
<option value="noisy">có cài lỗi + đáp án</option></select>
<button type="submit">Tạo</button></form>
<h2>Các lần kiểm tra</h2>
{'<table><tr><th>Task</th><th>Tên</th><th>Bắt đầu</th><th>Trạng thái</th><th></th></tr>' + rows + '</table>'
 if rows else '<p>Chưa có.</p>'}"""
        self._page('M44 Check', body)

    def check(self, q):
        if 'task' in q:
            task_id = int(q['task'][0])
        elif 'job' in q:
            task_id = task_of_job(int(q['job'][0]))
        else:
            return self._page('Thiếu tham số', '<p class="err">Cần ?task=… hoặc ?job=…</p>', 400)
        start_check(task_id)
        body = f"""<h1>M44 – đang kiểm tra task {task_id}</h1>
<p id="state">Đang bắt đầu…</p><pre id="log"></pre>
<script>
async function poll() {{
  const r = await (await fetch('/status?task={task_id}')).json();
  document.getElementById('log').textContent = (r.log || []).join('\\n');
  if (r.state === 'done') {{ location.href = '/report/{task_id}/'; return; }}
  if (r.state === 'error') {{
    const s = document.getElementById('state'); s.className = 'err';
    s.textContent = 'Lỗi: ' + r.error + ' – chụp màn hình gửi tech lead.'; return; }}
  document.getElementById('state').textContent = 'Đang chạy, thường mất 30 giây – vài phút…';
  setTimeout(poll, 2000);
}}
poll();
</script>"""
        self._page(f'M44 – task {task_id}', body)

    def create(self, q):
        running = next((j for j in CREATES.values() if j['state'] == 'running'), None)
        if running:
            job_id = next(k for k, v in CREATES.items() if v is running)
        else:
            preset = q.get('preset', [''])[0]
            if preset in ('pilot', 'label'):
                specs, title = (PILOT_SPECS, 'Tạo task pilot A + B') if preset == 'pilot' else \
                    (LABEL_SPECS, 'Tạo task gán nhãn (pilot phần 2)')
                done = existing_tasks({s['name'] for s in specs})
                if done and 'again' not in q:
                    items = ''.join(f"<li>{html.escape(t['name'])}: <a href='{t['url']}' target='_blank'>task "
                                    f"{t['task_id']}</a></li>" for t in done)
                    return self._page('Đã có task pilot', f"""<h1>Máy này đã tạo task pilot</h1><ul>{items}</ul>
<p>Dùng các task trên. Tạo lại sẽ ra task mới (trùng tên) – chỉ làm khi task cũ đã bị xoá hoặc hỏng.</p>
<p><a href="/create?preset={preset}&again=1">Vẫn tạo lại</a> · <a href="/">Về trang chính</a></p>""")
            else:
                name = q.get('name', ['M44 task'])[0].strip() or 'M44 task'
                start, count = int(q.get('start', ['0'])[0]), int(q.get('count', ['10'])[0])
                labels = q.get('labels', ['none'])[0]
                if labels not in ('none', 'gt', 'noisy') or not (0 <= start <= 80 and 1 <= count <= 81 - start):
                    return self._page('Sai tham số', '<p class="err">Frame phải trong 0–80, nhãn none/gt/noisy.</p>', 400)
                specs, title = [{'name': name, 'start': start, 'count': count, 'labels': labels}], f'Tạo task "{name}"'
            job_id = start_create(title, specs)

        body = f"""<h1 id="title">{html.escape(CREATES[job_id]['title'])}</h1>
<p id="state">Đang tạo task, mỗi task khoảng 1 phút…</p><pre id="log"></pre><div id="result"></div>
<script>
function esc(s) {{ return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]); }}
async function poll() {{
  const r = await (await fetch('/cstatus?id={job_id}')).json();
  document.getElementById('log').textContent = (r.log || []).join('\\n');
  if (r.state === 'running') {{ setTimeout(poll, 2000); return; }}
  const s = document.getElementById('state');
  if (r.state === 'error') {{ s.className = 'err'; s.textContent = 'Lỗi: ' + r.error + ' – chụp màn hình gửi tech lead.'; return; }}
  s.textContent = 'Xong. Mở task trên CVAT:';
  document.getElementById('result').innerHTML = '<ul>' + r.results.map(t => {{
    let check = '';
    if (t.expect != null) check = t.injected === t.expect
      ? ` – <b style="color:#1a7f37">${{t.injected}} lỗi cài ✓ đúng</b>`
      : ` – <b class="err">${{t.injected}} lỗi cài, phải là ${{t.expect}}: báo tech lead</b>`;
    return `<li><b>${{esc(t.name)}}</b>: <a href="${{t.url}}" target="_blank">task ${{t.task_id}}</a>${{check}}</li>`;
  }}).join('') + '</ul><p>Ghi các số task vào sheet. <a href="/">Về trang chính</a></p>';
}}
poll();
</script>"""
        self._page(CREATES[job_id]['title'], body)

    def report(self, path):
        parts = path.split('/', 3)  # ['', 'report', '<id>', 'rest']
        base = (ROOT / 'out' / f'cvat_check_{int(parts[2])}').resolve()
        rel = urllib.parse.unquote(parts[3] if len(parts) > 3 else '') or 'index.html'
        target = (base / rel).resolve()
        if base not in target.parents and target != base or not target.is_file():
            return self._page('Không tìm thấy', '<p>Chưa có báo cáo cho task này.</p>', 404)
        ctype = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        if ctype.startswith('text/'):
            ctype += '; charset=utf-8'
        self._send(target.read_bytes(), ctype)


def main():
    server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'M44 service: http://localhost:{PORT}  (Ctrl+C để tắt)')
    if '--open' in sys.argv:
        import webbrowser
        threading.Timer(1.0, webbrowser.open, [f'http://localhost:{PORT}/']).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
