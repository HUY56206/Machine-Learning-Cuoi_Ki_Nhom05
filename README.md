# QSR Demand Forecasting & Inventory Optimization

Dự báo nhu cầu **ngày mai** cho 15 nhà hàng × 50 món, từ đó đề xuất tồn kho an toàn và lượng cần chuẩn bị.
Cấu trúc dự án theo Slide 05 & 09 (PyQt6 và tích hợp mô hình Máy học) và quy trình Slide 08.

## Cấu trúc (kiến trúc đa tầng - Slide 12, 13)

```
Connectors/Connector.py      Tầng Data Access: kết nối MySQL, queryDataset() -> DataFrame
Database/qsr_schema.sql      Lược đồ CSDL qsr_db (5 bảng + bảng forecasts)
Models/                      Tầng ML Logic
  QSRDataCleaning.py           PREPARING DATA: làm sạch CSV thô, nạp vào MySQL
  QSRStatistic.py              Thống kê & biểu đồ (nạp dữ liệu từ MySQL)
  QSRMLModel.py                Lớp cơ sở: đặc trưng, chia tập, đánh giá, lưu/nạp, dự báo
  QSRBaselineModel.py          Seasonal Naive, Moving Average 7
  QSRRidgeRegression.py        Ridge Regression
  QSRLightGBM.py               LightGBM
  QSRCatBoost.py               CatBoost
  QSRInventory.py              Safety Stock & đề xuất lượng chuẩn bị
  MetricsResult.py             MAE, MSE, RMSE, R2, wMAPE, Bias
  TrainedModel.py              Gói mô hình đã train + thông tin tái sử dụng
Utils/
  Config.py                    Cấu hình chung (đọc mật khẩu từ .env)
  FileUtil.py                  saveModel / loadModel
Tests/                       Các App chạy từng bước + pytest
Assets/                      Mô hình đã lưu (.joblib), figures/, reports/
forecast/, ML_QSR/           Tầng UI (web Django)
```

## Quy trình (Slide 08)

| Phiên | Bước | Lớp / phương thức | Chạy |
|---|---|---|---|
| PREPARING DATA | (2)-(4) làm sạch, lưu CSDL | `QSRDataCleaning` | `python -m Tests.AppPrepareData` |
| | Thống kê, trực quan hoá | `QSRStatistic` | `python -m Tests.AppStatistic` |
| BUILD MODEL | (5) Filter & load data | `execQSRHistory()` → `processFeatures()` → `splitTrainValTest()` | |
| | (6) Select algorithm | `QSRBaselineModel`, `QSRRidgeRegression`, `QSRLightGBM`, `QSRCatBoost` | `python -m Tests.AppBaseline` |
| | (7) Train | `processTrain()` | `python -m Tests.AppRidgeRegression` |
| | (8) Evaluate | `evaluate()` → `MetricsResult` | `python -m Tests.AppLightGBM` |
| | (9) Save model | `saveModel()` | `python -m Tests.AppCatBoost` |
| | Chọn mô hình tốt nhất | theo wMAPE trên validation | `python -m Tests.AppCompareModels` |
| USE MODEL | (10) Load model | `loadModel("best_model.joblib")` | |
| | (11) Use model | `forecastDate()` + `QSRInventory` | `python -m Tests.AppInventory 2025-12-24 R01` |

## Cài đặt

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
brew install libomp            # macOS: LightGBM cần thư viện này
cp .env.example .env           # rồi điền mật khẩu MySQL
python -m Tests.TestConnector  # kiểm tra kết nối
python -m pytest               # kiểm thử chống rò rỉ dữ liệu + tồn kho
```

Luôn chạy bằng `python -m Tests.<TenFile>` từ thư mục gốc (hoặc đặt thư mục gốc làm Content Root trong PyCharm).

## Chia dữ liệu

| Tập | Thời gian | Vai trò |
|---|---|---|
| Train | 2021-01-29 → 2025-06-30 | huấn luyện |
| Validation | 2025-07-01 → 2025-09-30 | early stopping, chọn mô hình, sai số cho Safety Stock |
| Test | 2025-10-01 → 2025-12-31 (69.000 dòng) | báo cáo kết quả cuối |

Đánh giá dùng giá trị gốc `quantity_raw` và **loại các dòng `is_imputed = 1`**.

## Web Django (backend)

Web dùng chung MySQL `qsr_db` với pipeline ML (Django ORM + `mysqlclient`; thông tin kết nối đọc từ `.env`).

```bash
brew services run mysql                 # bật MySQL (macOS)
python manage.py migrate                # tạo bảng của web (hồ sơ, kiểm kho, đề xuất, thông báo, cấu hình)
python manage.py seed_demo              # tài khoản mẫu + lịch sử kiểm kho + 1 đề xuất chờ duyệt
python manage.py runserver              # http://127.0.0.1:8000/
python manage.py test forecast          # 37 bài kiểm thử nghiệp vụ & phân quyền
python manage.py send_reminders         # (cron) nhắc nhân viên kiểm kho cuối ca
```

Tài khoản mẫu (mật khẩu mặc định `Qsr@2025!`, đổi bằng `seed_demo --password ...`):
`lan.r01` quản lý R01 · `minh.r01` nhân viên R01 · `hung.r02` / `mai.r02` R02 · `admin` quản trị.

| Thành phần | Vị trí |
|---|---|
| Model (bảng ML `managed=False` + bảng web) | `forecast/models.py` |
| Gọi mô hình đã train, dự báo 1 cửa hàng/ngày | `forecast/services/engine.py` |
| Đề xuất chuẩn bị, duyệt/mở lại, kiểm kho | `forecast/services/plans.py` |
| Quản trị: dữ liệu/nhập tệp, chạy dự báo, cửa hàng, tài khoản, cấu hình | `forecast/services/adminops.py` · `forecast/api_admin.py` |
| Thông báo theo vai trò và tùy chọn hồ sơ | `forecast/services/notifications.py` |
| Trang HTML / API JSON / phân quyền | `forecast/views.py` · `forecast/api.py` · `forecast/permissions.py` |

Bắt buộc quản lý duyệt (`require_approval`) và ngày vận hành chỉ đổi trong Django Admin (`/admin/`, mục *Cấu hình hệ thống*). Ngày vận hành là cấu hình (`SystemConfig.operating_date`, demo = 30/10/2025); dự báo cho ngày kế tiếp và không hiển thị số bán sau ngày vận hành.
