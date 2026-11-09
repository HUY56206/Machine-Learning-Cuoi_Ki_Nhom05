# MỤC LỤC BÁO CÁO ĐỒ ÁN

**Đề tài:** Ứng dụng Machine Learning trong dự báo nhu cầu ngắn hạn và tối ưu tồn kho cho chuỗi nhà hàng phục vụ nhanh (QSR)
**Môn:** Học máy trong kinh doanh

---

## CHƯƠNG 1. GIỚI THIỆU
- 1.1. Bối cảnh và lý do thực hiện đề tài
- 1.2. Vấn đề cần giải quyết
- 1.3. Mục tiêu của dự án
  - 1.3.1. Mục tiêu kinh doanh
  - 1.3.2. Mục tiêu học máy
- 1.4. Phạm vi và giới hạn của dự án
  - 1.4.1. Đối tượng sử dụng
  - 1.4.2. Phạm vi dữ liệu
  - 1.4.3. Phạm vi chức năng
  - 1.4.4. Ngoài phạm vi
  - 1.4.5. Giới hạn của đề tài
- 1.5. Phương pháp nghiên cứu và cách tiếp cận
- 1.6. Bố cục báo cáo

## CHƯƠNG 2. CƠ SỞ LÝ THUYẾT
- 2.1. Tổng quan các khái niệm liên quan
  - 2.1.1. Chuỗi nhà hàng phục vụ nhanh và bài toán chuẩn bị hàng
  - 2.1.2. Dự báo nhu cầu và dữ liệu chuỗi thời gian
  - 2.1.3. Học máy có giám sát trên dữ liệu bảng
  - 2.1.4. Học máy giải thích được (XAI)
  - 2.1.5. Quản trị tồn kho: tồn an toàn và mức phục vụ
- 2.2. Các nghiên cứu và dự án liên quan
  - 2.2.1. Dự báo nhu cầu trong bán lẻ và F&B
  - 2.2.2. Gradient boosting trong các cuộc thi dự báo
  - 2.2.3. Giải thích mô hình dự báo
  - 2.2.4. Kết hợp dự báo với quyết định tồn kho
  - 2.2.5. Khoảng trống và định vị của đề tài
- 2.3. Lý thuyết và mô hình được áp dụng
  - 2.3.1. Mô hình cơ sở: Seasonal Naive và Moving Average
  - 2.3.2. Hồi quy tuyến tính và Ridge Regression
  - 2.3.3. CatBoost
  - 2.3.4. LightGBM
  - 2.3.5. Độ đo đánh giá: MAE, RMSE, wMAPE
  - 2.3.6. Giải thích mô hình bằng SHAP (TreeSHAP)
  - 2.3.7. Công thức dự phòng và lượng cần chuẩn bị (z × RMSE)

## CHƯƠNG 3. PHÂN TÍCH BÀI TOÁN VÀ DỮ LIỆU
- 3.1. Phương pháp và quy trình triển khai
- 3.2. Phân tích nghiệp vụ
  - 3.2.1. Tác nhân (Actor)
  - 3.2.2. Ma trận phân quyền
  - 3.2.3. Quy trình chuẩn bị hàng hằng ngày
  - 3.2.4. Công thức nghiệp vụ (dự phòng, lượng cần chuẩn bị, mức cảnh báo)
  - 3.2.5. Quy tắc nghiệp vụ
- 3.3. Mô tả bộ dữ liệu
  - 3.3.1. Nguồn dữ liệu
  - 3.3.2. Các nhóm dữ liệu và từ điển dữ liệu
- 3.4. Làm sạch dữ liệu
  - 3.4.1. Kiểm tra chất lượng dữ liệu
  - 3.4.2. Xử lý giá trị thiếu
  - 3.4.3. Xử lý trùng lặp và ngoại lai
