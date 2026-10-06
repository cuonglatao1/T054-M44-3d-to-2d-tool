#!/bin/bash
# Generate mmdet3d info .pkl files for nuScenes-mini (run once after extracting v1.0-mini to D:\data\nuscenes).
set -euo pipefail
ROOT=${1:-/mnt/d/data/nuscenes}
source /opt/m3d/bin/activate
# nuscenes-devkit pulls a newer opencv/numpy unless pinned
pip install -q nuscenes-devkit "numpy<2" "opencv-python==4.10.0.84"
cd /root/work/mmdetection3d
# mmdet3d 1.4 update_infos_to_v2 hard-codes ./data/nuscenes as the devkit dataroot
mkdir -p data && ln -sfn "$ROOT" data/nuscenes
PYTHONPATH=. python tools/create_data.py nuscenes --root-path "$ROOT" --out-dir "$ROOT" \
  --extra-tag nuscenes --version v1.0-mini
ls -la "$ROOT"/nuscenes_infos_*.pkl
