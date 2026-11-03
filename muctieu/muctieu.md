ỨNG DỤNG MACHINE LEARNING TRONG DỰ BÁO NHU CẦU SẢN PHẨM NGẮN HẠN VÀ TỐI ƯU TỒN KHO CHO CHUỖI NHÀ HÀNG PHỤC VỤ NHANH (QSR)

Link dataset: 2026 HAVI - NIU Hackathon: Quick Service Restaurant Demand Forecasting Challenge   


Chủ đề 
Kiến thức sử dụng
Slide đã học
1. Tiền xử lý dữ liệu
Làm sạch dữ liệu bán hàng 5 năm, xử lý dữ liệu thiếu (missing values), phát hiện dị biệt.
Slide 04: Dữ liệu
2. Cơ sở dữ liệu
Thiết kế CSDL MySQL 5 bảng (Stores, Products, Daily_Sales, Promotions, Weather_Events).
• Lập trình Python kết nối MySQL (mysql-connector-python) để lưu trữ và truy vấn dữ liệu.
Slide 05: Dữ liệu - MySQL Interaction
3. Bài toán Hồi quy & Đo sai số
Bản chất bài toán Hồi quy dự báo định lượng (Regression).
• Đo lường sai số dự báo bằng các hàm mất mát chuẩn: MAE, RMSE.
Slide 06: Các nhóm giải thuật máy học
4. Quy trình thiết kế hệ thống ML
Tuân thủ chuẩn quy trình End-to-End: Preparing Data → Filter Data → Build Model → Train/Evaluate → Integrated ML.
Slide 08: Thiết kế hệ thống máy học
5. Giao diện Desktop Django
• Thiết kế giao diện (TableWidget, ComboBox, PushButton).
• Trực quan hóa biểu đồ doanh số.
• Nạp file mô hình đã huấn luyện (.pkl / .joblib) để chạy dự báo tương tác trên UI.
Slide 09: PyQt6 và tích hợp mô hình Máy học
6. Kiến trúc phần mềm đa tầng
Thiết kế phần mềm theo mô hình đa tầng (Multi-tier Architecture), tách biệt rõ ràng tầng Data Access (MySQL), tầng ML Logic và tầng Giao diện (UI).
Slide 12 & 13: Integrated Model into Project



Nội dung mở rộng
Chi tiết kỹ thuật nâng cao
Giá trị mang lại
1. Time-series Feature Engineering & Time-based Split
• Tạo biến trễ (Lag_1, Lag_7, Lag_14) và biến cuộn (Rolling Mean/Std 7 ngày).
• Phân chia Train/Val/Test theo trục thời gian (chống rò rỉ dữ liệu - Data Leakage).
Slide chỉ dạy bảng dữ liệu tĩnh (Tabular cơ bản). Đây là kỹ thuật chuyên sâu bắt buộc cho dữ liệu chuỗi thời gian (Time-series).
2. Mô hình SOTA (CatBoost & LightGBM)
• Dùng CatBoost (xử lý trực tiếp biến phân loại Store_ID, Product_ID, Weather) và LightGBM (tốc độ cao, tiết kiệm RAM).
Nâng cấp vượt trội so với Hồi quy tuyến tính trong slide, cho độ chính xác cao hơn hẳn và đúng chuẩn thực tế ngành Data.
3. Chỉ số đánh giá wMAPE
• Đo lường sai số trên tổng dung lượng nhu cầu: wMAPE=y-yy.
Chỉ số chuẩn mực của các cuộc thi Kaggle và bài toán dự báo bán lẻ (phản ánh sát thực tế hơn MAE/RMSE thuần túy).
4. Nghiệp vụ Quản trị Tồn kho (Safety Stock)
• Tận dụng sai số RMSE của mô hình để tính Tồn kho an toàn: SafetyStock=1.65RMSE
• Tự động đề xuất: Lượng cần chuẩn bị = Dự báo + Tồn an toàn - Tồn hiện tại.
Đưa kết quả máy học vào giải quyết trực tiếp bài toán kinh doanh F&B (chống lãng phí thực phẩm & chống cháy hàng).
5. Explainable AI (XAI với TreeSHAP)
• Sử dụng TreeSHAP để bóc tách đóng góp của từng đặc trưng (Thứ 7, Khuyến mãi, Thời tiết) vào từng dự báo cụ thể.
Giải thích minh bạch lý do dự báo, tăng độ tin cậy khi thuyết phục quản lý nhà hàng ra quyết định.


