"""Compare several match configs in one process (data and detections loaded once).

  python scripts/sweep.py --info …train.pkl --data-root … --dets out/mini_train/det_2d.json --configs configs/sweep.json
configs/sweep.json: {"name": {cfg overrides} or "path/to/cfg.json", …}
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


def run(frames, dets, clean_proj, noisy_sets, cfg):
    clean_flags, clean_matches = check(clean_proj, dets, cfg)
    eligible = {m['box_id'] for m in clean_matches} - {f['box_id'] for f in clean_flags if f['box_id']}
    by_type = defaultdict(lambda: [0, 0])
    for seed, (noisy_frames_fn) in enumerate(noisy_sets):
        noisy, injected = noisy_frames_fn(eligible)
        flags, _ = check([p for f in noisy for p in project_frame(f)], dets, cfg)
        for t, r in evaluate(flags, injected, clean_proj)['recall_by_type'].items():
            by_type[t][0] += r['caught']
            by_type[t][1] += r['total']
    caught, total = sum(c for c, _ in by_type.values()), sum(n for _, n in by_type.values())
    return {
        'fa_per_frame': len(clean_flags) / len(frames),
        'fa_by_type': dict(Counter(f['type'] for f in clean_flags)),
        'eligible_per_frame': len(eligible) / len(frames),
        'recall': caught / total if total else 0.0,
        'recall_by_type': {t: c / n for t, (c, n) in sorted(by_type.items())},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--info', required=True)
    ap.add_argument('--data-root', required=True)
    ap.add_argument('--dets', required=True)
    ap.add_argument('--configs', required=True)
    ap.add_argument('--seeds', type=int, default=5)
    ap.add_argument('--rate', type=float, default=0.3)
    args = ap.parse_args()

    frames = load_frames(args.info, args.data_root)
    dets = json.loads(Path(args.dets).read_text(encoding='utf-8'))
    clean_proj = [p for f in frames for p in project_frame(f)]
    noisy_sets = [lambda elig, s=s: inject(frames, elig, args.rate, s) for s in range(args.seeds)]
    configs = json.loads(Path(args.configs).read_text(encoding='utf-8'))

    print(f'{"config":<14}{"FA/frame":>9}{"checked/frame":>15}{"recall":>8}   per type')
    results = {}
    for name, cfg in configs.items():
        # a value is either inline overrides or a path to a config file
        cfg = load_cfg(cfg if isinstance(cfg, str) else json.dumps(cfg))
        r = results[name] = run(frames, dets, clean_proj, noisy_sets, cfg)
        print(f'{name:<14}{r["fa_per_frame"]:>9.2f}{r["eligible_per_frame"]:>15.1f}{r["recall"]:>8.1%}   ' +
              ' '.join(f'{t}={v:.0%}' for t, v in r['recall_by_type'].items()) +
              f'   FA: {r["fa_by_type"]}')
    out = Path(args.dets).with_name('sweep_results.json')
    out.write_text(json.dumps({'configs': configs, 'results': results}, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
