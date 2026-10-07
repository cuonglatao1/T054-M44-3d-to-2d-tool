"""Score one pilot review: which injected errors did the reviewer fix, and which correct cuboids got damaged.

  python scripts/pilot_score.py --task-id 60 --name "Thuy" --set A --mode tay --minutes 20

Compares the task's current cuboids in CVAT with the original nuScenes cuboids:
  * an injected error counts as fixed when a cuboid of the right class again sits where the original one was
    (center <= 0.7 m, each side within 25 %, heading within 20 deg, ignoring a 180 deg flip);
  * a cuboid that was correct when the task was created counts as damaged when no such cuboid is left.
Matching is one-to-one (closest first). The answer key comes from out/cvat_tasks/task_<id>/answer_key.json.
Writes out/pilot/<name>_<set>_<mode>.json for scripts/pilot_report.py.
"""
import argparse
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from m44 import cvat_io  # noqa: E402
from m44.loader import load_frames_nusc  # noqa: E402

TOL_CENTER_M, TOL_SIZE, TOL_YAW_DEG = 0.7, 0.25, 20.0


def same_object(gt: dict, box: dict) -> float | None:
    """Distance if `box` reproduces `gt` within tolerance, else None."""
    if box['cls'] != gt['cls']:
        return None
    gc = np.asarray(gt['center']) + [0, 0, gt['size'][2] / 2]
    bc = np.asarray(box['center']) + [0, 0, box['size'][2] / 2]
    dist = float(np.linalg.norm(gc - bc))
    if dist > TOL_CENTER_M:
        return None
    if any(abs(b / g - 1) > TOL_SIZE for g, b in zip(gt['size'], box['size']) if g > 0):
        return None
    d_yaw = abs((box['yaw'] - gt['yaw'] + math.pi / 2) % math.pi - math.pi / 2)  # 180 deg flip allowed
    if gt['cls'] not in ('pedestrian', 'traffic_cone') and math.degrees(d_yaw) > TOL_YAW_DEG:
        return None  # heading of round-ish objects is not meaningful
    return dist


def match(gt_boxes: list[dict], final_boxes: list[dict]) -> set[str]:
    """Original box ids that still have a matching final cuboid (greedy one-to-one, closest first)."""
    pairs = []
    for g in gt_boxes:
        for j, b in enumerate(final_boxes):
            d = same_object(g, b)
            if d is not None:
                pairs.append((d, g['box_id'], j))
    used_g, used_b = set(), set()
    for d, gid, j in sorted(pairs):
        if gid not in used_g and j not in used_b:
            used_g.add(gid)
            used_b.add(j)
    return used_g


def score(task, base: dict[str, dict], key: dict) -> dict:
    frames, _ = cvat_io.read_frames(task, base)
    injected = {(e['sample'], e['box_id']): e for e in key['injected']}
    result = {'fixed_by_type': Counter(), 'total_by_type': Counter(), 'damaged': 0, 'correct_at_start': 0,
              'final_cuboids': sum(len(f['boxes']) for f in frames)}
    for f in frames:
        gt = base[f['sample']]['boxes']
        ok = match(gt, f['boxes'])
        for g in gt:
            e = injected.get((f['sample'], g['box_id']))
            if e:
                result['total_by_type'][e['type']] += 1
                result['fixed_by_type'][e['type']] += g['box_id'] in ok
            else:
                result['correct_at_start'] += 1
                result['damaged'] += g['box_id'] not in ok
    fixed, total = sum(result['fixed_by_type'].values()), sum(result['total_by_type'].values())
    result.update(fixed=fixed, injected=total, fixed_rate=round(fixed / total, 3) if total else None,
                  fixed_by_type=dict(result['fixed_by_type']), total_by_type=dict(result['total_by_type']))
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task-id', type=int, required=True)
    ap.add_argument('--name', required=True, help='reviewer name')
    ap.add_argument('--set', required=True, choices=['A', 'B'])
    ap.add_argument('--mode', required=True, choices=['tay', 'tool'])
    ap.add_argument('--minutes', type=float, required=True, help='time spent reviewing')
    ap.add_argument('--answer-key', help='default out/cvat_tasks/task_<id>/answer_key.json')
    ap.add_argument('--nusc-root', default=None)
    args = ap.parse_args()

    cvat_io.load_env(ROOT / '.cvat.env')
    key_path = Path(args.answer_key or ROOT / 'out' / 'cvat_tasks' / f'task_{args.task_id}' / 'answer_key.json')
    if not key_path.exists():
        raise SystemExit(f'Không thấy đáp án {key_path} – task phải tạo bằng pilot_setup.bat trên máy này.')
    key = json.loads(key_path.read_text(encoding='utf-8'))
    nusc_root = args.nusc_root or os.environ.get('NUSC_ROOT', str(ROOT / 'data' / 'nuscenes'))

    with cvat_io.connect() as client:
        task = client.tasks.retrieve(args.task_id)
        tokens = set(cvat_io.task_samples(task))
        base = {f['sample']: f for f in load_frames_nusc(nusc_root, 'all', samples=tokens)}
        r = score(task, base, key)

    r.update(name=args.name, set=args.set, mode=args.mode, minutes=args.minutes, task_id=args.task_id,
             scored_at=datetime.now().isoformat(timespec='seconds'))
    out = ROOT / 'out' / 'pilot'
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{args.name.replace(' ', '_')}_{args.set}_{args.mode}.json"
    path.write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f"{args.name} – bộ {args.set} – {args.mode}: sửa được {r['fixed']}/{r['injected']} lỗi "
          f"trong {args.minutes:g} phút; làm hỏng {r['damaged']}/{r['correct_at_start']} cuboid đúng.")
    print(f'Kết quả: {path}  → gửi file này cho tech lead.')


if __name__ == '__main__':
    main()
