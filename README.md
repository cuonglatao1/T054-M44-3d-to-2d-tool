# M44 – 2D–3D Consistency Checker

Tool tự kiểm tra nhãn cuboid 3D (nuScenes) bằng camera: chiếu từng cuboid lên 6 camera, so với vật thể YOLO
phát hiện trên ảnh, rồi báo các chỗ không nhất quán để reviewer xem nhanh thay vì mở từng camera đối chiếu bằng tay.

![Ví dụ: cuboid chiếu lên CAM_FRONT](docs/img/example_cam_front.jpg)

*Xanh lá: cuboid khớp vật thể · Đỏ: cuboid bị cảnh báo · Xanh dương: vật thể YOLO thấy · Cam: vật thể chưa có cuboid.
Ảnh từ nuScenes (CC BY-NC-SA 4.0).*

**Mới vào nhóm?** Đọc [docs/HUONG-DAN-TEAM.md](docs/HUONG-DAN-TEAM.md) – tool làm gì, đã làm đến đâu, ai làm gì tiếp.

## Bắt đầu nhanh (Windows, không cần GPU)

1. Cài **Python 3.11** từ [python.org](https://www.python.org/downloads/) – tick *Add python.exe to PATH*.
2. Clone repo này, bấm đúp **`setup_windows.bat`** (một lần, 5–10 phút, tải ~1 GB).
3. Tải **nuScenes-mini** (3,9 GB): <https://www.nuscenes.org/data/v1.0-mini.tgz>, giải nén vào `data\nuscenes`
   trong thư mục repo (bên trong phải có `samples`, `sweeps`, `maps`, `v1.0-mini`).
   Dữ liệu dùng theo giấy phép nuScenes (phi thương mại) – không commit lên GitHub.
4. Bấm đúp **`run_demo.bat`** → chạy 10 frame (~2 phút trên CPU) → báo cáo tự mở trong trình duyệt.

Để dữ liệu chỗ khác: đặt biến môi trường `NUSC_ROOT`, ví dụ `set NUSC_ROOT=D:\data\nuscenes` trước khi chạy.
Kịch bản demo 5 phút: [docs/demo.md](docs/demo.md).

## Kết quả hiện tại

Trên tập val nuScenes-mini (81 frame, **không** dùng khi chỉnh ngưỡng), trung bình 10 lần cài lỗi ngẫu nhiên:

| | Báo động giả / frame | Lỗi bắt được |
|---|---|---|
| Ngưỡng mặc định | 11,01 | 70,1% |
| **Ngưỡng đã chỉnh (`configs/tuned.json`, mặc định của mọi script)** | **2,48** | **63,1%** |

Theo loại lỗi: sai class 97%, sai kích thước 90%, lệch vị trí 48%, thiếu cuboid 45%, xoay hướng 30%.
Cách ra con số và các giới hạn: [docs/decision-log.md](docs/decision-log.md) (D-008, D-009, D-011).

## Cảnh báo

| Cảnh báo | Ý nghĩa |
|---|---|
| `LOW_IOU` | Cuboid lệch vị trí so với vật thể trên ảnh |
| `SIZE_MISMATCH` | Chiều cao / chiều rộng cuboid không khớp vật thể (sai kích thước hoặc sai hướng) |
| `CLASS_MISMATCH` | Class của cuboid khác class vật thể trên ảnh |
| `NO_2D_MATCH` | Cuboid không khớp vật thể nào trên ảnh (lệch xa, sai hẳn, hoặc bị che khuất) |
| `MISSING_3D` | Vật thể thấy rõ trên ảnh nhưng chưa có cuboid |

## Pipeline

```
nuScenes ─► loader ─► gt_boxes ─► inject (cài lỗi có đáp án) ─► noisy_boxes + injected_errors
                                                                    │
                                        projection ─► proj_2d ──────┤
6 ảnh camera ─► YOLO ─► det_2d ─────────────────────────────► match ─► flags ─► evaluate (recall)
                                                                             └► report (HTML + CSV)
```

Mỗi lần chạy kiểm tra **hai lần**: trên GT sạch (đo báo động giả + reprojection error) và trên GT đã cài lỗi
(đo tool bắt được bao nhiêu lỗi). Định dạng các file JSON: [docs/json-formats.md](docs/json-formats.md).

## Hai chế độ

| Script | Làm gì | Dùng khi |
|---|---|---|
| `scripts\check.py` | **Kiểm nhãn thật**: chỉ gắn cờ + báo cáo, không đụng vào nhãn | Review nhãn, pilot |
| `scripts\run_all.py` | **Đo tool**: cài lỗi giả có đáp án rồi xem tool bắt được bao nhiêu | Đánh giá, demo, chỉnh ngưỡng |

```bat
.venv\Scripts\activate
python scripts\check.py --split val --out out\check_val             :: kiểm nhãn gốc nuScenes (81 frame)
python scripts\run_all.py --split val --out out\mini_val            :: đo tool trên cả tập val
python scripts\run_all.py --split val --max-frames 10 --out out\x   :: thử nhanh
```

`check.py --frames-json file.json` kiểm nhãn xuất từ công cụ khác (cùng định dạng loader, xem
[docs/json-formats.md](docs/json-formats.md)).

## Nút "M44 Check" (dễ nhất)

1. Bấm đúp **`m44_server.bat`** (giữ cửa sổ mở) → trang `http://localhost:8765` tự mở.
2. Kéo nút **M44 Check** trên trang đó lên **thanh dấu trang** của trình duyệt (một lần; `Ctrl+Shift+B` nếu
   chưa thấy thanh dấu trang).
3. Mở một task hoặc job 3D trên CVAT → bấm **M44 Check** → tab mới hiện tiến trình rồi tự chuyển sang **danh
   sách lỗi**; cờ `qc`/Score đã được ghi vào CVAT; mỗi dòng có nút mở đúng cuboid trong CVAT.

Nút chỉ đọc ID task/job từ địa chỉ trang rồi gọi dịch vụ trên máy bạn, không sửa gì CVAT – dùng được với CVAT
của nhóm hay của BTC (dịch vụ đăng nhập CVAT bằng thông tin trong `.cvat.env`).

## Dùng với CVAT 3D

CVAT 3D không có Issue / chế độ Review, nên tool ghi kết quả lên **từng cuboid**:
- thuộc tính `qc` = loại cảnh báo (`OK`, `LOW_IOU`, `SIZE_MISMATCH`, `CLASS_MISMATCH`, `NO_2D_MATCH`) – xem trong DETAILS;
- **Score** = 0 nếu bị gắn cờ, 1 nếu OK.

**Cách reviewer làm việc (dễ nhất):** mở báo cáo HTML, đi lần lượt từng dòng, bấm **"Mở trong CVAT"** → CVAT mở
đúng frame và **chỉ hiện cuboid bị cảnh báo** (link có `type=shape&serverID=…`, tính năng có sẵn của CVAT) → sửa →
Save → quay lại báo cáo. Muốn xem lại mọi object trong frame: Filters → Clear filters.

**Hoặc lọc trong CVAT:** Filters → Add rule → **Score** `<` `1` → Submit (một luật cho mọi label; lần sau chọn
lại trong "Recently used"). Không lọc bằng `qc != OK`: thuộc tính đó gắn theo label, cuboid label khác không có
nó nên CVAT coi là "khác OK" và vẫn hiện ra.
`MISSING_3D` (không có cuboid để gắn) chỉ có trong báo cáo HTML, kèm link mở đúng frame trong CVAT.

1. Copy `.cvat.env.example` thành `.cvat.env`, điền `CVAT_URL` và Personal Access Token (hoặc user/password).
   File này không được commit.
2. Tạo task từ nuScenes (point cloud + 6 ảnh camera mỗi frame; mỗi cuboid có thuộc tính `visibility` và `qc`):
   ```bat
   python scripts\cvat_create_task.py --split val --max-frames 10 --name "M44 pilot" --labels noisy
   ```
   `--labels gt` nạp nhãn gốc, `noisy` nạp nhãn có cài lỗi + đáp án `out\cvat_tasks\task_<id>\answer_key.json`
   (**không đưa reviewer**), `none` để trống cho annotator tự gán.
3. Sau khi annotator làm xong (hoặc bất cứ lúc nào): bấm đúp `cvat_check.bat` và nhập ID task, hoặc
   ```bat
   python scripts\cvat_check.py --task-id 52 [--answer-key out\cvat_tasks\task_52\answer_key.json] [--dry-run]
   ```
   Tool đọc cuboid hiện tại từ CVAT, kiểm tra, ghi `qc` ngược lại và mở báo cáo có nút "Mở trong CVAT".

Annotator vẽ cuboid mới thì `visibility` mặc định `4` (thấy rõ) → tool kiểm tra cuboid đó đầy đủ; nên sửa
`visibility` cho vật bị che để tránh báo nhầm.

Tham số: `--nusc-root` (thư mục nuScenes, mặc định `data\nuscenes` hoặc `NUSC_ROOT`), `--split train|val`,
`--max-frames N`, `--rate 0.3` (tỉ lệ cuboid bị cài lỗi), `--seed 1` (bộ lỗi khác), `--redetect` (chạy lại YOLO
thay vì dùng cache `det_2d.json`), `--device cpu|0|auto`, `--cfg default` (ngưỡng chưa chỉnh).

Test: `python tests\test_projection.py` (cần frame demo của mmdet3d) và `python tests\test_loader_nusc.py`
(cần info .pkl của mmdet3d) – chỉ chạy được trong môi trường WSL bên dưới.

## Chỉnh ngưỡng (tuning)

Chỉnh trên tập **train**, đo cuối trên tập **val** (cần `det_2d.json` từ một lần `run_all.py` trên split đó):

```bat
python scripts\calibrate.py --split train --dets out\mini_train\det_2d.json --q 5 --size-q 2 --write configs\calibrated.json
python scripts\sweep.py --split train --dets out\mini_train\det_2d.json --configs configs\sweep2.json
python scripts\eval_seeds.py --split val --dets out\mini_val\det_2d.json --cfg configs\tuned.json
```

## Đầu ra (`out\<tên>\`)

| File | Dùng cho |
|---|---|
| `index.html` | Reviewer xem cảnh báo + ảnh 6 camera |
| `flags_for_grading.csv` | Dán vào Google Sheet "Chấm tool" – điền Đúng/Nhầm (chấm mù, không biết lỗi nào là cài) |
| `metrics.json` | Recall theo loại lỗi, báo động giả, reprojection error |
| `injected_errors.json` | Đáp án lỗi đã cài (có cột `caught`) – **không đưa cho người chấm** |

## Cấu trúc

```
src/m44/   loader · geometry · detect · match · inject · evaluate · report · cvat_io
scripts/   check.py · cvat_create_task.py · cvat_check.py · run_all.py · calibrate.py · sweep.py · eval_seeds.py
           prepare_nuscenes_mini.sh (chỉ WSL)
configs/   tuned.json (cấu hình dùng thật) · calibrated_*.json · sweep*.json
tests/     test_projection.py · test_loader_nusc.py
docs/      HUONG-DAN-TEAM.md · demo.md · decision-log.md · json-formats.md
templates/ baseline_review.csv – sheet bấm giờ review, dùng cho cả baseline (tay) và pilot (có tool)
```

## Môi trường GPU (WSL, nâng cao)

Máy tech lead chạy trong WSL distro `mmdet3d` (CUDA, PyTorch 2.1, mmdet3d 1.4 – cần cho PointPillars và để sinh
info .pkl cho test). Không cần cho việc chạy tool.

```bash
wsl -d mmdet3d
source /opt/m3d/bin/activate
cd /mnt/d/m44-consistency-checker
python scripts/run_all.py --nusc-root /mnt/d/data/nuscenes --split val --out out/mini_val
```
