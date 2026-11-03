# KỊCH BẢN KIỂM THỬ END-TO-END
**Website dự báo nhu cầu & lập danh sách chuẩn bị hàng QSR Forecast (Django + Machine Learning)**

## 1. Tổng quan

Tài liệu gồm **20 kịch bản** kiểm thử theo nghiệp vụ, chạy trên web đã nạp dữ liệu lịch sử bán hàng (≈ 1,32 triệu dòng, 15 cửa hàng × 50 món, đến hết ngày vận hành **30/10/2025**). Mỗi kịch bản kiểm tra một vấn đề thật của nhân viên, quản lý hoặc quản trị viên, ghi rõ ai làm bước nào và mong đợi gì. Phần học máy (ML) được kiểm tra xuyên suốt trong KB-M1 → KB-M4 và qua các kịch bản có bấm **Chạy dự báo**.

Kịch bản chính (KB-01 → KB-06) chạy **ghép cặp Nhân viên – Quản lý** theo vòng 6 bước: kiểm kho → dự báo → duyệt → bếp thực hiện → hoàn thành → mở lại. Các kịch bản khác một người tự chạy, mở trình duyệt thứ hai để đổi vai trò.

### 1.1 Đường link

> ⚠️ **Chưa có link thật.** 3 đường link bên dưới là chỗ để điền sau khi triển khai (xem mục 1.9). Hiện web chỉ chạy được local: `python manage.py runserver` → http://127.0.0.1:8000

| Vai trò | Link (điền sau khi triển khai) | Trang mở sau khi đăng nhập |
|---|---|---|
| Nhân viên bếp/kho | `https://<CHƯA-CÓ>/login/` | Chuẩn bị hàng (`/staff/prep/`) |
| Quản lý cửa hàng | `https://<CHƯA-CÓ>/login/` | Tổng quan (`/dashboard/`) |
| Quản trị viên | `https://<CHƯA-CÓ>/login/` | Dữ liệu (`/admin-data/`) |

Ba vai trò dùng chung một ứng dụng; hệ thống tự mở đúng màn hình theo vai trò sau khi đăng nhập. Có thể dùng một link chung cho cả ba.

### 1.2 Phân công (đề xuất, nhóm tự điều chỉnh)

| Người | Phạm vi | Kịch bản | Cách chạy |
|---|---|---|---|
| Người A | Nhân viên: kiểm kho, danh sách chuẩn bị | KB-01, KB-02, KB-05 | Ghép cặp với người B |
| Người B | Quản lý: tổng quan, duyệt, báo cáo | KB-03, KB-04, KB-06, KB-07, KB-08 | Ghép cặp với người A |
| Người C | Quản trị: dữ liệu, mô hình, cửa hàng, tài khoản, cấu hình | KB-11 → KB-16 | Tự đổi vai trò |
| Người D | Chung (đăng nhập, thông báo, hồ sơ, quyền) và học máy | KB-09, KB-10, KB-M1 → KB-M4 | Tự đổi vai trò |

### 1.3 Tài khoản dùng thử

Tạo bằng `python manage.py seed_demo`. Mật khẩu mặc định **`Qsr@2025!`** (đổi bằng `--password`).

| Tên đăng nhập | Hiển thị | Vai trò | Cửa hàng | Ghi chú |
|---|---|---|---|---|
| `minh.r01` | Nhân viên R01 | Nhân viên | R01 Downtown Chicago Grill | Đã có lịch sử kiểm kho |
| `mai.r02` | Nhân viên R02 | Nhân viên | R02 | Đã có lịch sử kiểm kho |
| `lan.r01` | Quản lý R01 | Quản lý | R01 | Có sẵn đề xuất R01 chờ duyệt |
| `hung.r02` | Quản lý R02 | Quản lý | R02 | Dùng để kiểm tra không thấy dữ liệu R01 |
| `admin` | Quản trị | Quản trị viên | Toàn hệ thống (15 cửa hàng) | Cũng đăng nhập được Django Admin `/admin/` |
| *(tạo ở KB-13)* `qa.r03` | Nhân viên thử | Nhân viên | R03 | R03–R15 chưa có kiểm kho |
| *(tạo ở KB-13)* `qa.quanly` | Quản lý thử | Quản lý | Chưa gán | Dùng thử chặn 403 |

### 1.4 Đổi vai trò khi tự test
- Hai tài khoản khác vai trò phải đăng nhập ở **2 trình duyệt khác nhau** (Chrome + Edge) hoặc 2 hồ sơ Chrome; hai tab cùng trình duyệt dùng chung phiên và sẽ đá nhau ra.
- Cửa sổ ẩn danh dùng cho thử đăng nhập sai/khóa; đóng hết cửa sổ ẩn danh là mất phiên.

### 1.5 Bối cảnh và quy tắc cần nhớ khi test

