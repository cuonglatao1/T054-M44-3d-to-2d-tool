# Hướng dẫn dùng tool M44 với CVAT (cho thành viên nhóm)

Làm theo thứ tự. Mục nào ghi **(tech lead)** thì chỉ tech lead làm.

## 0. Bạn dùng CVAT nào?

**Mặc định: CVAT local trên máy bạn** (`http://localhost:8080`). Tool, dữ liệu và CVAT đều nằm trên máy bạn, không
phụ thuộc máy ai khác. Ở dưới, `<CVAT_URL>` = `http://localhost:8080`.

Dùng CVAT khác (của BTC, của một bạn trong nhóm) thì thay `<CVAT_URL>` bằng địa chỉ đó – mọi bước giữ nguyên.

Tool chạy được với CVAT local tự dựng (đã thử với CVAT 2.75): khác phiên bản thì chỉ hiện cảnh báo; label đặt tên
khác (`Car`, `Person`, `motorbike`…) vẫn được nhận; task thiếu thuộc tính `qc` vẫn kiểm tra được (chỉ ghi Score).
**Điều kiện duy nhất:** task phải tạo bằng tool (mục 4), vì tool cần ảnh camera + calibration của đúng frame.

## 1. Cài tool trên máy bạn (một lần, ~20 phút)

Cần cho ai muốn **bấm nút M44 Check** hoặc chạy tool. Người chỉ xem báo cáo thì bỏ qua – tech lead gửi báo cáo.

1. Cài **Python 3.11** từ <https://www.python.org/downloads/> – tick **Add python.exe to PATH**.
2. Tải code: trên GitHub bấm **Code → Download ZIP**, giải nén (ví dụ vào `D:\m44`). Biết Git thì `git clone`.
3. Bấm đúp **`setup_windows.bat`**, chờ chữ **OK** (5–10 phút, tải ~1 GB).
4. Tải **nuScenes-mini** (3,9 GB): <https://www.nuscenes.org/data/v1.0-mini.tgz>, giải nén vào thư mục `data\nuscenes`
   bên trong thư mục tool. Trong đó phải có `samples`, `sweeps`, `maps`, `v1.0-mini`.
   (File `.tgz` giải nén bằng 7-Zip: giải nén 2 lần, `.tgz` → `.tar` → thư mục.)

## 2. Cho tool đăng nhập CVAT bằng tài khoản của bạn

1. Đăng nhập `<CVAT_URL>` bằng tài khoản của bạn.
2. Bấm **tên tài khoản** (góc trên bên phải) → **Profile** → tab **Security** → phần **API Tokens** → tạo token
   mới, quyền **Read/Write**, đặt tên `m44`.
3. **Copy token ngay** – CVAT chỉ hiện một lần.
4. Trong thư mục tool, copy file `.cvat.env.example` thành **`.cvat.env`**, mở bằng Notepad, điền:
   ```
   CVAT_URL=<CVAT_URL>
   CVAT_ACCESS_TOKEN=<token vừa copy>
   ```
   Lưu lại. **Không gửi file này cho ai, không đưa lên GitHub** (repo đã chặn sẵn).

Tool làm mọi thứ dưới tên tài khoản của bạn. Trên CVAT local của bạn thì bạn có toàn quyền; với CVAT của người
khác, bạn phải **được giao (assign) task/job** đó.

## 3. Bật nút "M44 Check" (một lần)

1. Bấm đúp **`m44_server.bat`** → cửa sổ đen hiện "Dịch vụ M44 đang chạy" và trình duyệt mở trang
   `http://localhost:8765`. **Giữ cửa sổ đen mở** trong lúc làm việc (đóng = tắt tool).
2. Trên trang đó, **kéo nút xanh "M44 Check" lên thanh dấu trang** của trình duyệt (`Ctrl+Shift+B` nếu chưa thấy
   thanh dấu trang). Không kéo được: chuột phải nút → *Sao chép địa chỉ liên kết* → chuột phải thanh dấu trang →
   *Thêm trang…* → dán vào ô URL.
