"""Load frames (6 cameras + calibration + 3D boxes) from an mmdet3d nuScenes info .pkl.

The same format is produced for nuScenes-mini by mmdet3d `tools/create_data.py nuscenes`,
so the demo frame and the full dataset go through one code path.
"""
import pickle
from pathlib import Path

import numpy as np


def _resolve(data_root: Path, rel: str, cam: str) -> str:
    for cand in (data_root / rel, data_root / 'samples' / cam / rel, data_root / Path(rel).name):
        if cand.exists():
            return str(cand)
    raise FileNotFoundError(f'image not found for {cam}: {rel} (data_root={data_root})')


def _nusc_meta(data_root: Path, version: str):
    """Per-sample annotation visibility levels (1–4) and night flag from the nuScenes tables, if present."""
    if not (data_root / version).exists():
        return None
    from nuscenes.nuscenes import NuScenes

    nusc = NuScenes(version=version, dataroot=str(data_root), verbose=False)

    def meta(sample_token):
        sample = nusc.get('sample', sample_token)
        scene = nusc.get('scene', sample['scene_token'])
        vis = [int(nusc.get('sample_annotation', a)['visibility_token']) for a in sample['anns']]
        return vis, 'night' in scene['description'].lower()
    return meta


def load_frames(info_path: str, data_root: str, max_frames: int | None = None) -> list[dict]:
    with open(info_path, 'rb') as f:
        info = pickle.load(f)
    id2cls = {v: k for k, v in info['metainfo']['categories'].items()}
    root = Path(data_root)
    meta = _nusc_meta(root, info['metainfo'].get('version', 'v1.0-mini'))

    frames = []
    for s in info['data_list'][:max_frames]:
        # infos keep sample['anns'] order, so instance i <-> annotation i
        vis, night = meta(s['token']) if meta else (None, None)
        if vis is not None and len(vis) != len(s['instances']):
            vis = None
        cams = {
            name: {
                'img_path': _resolve(root, c['img_path'], name),
                'cam2img': np.asarray(c['cam2img'], dtype=float)[:3, :3].tolist(),
                'lidar2cam': np.asarray(c['lidar2cam'], dtype=float).tolist(),
            }
            for name, c in s['images'].items()
        }
        boxes = []
        for i, inst in enumerate(s['instances']):
            label = inst['bbox_label_3d']
            if label < 0:  # ignored category in nuScenes infos
                continue
            # infos store the gravity center; we keep the bottom-center (mmdet3d LiDAR box convention)
            x, y, z, l, w, h, yaw = inst['bbox_3d'][:7]
            boxes.append({
                'box_id': f"{s['token'][:8]}_{i:03d}",
                'cls': id2cls[label],
                'center': [x, y, z - h / 2],  # LiDAR frame, bottom-center
                'size': [l, w, h],
                'yaw': yaw,
                'num_lidar_pts': int(inst.get('num_lidar_pts', -1)),
                'visibility': vis[i] if vis else None,  # nuScenes: 1=0-40%, 2=40-60%, 3=60-80%, 4=80-100%
            })
        frames.append({'sample': s['token'], 'night': night, 'cams': cams, 'boxes': boxes})
    return frames