- 3.5. Phân tích khám phá dữ liệu (EDA)
  - 3.5.1. Xu hướng theo thời gian và mùa vụ
  - 3.5.2. Lượng bán theo thứ trong tuần
  - 3.5.3. Lượng bán theo cửa hàng và món
  - 3.5.4. Tác động của khuyến mãi, ngày lễ, sự kiện và thời tiết
  - 3.5.5. Tổng hợp phát hiện và hàm ý cho mô hình
- 3.6. Use Case
  - 3.6.1. Nhóm tài khoản (đăng nhập, hồ sơ, đổi mật khẩu)
  - 3.6.2. Nhóm kiểm kho (Nhân viên)
  - 3.6.3. Nhóm dự báo và đề xuất chuẩn bị (Quản lý)
  - 3.6.4. Nhóm báo cáo xu hướng và độ chính xác
  - 3.6.5. Nhóm quản trị (dữ liệu, tài khoản, cửa hàng, cấu hình)
  - 3.6.6. Nhóm thông báo
- 3.7. Mô hình hóa quy trình nghiệp vụ
  - 3.7.1. Máy trạng thái đề xuất chuẩn bị (nháp → chờ duyệt → đã duyệt → hoàn thành)
  - 3.7.2. Quy trình nghiệp vụ (BPMN)
  - 3.7.3. Sơ đồ tuần tự dự báo

## CHƯƠNG 4. XÂY DỰNG MÔ HÌNH VÀ HỆ THỐNG
- 4.1. Kiến trúc giải pháp đề xuất
  - 4.1.1. Kiến trúc tổng thể
  - 4.1.2. Tầng dữ liệu và lớp truy cập (MySQLConnector hướng đối tượng)
  - 4.1.3. Tầng logic và mô hình học máy
  - 4.1.4. Tầng giao diện web
- 4.2. Thiết kế dữ liệu
  - 4.2.1. Tổng quan và quy ước
  - 4.2.2. Nhóm bảng dữ liệu nguồn (stores, products, daily_sales, weather_events, promotions)
  - 4.2.3. Bảng kết quả dự báo (forecasts)
  - 4.2.4. Nhóm bảng của web (hồ sơ, kiểm kho, đề xuất chuẩn bị, thông báo, cấu hình)
  - 4.2.5. Sơ đồ quan hệ thực thể (ERD)
- 4.3. Thiết kế pipeline học máy
  - 4.3.1. Chia dữ liệu theo thời gian (train ≤ 30/06/2025, validation 07–09/2025, test 10–12/2025)
  - 4.3.2. Xây dựng đặc trưng (phân loại, lịch, biết trước, lag/rolling)
  - 4.3.3. Chống rò rỉ dữ liệu (shift trước khi tính đặc trưng lịch sử)
  - 4.3.4. Huấn luyện và tinh chỉnh mô hình (Baseline, Ridge, LightGBM, CatBoost)
  - 4.3.5. Lưu và nạp mô hình (best_model.joblib)
  - 4.3.6. Giải thích dự báo bằng SHAP
  - 4.3.7. Từ dự báo đến đề xuất chuẩn bị (RMSE theo cặp cửa hàng–món)
- 4.4. Thiết kế giao diện và điều hướng
  - 4.4.1. Tổng quan và sitemap
  - 4.4.2. Màn hình của Nhân viên (kiểm kho, danh sách chuẩn bị)
  - 4.4.3. Màn hình của Quản lý (tổng quan, dự báo, đề xuất, báo cáo)
  - 4.4.4. Màn hình của Quản trị viên (dữ liệu, tài khoản, cửa hàng, cấu hình)
  - 4.4.5. Trạng thái đang tải, rỗng, lỗi
- 4.5. Sơ đồ giải thuật
  - 4.5.1. Giải thuật dự báo cho một ngày bất kỳ và xử lý ngày ngoài kỳ dữ liệu
  - 4.5.2. Giải thuật tính dự phòng và lượng cần chuẩn bị
  - 4.5.3. Giải thuật chuyển trạng thái đề xuất