1. Ý tưởng tổng quan
Trong hoạt động của một chuỗi nhà hàng phục vụ nhanh (Quick-Service Restaurant - QSR), một trong những câu hỏi quan trọng cần được giải quyết mỗi ngày là: “Ngày mai, mỗi nhà hàng sẽ bán được bao nhiêu đơn vị của từng sản phẩm?” Đây tưởng chừng là một câu hỏi đơn giản, nhưng trên thực tế nhu cầu của khách hàng không cố định. Cùng một sản phẩm có thể bán rất tốt tại một nhà hàng nhưng có nhu cầu thấp hơn tại nhà hàng khác; lượng bán vào cuối tuần có thể khác ngày thường; đồng thời khuyến mãi, ngày lễ, sự kiện địa phương hay điều kiện thời tiết cũng có thể làm nhu cầu thay đổi đáng kể.
Khác với ngành bán lẻ thông thường, nguyên liệu thực phẩm trong ngành F&B/QSR có hạn sử dụng rất ngắn. Nếu doanh nghiệp dự báo nhu cầu cao hơn thực tế, lượng thực phẩm chuẩn bị có thể vượt quá nhu cầu, từ đó làm tăng chi phí và nguy cơ lãng phí do hư hỏng. Ngược lại, nếu dự báo thấp hơn nhu cầu thực tế, nhà hàng có thể không chuẩn bị đủ sản phẩm để phục vụ khách hàng, dẫn đến tình trạng "cháy hàng" và mất cơ hội bán hàng. Vấn đề cốt lõi vì vậy không chỉ nằm ở việc biết “đã bán được bao nhiêu”, mà quan trọng hơn là có khả năng ước lượng “sẽ bán được bao nhiêu trong tương lai” để từ đó đưa ra quyết định chuẩn bị lượng thực phẩm và tồn kho tối ưu.
Từ vấn đề này, nhóm đề xuất đề tài “Ứng dụng Machine Learning trong dự báo nhu cầu sản phẩm ngắn hạn và tối ưu tồn kho cho chuỗi nhà hàng phục vụ nhanh”. Mục tiêu của đề tài là xây dựng mô hình học máy có khả năng học từ dữ liệu bán hàng trong quá khứ và các yếu tố liên quan để dự báo số lượng bán hằng ngày của từng sản phẩm tại từng nhà hàng trong tương lai, đồng thời tự động tính toán mức tồn kho an toàn và đề xuất lượng nhập/chuẩn bị nguyên liệu hằng ngày.
Có thể khái quát ý tưởng của đề tài theo chuỗi: Dữ liệu bán hàng lịch sử + Nhà hàng + Sản phẩm + Thời gian + Khuyến mãi + Ngày lễ + Sự kiện + Thời tiết
→ Machine Learning
→ Dự báo số lượng sản phẩm bán ra
-> Giải thích mô hình (SHAP) & Đề xuất lượng chuẩn bị hàng tồn kho an toàn 
Như vậy, đầu ra cuối cùng của hệ thống không chỉ dừng lại ở một con số dự báo định lượng cụ thể (chẳng hạn: ngày mai sản phẩm A tại nhà hàng 01 bán được khoảng 85 đơn vị), mà còn cung cấp cơ sở giải thích tại sao có con số đó và đề xuất chính xác số lượng sản phẩm/nguyên liệu nhà hàng cần chuẩn bị thực tế trong ngày.
2. Nguồn dữ liệu và lý do lựa chọn
Dữ liệu dự kiến sử dụng được lấy từ 2026 HAVI - NIU Hackathon: Quick Service Restaurant Demand Forecasting Challenge trên nền tảng Kaggle. Đây là một bài toán Machine Learning về dự báo nhu cầu trong môi trường QSR, do HAVI (tập đoàn đối tác quản lý chuỗi cung ứng toàn cầu của McDonald's) đưa ra trong khuôn khổ hackathon dành cho sinh viên Northern Illinois University.
Dataset mô phỏng hoạt động của 15 nhà hàng và 50 sản phẩm, với dữ liệu bán hàng hằng ngày trong khoảng 5 năm, từ năm 2021 đến năm 2025. Ngoài lịch sử số lượng bán, dữ liệu còn được bổ sung các thông tin liên quan đến thời tiết (nhiệt độ, thời tiết xấu/tốt), ngày lễ, sự kiện địa phương và chương trình khuyến mãi. Nhờ đó, nhóm có thể nghiên cứu bài toán demand forecasting dưới góc nhìn đa biến thay vì chỉ dựa vào chuỗi doanh số quá khứ.
Bài toán yêu cầu dự báo nhu cầu cho giai đoạn từ ngày 01/10/2025 đến 31/12/2025. Với 92 ngày dự báo, 15 nhà hàng và 50 sản phẩm, mô hình cần tạo ra tổng cộng: 
92 ngày × 15 nhà hàng × 50 sản phẩm = 69.000 giá trị dự báo.

3. Vấn đề Machine Learning cần giải quyết
Bài toán dự báo chuỗi thời gian (time-series forecasting) được biểu diễn dưới dạng bài toán hồi quy có giám sát trên dữ liệu dạng bảng (supervised tabular regression).
Biến mục tiêu của mô hình là: Target=Daily Quantity Sold\text{Target} = \text{Daily Quantity Sold}Target=Daily Quantity Sold (Tức số lượng của một sản phẩm được bán tại một nhà hàng cụ thể trong một ngày).
Các biến đầu vào không chỉ bao gồm thông tin nhận diện nhà hàng và sản phẩm mà còn được xây dựng từ ba nhóm thông tin chính:
Thứ nhất là lịch sử nhu cầu (Lag & Rolling Features): Từ lượng bán trong quá khứ, nhóm tạo các đặc trưng như lượng bán của 1 ngày, 7 ngày (cùng thứ tuần trước), 14 ngày hoặc 28 ngày trước; giá trị trung bình động (Rolling Mean) và độ biến động (Rolling Std) trong 7 hoặc 28 ngày gần nhất. Các đặc trưng này giúp mô hình nhận biết xu hướng và quy luật lặp lại trong hành vi mua.
Thứ hai là đặc trưng thời gian (Calendar Features): Bao gồm thứ trong tuần, tuần trong năm, tháng, cờ đánh dấu ngày thường hay cuối tuần. Ví dụ, nếu một sản phẩm thường bán nhiều vào thứ Bảy và Chủ Nhật, mô hình có thể học được quy luật này từ dữ liệu thay vì xem tất cả các ngày là tương đương.
Thứ ba là các yếu tố ngoại sinh (Exogenous Features): Gồm chương trình khuyến mãi, ngày lễ, sự kiện địa phương và điều kiện thời tiết. Việc kết hợp các yếu tố này cho phép nhóm kiểm chứng câu hỏi quan trọng: liệu việc bổ sung thông tin bối cảnh có giúp mô hình dự báo chính xác hơn so với chỉ dựa vào lịch sử bán hàng thuần túy hay không.

4. Hướng xây dựng đề tài
Đề tài dự kiến được triển khai theo một quy trình Machine Learning hoàn chỉnh và thực tế:
Data Understanding & Preprocessing: Tìm hiểu cấu trúc dataset, kiểm tra và xử lý dữ liệu thiếu, dữ liệu trùng lặp, chuẩn hóa kiểu dữ liệu, phát hiện giá trị bất thường và đảm bảo tính liên tục của chuỗi thời gian.
Exploratory Data Analysis (EDA): Phân tích nhu cầu theo thời gian, nhà hàng và sản phẩm; kiểm tra sự khác biệt giữa ngày thường và cuối tuần; khảo sát mối quan hệ giữa lượng bán với promotion, holiday, local events và weather nhằm làm cơ sở trực tiếp cho việc chọn lọc đặc trưng.
Feature Engineering & Time-based Splitting: Xây dựng các biến thời gian, biến trễ (lag) và biến cuộn (rolling mean/std). Tất cả đặc trưng đều được tạo nghiêm ngặt từ thông tin tồn tại trước thời điểm dự báo nhằm triệt tiêu hoàn toàn hiện tượng rò rỉ dữ liệu (data leakage). Dữ liệu được chia thành tập Train, Validation và Test theo trục thời gian thực tế.
4.   Huấn luyện & Đánh giá Mô hình:
Đề tài xây dựng bài toán dự báo nhu cầu bán hàng dưới dạng hồi quy có giám sát trên dữ liệu chuỗi thời gian được biểu diễn thành bảng. Nhóm sử dụng các đặc trưng lịch sử, thời gian và yếu tố bối cảnh để dự báo số lượng bán theo ngày cho từng sản phẩm tại từng nhà hàng. Seasonal Naive và Moving Average được dùng làm mô hình cơ sở; CatBoost Regressor và LightGBM Regressor được đưa vào so sánh để đánh giá mức độ phù hợp với dữ liệu và mục tiêu dự báo.
5. Kết quả dự kiến
Kết quả cuối cùng mà nhóm hướng đến là xây dựng được một hệ thống hoàn chỉnh:
Một mô hình Machine Learning đạt độ chính xác cao trong việc dự báo số lượng bán hằng ngày cho từng món ăn tại từng nhà hàng dựa trên lịch sử nhu cầu và các yếu tố bối cảnh.
Module giải thích mức độ ảnh hưởng của từng yếu tố đến kết quả dự báo (Explainable AI).
Module tự động tính toán tồn kho an toàn và đề xuất số lượng chuẩn bị thực tế, giúp quản lý chuỗi nhà hàng đưa ra quyết định vận hành chính xác.
6. Kiến trúc Hệ thống & Mở rộng Ứng dụng Thực tế
A. Cơ sở dữ liệu MySQL & Ứng dụng Django Web 
Cơ sở dữ liệu MySQL: Thiết kế CSDL quan hệ gồm các bảng: Stores, Products, Daily_Sales, Promotions, Weather_Events. Viết module kết nối Python ↔ MySQL để lưu trữ, truy vấn lịch sử bán hàng và lưu kết quả dự báo.
Ứng dụng giao diện Django(2 Tab tối giản, chuyên nghiệp):
Tab 1 - Giám sát & Báo cáo Lịch sử: Cho phép chọn cửa hàng/khoảng thời gian để truy vấn dữ liệu từ MySQL, hiển thị biểu đồ doanh thu và danh sách các món bán chạy.
Tab 2 - Dự báo & Quản trị Tồn kho: Cho phép người dùng chọn ngày cần dự báo → bấm nút "Chạy dự báo" → hiển thị bảng kế hoạch chuẩn bị hàng chi tiết.
B. Từ "Dự báo con số" sang "Quản trị Tồn kho thực tế" (Điểm nhấn nghiệp vụ F&B)
Nhằm giải quyết bài toán không để thiếu hàng mất khách và không để thừa thức ăn gây hư hỏng, hệ thống phát triển thêm module nghiệp vụ:
Tồn kho an toàn (Safety Stock): Tính toán dựa trên sai số dự báo RMSE của mô hình: Safety Stock = 1.65 x RMSE (tương ứng với mức độ đáp ứng dịch vụ 95%)
Đề xuất lượng chuẩn bị/nhập hàng (Order Recommendation): Số lượng cần chuẩn bị = Nhu cầu dự báo +Tồn kho an toàn - Tồn hiện tại trong kho
Cảnh báo màu sắc trên giao diện: Tự động tô màu đỏ cảnh báo các món có nguy cơ thiếu hàng (Out-of-stock) khi tồn hiện tại thấp hơn mức tồn kho an toàn.
C. Giải thích mô hình (Explainable AI - XAI với TreeSHAP)
Để tăng độ tin cậy khi đưa mô hình vào thực tế, hệ thống tích hợp thư viện SHAP:
Giải thích rõ ràng nguyên nhân: "Tại sao mô hình dự đoán ngày mai món A bán được 85 phần thay vì 60 phần thông thường?"
Phân tích đóng góp: Do ngày mai là Thứ Bảy đóng góp +15+15+15 phần; do có chương trình Khuyến mãi đóng góp +10+10+10 phần; do dự báo trời mưa giảm −5-5−5 phần.
Hiển thị biểu đồ trực quan mức độ đóng góp đặc trưng (Feature Attribution) ngay trên giao diện Django khi người dùng nhấp chọn vào từng món ăn.

Về khía cạnh thuật toán và mô hình hóa, nhóm triển khai so sánh thực nghiệm bài bản theo 3 cấp độ:
1. Mô hình cơ sở (Benchmark): Seasonal Naive & Moving Average (7 ngày).
2. Mô hình tuyến tính bài giảng : Ridge Regression.
3. Mô hình Ensemble SOTA: CatBoost Regressor (chuyên trị biến phân loại Store/Product/Weather) và LightGBM Regressor (tối ưu quan hệ phi tuyến & tốc độ).
4. Mô hình giải thích (XAI): Tích hợp TreeSHAP để bóc tách nguyên nhân đằng sau từng con số dự báo.
Mô hình có chỉ số wMAPE/RMSE tối ưu nhất sẽ được đóng gói (.pkl) và tích hợp vào giao diện Django để vận hành tính toán Tồn kho an toàn (Safety Stock).






