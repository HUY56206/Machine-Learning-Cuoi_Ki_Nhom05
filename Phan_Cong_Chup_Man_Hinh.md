# Phân công chụp màn hình QSR Forecast

Tổng 102 ảnh. Đặt tên ảnh theo mã (ví dụ `B13.png`).

| Nhóm | Người phụ trách | Tài khoản | Số ảnh |
|---|---|---|---|
| Nhóm A · Nhân viên | Trầm | `khanh.r01` | 27 |
| Nhóm B · Quản lý | Toàn | `lan.r01` | 36 |
| Nhóm C · Quản trị viên | Lê | `admin` | 39 |

**Lưu ý:** chạy `python manage.py seed_demo --reset` một lần trước khi bắt đầu. Nhóm A kiểm kho trước, nhóm B duyệt sau, rồi nhóm A mới chụp được danh sách đã duyệt. Hai vai trò khác nhau dùng hai trình duyệt hoặc hai hồ sơ Chrome.

## Nhóm A · Nhân viên · Trầm (`khanh.r01`)

**Đăng nhập**
- [ ] A1. Trang đăng nhập
- [ ] A2. Sai mật khẩu: hộp thoại “Không thể đăng nhập”
- [ ] A3. Bị khóa sau 5 lần sai
- [ ] A4. Hộp thoại “Yêu cầu cấp lại mật khẩu”
- [ ] A5. Yêu cầu đã được ghi nhận

