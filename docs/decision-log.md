# Decision log

Mỗi quyết định kỹ thuật: bối cảnh → quyết định → lý do → hệ quả. Mới nhất ở trên cùng.

## D-010 · Đọc nuScenes trực tiếp bằng nuscenes-devkit, bỏ phụ thuộc mmdet3d / WSL khi chạy tool
- **Bối cảnh:** môi trường cũ (WSL + PyTorch CUDA + mmcv + mmdet3d, ~9 GB, nhiều lỗi phiên bản) chỉ cần mmdet3d để
  sinh file info `.pkl`. Thành viên không có nền tảng kỹ thuật không thể tự cài.
- **Quyết định:** `loader.load_frames_nusc` đọc thẳng bảng nuScenes; `requirements.txt` chỉ còn numpy, scipy,
  pillow, nuscenes-devkit, ultralytics; thêm `setup_windows.bat`, `run_demo.bat` chạy Python Windows, CPU được.
  `run_all.py` dùng `configs/tuned.json` làm mặc định để không ai quên.
- **Kiểm chứng:** `tests/test_loader_nusc.py` – 81 frame / 4.441 cuboid val khớp loader cũ tuyệt đối (lidar2cam
  lệch 5·10⁻⁸ do pkl lưu float32). Cài từ bản sao sạch của repo trên Windows: chạy được, kết quả demo giống hệt bản
  GPU trong WSL (482 detection, 42/59 lỗi, 90 cảnh báo); 10 frame mất ~2 phút trên CPU.

## D-009 · Chọn cấu hình `configs/tuned.json`, kiểm chứng trên tập val
- **Quy trình:** chỉnh mọi ngưỡng trên nuScenes-mini **train** (323 frame, 8 cảnh); đo cuối trên **val** (81 frame,
  2 cảnh) chưa dùng khi chỉnh. Recall = trung bình 10 lần cài lỗi ngẫu nhiên (30% cuboid kiểm tra được).
- **Kết quả val:** báo động giả 11,01 → **2,53 cảnh báo/frame** (÷4,4); recall 70,1% → **62,9%**.
  Theo loại: CLASS_SWAP 95%, SCALE 90%, OFFSET 48%, DELETE 45%, ROTATE 30%.
- **Lựa chọn trên train (sweep, `configs/sweep*.json`):**

  | Cấu hình | Báo động giả/frame | Recall |
  |---|---|---|
  | A mặc định | 7,12 | 71,5% |
  | E lọc visibility ≥ 3, kích thước ≥ 60 px, bỏ đêm, IoU theo class p2 | 0,66 | 37,1% |
  | G2 = E + IoU p5 + `SIZE_MISMATCH` (p2–p98) → **chọn** | 1,30 | 58,9% |
- **Giới hạn:** val chỉ có 2 cảnh → con số còn dao động; cần đo lại trên batch pilot thật ở tuần 6.

## D-008 · Thêm cảnh báo `SIZE_MISMATCH` (so chiều cao / chiều rộng) và lọc theo dữ liệu nuScenes
- **Bối cảnh:** trên train, GT sạch sinh 7,1 báo động giả/frame. Phân tích (`scripts/calibrate.py`):
  54% là `NO_2D_MATCH` do YOLO không thấy (ban đêm, mờ, vật bị cây/biển hiệu che, người xa);
  `LOW_IOU` với ngưỡng 0,5 báo nhầm 31–48% người / xe máy / xe đạp đúng nhãn.
  Siết IoU theo class giảm báo nhầm nhưng làm recall SCALE 85% → 28%, ROTATE 44% → 6%: IoU quá thô.
- **Quyết định:**
  1. Loader gắn `visibility` (1–4) và cờ `night` từ bảng nuScenes; kiểm tra tính khớp: 18.538 nhãn, lệch 0.
  2. Chỉ kiểm tra cuboid visibility ≥ 3; `NO_2D_MATCH`/`MISSING_3D` (chỉ dựa vào việc YOLO thấy hay không) cần
     vật thể ≥ 60 px, `MISSING_3D` cần độ tin ≥ 0,7, và tắt ở cảnh đêm.
  3. `SIZE_MISMATCH`: log(cao chiếu / cao YOLO) và log(rộng chiếu / rộng YOLO) nằm ngoài khoảng p2–p98 của GT sạch
     theo từng class. Cuboid phóng to ×1,6 hay xe xoay 90° làm tỉ lệ này lệch rõ, trong khi IoU vẫn "chấp nhận được".
- **Hệ quả:** ngưỡng sinh tự động bằng `calibrate.py --write`; muốn dùng YOLO khác hay dữ liệu khác thì chạy lại.

