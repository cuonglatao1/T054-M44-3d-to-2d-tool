"""End-to-end M44 pipeline.

  load GT -> project -> YOLO (cached) -> check clean GT (noise floor + reprojection error)
          -> inject errors -> project -> check -> evaluate recall -> HTML/CSV report

Example (demo frame shipped with mmdet3d):
  python scripts/run_all.py --info /root/work/mmdetection3d/demo/data/nuscenes/n015-2018-07-24-11-22-45+0800.pkl \
      --data-root /root/work/mmdetection3d/demo/data/nuscenes --out out/demo
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from m44.evaluate import evaluate, reprojection_stats  # noqa: E402
from m44.geometry import project_frame  # noqa: E402
from m44.inject import inject  # noqa: E402
from m44.loader import load_frames  # noqa: E402
from m44.match import DEFAULT_CFG, check, load_cfg  # noqa: E402
from m44.report import build_report  # noqa: E402


def dump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding='utf-8')


def project_all(frames):
    return [p for f in frames for p in project_frame(f)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--info', required=True, help='mmdet3d nuScenes info .pkl')
    ap.add_argument('--data-root', required=True)
    ap.add_argument('--out', default='out/run')
    ap.add_argument('--max-frames', type=int)
    ap.add_argument('--weights', default='yolo11m.pt')
    ap.add_argument('--device', default='0')
    ap.add_argument('--redetect', action='store_true', help='ignore cached det_2d.json')
    ap.add_argument('--rate', type=float, default=0.3, help='share of eligible boxes to corrupt')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--cfg', help='JSON file or inline JSON overriding match.DEFAULT_CFG (e.g. configs/tuned.json)')
    args = ap.parse_args()
    cfg = load_cfg(args.cfg)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frames = load_frames(args.info, args.data_root, args.max_frames)
    print(f'{len(frames)} frames, {sum(len(f["boxes"]) for f in frames)} cuboids')
    dump([{'sample': f['sample'], 'boxes': f['boxes']} for f in frames], out / 'gt_boxes.json')

    det_path = out / 'det_2d.json'
    if det_path.exists() and not args.redetect:
        dets = json.loads(det_path.read_text(encoding='utf-8'))
    else:
        from m44.detect import detect
        dets = detect(frames, args.weights, device=args.device)
        dump(dets, det_path)
    print(f'{len(dets)} YOLO detections')

    # 1) clean GT: false-alarm floor and reprojection error
    clean_proj = project_all(frames)
    clean_flags, clean_matches = check(clean_proj, dets, cfg)
    reproj = reprojection_stats(clean_matches)

    # 2) corrupted GT: corrupt only boxes the checker verifies cleanly when they are correct
    #    (matched to a detection, no flag on clean GT) – recall then measures error detection,
    #    not YOLO misses or occlusion, which the clean-GT false-alarm count reports separately.
    eligible = {m['box_id'] for m in clean_matches} - {f['box_id'] for f in clean_flags if f['box_id']}
    noisy, injected = inject(frames, eligible, args.rate, args.seed)
    noisy_proj = project_all(noisy)
    flags, _ = check(noisy_proj, dets, cfg)
    metrics = evaluate(flags, injected, clean_proj)
    caught = metrics.pop('_caught_per_error')
    for e, c in zip(injected, caught):
        e['caught'] = c

    dump([{'sample': f['sample'], 'boxes': f['boxes']} for f in noisy], out / 'noisy_boxes.json')
    dump(injected, out / 'injected_errors.json')
    dump(noisy_proj, out / 'proj_2d.json')
    dump(flags, out / 'flags.json')
    result = {'config': {**DEFAULT_CFG, **cfg}, 'clean_gt': {'flags': len(clean_flags), 'reprojection': reproj,
                                                   'eligible_boxes': len(eligible)},
              'injected_run': metrics}
    dump(result, out / 'metrics.json')

    summary = {
        'Số frame': len(frames),
        'Cuboid kiểm tra được (trên GT sạch)': len(eligible),
        'Cảnh báo trên GT sạch (báo động giả nền)': len(clean_flags),
        'Reprojection: IoU trung vị / sai lệch tâm trung vị (px)':
            f"{reproj.get('iou_median')} / {reproj.get('center_err_px_median')}",
        'Lỗi đã cài / tool bắt được': f"{metrics['injected']} / {metrics['caught']} (recall {metrics['recall']})",
        'Tổng cảnh báo trên dữ liệu có lỗi': metrics['flags_total'],
    }
    build_report(noisy, noisy_proj, dets, flags, out, summary)
    print(json.dumps(result, indent=1, ensure_ascii=False))
    print(f'report: {out / "index.html"}')


if __name__ == '__main__':
    main()