3. Mỗi lần mở máy làm việc: chỉ cần bấm đúp lại `m44_server.bat`.

## 4. Tạo task trên CVAT của bạn

Bấm đúp **`create_task.bat`**, trả lời 4 câu (Enter để lấy giá trị mặc định):

| Câu hỏi | Gợi ý |
|---|---|
| Tên task | ví dụ `Pilot - Lan` |
| Bắt đầu từ frame số | `0`–`80` (tập val). Mỗi người chọn đoạn khác nhau để không trùng |
| Số frame | `10` |
| Nhãn sẵn | `none` = task trống để **tự gán** (pilot thật) · `gt` = nhãn gốc · `noisy` = nhãn có cài lỗi + đáp án |

Cuối cùng hiện `task <id>: http://localhost:8080/tasks/<id>` – mở link đó trên CVAT.

- `noisy` lưu đáp án ở `out\cvat_tasks\task_<id>\answer_key.json` – **không đưa cho reviewer**.
- Task tạo tay trên giao diện CVAT (Create task) thì tool **không** kiểm tra được và sẽ báo rõ lý do.
- Dòng lệnh tương đương: `python scripts\cvat_create_task.py --split val --start-frame 50 --max-frames 10 --name "..." --labels none`.

## 5. Annotator: gán nhãn

Mở job được giao → vẽ cuboid như bình thường. Mỗi cuboid có 2 thuộc tính:
- **visibility** – vật thấy rõ bao nhiêu: `4` = 80–100% (mặc định), `3` = 60–80%, `2` = 40–60%, `1` = < 40%.
  **Hãy chỉnh cho vật bị che**, nếu không tool sẽ báo nhầm.
- **qc** – tool tự điền, **đừng sửa**.

Xong bấm **Save**.

## 6. Reviewer: kiểm tra bằng một nút

1. Đảm bảo cửa sổ `m44_server.bat` đang mở.
2. Mở task hoặc job trên CVAT → bấm **M44 Check** trên thanh dấu trang.
3. Tab mới hiện "đang kiểm tra…" (lần đầu 1–2 phút) rồi tự chuyển sang **danh sách lỗi**.
4. Từng dòng: xem ảnh, bấm **Mở trong CVAT** → CVAT mở đúng frame và **chỉ hiện cuboid bị cảnh báo** → sửa →
   **Save** → quay lại danh sách. Xem lý do ở dòng `qc` trong DETAILS của cuboid.
5. Muốn xem mọi cuboid bị gắn cờ cùng lúc trong CVAT: **Filters → Add rule → Score `<` 1 → Submit**.
   Bỏ lọc: **Filters → Clear filters**.
6. Sửa xong bấm **M44 Check** lần nữa để kiểm tra lại.

`MISSING_3D` (trên ảnh có vật nhưng chưa có cuboid) chỉ có trong danh sách lỗi, không có trong CVAT – mở link,
tự vẽ cuboid còn thiếu.

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Bấm M44 Check không có gì xảy ra / tab báo không kết nối được | Chưa bật `m44_server.bat`, hoặc đã đóng cửa sổ đen |
| "hãy mở một task hoặc job CVAT trước" | Bạn đang không ở trang task/job của CVAT |
| Lỗi `401` / `403` | Token sai hoặc hết hạn, hoặc bạn chưa được giao task đó |
| "frame … không có mã nuScenes trong tên" | Task tạo tay trên CVAT – tạo lại bằng `create_task.bat` |
| "Không tìm thấy frame nuScenes …" | Thiếu hoặc sai chỗ dữ liệu `data\nuscenes` |
| `Connection refused` tới `localhost:8080` | CVAT local chưa chạy – mở Docker Desktop, chờ CVAT khởi động |
| Cờ `qc` không đổi trong CVAT | Tải lại trang CVAT (F5) sau khi tool chạy xong |
| Khác | Chụp màn hình cửa sổ đen + trang lỗi, gửi vào Discord nhóm |