| Chủ đề | Quy tắc |
|---|---|
| Ngày | Ngày vận hành **30/10/2025**; ngày phục vụ cần chuẩn bị **31/10/2025** (Halloween). Chỉ dự báo cho ngày vận hành + 1; chọn ngày khác → "Chưa có dữ liệu". |
| Công thức | `Dự phòng = z × RMSE` (90 % → 1,28; **95 % → 1,65**; 99 % → 2,33). `Cần chuẩn bị = Dự kiến bán + Dự phòng − Đang có`, không nhỏ hơn 0. Ví dụ French Fries Regular: 118 + 25 − 20 = 123. |
| Mức độ món | **Thiếu hàng**: Đang có < Dự phòng. **Cần bổ sung**: Đang có ≥ Dự phòng nhưng Cần chuẩn bị > 0. **Đủ hàng**: Cần chuẩn bị = 0. |
| Kiểm kho | 50 món, 8 nhóm (Đồ uống, Burger, Gà, Món phụ, Combo, Bữa sáng, Tráng miệng, Đặc biệt), 5 dòng/trang. Số nhập < 25 % kỳ trước → **Cần xem lại**. Chưa đủ 50 món → chỉ Lưu nháp, không tính lại đề xuất. |
| Điều chỉnh dự báo | 5 mức: −30 / −15 / 0 / +15 / +30 %. Lý do: Sự kiện tại cửa hàng, Khuyến mãi, Thay đổi giờ phục vụ, Khác (bắt buộc nhập). |
| Duyệt | Đề xuất: Chờ duyệt → Đã duyệt. Đã duyệt thì **không chạy lại**; phải **Mở lại**; bếp vẫn thấy bản duyệt gần nhất. `require_approval` tắt → gửi bếp ngay. |
| Đề xuất hết hạn | Chạy lại tạo phiên bản mới (version + 1), bản cũ thành "Đã thay thế". |
| Hạn bếp | Mặc định 10:00 (chọn 09:00/10:00/11:00). Nhắc kiểm kho mặc định 21:00 (20:00/21:00/22:00). |
| Đăng nhập | Sai 5 lần → khóa 15 phút. Mật khẩu mới ≥ 8 ký tự. Mật khẩu tạm của tài khoản mới chỉ hiện một lần. |
| Nhập dữ liệu (admin) | Tối đa 200.000 dòng và 20 MB/tệp; CSV hoặc Excel; có xem trước, chỉ ghi sau khi xác nhận. |

### 1.6 Ảnh chụp cho báo cáo
- Máy tính: cửa sổ rộng 1280 px, thu phóng 100 %. Điện thoại: DevTools (F12) chế độ thiết bị, rộng 390 px. Chế độ sáng.
- Chụp vùng nội dung, không chụp thanh địa chỉ. Đặt tên đúng bảng (VD `KB03-1-tong-quan.png`), lưu PNG vào thư mục ảnh chung.
- Chỉ chụp khi bước chạy đúng Mong đợi; nếu có lỗi thì ghi vào bảng cuối kịch bản, sửa xong chạy lại và chụp thay.

### 1.7 Cách chạy và ghi kết quả
- Chạy theo thứ tự số trong phạm vi của mình. **Chạy KB-11 (dữ liệu) trước KB-13** nếu cần tài khoản thử.
- Bảng cuối mỗi kịch bản: **Người thực hiện** (tên + ngày), **Lỗi logic** (số tiền, trạng thái, quyền, thông báo sai), **Lỗi bố cục** (vỡ khung, chữ tràn, khó bấm trên điện thoại). Mỗi lỗi ghi bước, trình duyệt, kích thước màn hình, kèm ảnh. Không lỗi thì ghi "Không".
- Không sửa dữ liệu dùng chung ngoài kịch bản. Cấu hình bị đổi để thử phải **trả lại như cũ** trong cùng kịch bản.
- Sau khi chạy xong có thể dọn bằng `python manage.py seed_demo` để về trạng thái ban đầu.

### 1.8 Chuẩn bị môi trường
1. Bật MySQL và nạp `Database/qsr_schema.sql` + dữ liệu `data/processed/qsr_clean 13.20.26.csv` (web đọc từ MySQL, không đọc trực tiếp file CSV khi chạy).
2. `python manage.py migrate` → `python manage.py seed_demo` → `python manage.py runserver`.
3. Kiểm tra `Assets/best_model.joblib` tồn tại (mô hình tốt nhất, nạp một lần mỗi tiến trình; lần chạy dự báo đầu tiên chậm hơn).

### 1.9 Triển khai: xem `Trien_Khai.md` (Railway, một link chung cho 3 vai trò)

<details><summary>Vì sao không dùng Vercel</summary>
Chưa tạo được link và **không nên làm mà chưa xác nhận**, vì:
- Cần tài khoản/token Vercel của nhóm (việc triển khai công khai là hành động ra bên ngoài).
- Dự án dùng **MySQL** (1,3 triệu dòng) → phải có MySQL đặt trên máy chủ ngoài (PlanetScale, Railway, Aiven…), Vercel không cung cấp.
- Gói thư viện ML (pandas, CatBoost, LightGBM, scikit-learn) có thể vượt giới hạn dung lượng hàm serverless của Vercel (~250 MB); "Chạy cho tất cả cửa hàng" chạy đồng bộ có thể vượt thời gian cho phép.
- Phương án an toàn hơn: Railway/Render/Fly.io chạy `gunicorn ML_QSR.wsgi` cùng MySQL. Nếu vẫn muốn Vercel, cần thử trước xem build có qua giới hạn không.

Khi có link, điền vào bảng 1.1 và đặt biến môi trường theo `Trien_Khai.md`.

</details>

---

## 2. Kịch bản vòng chuẩn bị hàng (Nhân viên – Quản lý)

