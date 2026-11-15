ML_QSR - Dự báo nhu cầu nguyên liệu cho chuỗi nhà hàng phục vụ nhanh


Hệ thống dự báo số lượng món bán ra theo từng cửa hàng và từng ngày cho chuỗi 15 nhà hàng phục vụ nhanh (QSR, 50 món), từ đó lập kế hoạch chuẩn bị nguyên liệu có tính tồn kho an toàn. Mô hình học máy (CatBoost) được tích hợp vào một ứng dụng web Django với ba vai trò: quản trị viên, quản lý cửa hàng và nhân viên bếp/kho.

Đồ án môn Học máy do nhóm 5 thực hiện, mã học phần 261BIM401402, giảng viên hướng dẫn TS.Trần Duy Thanh, Trường Đại học Kinh tế - Luật (DHQGTPHCM).

## Chức năng chính

### Quản lý cửa hàng
- Xem dashboard dự báo của cửa hàng mình và biểu đồ nhu cầu các ngày tới.
- Chạy dự báo cho một ngày bất kỳ sau ngày vận hành; hệ thống từ chối các ngày thuộc tập huấn luyện.
- Duyệt, điều chỉnh số lượng từng dòng, khoá hoặc mở lại kế hoạch chuẩn bị; xem lý do của từng dự báo.
- Xuất kế hoạch chuẩn bị và xem báo cáo.

### Nhân viên bếp/kho
- Kiểm kho: lưu nháp rồi lưu chính thức, bắt buộc đủ mặt hàng; số liệu kiểm kho là đầu vào để tạo kế hoạch.
- Xem kế hoạch chuẩn bị đã duyệt và đánh dấu hoàn tất từng dòng.
- Nhận thông báo (cảnh báo thiếu hàng, nhắc kiểm kho, sự kiện sắp tới).

### Quản trị viên
- Nhập dữ liệu bán hàng, thời tiết, ngày lễ từ Excel/CSV; phát hiện ngày còn thiếu dữ liệu.
- Chạy dự báo cho một cửa hàng hoặc toàn chuỗi; xem mô hình đang dùng, độ quan trọng đặc trưng và giải thích.
- Quản lý cửa hàng, tài khoản (tạo, khoá, đặt lại mật khẩu) và cấu hình hệ thống.

## Công nghệ

| Tầng | Công nghệ |
|---|---|
| Giao diện | Django Templates, Tailwind CSS, Lucide, JavaScript thuần |
| Máy chủ | Python 3.12, Django 6 |
| Cơ sở dữ liệu | MySQL 8 (`mysql-connector-python` cho phần ML, `mysqlclient` cho Django ORM) |
| Xác thực | Django auth, phân quyền theo vai trò, giới hạn số lần đăng nhập |
| Học máy | pandas, scikit-learn (Ridge), LightGBM, CatBoost, joblib |
| Kiểm thử | pytest, pytest-django |

## Cấu trúc thư mục

