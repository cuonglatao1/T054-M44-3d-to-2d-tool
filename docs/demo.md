# Hướng dẫn chạy và demo

## Cách chạy

**Cách 1 – bấm đúp (cho cả nhóm):** mở `D:\m44-consistency-checker\run_demo.bat`. Tool chạy trên 10 frame
nuScenes-mini (khoảng 30 giây) và tự mở báo cáo trong trình duyệt.

**Cách 2 – xem kết quả có sẵn (không cần chạy):** mở bằng trình duyệt
- `out\demo_live\index.html` – 10 frame, dùng khi demo
- `out\mini_val\index.html` – toàn bộ tập val (81 frame), dùng để chấm tool

**Cách 3 – dòng lệnh (tech lead):**
```bash
wsl -d mmdet3d
source /opt/m3d/bin/activate
cd /mnt/d/m44-consistency-checker/weights
python ../scripts/run_all.py --info /mnt/d/data/nuscenes/nuscenes_infos_val.pkl \
  --data-root /mnt/d/data/nuscenes --out ../out/demo_live --max-frames 10 --cfg ../configs/tuned.json
```
Kết quả không đổi giữa các lần chạy (cùng seed, YOLO cache trong `det_2d.json`), nên các mã cảnh báo bên dưới
luôn trỏ đúng chỗ.

## Đọc báo cáo

| Màu | Ý nghĩa |
|---|---|
| Xanh lá | Cuboid khớp vật thể trên ảnh |
| Đỏ | Cuboid bị cảnh báo |
| Xanh dương | Vật thể YOLO nhìn thấy |
| Cam | Vật thể thấy trên ảnh nhưng chưa có cuboid |

## Kịch bản demo 5 phút

**1. Vấn đề (30 giây).** "Review nhãn 3D phải mở từng camera để đối chiếu cuboid bằng mắt: chậm, dễ sót."
Dẫn issue thật trong backlog của nhóm.

**2. Tool nhìn thấy gì (1 phút).** Kéo xuống phần "6 camera", mở một ảnh CAM_FRONT.
"Mỗi cuboid 3D được chiếu lên đúng vị trí trên ảnh – sai lệch trung bình ~1 pixel so với chuẩn của nuScenes."

**3. Bắt lỗi thật (2 phút).** Trong bảng cảnh báo, chỉ lần lượt:

| Mã | Lỗi đã cài | Tool báo | Nói gì |
|---|---|---|---|
| F0007 | Cuboid người bị thu nhỏ còn 60% | `SIZE_MISMATCH` | "Hộp đỏ chỉ bằng nửa người – tool so chiều cao với vật thể trên ảnh" |
| F0048 | Cuboid ô tô xoay 90° | `LOW_IOU` | "Cuboid chĩa ngang ra khỏi xe – sai hướng" |
| F0006 | Xoá cuboid một người | `MISSING_3D` | "Có người trên ảnh nhưng không có nhãn 3D – khoanh cam" |
| F0002 | Người bị gán class ô tô | `CLASS_MISMATCH` | "3D nói ô tô, camera thấy người" |
| F0001 | Cuboid lệch 1,7 m | `LOW_IOU` | "Cuboid lệch khỏi người thật" |

**4. Số liệu (1 phút).** Từ `docs/decision-log.md` (D-009), đo trên 81 frame không dùng khi chỉnh:
- Bắt được **62,9%** lỗi cài vào; sai class 95%, sai kích thước 90%.
- Báo nhầm giảm từ 11 xuống **2,5 cảnh báo/frame** nhờ chỉnh ngưỡng theo dữ liệu.
- Kết quả pilot (tuần 6): thời gian review/frame tay vs có tool – điền khi có.

**5. Giới hạn – nói thẳng (30 giây).** Tool dựa vào YOLO nên kém ở ban đêm, vật bị che, người đứng sát nhau;
lỗi xoay hướng mới bắt được ~30%. Hướng tiếp: detector tốt hơn, bù chuyển động xe giữa LiDAR và camera.

## Chuẩn bị trước buổi demo
- Chạy `run_demo.bat` một lần trước (để có sẵn kết quả, không phải chờ YOLO).
- Mở sẵn `out\demo_live\index.html`, zoom trình duyệt 125–150% cho máy chiếu.
- Phòng khi máy lỗi: chụp màn hình 5 cảnh báo trên + bảng số liệu, đưa vào slide.
