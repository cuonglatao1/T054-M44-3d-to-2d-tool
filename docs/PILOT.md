# Pilot M44 – tuần 6

## Mục tiêu

Đo xem **có tool M44 thì review nhãn 3D tốt hơn bao nhiêu** so với review tay, và tool **không làm chất lượng
tụt** (người review không sửa hỏng cuboid đúng). Đây là số liệu chính của báo cáo cuối.

| Chỉ số | Cách đo |
|---|---|
| Lỗi sửa được | Script so nhãn sau khi sửa với nhãn gốc nuScenes, đối chiếu đáp án lỗi đã cài |
| Lỗi sửa được mỗi phút | Lỗi sửa được ÷ số phút làm (tối đa 20 phút / lượt) |
| Cuboid đúng bị làm hỏng | Cuboid vốn đúng mà sau review không còn khớp nhãn gốc |

Một lỗi tính là **đã sửa** khi lại có cuboid đúng class nằm đúng chỗ vật thật: tâm lệch ≤ 0,7 m, mỗi cạnh lệch
≤ 25 %, hướng lệch ≤ 20°. **Sửa gần đúng là được**, không cần chính xác tuyệt đối.

## Phân công

2 bộ dữ liệu khác nhau, mỗi bộ 5 frame có lỗi cài sẵn: **bộ A** (Boston, 25 lỗi) và **bộ B** (Singapore, 18 lỗi).
Mỗi người làm cả hai chế độ, mỗi bộ một lần; thứ tự đảo chéo để công bằng:

| Người | Lượt 1 | Lượt 2 |
|---|---|---|
| Thúy | Bộ A – **tay** | Bộ B – **tool** |
| Trọng | Bộ B – **tay** | Bộ A – **tool** |
| Duy | Bộ A – **tool** | Bộ B – **tay** |
| Tùng | Bộ B – **tool** | Bộ A – **tay** |

Tech lead không review, chỉ chuẩn bị và tổng hợp.

## Chuẩn bị (mỗi người, làm trước buổi pilot)

1. Cài tool, tạo `.cvat.env`, bật nút **M44 Check**: [HUONG-DAN-CVAT.md](HUONG-DAN-CVAT.md) mục 1–3.
2. Mở trang **`http://localhost:8765`** (cửa sổ `m44_server.bat` đang chạy) → bấm nút **"Tạo task pilot (A + B)"**
   (phần 1; task cho phần 2 tạo bằng nút **"Tạo task gán nhãn"** khi làm phần 2)
   → chờ ~2 phút. Trang hiện **PILOT A: 25 lỗi cài ✓ đúng** và **PILOT B: 18 lỗi cài ✓ đúng** kèm link mở task.
   Hiện chữ đỏ (số khác) → báo tech lead. Lỡ bấm lại thì trang báo task đã có, không tạo trùng.
   (Cách khác: bấm đúp `pilot_setup.bat`, phải thấy `injected 25 errors` và `injected 18 errors`.)
3. Ghi 2 số **task id** vào sheet pilot.
4. **Không mở thư mục `out\cvat_tasks`** – trong đó có đáp án.

## Luật

- Mỗi lượt **tối đa 20 phút**, bấm giờ điện thoại. Xong sớm thì dừng, ghi số phút thật.
- Nghỉ ít nhất 5 phút giữa hai lượt. Không trao đổi với nhau về lỗi đã thấy.
- **Lượt "tay":** KHÔNG bấm M44 Check, KHÔNG lọc Score, KHÔNG mở báo cáo. Tự xem từng frame, so cuboid với ảnh
  camera và point cloud.
- **Lượt "tool":** bấm **M44 Check** → làm theo danh sách lỗi (nút "Mở trong CVAT"). Thấy lỗi khác ngoài danh sách
  thì vẫn sửa.

## Làm một lượt

