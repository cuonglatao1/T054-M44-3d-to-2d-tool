"""Aggregate recall over many random error injections (uses the cached det_2d.json of a run_all output).

Use this when tuning match.py: one injection is too few errors to compare settings.
  python scripts/eval_seeds.py --info … --data-root … --dets out/mini_train/det_2d.json --seeds 10 \
      --cfg configs/tuned.json
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from m44.evaluate import evaluate  # noqa: E402
from m44.geometry import project_frame  # noqa: E402
from m44.inject import inject  # noqa: E402
from m44.loader import load_frames  # noqa: E402
from m44.match import check, load_cfg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--info', required=True)
    ap.add_argument('--data-root', required=True)
    ap.add_argument('--dets', required=True)
    ap.add_argument('--cfg', help='JSON file or inline JSON overriding match.DEFAULT_CFG')
    ap.add_argument('--max-frames', type=int)
    ap.add_argument('--seeds', type=int, default=10)
    ap.add_argument('--rate', type=float, default=0.3)
    args = ap.parse_args()

    cfg = load_cfg(args.cfg)
    frames = load_frames(args.info, args.data_root, args.max_frames)
    dets = json.loads(Path(args.dets).read_text(encoding='utf-8'))
    clean_proj = [p for f in frames for p in project_frame(f)]
    clean_flags, clean_matches = check(clean_proj, dets, cfg)
    eligible = {m['box_id'] for m in clean_matches} - {f['box_id'] for f in clean_flags if f['box_id']}

    by_type = defaultdict(lambda: [0, 0])
    for seed in range(args.seeds):
        noisy, injected = inject(frames, eligible, args.rate, seed)
        flags, _ = check([p for f in noisy for p in project_frame(f)], dets, cfg)
        m = evaluate(flags, injected, clean_proj)
        for t, r in m['recall_by_type'].items():
            by_type[t][0] += r['caught']
            by_type[t][1] += r['total']

    caught = sum(c for c, _ in by_type.values())
    total = sum(n for _, n in by_type.values())
    n = len(frames)
    print(f'cfg: {json.dumps(cfg)}')
    print(f'clean-GT flags (false alarms): {len(clean_flags)} = {len(clean_flags) / n:.2f}/frame '
          f'{dict(Counter(f["type"] for f in clean_flags))}')
    print(f'eligible boxes: {len(eligible)} ({len(eligible) / n:.1f}/frame) | seeds: {args.seeds} | '
          f'injected errors: {total}')
    print(f'overall recall: {caught}/{total} = {caught / total:.1%}  |  ' +
          '  '.join(f'{t} {c / k:.0%}' for t, (c, k) in sorted(by_type.items())))


if __name__ == '__main__':
    main()