### KB-01. Nhân viên kiểm kho cuối ca và lưu nháp
**Mục tiêu:** Nhập đủ tồn kho 50 món, bị chặn khi nhập thiếu/bất thường, lưu nháp không làm tính lại đề xuất.
**Người thực hiện:** Người A (`minh.r01`)
**Chuẩn bị:** Chạy `seed_demo --no-plan` để chưa có đề xuất mới (hoặc chấp nhận bản có sẵn).

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Mở Kiểm kho | Đăng nhập `minh.r01` → menu Kiểm kho. Chọn ngày kiểm kho. | Có ghi chú đơn vị (1 ly = nguyên liệu cho 1 ly), thanh tiến độ Đã nhập / Cần xem lại / Chưa nhập, 8 nhóm món, mỗi trang 5 dòng, cột Tồn kỳ trước |
| 2. Nhập số | Nhập số còn lại cho vài món ở nhiều nhóm; riêng 1 món nhập số nhỏ hơn 25 % tồn kỳ trước (VD 40 → 4). | Món đó gắn **Cần xem lại**; thanh dưới cùng đếm số thay đổi chưa lưu |
| 3. Lưu nháp | Bấm **Lưu nháp** khi chưa đủ 50 món. | Hộp thoại "Đã lưu nháp kiểm kho (x/50 món)"; **chưa** tính lại đề xuất, chưa có thông báo cho quản lý |
| 4. Huỷ | Sửa vài ô rồi bấm **Huỷ**. | Hộp thoại có Tiếp tục nhập / Hủy thay đổi; hủy xong số về như lần lưu trước |
| 5. Lịch sử | Kéo xuống cuối trang. | Có Lịch sử kiểm kho các ca trước (ngày giờ, số món đã nhập) |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

### KB-02. Lưu & tính lại đề xuất: thiếu món, món bất thường, thành công
**Mục tiêu:** Hệ thống chặn kiểm kho chưa đầy đủ, bắt xác nhận số lệch, và chỉ tính đề xuất khi hợp lệ.
**Người thực hiện:** Người A (`minh.r01`), Người B (`lan.r01`, xem thông báo)
**Chuẩn bị:** Tiếp tục KB-01.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Thiếu món | Còn món chưa nhập, bấm **Lưu & tính lại đề xuất**. | Hộp thoại "Kiểm kho chưa đầy đủ" có nút **Nhập số còn thiếu** |
| 2. Món cần xem lại | Nhập đủ 50 món, trong đó có món lệch nhiều; bấm Lưu & tính lại. | Hộp thoại "Kiểm tra tồn kho trước khi lưu": Quay lại kiểm tra / Xác nhận và lưu |
| 3. Hợp lệ | Chọn Xác nhận và lưu. | "Đang lưu kiểm kho (đang tính lại lượng cần chuẩn bị)" → "Kiểm kho đã được lưu", đề xuất ở **Chờ duyệt** |
| 4. Quản lý nhận tin | Người B mở chuông ở `lan.r01`. | Có thông báo đề xuất mới/kiểm kho hoàn tất của R01 |
| 5. Chạy lại | Nhân viên lưu lần nữa (khi chưa duyệt). | Phiên bản đề xuất tăng; bản cũ **Đã thay thế** |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

### KB-03. Quản lý xem Tổng quan ngày phục vụ
**Mục tiêu:** Quản lý biết ngay ngày mai món nào cần xử lý gấp.
**Người thực hiện:** Người B (`lan.r01`)
**Chuẩn bị:** Có đề xuất R01 cho 31/10/2025.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Mở Tổng quan | Đăng nhập `lan.r01`. | Tự vào Tổng quan; chỉ thấy cửa hàng R01 |
| 2. Chọn ngày | Mở lịch (chuyển tháng bằng ‹ ›), chọn 31/10/2025 → Xem dữ liệu. | Có trạng thái đang tải; biểu đồ lượng bán 7 ngày (Thực tế / Dự báo) |
| 3. Ba thẻ | Đọc thẻ Thiếu hàng / Cần bổ sung / Đủ hàng. | Tổng 3 thẻ = số món trong đề xuất (50). Thẻ khớp mức độ ở trang Chuẩn bị hàng |
| 4. Việc cần xử lý | Xem bảng món thiếu hàng, bấm **Xem** ở một món. | Phân trang 5 dòng; popup "Vì sao cần chuẩn bị thêm" |
| 5. Ngày không có dữ liệu | Chọn ngày khác 31/10 (VD 05/11/2025). | "Chưa có dữ liệu cho ngày đã chọn" + nút **Chọn ngày** |
| 6. Chặn thẻ vàng | (Phối hợp KB-15) tắt cảnh báo vàng. | Thẻ Cần bổ sung ẩn |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