1. Mở task đúng bộ trên CVAT → mở job → **bắt đầu bấm giờ**.
2. Sửa lỗi (xem *Cách sửa* bên dưới). Bấm **Save** (`Ctrl+S`) thường xuyên.
3. Hết giờ hoặc xong: **Save lần cuối**, ghi số phút.
4. Bấm đúp **`pilot_score.bat`**, nhập: tên, bộ (`A`/`B`), chế độ (`tay`/`tool`), task id, số phút.
5. Gửi file `out\pilot\<tên>_<bộ>_<chế độ>.json` cho tech lead (Discord/Drive) và điền kết quả vào sheet.

## Cách sửa trong CVAT 3D

| Lỗi | Sửa thế nào |
|---|---|
| Cuboid lệch chỗ | Chọn cuboid → kéo trong ô **Top** (nhìn từ trên), chỉnh độ cao trong **Side**/**Front** |
| Sai kích thước | Kéo các chấm đỏ ở góc cuboid trong ô Top / Side / Front |
| Sai hướng | Kéo chấm xanh lá (xoay) trong ô **Top** |
| Sai class | Đổi label ở danh sách object bên phải |
| Thiếu cuboid | Chọn công cụ vẽ cuboid (thanh bên trái) → vẽ quanh vật thể → chỉnh trong Top/Side/Front |
| Cuboid thừa / vẽ vào chỗ trống | Chọn cuboid → phím `Delete` |

## Phần 2 – Gán nhãn từ đầu rồi sửa theo M44 Check (mỗi người, sau phần 1, ~40 phút)

Phần 1 đo việc **review** nhãn có lỗi giả. Phần 2 đo đúng quy trình thật: **tự gán nhãn → bấm M44 Check → sửa**,
với **lỗi thật** của chính bạn. Mọi người gán cùng 1 frame (Boston, 10 ô tô + 7 người đi bộ trong vòng 30 m).

1. Trang `http://localhost:8765` → bấm **"Tạo task gán nhãn"** → mở task **PILOT GAN NHAN** (1 frame, chưa có nhãn).
2. **Gán nhãn – tối đa 25 phút:** vẽ cuboid cho **tất cả ô tô (`car`) và người đi bộ (`pedestrian`) nhìn rõ trong
   vòng ~30 m quanh xe** (vùng point cloud dày đặc gần tâm). Chỉnh `visibility` cho vật bị che. **Save.**
3. **Chưa bấm M44 Check.** Bấm đúp **`pilot_label_score.bat`** → lần chấm `truoc`, số phút đã gán.
4. **Sửa theo tool – tối đa 10 phút:** bấm **M44 Check** → sửa theo danh sách lỗi (thêm cuboid còn thiếu nếu danh
   sách có `MISSING_3D`). **Save.**
5. Bấm đúp **`pilot_label_score.bat`** → lần chấm `sau`, số phút đã sửa.
6. Gửi 2 file `out\pilot\<tên>_label_truoc.json` và `<tên>_label_sau.json` cho tech lead.

Đo được: nhãn đúng / lệch / bỏ sót / thừa **trước và sau** khi sửa theo tool, và **cảnh báo của tool trên nhãn
người thật** có chỉ đúng cuboid sai không (độ chính xác) và bắt được bao nhiêu cuboid sai (độ phủ).

## Tech lead tổng hợp

Gom các file `*.json` của mọi người vào `out\pilot\` rồi chạy:

```bat
.venv\Scripts\python scripts\pilot_report.py
```

Kết quả: `out\pilot\pilot_summary.md` (phần 1: bảng so sánh tay / tool, theo loại lỗi, từng người; phần 2: chất
lượng nhãn trước → sau khi sửa theo tool và độ chính xác của tool trên nhãn thật) và `pilot_summary.csv`.
Kiểm tra trước khi pilot: tạo task, không sửa gì, chấm → phải ra 0 lỗi sửa được; đưa nhãn về nhãn gốc → 25/25 và
18/18 (đã thử, D-015 trong decision log).
