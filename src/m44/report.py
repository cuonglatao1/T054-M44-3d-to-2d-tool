"""Visual report for reviewers: annotated camera images, one crop per flag, HTML index and a CSV
that can be pasted into the team's grading Google Sheet. Grading is blind: the report never says
which flags come from injected errors."""
import csv
import html
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw

from .geometry import EDGES

FLAG_TEXT = {
    'LOW_IOU': 'Cuboid lệch vị trí / sai kích thước so với vật thể trên ảnh',
    'SIZE_MISMATCH': 'Chiều cao / chiều rộng cuboid không khớp vật thể (sai kích thước hoặc sai hướng)',
    'CLASS_MISMATCH': 'Class của cuboid khác class vật thể trên ảnh',
    'NO_2D_MATCH': 'Cuboid không khớp vật thể nào trên ảnh',
    'MISSING_3D': 'Vật thể thấy trên ảnh nhưng chưa có cuboid',
}
GREEN, RED, GRAY, BLUE, ORANGE = (40, 200, 80), (235, 40, 40), (150, 150, 150), (60, 140, 255), (255, 150, 0)


def _draw_cuboid(draw, corners_2d, color, width):
    for a, b in EDGES:
        if corners_2d[a] is not None and corners_2d[b] is not None:
            draw.line([tuple(corners_2d[a]), tuple(corners_2d[b])], fill=color, width=width)


def build_report(frames, proj, dets, flags, out_dir, summary: dict | None = None, title: str | None = None,
                 links: dict | None = None):
    """links: optional {flag_id: url}, e.g. the CVAT frame where the reviewer fixes the cuboid."""
    out = Path(out_dir)
    (out / 'vis').mkdir(parents=True, exist_ok=True)
    (out / 'flags').mkdir(parents=True, exist_ok=True)

    flagged = {(f['sample'], f['cam'], f['box_id']) for f in flags if f['box_id']}
    by_cam_p, by_cam_d, by_cam_f = defaultdict(list), defaultdict(list), defaultdict(list)
    for p in proj:
        by_cam_p[(p['sample'], p['cam'])].append(p)
    for d in dets:
        by_cam_d[(d['sample'], d['cam'])].append(d)
    for f in flags:
        by_cam_f[(f['sample'], f['cam'])].append(f)

    vis_files = []
    for frame in frames:
        for cam_name, cam in frame['cams'].items():
            key = (frame['sample'], cam_name)
            img = Image.open(cam['img_path']).convert('RGB')
            raw = img.copy()
            draw = ImageDraw.Draw(img)
            for d in by_cam_d[key]:
                draw.rectangle(d['bbox'], outline=BLUE, width=2)
            for p in sorted(by_cam_p[key], key=lambda p: -p['depth']):
                bad = (p['sample'], p['cam'], p['box_id']) in flagged
                _draw_cuboid(draw, p['corners_2d'], RED if bad else GREEN, 3 if bad else 2)
            for f in by_cam_f[key]:
                if f['type'] == 'MISSING_3D':
                    draw.rectangle(f['det_bbox'], outline=ORANGE, width=4)
                anchor = f['p_bbox'] or f['det_bbox']
                draw.text((anchor[0] + 2, max(anchor[1] - 12, 0)), f['flag_id'], fill=(255, 255, 0))
            name = f"{frame['sample'][:8]}_{cam_name}.jpg"
            img.save(out / 'vis' / name, quality=88)
            vis_files.append((cam_name, name, len(by_cam_f[key])))

            for f in by_cam_f[key]:  # crop around the flagged region, from the annotated image
                boxes = [b for b in (f['p_bbox'], f['det_bbox']) if b]
                x1, y1 = min(b[0] for b in boxes), min(b[1] for b in boxes)
                x2, y2 = max(b[2] for b in boxes), max(b[3] for b in boxes)
                m = max(40, 0.6 * max(x2 - x1, y2 - y1))
                crop = img.crop((max(0, x1 - m), max(0, y1 - m), min(raw.width, x2 + m), min(raw.height, y2 + m)))
                crop.thumbnail((360, 360))
                crop.save(out / 'flags' / f"{f['flag_id']}.jpg", quality=88)

    with open(out / 'flags_for_grading.csv', 'w', newline='', encoding='utf-8-sig') as fh:
        w = csv.writer(fh)
        w.writerow(['flag_id', 'sample', 'camera', 'loai_loi', 'mo_ta', 'class_3d', 'class_2d', 'iou',
                    'anh', 'Dung_hay_Nham (Đúng/Nhầm)', 'Ghi_chu'])
        for f in flags:
            w.writerow([f['flag_id'], f['sample'][:8], f['cam'], f['type'], FLAG_TEXT[f['type']],
                        f['cls_3d'] or '', f['cls_2d'] or '', f['iou'] if f['iou'] is not None else '',
                        f"flags/{f['flag_id']}.jpg", '', ''])

    links = links or {}

    def open_cell(f):
        url = links.get(f['flag_id'])
        return f"<td><a href='{html.escape(url)}' target='_blank'>Mở trong CVAT</a></td>" if url else ''

    rows = '\n'.join(
        f"<tr><td>{f['flag_id']}</td><td><img src='flags/{f['flag_id']}.jpg'></td>"
        f"<td><b>{f['type']}</b><br>{html.escape(FLAG_TEXT[f['type']])}</td><td>{f['cam']}</td>"
        f"<td>{f['cls_3d'] or '–'} / {f['cls_2d'] or '–'}</td><td>{f['iou'] if f['iou'] is not None else '–'}</td>"
        f"{open_cell(f)}</tr>"
        for f in flags)
    link_th = '<th>Sửa</th>' if links else ''
    cams = '\n'.join(f"<figure><a href='vis/{n}'><img src='vis/{n}'></a><figcaption>{c} – {k} cảnh báo"
                     f"</figcaption></figure>" for c, n, k in vis_files)
    summ = ''
    if summary:
        summ = '<h2>Tóm tắt</h2><table>' + ''.join(
            f'<tr><td>{html.escape(k)}</td><td>{html.escape(str(v))}</td></tr>' for k, v in summary.items()) + '</table>'

    (out / 'index.html').write_text(f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>M44 Consistency Report</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}}
table{{border-collapse:collapse;margin:8px 0}}td,th{{border:1px solid #ccc;padding:6px;vertical-align:top}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}}
figure{{margin:0}}figure img{{width:100%}}td img{{max-width:360px}}
.legend span{{display:inline-block;margin-right:16px}}</style></head><body>
<h1>{html.escape(title or 'M44 – Báo cáo kiểm tra nhất quán 2D–3D')}</h1>
<p class="legend"><span style="color:#28c850">■ cuboid ổn</span><span style="color:#eb2828">■ cuboid bị cảnh báo</span>
<span style="color:#3c8cff">■ vật thể YOLO thấy</span><span style="color:#ff9600">■ vật thể chưa có cuboid</span></p>
{summ}
<h2>Cảnh báo ({len(flags)})</h2>
<p>Chấm từng dòng trong file <code>flags_for_grading.csv</code>: cảnh báo này <b>Đúng</b> hay <b>Nhầm</b>?</p>
<table><tr><th>ID</th><th>Ảnh</th><th>Loại</th><th>Camera</th><th>Class 3D / 2D</th><th>IoU</th>{link_th}</tr>
{rows}</table>
<h2>6 camera</h2><div class="grid">{cams}</div></body></html>""", encoding='utf-8')