### KB-04. Quản lý kiểm tra đề xuất, chỉnh số lượng và hiểu lý do (có ML)
**Mục tiêu:** Quản lý đọc được phép tính, sửa từng món, hiểu vì sao mô hình đề xuất.
**Người thực hiện:** Người B (`lan.r01`)
**Chuẩn bị:** Đề xuất R01 đang Chờ duyệt.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Bảng đề xuất | Menu Chuẩn bị hàng, chọn 31/10/2025. | Có Hạn chuẩn bị (10:00), nút Tải Excel, nút Duyệt, dòng "Kiểm kho: tên · ngày giờ"; cột Món, Dự báo, Tồn an toàn, Tồn hiện tại, Cần chuẩn bị, Trạng thái, Lý do |
| 2. Kiểm tra công thức | Chọn 3 món, tính tay `Dự báo + Tồn an toàn − Tồn hiện tại`. | Khớp cột Cần chuẩn bị (không âm). Mức độ đúng định nghĩa mục 1.5 |
| 3. Bộ lọc | Bấm Tất cả / Thiếu hàng / Cần bổ sung / Đủ hàng. | Số trên nhãn khớp số dòng; **Đủ hàng = 0** → hộp thoại "Không cần chuẩn bị thêm (0/50 món)" |
| 4. Lý do | Bấm **Xem** ở một món. | Phép tính, dự phòng, các yếu tố (lượng bán gần đây, thứ trong tuần, sự kiện, thời tiết, khuyến mãi), 4 ngày cùng thứ gần nhất |
| 5. Sửa số | Bấm số ở cột Cần chuẩn bị, đổi (VD 123 → 130), Lưu số lượng. | Dòng ghi nhãn **Đã sửa** + "Đề xuất gốc 123" |
| 6. Phân trang | Bấm Trang 2, 3… | Danh sách và bộ lọc giữ nguyên, tổng 50 món |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

### KB-05. Quản lý duyệt, bếp thực hiện, hoàn thành
**Mục tiêu:** Bếp chỉ thấy danh sách sau khi quản lý duyệt; xong hết thì quản lý được báo.
**Người thực hiện:** Người B (`lan.r01`), Người A (`minh.r01`)
**Chuẩn bị:** Đề xuất Chờ duyệt; `require_approval` đang **bật**.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Bếp khi chờ | `minh.r01` mở Chuẩn bị hàng. | Nhãn **Chờ duyệt**, "Hoàn thành 0/… việc · Hạn 10:00", "Chờ quản lý duyệt"; danh sách chưa hiện; có nút **Mở kiểm kho** |
| 2. Duyệt | `lan.r01` bấm **Duyệt**. | Hộp thoại tóm tắt cửa hàng, ngày, người duyệt, phạm vi 50 món, phân loại, tổng gốc và tổng sau điều chỉnh. Chọn Duyệt |
| 3. Sau duyệt | Nhìn lại trang. | Trạng thái **Đã duyệt** (người duyệt, giờ); nút **Chạy dự báo vô hiệu**; thử bấm → hộp thoại "Đã duyệt – không chạy lại dự báo" |
| 4. Bếp thực hiện | `minh.r01` tải lại. | Dòng "Đã duyệt · tên · giờ", tổng số lượng đã chốt, "Đã xong n/50"; 2 nhóm Thiếu hàng – làm trước / Cần bổ sung; mỗi dòng ghi "Làm thêm …" |
| 5. Đánh dấu xong | Bấm **Đánh dấu xong** cho vài món. | Món chuyển sang cột **Đã xong** kèm tên người và giờ; đếm n/50 tăng |
| 6. Hoàn thành | Đánh dấu hết món. | Nhãn **Hoàn thành**; `lan.r01` có thông báo "đã hoàn tất" |
| 7. Tải danh sách | `lan.r01` bấm **Tải Excel**. | Tải được file CSV (mở được bằng Excel, đúng dấu tiếng Việt) |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

### KB-06. Mở lại danh sách đã duyệt và duyệt lại
**Mục tiêu:** Quản lý đổi được kế hoạch sau khi duyệt mà bếp không bị mất danh sách.
**Người thực hiện:** Người B (`lan.r01`), Người A (`minh.r01`)
**Chuẩn bị:** Đã làm KB-05 bước 2–3 (đã duyệt, chưa xong hết).

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Mở lại | Ở trang Chuẩn bị hàng bấm **Mở lại danh sách**, chọn Mở lại danh sách (hoặc Hủy). | Trạng thái về chờ chỉnh; nút Chạy dự báo bật lại |
| 2. Bếp trong lúc mở lại | `minh.r01` tải lại. | **Vẫn thấy bản duyệt gần nhất**, tiếp tục đánh dấu được |
| 3. Chạy lại | Quản lý chạy dự báo lại (kiểm kho đã đổi) và Duyệt. | Phiên bản mới thay thế; bếp thấy danh sách mới sau khi duyệt lại |
| 4. Tắt duyệt | (Phối hợp KB-15) tắt `require_approval`, nhân viên lưu kiểm kho. | Danh sách tới bếp ngay, không cần duyệt |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

---

## 3. Kịch bản Quản lý: dự báo và báo cáo