```
ML_QSR/                              (thư mục gốc dự án)
├── manage.py                        lệnh quản lý Django
├── requirements.txt                 danh sách thư viện (đã ghim phiên bản)
├── pytest.ini                       cấu hình pytest (chạy cả Tests/ và forecast/tests.py)
├── .env.example                     mẫu biến môi trường (sao chép thành .env)
├── .gitignore
├── README.md
│
├── ML_QSR/                          cấu hình project Django
│   ├── settings.py                  cấu hình, đọc thông tin MySQL từ Utils/Config.py
│   ├── urls.py                      định tuyến gốc
│   ├── asgi.py
│   └── wsgi.py
│
├── forecast/                        ứng dụng web
│   ├── models.py                    mô hình dữ liệu: Store, Product, DailySale, PrepPlan, InventoryCount, ...
│   ├── views.py                     các trang giao diện
│   ├── api.py                       API cho quản lý và nhân viên (kế hoạch, kiểm kho, thông báo, tài khoản)
│   ├── api_admin.py                 API cho quản trị viên (nhập dữ liệu, chạy dự báo, giải thích mô hình, cửa hàng, tài khoản)
│   ├── urls.py                      định tuyến của ứng dụng
│   ├── permissions.py               phân quyền theo vai trò (admin, manager, staff)
│   ├── context_processors.py        biến dùng chung cho mọi template
│   ├── admin.py                     đăng ký Django admin
│   ├── tests.py                     58 test nghiệp vụ và phân quyền
│   ├── services/                    lớp nghiệp vụ
│   │   ├── engine.py                nạp best_model.joblib, sinh dự báo và tồn kho an toàn
│   │   ├── plans.py                 tạo, duyệt, khoá, mở lại, điều chỉnh kế hoạch chuẩn bị
│   │   ├── adminops.py              nhập dữ liệu, chạy dự báo hàng loạt, quản lý tài khoản và cấu hình
│   │   ├── explain.py               giải thích dự báo theo cửa hàng
│   │   ├── insights.py              lý do và cảnh báo cho từng dòng dự báo
│   │   ├── notifications.py         thông báo (thiếu hàng, hoàn tất, nhắc kiểm kho, sự kiện)
│   │   └── units.py                 đơn vị tính của từng món
│   ├── management/commands/
│   │   ├── seed_demo.py             tạo tài khoản và dữ liệu demo
│   │   └── send_reminders.py        gửi nhắc kiểm kho
│   ├── migrations/                  0001_initial, 0002_..., 0003_alter_notification_kind
│   ├── templatetags/qsr.py          bộ lọc template (định dạng số)
│   ├── templates/forecast/          giao diện (16 file)
│   │   ├── base.html, _nav_item.html            khung trang và mục điều hướng
│   │   ├── login.html, profile.html, no_access.html
│   │   ├── dashboard.html, forecast.html, prep.html, report.html     quản lý cửa hàng
│   │   ├── staff_prep.html, inventory.html                           nhân viên bếp/kho
│   │   └── data.html, model.html, stores.html, accounts.html, config.html   quản trị viên
│   └── static/forecast/
│       ├── js/modals.js             hộp thoại và gọi API từ giao diện
│       └── img/login-burger.png     ảnh trang đăng nhập
│
├── Models/                          lớp ML (huấn luyện, đánh giá)
│   ├── QSRStatistic.py              lớp cơ sở: tải lịch sử bán hàng từ MySQL, thống kê mô tả, vẽ biểu đồ phân tích
│   ├── QSRMLModel.py                lớp cha của các mô hình học máy (kế thừa QSRStatistic): tạo đặc trưng, chia train/val/test, đánh giá
│   ├── QSRBaselineModel.py          baseline Seasonal Naive và Moving Average
│   ├── QSRRidgeRegression.py        mô hình Ridge
│   ├── QSRLightGBM.py               mô hình LightGBM
│   ├── QSRCatBoost.py               mô hình CatBoost (mô hình chính)
│   ├── QSRDataCleaning.py           làm sạch dữ liệu thô và nạp vào MySQL
│   ├── QSRInventory.py              tính kế hoạch tồn kho từ dự báo
│   ├── MetricsResult.py             lưu kết quả đánh giá (wMAPE, MAE, RMSE, R², bias)
│   └── TrainedModel.py              đóng gói model đã train cùng tên và danh sách cột đầu vào
│
├── Connectors/Connector.py          kết nối MySQL, chạy truy vấn và script SQL
├── Utils/
│   ├── Config.py                    cấu hình chung: DB, đường dẫn, đặc trưng, mốc chia dữ liệu
│   └── FileUtil.py                  lưu và nạp model bằng joblib
│
├── Database/
│   ├── qsr_schema.sql               tạo CSDL và các bảng
│   └── qsr_data.sql.gz              dữ liệu nạp sẵn (khoảng 1,37 triệu dòng bán hàng)
│
├── Assets/
│   ├── best_model.joblib            mô hình tốt nhất (CatBoost) cho web
│   └── reports/metrics.csv          bảng metric của các mô hình
│
├── scripts/                         script thực nghiệm (chạy dạng python -m scripts.<tên>)
│   ├── check_connection.py          kiểm tra kết nối và số dòng các bảng
│   ├── AppPrepareData.py            làm sạch dữ liệu thô, tạo schema, nạp MySQL
│   ├── AppStatistic.py              thống kê mô tả và biểu đồ phân tích dữ liệu
│   ├── AppBaseline.py               huấn luyện và đánh giá baseline
│   ├── AppRidgeRegression.py
│   ├── AppLightGBM.py
│   ├── AppCatBoost.py
│   ├── AppCompareModels.py          so sánh các mô hình, chọn mô hình tốt nhất
│   ├── AppAblation.py               thí nghiệm bỏ từng nhóm đặc trưng (lịch sử bán, lịch, ngày lễ, thời tiết, giá, ...) với CatBoost
│   ├── AppBusinessImpact.py         đánh giá tác động nghiệp vụ của các mô hình ở các mức phục vụ 90%, 95%, 99%
│   └── AppInventory.py              sinh kế hoạch tồn kho cho một ngày
│
├── notebook/
│   └── ML_HK7.ipynb                 notebook phân tích khám phá dữ liệu (EDA): cấu trúc dữ liệu, làm sạch, nhu cầu theo thời gian, cuối tuần, cửa hàng, ...
│
└── Tests/                           11 test cho phần ML
    ├── test_model.py                chống rò rỉ dữ liệu (lag, rolling), chia tập, đánh giá
    └── test_inventory.py            kiểm tra tính tồn kho
```

