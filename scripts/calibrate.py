"""Analyse clean-GT behaviour to set thresholds from data instead of guessing.

On correct labels, every flag is a false alarm. This prints where they come from and proposes a
per-class LOW_IOU threshold = the q-th percentile of IoU between projected cuboids and their
matched detections on clean GT (so ~q of correct boxes would be flagged).

  python scripts/calibrate.py --split train --dets out/mini_train/det_2d.json
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from m44.geometry import project_frame  # noqa: E402
from m44.loader import add_data_args, frames_from_args  # noqa: E402
from m44.match import check  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    add_data_args(ap)
    ap.add_argument('--dets', required=True)
    ap.add_argument('--q', type=float, default=2.0, help='percentile for the proposed LOW_IOU threshold')
    ap.add_argument('--size-q', type=float, default=1.0, help='size bounds = [q, 100-q] percentiles')
    ap.add_argument('--write', help='write {"offset_iou", "size_bounds"} to this JSON for --cfg')
    args = ap.parse_args()

    frames = frames_from_args(args)
    dets = json.loads(Path(args.dets).read_text(encoding='utf-8'))
    proj = [p for f in frames for p in project_frame(f)]
    flags, matches = check(proj, dets)
    cls_of = {p['box_id']: p['cls'] for p in proj}
    depth_of = {(p['cam'], p['box_id']): p['depth'] for p in proj}

    n_frames = len(frames)
    print(f'{n_frames} frames, {len(dets)} detections, {len(matches)} matched pairs, {len(flags)} clean-GT flags '
          f'({len(flags) / n_frames:.2f}/frame)')
    print('flags by type:', dict(Counter(f['type'] for f in flags)))
    for t in ['LOW_IOU', 'NO_2D_MATCH', 'CLASS_MISMATCH']:
        sub = [f for f in flags if f['type'] == t]
        if sub:
            print(f'  {t} by class:', dict(Counter(f['cls_3d'] for f in sub).most_common()))
    sub = [f for f in flags if f['type'] == 'CLASS_MISMATCH']
    if sub:
        print('  CLASS_MISMATCH pairs (3d -> 2d):', dict(Counter((f['cls_3d'], f['cls_2d']) for f in sub).most_common(8)))
    sub = [f for f in flags if f['type'] == 'NO_2D_MATCH']
    if sub:
        d = np.array([depth_of[(f['cam'], f['box_id'])] for f in sub])
        print(f'  NO_2D_MATCH depth: median {np.median(d):.1f} m, share > 30 m: {np.mean(d > 30):.0%}')
    sub = [f for f in flags if f['type'] == 'MISSING_3D']
    if sub:
        print('  MISSING_3D by detected class:', dict(Counter(f['cls_2d'] for f in sub).most_common()))

    # NO_2D_MATCH rate among checked cuboids, by projected height: where does YOLO stop seeing objects?
    heights = {(m['cam'], m['box_id']): m['p_bbox'][3] - m['p_bbox'][1] for m in matches}
    nomatch = {(f['cam'], f['box_id']): f['p_bbox'][3] - f['p_bbox'][1] for f in flags if f['type'] == 'NO_2D_MATCH'}
    bins = [25, 40, 60, 80, 120, 10_000]
    print('\nNO_2D_MATCH rate by projected height (px):')
    for lo, hi in zip(bins, bins[1:]):
        n_ok = sum(lo <= h < hi for h in heights.values())
        n_bad = sum(lo <= h < hi for h in nomatch.values())
        if n_ok + n_bad:
            print(f'  {lo:>4}-{hi:<6} checked={n_ok + n_bad:<5} no_match={n_bad / (n_ok + n_bad):.1%}')

    miss = [f for f in flags if f['type'] == 'MISSING_3D']
    if miss:
        print('\nMISSING_3D by detection score / height:')
        for lo, hi in [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]:
            sub = [f for f in miss if lo <= f['score'] < hi]
            print(f'  score {lo:.1f}-{hi:.1f}: {len(sub):<4} height>=60px: {sum(f["det_bbox"][3] - f["det_bbox"][1] >= 60 for f in sub)}')

    print(f'\nIoU of matched pairs on clean GT (proposed LOW_IOU threshold = p{args.q:g}):')
    by_cls = defaultdict(list)
    for m in matches:
        by_cls[cls_of[m['box_id']]].append(m['iou'])
    proposal = {}
    for c, v in sorted(by_cls.items(), key=lambda kv: -len(kv[1])):
        v = np.array(v)
        proposal[c] = round(float(np.percentile(v, args.q)), 2)
        print(f'  {c:<20} n={len(v):<5} median={np.median(v):.2f}  p5={np.percentile(v, 5):.2f}  '
              f'p{args.q:g}={proposal[c]:.2f}  share<0.5={np.mean(v < 0.5):.1%}')
    print('\nproposed offset_iou:', json.dumps(proposal))

    # log size ratios projected/detected; width skipped when either box touches the image border
    print('\nlog(h_proj/h_det) and log(w_proj/w_det) on clean GT [p1, p2, p50, p98, p99]:')
    ratios = defaultdict(lambda: ([], []))
    for m in matches:
        p, d = m['p_bbox'], m['d_bbox']
        rh, rw = ratios[cls_of[m['box_id']]]
        rh.append(np.log((p[3] - p[1]) / (d[3] - d[1])))
        if min(p[0], d[0]) > 2 and max(p[2], d[2]) < 1598:
            rw.append(np.log((p[2] - p[0]) / (d[2] - d[0])))
    size_bounds = {}
    for c, (rh, rw) in sorted(ratios.items(), key=lambda kv: -len(kv[1][0])):
        if len(rh) < 20:  # too few pairs to estimate a tail
            continue
        ph = np.percentile(rh, [1, 2, 50, 98, 99]).round(2)
        pw = np.percentile(rw, [1, 2, 50, 98, 99]).round(2) if len(rw) >= 20 else '-'
        print(f'  {c:<20} h: {ph}   w: {pw}')
        lo, hi = args.size_q, 100 - args.size_q
        size_bounds[c] = {'h': np.percentile(rh, [lo, hi]).round(3).tolist()}
        if len(rw) >= 20:
            size_bounds[c]['w'] = np.percentile(rw, [lo, hi]).round(3).tolist()

    if args.write:
        Path(args.write).write_text(json.dumps({'offset_iou': proposal, 'size_bounds': size_bounds}, indent=1),
                                    encoding='utf-8')
        print(f'\nwrote {args.write}')


if __name__ == '__main__':
    main()