### KB-07. Trang Dự báo: xem, điều chỉnh %, tạo đề xuất (có ML)
**Mục tiêu:** Quản lý áp tỷ lệ điều chỉnh khi biết trước điều mô hình chưa biết, rồi tạo đề xuất.
**Người thực hiện:** Người B (`lan.r01`)
**Chuẩn bị:** R01 đã có kiểm kho đã lưu.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Xem dự báo | Menu Dự báo, chọn ngày 31/10, bấm **Xem dự báo**. | Dải ngày: 31/10 "Đã có dự báo" (tổng phần); các ngày sau "Chờ số bán ngày trước" |
| 2. So với bình thường | Đọc bảng Dự báo theo món. | Mỗi món có mức **Bình thường** (TB 7 ngày) và mức chênh (VD "Nhiều hơn 52 %"); Xem danh sách mở đủ món |
| 3. Yếu tố ảnh hưởng | Đọc khung yếu tố. | Hiện Sự kiện, Thời tiết, Ngày lễ, Khuyến mãi của 31/10 (Halloween là sự kiện) |
| 4. Điều chỉnh | Chọn +15 %, lý do "Khuyến mãi", Lưu điều chỉnh. | Chỉ có 5 mức (−30/−15/0/+15/+30); xác nhận nêu tổng dự báo sau điều chỉnh + lý do. Chọn "Khác" mà không nhập lý do → bị chặn |
| 5. Tạo đề xuất | Bấm **Tạo đề xuất chuẩn bị**. | "Đang chạy dự báo" → "Dự báo đã hoàn tất" (cửa hàng, ngày, tổng, 50 món, **Chờ duyệt**) |
| 6. Ngày sai | Chọn ngày khác 31/10 rồi Tạo đề xuất. | "Không thể chạy dự báo", có nút Chạy lại; không dùng số bán sau 30/10 |
| 7. Đã duyệt | Khi đã duyệt, thử tạo lại. | Bị chặn, có hướng dẫn Mở lại |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|
| | | |

### KB-08. Báo cáo xu hướng và độ chính xác
**Mục tiêu:** Quản lý xem lại số liệu và độ chính xác dự báo; báo rõ khi chưa đủ dữ liệu.
**Người thực hiện:** Người B (`lan.r01`)
**Chuẩn bị:** Không.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Chọn kỳ | Mở Báo cáo, chọn cửa hàng (chỉ thấy R01) và khoảng thời gian, **Xem báo cáo**. | Có trạng thái "Đang tải báo cáo" |
| 2. Tab Xu hướng | Đọc doanh thu theo tháng, tổng phần đã bán, món doanh thu cao nhất. | Có số bán TB theo tháng/theo thứ; chênh lệch theo 6 yếu tố (sự kiện, khuyến mãi, cuối tuần, ngày lễ, mưa, tuyết); bán chạy nhất/chậm nhất |
| 3. Tab Độ chính xác | Chuyển tab. | wMAPE/sai số TB của kỳ đối chiếu và sai số từng ngày; ngày chưa có số thực tế ghi rõ **chưa đánh giá** |
| 4. Thiếu dữ liệu | Chọn kỳ không có dữ liệu đối chiếu. | Thông báo kèm nút **Chọn kỳ đối chiếu** |
| 5. Chỉ đọc | Tìm nút sửa/ghi. | Không có; báo cáo chỉ đọc |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

---

## 4. Kịch bản dùng chung và phân quyền

### KB-09. Đăng nhập, ghi nhớ, khóa, cấp lại mật khẩu
**Mục tiêu:** Đăng nhập an toàn và mở đúng màn hình theo vai trò.
**Người thực hiện:** Người D (ẩn danh)

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Sai thông tin | Đăng nhập `lan.r01` với mật khẩu sai. | Hộp thoại "Không thể đăng nhập", bấm Đóng thử lại; không nói sai tên hay sai mật khẩu |
| 2. Khóa | Sai liên tiếp 5 lần. | Bị khóa **15 phút**, kể cả nhập đúng; sau 15 phút đăng nhập lại được |
| 3. Chọn nhanh | Mở danh sách ở ô tên đăng nhập. | Có 3 tài khoản mẫu (lan.r01, minh.r01, admin) |
| 4. Mở đúng trang | Đăng nhập lần lượt 3 vai trò. | Nhân viên → Chuẩn bị hàng; Quản lý → Tổng quan; Quản trị → Dữ liệu |
| 5. Ghi nhớ | Tick **Ghi nhớ đăng nhập**, đóng và mở lại trình duyệt. | Vẫn đăng nhập; không tick thì mất phiên khi đóng |
| 6. Quên mật khẩu | Bấm **Cấp lại mật khẩu**, nhập tên đăng nhập, Ghi nhận yêu cầu. | Hộp thoại: trạng thái **Chờ xử lý**, người xử lý Quản trị viên, kèm giờ |
| 7. Đăng xuất | Bấm tên tài khoản → Đăng xuất. | Về trang đăng nhập; nút Back không vào lại được |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-10. Thông báo, hồ sơ, đổi mật khẩu và chặn quyền
**Mục tiêu:** Mỗi vai trò chỉ thấy thông báo và trang của mình.
**Người thực hiện:** Người D (3 vai trò)

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Chuông | Mở chuông ở từng vai trò. | NV: đề xuất chờ duyệt (nút Mở danh sách chuẩn bị, Mở kiểm kho). QL: đề xuất mới, kiểm kho hoàn tất, sự kiện sắp tới (Halloween), danh sách hoàn thành. QTV: dữ liệu thiếu số lượng (nút Kiểm tra dữ liệu) |
| 2. Đã đọc | Đánh dấu đã đọc một dòng, rồi **Đánh dấu tất cả đã đọc**; mở Xem tất cả thông báo. | Số trên chuông giảm; nút Xem mỗi dòng đi đúng trang |
| 3. Hồ sơ | Bấm tên tài khoản. | Thấy tên, cửa hàng, vai trò (**không tự đổi được**) |
| 4. Đổi mật khẩu | Thử: thiếu trường; mật khẩu mới dưới 8 ký tự; sai mật khẩu hiện tại; rồi đúng. | 3 lỗi đầu: "Không thể cập nhật mật khẩu". Đúng: "Mật khẩu đã được cập nhật"; đăng nhập lại bằng mật khẩu mới được (đổi lại như cũ sau khi thử) |
| 5. Tùy chọn | Tắt "thông báo khi có đề xuất mới"/"nhắc kiểm kho", làm một việc tạo thông báo. | Thông báo loại đó không còn hiện với tài khoản này. (Email hằng tuần: chỉ lưu công tắc, **chưa gửi mail**) |
| 6. Sai vai trò | NV mở `/dashboard/`; QL mở `/admin-data/`; QL mở `/staff/inventory/`. | Màn "Không có quyền truy cập" + nút **Về trang của tôi** về đúng trang theo vai trò |
| 7. Cách ly cửa hàng | `hung.r02` mở Chuẩn bị hàng. | Chỉ thấy R02, không thấy dữ liệu R01 |
| 8. Chưa gán cửa hàng | Đăng nhập `qa.quanly` (từ KB-13). | Bị chặn 403 thay vì lỗi trang |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

