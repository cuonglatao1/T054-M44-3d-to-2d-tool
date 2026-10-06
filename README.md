# M44 – 2D–3D Consistency Checker

Tool tự kiểm tra nhãn cuboid 3D (nuScenes) bằng camera: chiếu từng cuboid lên 6 camera, so với vật thể YOLO
phát hiện trên ảnh, rồi báo các chỗ không nhất quán để reviewer xem nhanh thay vì mở từng camera đối chiếu bằng tay.

| Cảnh báo | Ý nghĩa |
|---|---|
| `LOW_IOU` | Cuboid lệch vị trí / sai kích thước so với vật thể trên ảnh |
| `CLASS_MISMATCH` | Class của cuboid khác class vật thể trên ảnh |
| `SIZE_MISMATCH` | Chiều cao / chiều rộng cuboid không khớp vật thể (sai kích thước hoặc sai hướng) |
| `NO_2D_MATCH` | Cuboid không khớp vật thể nào trên ảnh (lệch xa, sai hẳn, hoặc bị che khuất) |
| `MISSING_3D` | Vật thể thấy rõ trên ảnh nhưng chưa có cuboid |

**Chạy nhanh:** bấm đúp `run_demo.bat` → báo cáo tự mở trong trình duyệt.
Kịch bản demo 5 phút: [docs/demo.md](docs/demo.md).

## Pipeline

```
info .pkl ─► loader ─► gt_boxes ─► inject (cài lỗi có đáp án) ─► noisy_boxes + injected_errors
                                                                     │
                                         projection ─► proj_2d ──────┤
6 ảnh camera ─► YOLO ─► det_2d ──────────────────────────────► match ─► flags ─► evaluate (recall)
                                                                              └► report (HTML + CSV)
```

Mỗi lần chạy kiểm tra **hai lần**: trên GT sạch (đo báo động giả nền + reprojection error) và trên GT đã cài lỗi
(đo tool bắt được bao nhiêu lỗi). Định dạng các file JSON: [docs/json-formats.md](docs/json-formats.md).

## Môi trường

Chạy trong WSL distro `mmdet3d` (nằm ở `D:\WSL\mmdet3d`, venv `/opt/m3d`):

```bash
wsl -d mmdet3d
source /opt/m3d/bin/activate
cd /mnt/d/m44-consistency-checker
```

Cài mới trên máy khác: xem `requirements.txt` (cần GPU NVIDIA cho YOLO nhanh; không có GPU thì thêm `--device cpu`).

## Chạy thử trên frame demo (không cần tải dữ liệu)

```bash
python tests/test_projection.py          # kiểm chứng phép chiếu với box 2D mmdet3d tính sẵn
python scripts/run_all.py \
  --info /root/work/mmdetection3d/demo/data/nuscenes/n015-2018-07-24-11-22-45+0800.pkl \
  --data-root /root/work/mmdetection3d/demo/data/nuscenes --out out/demo
```

Mở `out/demo/index.html` bằng trình duyệt.

## Chạy trên nuScenes-mini

1. Tải **v1.0-mini** tại nuscenes.org (cần tài khoản), giải nén vào `D:\data\nuscenes`
   (bên trong có `samples/`, `sweeps/`, `maps/`, `v1.0-mini/`).
2. `bash scripts/prepare_nuscenes_mini.sh` – sinh file info `.pkl` (một lần).
3. ```bash
   python scripts/run_all.py --info /mnt/d/data/nuscenes/nuscenes_infos_val.pkl \
     --data-root /mnt/d/data/nuscenes --out out/mini_val --cfg configs/tuned.json
   ```

**Luôn dùng `--cfg configs/tuned.json`.** Không có nó, tool chạy với ngưỡng mặc định và báo nhầm nhiều gấp ~4 lần.

Kết quả hiện tại trên tập val (81 frame, không dùng khi chỉnh ngưỡng): **2,53 báo động giả/frame, bắt được 62,9%
lỗi cài vào** (mặc định: 11,01 / 70,1%). Chi tiết: [docs/decision-log.md](docs/decision-log.md) D-008, D-009.

## Chỉnh ngưỡng (tuning)

Chỉnh trên tập **train**, đo cuối trên tập **val**:

```bash
python scripts/calibrate.py --info …train.pkl --data-root … --dets out/mini_train/det_2d.json \
  --q 5 --size-q 2 --write configs/calibrated.json   # phân tích báo nhầm + sinh ngưỡng theo class
python scripts/sweep.py --info …train.pkl --data-root … --dets out/mini_train/det_2d.json \
  --configs configs/sweep2.json                      # so nhiều cấu hình: báo động giả/frame vs recall
python scripts/eval_seeds.py … --cfg configs/tuned.json   # một cấu hình, nhiều lần cài lỗi
```

Tham số hay dùng: `--max-frames 20` (chạy thử ít frame), `--rate 0.3` (tỉ lệ cuboid bị cài lỗi), `--seed 1`
(bộ lỗi khác), `--redetect` (chạy lại YOLO thay vì dùng cache `det_2d.json`).

## Đầu ra (`out/<tên>/`)

| File | Dùng cho |
|---|---|
| `index.html` | Reviewer xem cảnh báo + ảnh 6 camera |
| `flags_for_grading.csv` | Dán vào Google Sheet "Chấm tool" – người chấm điền Đúng/Nhầm (chấm mù, không biết lỗi nào là cài) |
| `metrics.json` | Recall theo loại lỗi, báo động giả, reprojection error |
| `injected_errors.json` | Đáp án lỗi đã cài (có cột `caught`) – **không đưa cho người chấm** |

## Cấu trúc

```
src/m44/   loader · geometry · detect · match · inject · evaluate · report
scripts/   run_all.py · prepare_nuscenes_mini.sh · calibrate.py · sweep.py · eval_seeds.py
configs/   tuned.json (cấu hình dùng thật) · calibrated_*.json · sweep*.json
tests/     test_projection.py
docs/      decision-log.md · json-formats.md
templates/ baseline_review.csv – sheet bấm giờ review, dùng cho cả baseline (tay) và pilot (có tool)
```
