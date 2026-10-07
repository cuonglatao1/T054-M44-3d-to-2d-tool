"""Check real labels: no error injection, just flags + report for the reviewer.

  python scripts/check.py --split val --out out/check_val
  python scripts/check.py --frames-json my_labels.json --out out/check_job   (labels from another tool, e.g. CVAT)

run_all.py is the evaluation harness (it corrupts labels on purpose to measure recall); use this script on
labels you actually want reviewed.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from m44.geometry import project_frame  # noqa: E402
from m44.loader import add_data_args, frames_from_args  # noqa: E402
from m44.match import check, load_cfg  # noqa: E402
from m44.report import build_report  # noqa: E402

TUNED_CFG = Path(__file__).resolve().parents[1] / 'configs' / 'tuned.json'


def dump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def run_check(frames, out_dir, cfg, weights='yolo11m.pt', device='auto', redetect=False, title=None,
              links_fn=None):
    """Detect (cached in out_dir/det_2d.json), check and write flags.json + report. Returns flags.
    links_fn(flags) -> {flag_id: url} adds a "fix it here" link per flag to the report."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    det_path = out / 'det_2d.json'
    if det_path.exists() and not redetect:
        dets = json.loads(det_path.read_text(encoding='utf-8'))
    else:
        from m44.detect import detect
        dets = detect(frames, weights, device=device)
        dump(dets, det_path)

    proj = [p for f in frames for p in project_frame(f)]
    flags, matches = check(proj, dets, cfg)
    dump(flags, out / 'flags.json')

    by_type = Counter(f['type'] for f in flags)
    flagged_boxes = {(f['sample'], f['box_id']) for f in flags if f['box_id']}
    summary = {
        'Số frame': len(frames),
        'Số cuboid': sum(len(f['boxes']) for f in frames),
        'Cuboid đối chiếu được với ảnh': len({(m['sample'], m['box_id']) for m in matches}),
        'Cuboid bị cảnh báo': len(flagged_boxes),
        'Tổng cảnh báo': len(flags),
        'Theo loại': ', '.join(f'{t} {n}' for t, n in by_type.most_common()) or '–',
    }
    dump(summary, out / 'summary.json')
    build_report(frames, proj, dets, flags, out, summary, title=title,
                 links=links_fn(flags) if links_fn else None)
    return flags


def main():
    ap = argparse.ArgumentParser()
    add_data_args(ap)
    ap.add_argument('--frames-json', help='frames exported by another tool (same format as loader output)')
    ap.add_argument('--out', default='out/check')
    ap.add_argument('--weights', default='yolo11m.pt')
    ap.add_argument('--device', default='auto')
    ap.add_argument('--redetect', action='store_true')
    ap.add_argument('--cfg', default=str(TUNED_CFG), help="JSON file/inline JSON; 'default' = untuned thresholds")
    args = ap.parse_args()

    cfg = {} if args.cfg == 'default' else load_cfg(args.cfg)
    if args.frames_json:
        frames = json.loads(Path(args.frames_json).read_text(encoding='utf-8'))
    else:
        frames = frames_from_args(args)
    flags = run_check(frames, args.out, cfg, args.weights, args.device, args.redetect)
    print(f'{len(frames)} frames, {len(flags)} flags -> {Path(args.out) / "index.html"}')


if __name__ == '__main__':
    main()