## D-007 · `MISSING_3D`: chỉ cuboid cùng nhóm class mới "giải thích" được một detection
- **Bối cảnh:** lỗi xoá cuboid chỉ bắt được 50,6% (100 lần cài lỗi ngẫu nhiên trên frame demo). Debug thấy detection
  "car" bị coi là đã có cuboid vì chạm 0,11 IoU với cuboid **cọc tiêu**, hoặc 0,15 với **người đi bộ ở xa phía sau**.
- **Quyết định:** detection không ghép cặp chỉ được bỏ qua khi (a) trùng ≥ 0,1 IoU với cuboid *không kiểm tra được*
  có class tương thích, hoặc (b) trùng ≥ 0,5 với bất kỳ cuboid nào (detection trùng lặp, vd car + truck).
- **Kết quả:** recall DELETE 50,6% → 79,0%; báo động giả trên GT sạch giữ nguyên (7); tổng recall 76,0% → 81,8%.
- **Còn lại (giới hạn đã biết):** (1) nhóm người đứng sát nhau mà YOLO chỉ thấy một phần – cuboid bên cạnh "nhận"
  detection của người bị xoá, nhìn từ 2D không còn mâu thuẫn; (2) vật thể xa YOLO kém tự tin (< `missing_conf` 0,5).

## D-006 · Chỉ cài lỗi vào cuboid tool "nhìn thấy được" khi đúng
- **Quyết định:** cuboid đủ điều kiện cài lỗi = khớp được với một detection YOLO và không bị cảnh báo trên GT sạch.
- **Lý do:** tách hai câu hỏi: (1) tool có phát hiện lỗi khi nhìn thấy vật thể không (recall), (2) tool báo động giả
  bao nhiêu (đo riêng trên GT sạch). Nếu cài lỗi vào vật thể bị che hoàn toàn thì recall đo cả khả năng của YOLO.
- **Hệ quả:** recall là "recall trên vùng kiểm tra được". Báo cáo phải nêu kèm tỉ lệ cuboid kiểm tra được.

## D-005 · Bỏ qua vật thể quá xa / quá nhỏ / bị che
- **Quyết định:** chỉ kiểm tra cuboid có depth ≤ 50 m, chiều cao chiếu ≥ 25 px, ≥ 50% nằm trong ảnh, bị cuboid gần
  hơn che ≤ 50%.
- **Lý do:** nuScenes có nhiều người đi bộ ở xa chỉ 1–5 điểm LiDAR, trên ảnh vài pixel – YOLO không thấy, sẽ thành
  báo động giả.
- **Hệ quả:** ngưỡng chỉnh ở `match.DEFAULT_CFG`, tinh chỉnh tuần 5 dựa trên kết quả chấm.

## D-004 · Ánh xạ class nuScenes ↔ COCO theo nhóm tương thích
- **Quyết định:** dùng YOLO pretrained COCO, một class nuScenes chấp nhận nhiều class COCO (car ↔ car/truck, …).
  `barrier`, `traffic_cone` không có trong COCO → không kiểm tra class/vị trí được, chỉ dùng để tránh báo
  `MISSING_3D` nhầm.
- **Lý do:** YOLO hay gọi SUV/bán tải là "truck"; bắt khớp tuyệt đối sẽ ra nhiều `CLASS_MISMATCH` giả.
- **Hệ quả:** lỗi đổi class giữa hai class cùng nhóm (car ↔ truck) không bắt được – nêu trong giới hạn.

## D-003 · Chấp nhận sai lệch ~1 px so với box 2D tham chiếu của mmdet3d
- **Bối cảnh:** so với box 2D mmdet3d tính sẵn: IoU trung vị 0,949, lệch ~1 px.
- **Sửa lại (khi làm D-010):** ban đầu ghi lý do là `lidar2cam` trong info không bù chuyển động của xe – **sai**.
  Đọc code mmdet3d (`obtain_sensor2top`) thấy `lidar2cam` đã đi qua ego-pose ở cả thời điểm LiDAR và camera, tức
  là đã bù. Nguyên nhân chính xác của ~1 px chưa xác định (có thể do cách mmdet3d lấy bao lồi rồi cắt theo ảnh).
- **Hệ quả:** không ảnh hưởng ngưỡng; loader D-010 tính cùng chuỗi biến đổi nên có bù chuyển động.

## D-002 · `bbox_3d` trong info pkl là tâm khối, không phải tâm đáy
- **Bối cảnh:** lần chiếu đầu IoU luôn ≈ 0,333 – đúng bằng IoU khi box bị dịch lên nửa chiều cao.
- **Quyết định:** loader đổi về tâm đáy (`z - h/2`), quy ước box LiDAR của mmdet3d.
- **Hệ quả:** có test `tests/test_projection.py` để không tái phát.

## D-001 · Đọc dữ liệu qua file info .pkl của mmdet3d thay vì nuscenes-devkit trực tiếp
- **Lý do:** frame demo của mmdet3d và nuScenes-mini (sau `create_data.py`) cùng một định dạng → một code path,
  chạy được ngay khi chưa tải dataset.
