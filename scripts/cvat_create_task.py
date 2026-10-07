"""Create a CVAT 3D task (LiDAR point cloud + 6 camera images per frame) from nuScenes frames.

  python scripts/cvat_create_task.py --split val --max-frames 10 --name "M44 pilot" --labels noisy

--labels gt     original nuScenes cuboids
--labels noisy  cuboids with injected errors; the answer key goes to <out>/answer_key.json (keep it from reviewers)
--labels none   empty task for annotators to label from scratch
Credentials: .cvat.env in the repo root (see .cvat.env.example).
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from m44 import cvat_io  # noqa: E402
from m44.inject import inject  # noqa: E402
from m44.loader import add_data_args, frames_from_args  # noqa: E402
from m44.match import COMPATIBLE  # noqa: E402


def create_nusc_task(frames: list[dict], name: str, labels: str = 'gt', rate: float = 0.15, seed: int = 0,
                     project_id: int | None = None, out: str | Path = ROOT / 'out' / 'cvat_tasks',
                     log=print) -> dict:
    """Create one CVAT task from loader frames (also used by scripts/m44_server.py). Returns task info."""
    cvat_io.load_env(ROOT / '.cvat.env')
    work = Path(out)
    work.mkdir(parents=True, exist_ok=True)

    log(f'{len(frames)} frames -> building upload archive...')
    zip_path = cvat_io.build_task_zip(frames, work)
    log(f'{zip_path.name} ({zip_path.stat().st_size / 1e6:.1f} MB), creating task "{name}"...')
    with cvat_io.connect() as client:
        task = cvat_io.create_task(client, name, zip_path, project_id)
        task_dir = work / f'task_{task.id}'
        task_dir.mkdir(exist_ok=True)
        zip_path.unlink()

        boxes_to_upload, injected = frames, None
        if labels == 'noisy':
            # corrupt boxes a reviewer could check against the cameras: verifiable class, mostly visible
            eligible = {b['box_id'] for f in frames for b in f['boxes']
                        if b['cls'] in COMPATIBLE and (b.get('visibility') or 4) >= 3}
            boxes_to_upload, injected = inject(frames, eligible, rate, seed)
            key = {'task_id': task.id, 'rate': rate, 'seed': seed, 'injected': injected,
                   'uploaded': [{'sample': f['sample'], 'box_id': b['box_id'], 'center': b['center']}
                                for f in boxes_to_upload for b in f['boxes']]}
            (task_dir / 'answer_key.json').write_text(json.dumps(key, indent=1), encoding='utf-8')
            log(f'injected {len(injected)} errors -> {task_dir / "answer_key.json"} (do not share with reviewers)')
        if labels != 'none':
            n = cvat_io.upload_boxes(task, boxes_to_upload)
            log(f'uploaded {n} cuboids')

        url = f"{os.environ.get('CVAT_URL', 'http://localhost:8080').rstrip('/')}/tasks/{task.id}"
        info = {'task_id': task.id, 'name': name, 'labels': labels, 'url': url,
                'samples': [f['sample'] for f in frames]}
        (task_dir / 'task.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
        log(f'task {task.id}: {url}')
    return {**info, 'injected': len(injected) if injected is not None else None}


def main():
    ap = argparse.ArgumentParser()
    add_data_args(ap)
    ap.add_argument('--name', default='M44 nuScenes')
    ap.add_argument('--labels', default='gt', choices=['gt', 'noisy', 'none'])
    ap.add_argument('--rate', type=float, default=0.15, help='share of eligible cuboids corrupted (noisy)')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--project-id', type=int, help='create inside a CVAT project (uses its labels)')
    ap.add_argument('--out', default=str(ROOT / 'out' / 'cvat_tasks'))
    args = ap.parse_args()

    create_nusc_task(frames_from_args(args), args.name, args.labels, args.rate, args.seed, args.project_id,
                     args.out)


if __name__ == '__main__':
    main()
