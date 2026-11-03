1. THÔNG TIN CHUNG:

- Tên đề tài: "Ứng dụng Machine Learning trong dự báo nhu cầu sản phẩm ngắn hạn và tối ưu tồn kho cho chuỗi nhà hàng phục vụ nhanh (QSR)"

- Dữ liệu: 2026 HAVI - NIU Hackathon (15 nhà hàng x 50 sản phẩm trong 5 năm, có biến thời tiết, khuyến mãi, ngày lễ).

2. MỤC TIÊU VÀ BÀI TOÁN KINH DOANH:

- Giải quyết bài toán cốt lõi của ngành F&B: Thực phẩm có hạn sử dụng ngắn, tránh lãng phí do dư thừa và tránh mất doanh thu do thiếu hàng.

- Luồng xử lý: Dữ liệu đa biến → ML Dự báo nhu cầu → Giải thích SHAP → Đề xuất Tồn kho an toàn (Safety Stock) & Lượng chuẩn bị hàng.

3. ÁP DỤNG KIẾN THỨC BÀI GIẢNG ĐÃ/SẮP HỌC

-Kiến trúc Hướng đối tượng Connector (OOP - Slide 05): Thiết kế tách lập class MySQLConnector theo chuẩn hướng đối tượng (đóng gói kết nối, xử lý ngoại lệ, đóng mở connection an toàn) để có thể tái sử dụng độc lập cho mọi dự án.

-Tiền xử lý & làm sạch dữ liệu chuỗi thời gian.

-Hàm truy vấn trả về DataFrame: Xây dựng các hàm truy vấn dữ liệu từ MySQL Server trả thẳng về pandas.DataFrame để cấp nguồn dữ liệu chuẩn hóa cho module thống kê và pipeline máy học.

-Hiểu sâu bản chất toán học Hồi quy đơn biến (Slide 06): Nắm vững công thức toán học của mô hình Hồi quy tuyến tính, thực nghiệm tính toán kiểm chứng đối chiếu song song giữa Excel và Python trước khi mở rộng mô hình.

-Thiết kế quy trình hệ thống End-to-End.

-Trực quan hóa Table & Chart trên GUI (Slide 09): Tích hợp hiển thị dữ liệu dạng bảng (QTableWidget) và vẽ biểu đồ tương tác trực tiếp (PyQt6-Charts / Matplotlib) trên giao diện người dùng.

-Kiến trúc phần mềm đa tầng (Slide 12, 13): Tách biệt rõ ràng 3 tầng: Tầng Dữ liệu (MySQL)↔Tầng Logic & Mô hình (ML Engine) ↔ Tầng Giao diện (PyQt6).

4. MÔ HÌNH THỬ NGHIỆM:

- Baseline: Seasonal Naive (chu kỳ 7 ngày) & Moving Average.

- Mô hình tuyến tính: Ridge Regression.

- Mô hình Ensemble SOTA: CatBoost (xử lý biến định danh Store/Product/Weather) & LightGBM (tốc độ cao, quan hệ phi tuyến).

- Mô hình giải thích (XAI): TreeSHAP bóc tách nguyên nhân dự báo (do Thứ 7, Khuyến mãi hay Thời tiết).

5. SẢN PHẨM ĐẦU RA:

- Pipeline mã nguồn ML hoàn chỉnh (.pkl).

- CSDL MySQL lưu trữ và truy vấn.

- Ứng dụng Desktop Django tích hợp: xem lịch sử, bấm chạy dự báo, cảnh báo hết hàng màu đỏ và đề xuất số lượng cần chuẩn bị thực tế.