Các thư mục sau không nằm trong git: `data/` (dữ liệu thô và tập train/val/test), `Assets/figures/` (biểu đồ), các model phụ trong `Assets/` (`catboost`, `lightgbm`, `ridge`, `MovingAverage_7`, `SeasonalNaive_7`), `.env` và `.venv/`.

## Chạy ở máy

Cần Python 3.12 và MySQL 8 trở lên.

### 1. Cài đặt

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Cấu hình

```bash
cp .env.example .env
```

| Biến | Ý nghĩa | Mặc định |
|---|---|---|
| `QSR_DB_HOST` | Máy chủ MySQL | `localhost` |
| `QSR_DB_PORT` | Cổng MySQL | `3306` |
| `QSR_DB_USER` | Tài khoản MySQL | `root` |
| `QSR_DB_PASSWORD` | Mật khẩu MySQL | (trống) |
| `QSR_DB_NAME` | Tên CSDL | `qsr_db` |

### 3. Nạp dữ liệu

```bash
mysql -u root -p < Database/qsr_schema.sql                  # tạo CSDL và các bảng
gunzip -c Database/qsr_data.sql.gz | mysql -u root -p qsr_db  # nạp khoảng 1,37 triệu dòng bán hàng
python manage.py migrate                                    # tạo bảng của Django
python manage.py seed_demo                                  # tạo tài khoản và dữ liệu demo
```

### 4. Chạy

```bash
python manage.py runserver     # mở http://127.0.0.1:8000
```

## Tài khoản demo (sau `python manage.py seed_demo`)

| Vai trò | Tài khoản | Mật khẩu |
|---|---|---|
| Quản trị viên | `admin` | `VaHhXjMc!75` |
| Quản lý R01 | `lan.r01` | `vjtSKDEP%96` |
| Nhân viên R01 | `khanh.r01` | `UTxmJhkV!40` |

Danh sách đủ cho 15 cửa hàng nằm trong `forecast/management/commands/seed_demo.py`.

## Kiểm thử

Tổng cộng 69 test, chia làm hai bộ và chạy chung bằng một lệnh:

```bash
pytest                                  # chạy cả hai bộ (cần MySQL đang chạy)
pytest Tests                            # chỉ 11 test của phần ML
pytest forecast                         # chỉ 58 test của ứng dụng web
pytest -k "PermissionTests" -v          # chạy một nhóm test và xem chi tiết
python manage.py test forecast          # cách chạy bằng Django (58 test web)
```

Bộ test web dùng CSDL kiểm thử riêng do Django tự tạo và xoá, không ảnh hưởng dữ liệu thật; các lời gọi mô hình được thay bằng dữ liệu giả nên không cần file model.

### Phần ML: `Tests/` (11 test)

| File | Test | Kiểm tra |
|---|---|---|
| `test_model.py` | `test_lag_uses_only_past` | đặc trưng trễ chỉ lấy dữ liệu quá khứ |
| | `test_rolling_excludes_current_day` | trung bình trượt không chứa ngày hiện tại |
| | `test_lags_do_not_cross_series` | đặc trưng trễ không lẫn giữa các chuỗi (cửa hàng, món) khác nhau |
| | `test_holiday_neighbours` | cờ ngày lễ hôm qua/ngày mai tính đúng |
| | `test_time_split_has_no_overlap` | tập train/val/test không chồng lấn thời gian |
| | `test_evaluate_excludes_imputed_rows` | đánh giá bỏ qua các dòng đã điền bù |
| `test_inventory.py` | `test_safety_stock_per_series` | tồn kho an toàn tính theo từng chuỗi |
| | `test_unknown_series_uses_median_rmse` | chuỗi chưa gặp dùng RMSE trung vị |
| | `test_recommend_order_formula` | công thức số lượng đề xuất đặt |
| | `test_residual_rmse_ignores_stockout_and_outlier_days` | RMSE sai số bỏ qua ngày hết hàng và ngày ngoại lai |
| | `test_stockout_warning` | cảnh báo thiếu hàng |

### Phần web: `forecast/tests.py` (58 test)