- 4.6. Công cụ và công nghệ sử dụng (Python 3.12, pandas, scikit-learn, LightGBM, CatBoost, SHAP, Django, MySQL, Git)
- 4.7. Cách đánh giá và đo lường kết quả
  - 4.7.1. Đánh giá mô hình dự báo (độ đo, so sánh với baseline, phân tích đóng góp nhóm đặc trưng)
  - 4.7.2. Đánh giá đề xuất chuẩn bị hàng (mô phỏng thiếu hàng và lượng thừa trên tập test)
  - 4.7.3. Kiểm thử chức năng hệ thống

## CHƯƠNG 5. KẾT QUẢ VÀ PHÂN TÍCH
- 5.1. Mô tả các kết quả đạt được
  - 5.1.1. Sản phẩm bàn giao (mã nguồn, CSDL, mô hình, web)
  - 5.1.2. Giao diện Nhân viên
  - 5.1.3. Giao diện Quản lý
  - 5.1.4. Giao diện Quản trị viên
- 5.2. Kết quả mô hình học máy
  - 5.2.1. Dữ liệu đầu vào cho mô hình (số dòng, số đặc trưng của train/validation/test)
  - 5.2.2. So sánh các mô hình trên tập test (CatBoost wMAPE ≈ 14,5 %, LightGBM, Ridge, 2 baseline)
  - 5.2.3. Tầm quan trọng đặc trưng và phân tích SHAP
  - 5.2.4. Phân tích sai số theo cửa hàng, nhóm món, thứ, ngày lễ
  - 5.2.5. Phân tích đóng góp của từng nhóm đặc trưng (ablation)
  - 5.2.6. Tác động kinh doanh của kế hoạch tồn kho: so sánh thiếu hàng và lượng thừa giữa mô hình và baseline ở mức an toàn 95 %
- 5.3. Kết quả kiểm thử
  - 5.3.1. Kiểm thử tự động
  - 5.3.2. Kiểm thử đầu cuối
  - 5.3.3. Hiệu năng và độ ổn định
- 5.4. Phân tích và đánh giá kết quả

## CHƯƠNG 6. THẢO LUẬN
- 6.1. So sánh kết quả với mục tiêu ban đầu
- 6.2. Điểm mạnh và hạn chế của dự án
- 6.3. Những phát hiện đáng chú ý

## CHƯƠNG 7. KẾT LUẬN VÀ ĐỀ XUẤT
- 7.1. Tổng kết
- 7.2. Ý nghĩa khoa học và thực tiễn
- 7.3. Hướng phát triển
- 7.4. Kiến nghị

## TÀI LIỆU THAM KHẢO

## PHỤ LỤC A. LIÊN KẾT MÃ NGUỒN VÀ TÀI KHOẢN DEMO
- A.1. Liên kết mã nguồn (GitHub) và dữ liệu
- A.2. Tài khoản demo (15 cửa hàng, 3 vai trò)

## PHỤ LỤC B. KỊCH BẢN KIỂM THỬ ĐẦU CUỐI VÀ KẾT QUẢ
- B.1. Cách tổ chức kiểm thử
- B.2. Kịch bản vòng chuẩn bị hàng (KB-01 → KB-06)
- B.3. Kịch bản dự báo và báo cáo (KB-07, KB-08)
- B.4. Kịch bản dùng chung và phân quyền (KB-09, KB-10)
- B.5. Kịch bản quản trị viên (KB-11 → KB-18)
- B.6. Kịch bản học máy (KB-M1 → KB-M4)

## PHỤ LỤC C. KẾT QUẢ ĐO MÔ HÌNH CHI TIẾT
- C.1. Bảng độ đo từng mô hình
- C.2. Kết quả theo cửa hàng và theo nhóm món
- C.3. Biểu đồ dự báo so với thực tế

## PHỤ LỤC D. HƯỚNG DẪN CÀI ĐẶT VÀ CẤU TRÚC MÃ NGUỒN
- D.1. Cài đặt môi trường (Python, MySQL, `.env`)
- D.2. Tạo CSDL và nạp dữ liệu
- D.3. Chạy web và tài khoản mẫu
- D.4. Cấu trúc thư mục mã nguồn
