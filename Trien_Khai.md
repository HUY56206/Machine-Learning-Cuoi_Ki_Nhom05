# Triển khai lên Railway (link cho cả nhóm)

Ba vai trò dùng chung **một link**. Dự án đã có sẵn `Procfile`, `railway.json`, `.railwayignore`, WhiteNoise + gunicorn.

## 1. Đưa mã lên GitHub
Dự án chưa là git repo.
```bash
cd Project_ML_QSR
git init && git add . && git commit -m "QSR Forecast"
# tạo repo rỗng trên GitHub (private) rồi:
git remote add origin https://github.com/<user>/<repo>.git && git push -u origin main
```
Đừng đẩy `.env` (đã nằm trong `.gitignore`; kiểm tra lại trước khi push).

## 2. Tạo dịch vụ trên Railway
1. railway.app → New Project → **Deploy from GitHub repo** (chọn repo vừa đẩy).
2. Trong project: **+ New → Database → MySQL**.
3. Ở dịch vụ web → **Variables**, thêm (lấy giá trị MySQL từ tab Variables/Connect của dịch vụ MySQL):

| Biến | Giá trị |
|---|---|
| `QSR_DB_HOST` | host MySQL (VD `xxx.proxy.rlwy.net` hoặc `mysql.railway.internal`) |
| `QSR_DB_PORT` | cổng |
| `QSR_DB_USER` / `QSR_DB_PASSWORD` / `QSR_DB_NAME` | thông tin MySQL (`railway` là tên DB mặc định) |
| `QSR_SECRET_KEY` | chuỗi ngẫu nhiên dài |
| `QSR_DEBUG` | `0` |
| `QSR_ALLOWED_HOSTS` | domain Railway, VD `ten-app.up.railway.app` |
| `QSR_CSRF_ORIGINS` | `https://ten-app.up.railway.app` |

4. Web service → Settings → **Generate Domain** để có link `https://....up.railway.app`.

## 3. Nạp dữ liệu vào MySQL Railway (làm một lần)
Từ máy bạn (MySQL local đã có `qsr_db` đầy đủ):
```bash
mysqldump -u root -p --single-transaction qsr_db > qsr_db.sql
mysql -h <HOST> -P <PORT> -u <USER> -p<PASS> <NAME> < qsr_db.sql
```
Dữ liệu ≈ 1,3 triệu dòng nên mất vài phút; nếu gói miễn phí hết dung lượng DB thì cần nâng gói.
Nếu chỉ muốn nạp bảng ML mà không kèm tài khoản cũ, dùng `--ignore-table` cho bảng `auth_*`, `forecast_*`.

## 4. Tạo tài khoản demo
Railway → web service → **Shell** (hoặc chạy local trỏ vào DB Railway):
```bash
python manage.py seed_demo --password "MatKhauDemo"
```
Lệnh này tạo `minh.r01`, `mai.r02`, `lan.r01`, `hung.r02`, `admin` và dữ liệu kiểm kho/đề xuất mẫu. Gửi link + mật khẩu cho nhóm.

## 5. Lưu ý
- Lần chạy dự báo đầu tiên chậm (nạp mô hình vào RAM). Cần ≥ 1 GB RAM; "Chạy tất cả cửa hàng" có thể mất vài phút (`--timeout 600` đã đặt).
- Nhắc kiểm kho cần cron: thêm Railway Cron gọi `python manage.py send_reminders`.
- Sau khi xong demo nên đổi mật khẩu và đặt repo ở chế độ private.