---

## 5. Kịch bản Quản trị viên

### KB-11. Dữ liệu: tổng quan và dòng thiếu
**Người thực hiện:** Người C (`admin`)

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Lọc | Menu Dữ liệu, chọn khoảng thời gian (có nút Toàn bộ dữ liệu), **Lọc dữ liệu**. | "Đang lọc dữ liệu"; số liệu đổi theo kỳ |
| 2. Cảnh báo | Đọc dải cảnh báo. | Số dòng thiếu số lượng bán (≈ 5.261 dòng, 0,4 % đến ngày vận hành) và cách xử lý là ước tính |
| 3. Các dòng thiếu | Bấm **Xem các dòng thiếu**. | Danh sách ngày bán, cửa hàng, món |
| 4. 6 nhóm | Đọc bảng nhóm dữ liệu, bấm **Mở** từng dòng. | 6 nhóm: Bán hàng hằng ngày, Khuyến mãi, Thời tiết, Ngày lễ & sự kiện, Kiểm kho, Dự báo; có số dòng, phạm vi, trạng thái; **Kiểm kho và Dự báo không nhập tay** |
| 5. Phân quyền | Đăng nhập `lan.r01`, mở `/admin-data/`. | Không có quyền |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-12. Nhập dữ liệu CSV/Excel (5 bước)
**Mục tiêu:** Nhập bổ sung dữ liệu an toàn, có xem trước, không ghi sai.
**Người thực hiện:** Người C (`admin`)
**Chuẩn bị:** Chuẩn bị 3 tệp nhỏ: CSV khuyến mãi hợp lệ (cột `promo_date`, `restaurant_id`, `menu_item_id`, ngày > 30/10/2025 để không ảnh hưởng dự báo); CSV thiếu cột; tệp .txt. **Ghi lại để xóa sau.**

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Nhóm dữ liệu | Bấm **Nhập dữ liệu**, chọn Khuyến mãi. | Chỉ 4 nhóm cho chọn (Bán hàng, Khuyến mãi, Thời tiết, Ngày lễ & sự kiện) |
| 2. Cách nhập | Chọn **Thêm dữ liệu mới**. | Có 2 cách: Thêm mới / Cập nhật theo khóa |
| 3. Tệp sai | Chưa chọn tệp, rồi tệp .txt, rồi CSV thiếu cột; bấm **Kiểm tra và xem trước**. | "Chưa thể xem trước dữ liệu" kèm lý do (cột thiếu, sai định dạng) |
| 4. Xem trước | Chọn CSV hợp lệ. | Tên tệp, kiểm tra cột/định dạng, vài dòng mẫu, số dòng hợp lệ/trùng khóa. **Chưa ghi DB** (số dòng nhóm vẫn như cũ) |
| 5. Ghi | Bấm **Nhập dữ liệu**. | "Đang nhập dữ liệu" → "Dữ liệu đã được nhập"; số dòng Khuyến mãi tăng đúng số dòng hợp lệ |
| 6. Nhập lại | Nhập lại đúng tệp đó (Thêm mới). | Dòng trùng khóa bị bỏ/báo, không nhân đôi |
| 7. Cập nhật theo khóa | Nhập tệp bán hàng bù số lượng cho dòng đang thiếu (Cập nhật theo khóa). | Số dòng thiếu giảm tương ứng |
| 8. Giới hạn | Thử tệp > 20 MB hoặc > 200.000 dòng. | Bị từ chối với thông báo rõ |
| 9. Dọn | Xóa các dòng thử khỏi DB. | Dữ liệu về như trước (ghi vào bảng lỗi nếu không dọn được) |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-13. Tài khoản: thêm, sửa, khóa, cấp lại mật khẩu
**Người thực hiện:** Người C (`admin`), trình duyệt B để thử đăng nhập

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Danh sách | Menu Tài khoản; lọc theo vai trò; bấm tìm. | Bảng Tên, Tên đăng nhập, Vai trò, Phạm vi, Sửa; hộp thoại tìm theo tên hiển thị/tên đăng nhập, có Xóa bộ lọc |
| 2. Thêm | Thêm `qa.r03` (Nhân viên, R03), Lưu tài khoản. | "Tài khoản đã được cập nhật"; hiện **mật khẩu tạm một lần** (đóng rồi không xem lại được) |
| 3. Thêm quản lý | Thêm `qa.quanly` (Quản lý, **không chọn cửa hàng**). | Bị chặn "Chưa thể lưu tài khoản" vì phạm vi không hợp vai trò; hoặc lưu được nhưng đăng nhập bị 403 (KB-10 bước 8) — ghi lại hành vi thực tế |
| 4. Trùng/thiếu | Thêm tên đăng nhập đã có; thêm thiếu Tên hiển thị. | Bị chặn kèm lý do |
| 5. Một quản lý/cửa hàng | Thêm quản lý thứ hai cho R01. | Bị chặn |
| 6. Đăng nhập mật khẩu tạm | Ở B đăng nhập `qa.r03`. | Vào được; chỉ thấy R03 (chưa có kiểm kho) |
| 7. Cấp lại mật khẩu | Cấp lại mật khẩu cho `qa.r03`. | Mật khẩu tạm mới hiện một lần; mật khẩu cũ hết dùng |
| 8. Vô hiệu hóa | Vô hiệu `qa.r03`. | Hộp thoại xác nhận "Ngừng hoạt động"; ở B không đăng nhập được; lịch sử duyệt/kiểm kho còn |
| 9. Tự bảo vệ | Thử vô hiệu chính `admin`. | Bị chặn; không khóa được **quản trị viên cuối cùng** |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-14. Cửa hàng: thêm, sửa, gán quản lý
**Người thực hiện:** Người C (`admin`)

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Bảng | Menu Cửa hàng. | Bảng Mã, Tên, Thành phố, Số món, TB phần/ngày 2025, Quản lý phụ trách, Trạng thái; cửa hàng cần xử lý xếp trước; cảnh báo vàng cho cửa hàng **chưa gán quản lý** kèm nút Gán quản lý |
| 2. Thêm | Nhập Mã, Tên, Thành phố, Lưu; rồi bỏ trống một trường. | Đủ: "Thông tin cửa hàng đã được lưu". Thiếu: "Chưa thể lưu cửa hàng" |
| 3. Gán quản lý | Sửa R03, chọn quản lý phụ trách (VD `qa.quanly`). | Lưu được; cảnh báo vàng của R03 biến mất |
| 4. Chuyển cửa hàng | Gán quản lý đó sang cửa hàng khác. | Phân công mới **thay thế** cửa hàng cũ của quản lý (cửa hàng cũ về Chưa gán) |
| 5. Dọn | Trả gán về như ban đầu. | Cấu hình khớp seed |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-15. Cấu hình hệ thống và tác động tới vòng chuẩn bị
**Mục tiêu:** Mỗi thiết lập đổi đúng hành vi hệ thống. **Cấu hình nào đổi phải trả lại.**
**Người thực hiện:** Người C (`admin`), người B (`lan.r01`), người A (`minh.r01`)

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Mức an toàn | Đổi 95 % → 99 %, **Lưu cấu hình**, quản lý chạy lại dự báo. | Hộp thoại "Cấu hình đã được lưu"; Tồn an toàn tăng (z 1,65 → 2,33); số món Thiếu hàng không giảm. Đổi lại 95 % sau khi thử |
| 2. Cảnh báo đỏ | Tắt cảnh báo đỏ, tạo đề xuất có món thiếu. | Không sinh thông báo "thiếu hàng" |
| 3. Cảnh báo vàng | Tắt cảnh báo vàng. | Thẻ "Cần bổ sung" ở Tổng quan quản lý ẩn |
| 4. Tự lập sau kiểm kho | Tắt "tự lập đề xuất sau khi lưu kiểm kho"; nhân viên lưu kiểm kho. | Không tự có đề xuất mới; bật lại thì có |
| 5. Cho phép quản lý chạy | Tắt "cho phép quản lý bấm Chạy dự báo". | Nút Chạy dự báo ở quản lý bị khóa/báo không có quyền |
| 6. Hạn bếp | Đổi hạn 10:00 → 11:00. | Hiện 11:00 ở Chuẩn bị hàng của cả quản lý lẫn nhân viên |
| 7. Giờ nhắc | Đổi giờ nhắc kiểm kho; chạy `python manage.py send_reminders` khi nhân viên chưa kiểm kho. | Nhân viên có thông báo nhắc (cần cron chạy lệnh theo giờ khi triển khai) |
| 8. Điều kiện gửi bếp | Thử tìm ô "Quản lý phê duyệt" trên trang Cấu hình. | **Không sửa được ở đây** (chỉ trong Django Admin `/admin/` → Cấu hình hệ thống); ghi lại khác biệt với thiết kế nếu cần |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-16. Admin chạy dự báo cho cửa hàng và toàn hệ thống (có ML)
**Mục tiêu:** Chạy đúng cửa hàng đủ điều kiện, bỏ qua cửa hàng chưa kiểm kho hoặc đã duyệt.
**Người thực hiện:** Người C (`admin`)
**Chuẩn bị:** Đề xuất R01 đã duyệt hoặc chờ duyệt; R03–R15 chưa kiểm kho.

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Thông tin mô hình | Menu Dự báo & Mô hình. | Mô hình đang dùng, kết quả offline (wMAPE test ≈ 14,5 %, đọc từ `metrics.csv`), ghi chú dữ liệu demo đến 30/10/2025 |
| 2. Bảng 15 cửa hàng | Đọc bảng. | Sắp xếp **Cần xử lý trước**; cột Kiểm kho, Dự báo, Đề xuất (VD Chờ duyệt), nút Chạy; ghi rõ cửa hàng chưa có dữ liệu / chưa chạy / chưa gán quản lý |
| 3. Chạy một cửa hàng | Bấm Chạy cho R02. | "Đang chạy dự báo" → "Dự báo cửa hàng đã hoàn tất" (cửa hàng, ngày, 50 món, tổng, Chờ duyệt) |
| 4. Chưa kiểm kho | Bấm Chạy cho R03. | Báo chưa có kiểm kho, không tạo đề xuất |
| 5. Đã duyệt | Chạy cửa hàng đã duyệt. | "Đã duyệt – không chạy lại", quản lý cần Mở lại trước |
| 6. Chạy tất cả | Bấm **Chạy cho tất cả cửa hàng**. | Xác nhận (15 cửa hàng, 750 cặp, lưu ý bếp giữ danh sách đến lần duyệt mới) → "Đang chạy · Toàn hệ thống" → "đã hoàn tất", liệt kê cửa hàng **bị bỏ qua** (chưa kiểm kho / đã duyệt). *Chạy tuần tự, có thể mất vài phút.* |
| 7. Biểu đồ | Chọn một cửa hàng. | Số bán thật đến 30/10, ngày 31/10 chỉ có dự báo |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

