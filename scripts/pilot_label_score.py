"""Pilot part 2: score cuboids a reviewer labelled from scratch, before and after fixing them with M44 Check.

  python scripts/pilot_label_score.py --task-id 61 --name Thuy --stage truoc --minutes 25
  ... bấm M44 Check, sửa theo danh sách, Save ...
  python scripts/pilot_label_score.py --task-id 61 --name Thuy --stage sau --minutes 8

Target objects = original nuScenes cars and pedestrians at least 60 % visible within 30 m of the ego car.
Each labelled car / pedestrian cuboid is
  * correct – same object within the pilot tolerance (center 0.7 m, sides 25 %, heading 20 deg; see pilot_score),
  * rough   – right class within 2 m of an object but not within tolerance (badly fitted),
  * wrong   – no object of that class nearby (ghost box / wrong class).
At stage "sau" the M44 flags (out/cvat_check_<task>/flags.json) are compared with the "truoc" snapshot:
how many flagged cuboids were really not correct (tool precision on real labels) and how many of the
not-correct cuboids the tool flagged (tool recall on real labels).
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from m44 import cvat_io  # noqa: E402
from m44.loader import load_frames_nusc  # noqa: E402
from pilot_score import same_object  # noqa: E402

CLASSES = ('car', 'pedestrian')
TARGET_RANGE_M, ROUGH_M = 30.0, 2.0


def gravity(b):
    return np.asarray(b['center']) + [0, 0, b['size'][2] / 2]


def grade(gt_boxes: list[dict], boxes: list[dict]) -> tuple[dict, dict]:
    """Per labelled box status + per target object status, one-to-one (closest first)."""
    gt = [g for g in gt_boxes if g['cls'] in CLASSES]
    targets = {g['box_id'] for g in gt if (g.get('visibility') or 0) >= 3
               and np.hypot(*g['center'][:2]) <= TARGET_RANGE_M}
    mine = [b for b in boxes if b['cls'] in CLASSES]

    status, matched_gt = {}, {}
    for level in ('correct', 'rough'):
        pairs = []
        for b in mine:
            if b['box_id'] in status:
                continue
            for g in gt:
                if g['box_id'] in matched_gt:
                    continue
                if level == 'correct':
                    d = same_object(g, b)
                else:
                    d = float(np.linalg.norm(gravity(g) - gravity(b))) if g['cls'] == b['cls'] else None
                    d = d if d is not None and d <= ROUGH_M else None
                if d is not None:
                    pairs.append((d, b['box_id'], g['box_id']))
        for d, bid, gid in sorted(pairs):
            if bid not in status and gid not in matched_gt:
                status[bid], matched_gt[gid] = level, level
    for b in mine:
        status.setdefault(b['box_id'], 'wrong')
    target_status = {gid: matched_gt.get(gid, 'missed') for gid in targets}
    return status, target_status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task-id', type=int, required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--stage', required=True, choices=['truoc', 'sau'])
    ap.add_argument('--minutes', type=float, required=True)
    ap.add_argument('--nusc-root', default=None)
    args = ap.parse_args()

    cvat_io.load_env(ROOT / '.cvat.env')
    nusc_root = args.nusc_root or os.environ.get('NUSC_ROOT', str(ROOT / 'data' / 'nuscenes'))
    with cvat_io.connect() as client:
        task = client.tasks.retrieve(args.task_id)
        tokens = set(cvat_io.task_samples(task))
        base = {f['sample']: f for f in load_frames_nusc(nusc_root, 'all', samples=tokens)}
        frames, _ = cvat_io.read_frames(task, base)

    status, target_status = {}, {}
    for f in frames:
        s, t = grade(base[f['sample']]['boxes'], f['boxes'])
        status.update(s)
        target_status.update(t)
    count = lambda d, v: sum(x == v for x in d.values())  # noqa: E731
    r = {'name': args.name, 'stage': args.stage, 'minutes': args.minutes, 'task_id': args.task_id,
         'targets': len(target_status), 'target_correct': count(target_status, 'correct'),
         'target_rough': count(target_status, 'rough'), 'target_missed': count(target_status, 'missed'),
         'labelled': len(status), 'correct': count(status, 'correct'), 'rough': count(status, 'rough'),
         'wrong': count(status, 'wrong'), 'box_status': status,
         'scored_at': datetime.now().isoformat(timespec='seconds')}

    out = ROOT / 'out' / 'pilot'
    out.mkdir(parents=True, exist_ok=True)
    stem = f"{args.name.replace(' ', '_')}_label"
    if args.stage == 'sau':
        before = out / f'{stem}_truoc.json'
        flags_path = ROOT / 'out' / f'cvat_check_{args.task_id}' / 'flags.json'
        if before.exists() and flags_path.exists():
            prev = json.loads(before.read_text(encoding='utf-8'))['box_status']
            flagged = {f['box_id'] for f in json.loads(flags_path.read_text(encoding='utf-8')) if f['box_id']}
            flagged &= set(prev)  # cuboids that existed (and were car/pedestrian) at stage "truoc"
            bad = {b for b, s in prev.items() if s != 'correct'}
            r['tool'] = {'flagged': len(flagged), 'flagged_really_bad': len(flagged & bad),
                         'bad_before': len(bad), 'bad_flagged': len(bad & flagged)}
        else:
            r['tool'] = None
            print('(Chưa có kết quả chấm "truoc" hoặc chưa bấm M44 Check – bỏ qua phần đánh giá tool.)')

    (out / f'{stem}_{args.stage}.json').write_text(json.dumps(r, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f"{args.name} – gán nhãn – {args.stage}: {r['target_correct']}/{r['targets']} vật gán đúng, "
          f"{r['target_rough']} gán lệch, {r['target_missed']} bỏ sót; {r['wrong']} cuboid sai/thừa "
          f"(trên {r['labelled']} cuboid car/pedestrian).")
    if r.get('tool'):
        t = r['tool']
        print(f"  Tool: gắn cờ {t['flagged']} cuboid, {t['flagged_really_bad']} cái thực sự chưa đúng; "
              f"bắt được {t['bad_flagged']}/{t['bad_before']} cuboid chưa đúng.")
    print(f'Kết quả: {out / (stem + "_" + args.stage + ".json")}  → gửi file này cho tech lead.')


if __name__ == '__main__':
    main()
