"""Cấu hình chung của dự án: đường dẫn, kết nối CSDL, mốc chia dữ liệu, danh sách đặc trưng.

Thông tin đăng nhập MySQL đọc từ file .env ở thư mục gốc (không đẩy lên Git):
    QSR_DB_HOST=127.0.0.1
    QSR_DB_PORT=3306
    QSR_DB_USER=root
    QSR_DB_PASSWORD=...
    QSR_DB_NAME=qsr_db
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path=BASE_DIR / ".env"):
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())


_load_env_file()

# ---------------------------------------------------------------- CSDL MySQL
DB_SERVER = os.getenv("QSR_DB_HOST", "localhost")
DB_PORT = int(os.getenv("QSR_DB_PORT", 3306))
DB_USERNAME = os.getenv("QSR_DB_USER", "root")
DB_PASSWORD = os.getenv("QSR_DB_PASSWORD", "")
DB_DATABASE = os.getenv("QSR_DB_NAME", "qsr_db")

# ---------------------------------------------------------------- Đường dẫn
RAW_FILE = BASE_DIR / "data" / "raw" / "qsr_demand_dataset.csv"
SPLIT_DIR = BASE_DIR / "data" / "splits"
SCHEMA_FILE = BASE_DIR / "Database" / "qsr_schema.sql"
ASSETS_DIR = BASE_DIR / "Assets"              # mô hình đã train (.joblib)
FIGURES_DIR = ASSETS_DIR / "figures"          # biểu đồ thống kê
REPORTS_DIR = ASSETS_DIR / "reports"          # bảng so sánh mô hình, kết quả dự báo

# ---------------------------------------------------------------- Chuỗi thời gian
DATE_COL = "date"
SERIES_KEYS = ["restaurant_id", "menu_item_id"]
TARGET = "quantity"          # đã làm sạch -> tạo lag và huấn luyện
TARGET_RAW = "quantity_raw"  # giá trị gốc -> đánh giá val/test

# Chia theo thời gian - bài toán dự báo ngày mai (one-step-ahead)
TRAIN_END = "2025-06-30"
VAL_START, VAL_END = "2025-07-01", "2025-09-30"
TEST_START, TEST_END = "2025-10-01", "2025-12-31"   # 15 x 50 x 92 = 69.000 dòng

RANDOM_STATE = 42

# Làm sạch: outlier khi quantity > median + k * 1.4826 * MAD (cùng nhà hàng, món, thứ),
# thống kê chỉ tính trên train và chỉ trên ngày thường (không promo / holiday / event)
OUTLIER_MAD_K = 8

# Tồn kho: mức phục vụ 95% -> z = 1.65
SERVICE_LEVEL_Z = 1.65

# ---------------------------------------------------------------- Đặc trưng
LAGS = [1, 7, 14, 28]
ROLL_WINDOWS = [7, 28]

CATEGORICAL_FEATURES = ["restaurant_id", "menu_item_id", "category", "city", "precip_type"]

NUMERIC_FEATURES = [
    # lịch
    "day_of_week_num", "is_weekend", "month", "week_of_year", "day_of_month", "day_of_year", "year",
    # ngoại sinh (đã biết trước tại thời điểm dự báo)
    "unit_price", "avg_temp_f", "precip_inches",
    "is_holiday", "is_holiday_tomorrow", "is_holiday_yesterday",
    "is_special_event", "is_promotion",
    # lịch sử bán hàng (chỉ dùng dữ liệu <= t-1)
    *[f"lag_{k}" for k in LAGS],
    *[f"roll_mean_{w}" for w in ROLL_WINDOWS],
    *[f"roll_std_{w}" for w in ROLL_WINDOWS],
    "dow_mean_4w",
]

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