**Chuẩn bị hàng  /staff/prep/**
- [ ] A6. Chưa có đề xuất
- [ ] A7. Đang chờ quản lý duyệt
- [ ] A8. Đã duyệt: hai nhóm Thiếu hàng và Cần bổ sung
- [ ] A9. Đã đánh dấu xong vài món
- [ ] A10. Hoàn thành (xong hết các món)
- [ ] A11. Tự động gửi bếp (khi tắt yêu cầu duyệt)

**Kiểm kho  /staff/inventory/**
- [ ] A12. Trang Kiểm kho, nhóm Đồ uống
- [ ] A13. Một nhóm khác (ví dụ Burger)
- [ ] A14. Món bị gắn “Cần xem lại”
- [ ] A15. Lịch chọn ngày kiểm kho
- [ ] A16. Lịch sử kiểm kho (cuối trang)
- [ ] A17. Hộp thoại “Đã lưu nháp kiểm kho”
- [ ] A18. Hộp thoại “Kiểm kho chưa đầy đủ”
- [ ] A19. Hộp thoại “Kiểm tra tồn kho trước khi lưu”
- [ ] A20. Hộp thoại “Kiểm kho đã được lưu”
- [ ] A21. Hộp thoại “Hủy thay đổi kiểm kho”
- [ ] A22. Xem ngày quá khứ (chỉ xem, không lưu được)

**Dùng chung**
- [ ] A23. Chuông thông báo
- [ ] A24. Hồ sơ cá nhân
- [ ] A25. Đổi mật khẩu: báo lỗi
- [ ] A26. Đổi mật khẩu: thành công
- [ ] A27. Không có quyền truy cập (mở /dashboard/)

## Nhóm B · Quản lý · Toàn (`lan.r01`)

**Tổng quan  /dashboard/**
- [ ] B1. Mặc định: biểu đồ 7 ngày và 3 thẻ
- [ ] B2. Bảng “Việc cần xử lý”
- [ ] B3. Hộp thoại “Vì sao cần chuẩn bị thêm” (có phần SHAP)
- [ ] B4. Lịch chọn ngày
- [ ] B5. Ngày chưa có dữ liệu

**Chuẩn bị hàng  /prep/**
- [ ] B6. Danh sách đang chờ duyệt
- [ ] B7. Bộ lọc Thiếu hàng
- [ ] B8. Bộ lọc Cần bổ sung
- [ ] B9. Bộ lọc Đủ hàng (hoặc hộp thoại “Không cần chuẩn bị thêm”)
- [ ] B10. Hộp thoại “Vì sao cần chuẩn bị thêm”
- [ ] B11. Hộp thoại “Điều chỉnh số lượng”
- [ ] B12. Dòng có nhãn “Đã sửa” và “Đề xuất gốc”
- [ ] B13. Hộp thoại “Duyệt danh sách chuẩn bị”
- [ ] B14. Hộp thoại “Danh sách đã được duyệt”
- [ ] B15. Trạng thái Đã duyệt (nút Chạy dự báo bị khóa)
- [ ] B16. Hộp thoại “Mở lại danh sách đã duyệt?”
- [ ] B17. Trạng thái Đã mở lại
- [ ] B18. Hộp thoại “Dự báo đã hoàn tất”
- [ ] B19. File CSV tải về, mở bằng Excel

**Dự báo  /forecast/**
- [ ] B20. Trang Dự báo với 3 thẻ ngày
- [ ] B21. Khung yếu tố ảnh hưởng và thanh điều chỉnh %
- [ ] B22. Chọn lý do điều chỉnh
- [ ] B23. Nhập lý do khác
- [ ] B24. Hộp thoại “Điều chỉnh dự báo đã được lưu”
- [ ] B25. Hộp thoại “Dự báo theo món” (Xem danh sách)
- [ ] B26. Tạo đề xuất: hoàn tất
- [ ] B27. Hộp thoại “Không thể chạy dự báo” (ngày ngoài dữ liệu)
- [ ] B28. Lịch chọn ngày (chỉ 07 đến 12/2025)

**Báo cáo  /report/**
- [ ] B29. Tab Xu hướng
- [ ] B30. Tab Độ chính xác
- [ ] B31. Hộp thoại “Chọn kỳ báo cáo”
- [ ] B32. Thông báo thiếu dữ liệu đối chiếu

**Dùng chung**
- [ ] B33. Chuông thông báo
- [ ] B34. Hồ sơ cá nhân
- [ ] B35. Đổi mật khẩu: thành công
- [ ] B36. Không có quyền truy cập (mở /admin-data/)

## Nhóm C · Quản trị viên · Lê (`admin`)

**Dữ liệu  /admin-data/**
- [ ] C1. Tổng quan dữ liệu
- [ ] C2. Lọc theo khoảng thời gian
- [ ] C3. Hộp thoại “Các dòng thiếu số lượng”
- [ ] C4. Mở một nhóm dữ liệu
- [ ] C5. Chọn nhóm dữ liệu nhập
- [ ] C6. Chọn cách nhập dữ liệu
- [ ] C7. Tệp sai: “Chưa thể xem trước dữ liệu”
- [ ] C8. Hộp thoại “Xem trước dữ liệu nhập”
- [ ] C9. Hộp thoại “Dữ liệu đã được nhập”
- [ ] C10. Bảng nhóm dữ liệu, trang 2

**Dự báo & Mô hình  /admin-model/**
- [ ] C11. Trang mô hình: chọn cửa hàng và biểu đồ
- [ ] C12. Khu “Mô hình dựa vào đâu để dự báo” theo nhóm
- [ ] C13. Chi tiết một món (chọn món)
- [ ] C14. Bảng 15 cửa hàng, trang 1
- [ ] C15. Bảng 15 cửa hàng, trang 2 hoặc sắp xếp
- [ ] C16. Chạy một cửa hàng: hoàn tất
- [ ] C17. Chạy cửa hàng chưa kiểm kho: báo lỗi
- [ ] C18. Xác nhận “Chạy dự báo cho tất cả cửa hàng”
- [ ] C19. Dự báo toàn hệ thống đã hoàn tất

**Cửa hàng  /admin-stores/**
- [ ] C20. Bảng cửa hàng
- [ ] C21. Hộp thoại thêm hoặc sửa cửa hàng
- [ ] C22. Chọn quản lý phụ trách
- [ ] C23. Lỗi “Chưa thể lưu cửa hàng”
- [ ] C24. Hộp thoại “Thông tin cửa hàng đã được lưu”

**Tài khoản  /admin-accounts/**
- [ ] C25. Danh sách tài khoản
- [ ] C26. Tìm kiếm tài khoản
- [ ] C27. Hộp thoại thêm tài khoản
- [ ] C28. Chọn vai trò và phạm vi
- [ ] C29. Mật khẩu tạm hiện một lần
- [ ] C30. Hộp thoại “Vô hiệu hóa tài khoản?”
- [ ] C31. Hộp thoại “Đã cấp lại mật khẩu”

**Cấu hình  /admin-config/**
- [ ] C32. Trang Cấu hình
- [ ] C33. Chọn mức an toàn
- [ ] C34. Chọn hạn chuẩn bị
- [ ] C35. Hộp thoại “Quy trình phê duyệt bắt buộc”
- [ ] C36. Hộp thoại “Cấu hình đã được lưu”

**Dùng chung**
- [ ] C37. Chuông thông báo (có yêu cầu cấp lại mật khẩu)
- [ ] C38. Hồ sơ cá nhân
- [ ] C39. Không có quyền truy cập (mở /prep/)