| Nhóm test | Số test | Kiểm tra |
|---|---|---|
| `PlanLogicTests` | 7 | tính mức chuẩn bị, tạo kế hoạch, duyệt/khoá/mở lại theo phiên bản, lưu dự báo thô sau khi commit, điều chỉnh và sửa dòng, trường hợp không có dữ liệu |
| `InventoryTests` | 3 | kiểm kho lưu nháp rồi lưu chính thức (bắt buộc đủ mặt hàng), tạo kế hoạch và lấy số lượng kỳ trước, bỏ qua kế hoạch đã khoá |
| `PermissionTests` | 8 | chưa đăng nhập bị chuyển hướng/401, phân quyền theo vai trò, không sửa được kế hoạch của cửa hàng khác, luồng API, tắt quyền chạy dự báo của quản lý, đổi mật khẩu |
| `Phase1LogicTests` | 12 | ngày được phép dự báo, ngày thuộc tập huấn luyện bị từ chối, ngày không có dữ liệu, gửi thẳng cho bếp khi không cần duyệt, thông báo (cảnh báo đỏ, hoàn tất, sự kiện, nhắc kiểm kho), ghi nhớ đăng nhập và giới hạn số lần thử, tài khoản chưa gán cửa hàng, API lý do dự báo |
| `AdminOpsTests` | 11 | quy tắc tài khoản, khoá và đặt lại mật khẩu, lưu cửa hàng và gán quản lý, lưu cấu hình, ngày vận hành, nhập dữ liệu bán hàng/thời tiết/ngày lễ (mới, cập nhật, bỏ qua dòng lỗi), chạy dự báo toàn chuỗi, quyền của API quản trị |
| `Round2FixTests` | 8 | chạy lại dự báo vẫn giữ điều chỉnh và sửa tay, trang chuẩn bị hiển thị số đã điều chỉnh, nút mở lại và kế hoạch đã khoá, tự công bố không có người duyệt, biểu đồ dashboard, thông báo lỗi máy chủ không lộ chi tiết |
| `Round2SecurityTests` | 3 | trang đăng nhập chỉ liệt kê tài khoản demo, đặt lại mật khẩu trả lời giống nhau và có giới hạn tần suất, trang mô hình vẫn mở khi thiếu file model |
| `ExplainTests` | 6 | quản lý chỉ thấy nhóm lý do nghiệp vụ, quản lý không dùng được chức năng giải thích của quản trị hay xem cửa hàng khác, nhân viên không thấy SHAP, quản trị xem được mọi cửa hàng kèm chi tiết kỹ thuật, kiểm tra tham số, trang mô hình chỉ có mục SHAP với quản trị |

## Mô hình dự báo

Dữ liệu gồm 15 nhà hàng, 50 món, từ doanh số hằng ngày kèm khuyến mãi, thời tiết, ngày lễ và sự kiện đặc biệt. Dữ liệu chia theo thời gian: huấn luyện đến 30/06/2025, kiểm định 01/07 đến 30/09/2025, kiểm tra 01/10 đến 31/12/2025. Đặc trưng gồm lịch, giá, thời tiết, cờ ngày lễ/khuyến mãi/sự kiện, độ trễ (1, 7, 14, 28 ngày) và trung bình/độ lệch chuẩn trượt (7, 28 ngày); các đặc trưng trễ chỉ dùng dữ liệu quá khứ, có test kiểm tra rò rỉ.

```bash
python -m scripts.AppPrepareData   # làm sạch dữ liệu thô (data/raw/qsr_demand_dataset.csv) và nạp MySQL
python -m scripts.AppBaseline      # Seasonal Naive và Moving Average
python -m scripts.AppRidgeRegression
python -m scripts.AppLightGBM
python -m scripts.AppCatBoost
python -m scripts.AppCompareModels # so sánh và chọn mô hình tốt nhất
```

Kết quả trên tập kiểm tra (wMAPE càng thấp càng tốt):

| Mô hình | wMAPE | MAE | RMSE | R² |
|---|---|---|---|---|
| Seasonal Naive (7) | 22,88% | 5,31 | 8,92 | 0,617 |
| Moving Average (7) | 19,92% | 4,62 | 7,90 | 0,700 |
| Ridge | 17,71% | 4,11 | 7,24 | 0,748 |
| LightGBM | 14,61% | 3,39 | 6,64 | 0,788 |
| **CatBoost** | **14,54%** | **3,37** | **6,62** | **0,789** |

CatBoost được chọn làm mô hình chính (`Assets/best_model.joblib`), giảm wMAPE khoảng 5,4 điểm phần trăm so với Moving Average. Số lượng chuẩn bị = dự báo + tồn kho an toàn với mức phục vụ 95% (z = 1,65).