---

## 6. Kịch bản học máy

### KB-M1. Tính đúng đắn của công thức tồn an toàn và mức độ
**Người thực hiện:** Người D

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Công thức | Ở R01 chọn 5 món, so với số hệ thống: `Cần chuẩn bị = Dự báo + 1,65×RMSE − Tồn`. | Khớp (±1 do làm tròn); ghi lại chênh lệch nếu có (mã làm tròn một lần cuối, PDF yêu cầu làm tròn trước khi cộng) |
| 2. Không âm | Tìm món tồn rất lớn. | Cần chuẩn bị = 0, mức **Đủ hàng** |
| 3. Phân mức | Món có Tồn < Dự phòng. | **Thiếu hàng**; món Tồn ≥ Dự phòng nhưng Cần chuẩn bị > 0 → **Cần bổ sung** |
| 4. Điều chỉnh % | Áp +30 % rồi so lại. | Dự báo tăng đúng 30 %, cần chuẩn bị tính lại; chỉnh tay từng món giữ nguyên số đã sửa |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-M2. Mô hình chỉ dùng dữ liệu đến hết ngày vận hành
**Người thực hiện:** Người D, Người C

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Ngày ngoài phạm vi | Chạy dự báo cho ngày khác 31/10/2025. | Từ chối, không đọc số bán sau 30/10 |
| 2. Nhập dữ liệu tương lai | Admin nhập 1 dòng bán 31/10 (tệp thử), quản lý chạy dự báo 31/10. | Số dự báo **không đổi** theo dòng vừa nhập (dùng đến 30/10). Xóa dòng thử sau đó |
| 3. Ngày vận hành | Đổi ngày vận hành trong Django Admin sang 31/10, quản lý chọn 01/11. | Dự báo cho ngày mới hoạt động; **trả lại 30/10** |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-M3. Độ chính xác và so sánh mô hình
**Người thực hiện:** Người D

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Số offline | So bảng mô hình (admin) với `Assets/reports/metrics.csv`. | Khớp wMAPE/MAE/RMSE; mô hình tốt nhất thấp hơn 2 baseline (SeasonalNaive 0,2288; MovingAverage 0,1992 trên tập test) |
| 2. Độ chính xác trên web | Báo cáo → tab Độ chính xác, kỳ đã có số thật. | Sai số theo ngày khớp tự tính (|dự báo − thực tế| / thực tế) trên 3 ngày mẫu |
| 3. Ngày chưa có thực tế | Chọn ngày sau 30/10. | Ghi "chưa đánh giá", không hiện số giả |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

