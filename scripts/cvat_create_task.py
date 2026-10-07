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


def main():
    ap = argparse.ArgumentParser()
    add_data_args(ap)
    ap.add_argument('--name', default='M44 nuScenes')
    ap.add_argument('--labels', default='gt', choices=['gt', 'noisy', 'none'])
    ap.add_argument('--rate', type=float, default=0.15, help='share of eligible cuboids corrupted (noisy)')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--project-id', type=int, help='create inside a CVAT project (uses its labels)')
    ap.add_argument('--out', default='out/cvat_tasks')
    args = ap.parse_args()

    cvat_io.load_env(ROOT / '.cvat.env')
    frames = frames_from_args(args)
    work = Path(args.out)
    work.mkdir(parents=True, exist_ok=True)

    print(f'{len(frames)} frames -> building upload archive...')
    zip_path = cvat_io.build_task_zip(frames, work)
    print(f'{zip_path} ({zip_path.stat().st_size / 1e6:.1f} MB), creating task...')
    with cvat_io.connect() as client:
        task = cvat_io.create_task(client, args.name, zip_path, args.project_id)
        task_dir = work / f'task_{task.id}'
        task_dir.mkdir(exist_ok=True)
        zip_path.unlink()

        boxes_to_upload = frames
        if args.labels == 'noisy':
            # corrupt boxes a reviewer could check against the cameras: verifiable class, mostly visible
            eligible = {b['box_id'] for f in frames for b in f['boxes']
                        if b['cls'] in COMPATIBLE and (b.get('visibility') or 4) >= 3}
            boxes_to_upload, injected = inject(frames, eligible, args.rate, args.seed)
            key = {'task_id': task.id, 'rate': args.rate, 'seed': args.seed, 'injected': injected,
                   'uploaded': [{'sample': f['sample'], 'box_id': b['box_id'], 'center': b['center']}
                                for f in boxes_to_upload for b in f['boxes']]}
            (task_dir / 'answer_key.json').write_text(json.dumps(key, indent=1), encoding='utf-8')
            print(f'injected {len(injected)} errors -> {task_dir / "answer_key.json"} (do not share with reviewers)')
        if args.labels != 'none':
            n = cvat_io.upload_boxes(task, boxes_to_upload)
            print(f'uploaded {n} cuboids')

        url = f"{os.environ.get('CVAT_URL', 'http://localhost:8080').rstrip('/')}/tasks/{task.id}"
        (task_dir / 'task.json').write_text(json.dumps(
            {'task_id': task.id, 'name': args.name, 'labels': args.labels, 'url': url,
             'samples': [f['sample'] for f in frames]}, indent=1), encoding='utf-8')
        print(f'task {task.id}: {url}')


if __name__ == '__main__':
    main()
