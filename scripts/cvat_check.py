"""Check the cuboids currently in a CVAT 3D task and write the result back.

  python scripts/cvat_check.py --task-id 51

1. reads the task's cuboids from CVAT (whatever annotators drew / edited)
2. checks them against the nuScenes camera images (frames are named <index>_<sample token>)
3. sets the `qc` attribute of every cuboid: OK or the flag type -> reviewers filter on `qc` in CVAT
4. writes an HTML report whose "Mở trong CVAT" links open the right job and frame

--answer-key (from cvat_create_task.py --labels noisy) also scores the tool against the injected errors.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from check import TUNED_CFG, run_check  # noqa: E402
from m44 import cvat_io  # noqa: E402
from m44.evaluate import evaluate  # noqa: E402
from m44.geometry import project_frame  # noqa: E402
from m44.loader import load_frames_nusc  # noqa: E402
from m44.match import load_cfg  # noqa: E402


def score_against_key(frames, flags, base, key_path):
    """Map CVAT cuboids back to the uploaded boxes (same sample, same center) and reuse evaluate()."""
    key = json.loads(Path(key_path).read_text(encoding='utf-8'))
    uploaded = {}
    for u in key['uploaded']:
        uploaded.setdefault(u['sample'], []).append(u)
    to_orig = {}
    for f in frames:
        for b in f['boxes']:
            cands = [u for u in uploaded.get(f['sample'], [])
                     if max(abs(x - y) for x, y in zip(u['center'], b['center'])) < 1e-3]
            if cands:
                to_orig[b['box_id']] = cands[0]['box_id']  # unchanged since upload
    mapped = [{**fl, 'box_id': to_orig.get(fl['box_id'], fl['box_id'])} for fl in flags]
    clean_proj = [p for f in base.values() for p in project_frame(f)]
    return evaluate(mapped, key['injected'], clean_proj)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--task-id', type=int, required=True)
    ap.add_argument('--nusc-root', default=None, help='nuScenes folder (default: env NUSC_ROOT or data/nuscenes)')
    ap.add_argument('--version', default='v1.0-mini')
    ap.add_argument('--out', help='default out/cvat_check_<task id>')
    ap.add_argument('--cfg', default=str(TUNED_CFG))
    ap.add_argument('--dry-run', action='store_true', help='do not write qc attributes to CVAT')
    ap.add_argument('--answer-key', help='answer_key.json from cvat_create_task.py --labels noisy')
    ap.add_argument('--device', default='auto')
    args = ap.parse_args()

    cvat_io.load_env(ROOT / '.cvat.env')
    nusc_root = args.nusc_root or os.environ.get('NUSC_ROOT', 'data/nuscenes')
    out = Path(args.out or f'out/cvat_check_{args.task_id}')
    cfg = {} if args.cfg == 'default' else load_cfg(args.cfg)

    with cvat_io.connect() as client:
        task = client.tasks.retrieve(args.task_id)
        tokens = {cvat_io.sample_of(fr.name) for fr in task.get_frames_info()}
        base = {f['sample']: f for f in load_frames_nusc(nusc_root, 'all', args.version, samples=tokens)}
        frames, shapes = cvat_io.read_frames(task, base)
        print(f'task {task.id} "{task.name}": {len(frames)} frames, {len(shapes)} cuboids')

        flags = run_check(frames, out, cfg, device=args.device, title=f'M44 – CVAT task {task.id}: {task.name}',
                          links_fn=lambda fl: cvat_io.frame_links(task, fl, frames))
        flagged = len({f['box_id'] for f in flags if f['box_id']})
        print(f'{len(flags)} flags on {flagged} cuboids -> {out / "index.html"}')

        if not args.dry_run:
            n = cvat_io.write_qc(task, shapes, flags)
            print(f'qc attribute written: {n} cuboids flagged, {len(shapes) - n} OK')

    if args.answer_key:
        m = score_against_key(frames, flags, base, args.answer_key)
        print(f"answer key: caught {m['caught']}/{m['injected']} injected errors ({m['recall']:.0%}); "
              f"{m['flags_unexplained']} other flags")
        (out / 'score.json').write_text(json.dumps(m, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