### KB-M4. Hiệu năng và độ ổn định khi chạy dự báo
**Người thực hiện:** Người D

| Bước | Thao tác | Mong đợi |
|---|---|---|
| 1. Lần đầu | Khởi động lại server, chạy dự báo R01, ghi thời gian. | Hoàn tất; lần đầu chậm hơn (nạp model một lần) |
| 2. Lần sau | Chạy lại ngay. | Nhanh hơn rõ rệt, kết quả cùng dữ liệu → cùng số |
| 3. Hai người cùng lúc | `lan.r01` và `admin` cùng chạy R01. | Không lỗi 500; tạo đúng một phiên bản mới mỗi lần, không có 2 đề xuất trùng phiên bản |
| 4. Thiếu model | Đổi tên tạm `Assets/best_model.joblib`, chạy dự báo, rồi đổi lại. | Báo lỗi dễ hiểu, không sập trang (ghi lại hành vi) |

| Người thực hiện | Lỗi logic | Lỗi bố cục |
|---|---|---|

---

## 7. Bảng tổng hợp kết quả

| Kịch bản | Người chạy | Ngày | Kết quả (Đạt / Lỗi) | Số lỗi logic | Số lỗi bố cục |
|---|---|---|---|---|---|
| KB-01 … KB-16, KB-M1 … KB-M4 | | | | | |

**Ghi chú mở:** (1) 3 link Vercel chưa có, xem 1.9. (2) Sai khác với thiết kế đã biết: làm tròn một lần cuối; "Quản lý phê duyệt" chỉ sửa ở Django Admin; email hằng tuần chưa gửi; Excel xuất ra CSV.
