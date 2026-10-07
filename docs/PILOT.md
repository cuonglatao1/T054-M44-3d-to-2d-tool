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

## Tech lead tổng hợp

Gom các file `*.json` của mọi người vào `out\pilot\` rồi chạy:

```bat
.venv\Scripts\python scripts\pilot_report.py
```

Kết quả: `out\pilot\pilot_summary.md` (bảng so sánh tay / tool, theo loại lỗi, từng người) và `pilot_summary.csv`.
Kiểm tra trước khi pilot: tạo task, không sửa gì, chấm → phải ra 0 lỗi sửa được; đưa nhãn về nhãn gốc → 25/25 và
18/18 (đã thử, D-015 trong decision log).
