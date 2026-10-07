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
from m44 import cvat_io  # noqa: E402

PORT = int(os.environ.get('M44_PORT', 8765))
RUNS: dict[int, dict] = {}            # task id -> {state, log, summary, error, started}
RUNS_LOCK = threading.Lock()
CHECK_LOCK = threading.Lock()         # one check at a time: YOLO shares the GPU / CPU

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
