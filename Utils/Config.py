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


DB_SERVER = os.getenv("QSR_DB_HOST", "localhost")
DB_PORT = int(os.getenv("QSR_DB_PORT", 3306))
DB_USERNAME = os.getenv("QSR_DB_USER", "root")
DB_PASSWORD = os.getenv("QSR_DB_PASSWORD", "")
DB_DATABASE = os.getenv("QSR_DB_NAME", "qsr_db")


RAW_FILE = BASE_DIR / "data" / "raw" / "qsr_demand_dataset.csv"
SPLIT_DIR = BASE_DIR / "data" / "splits"
SCHEMA_FILE = BASE_DIR / "Database" / "qsr_schema.sql"
ASSETS_DIR = BASE_DIR / "Assets"
FIGURES_DIR = ASSETS_DIR / "figures"
REPORTS_DIR = ASSETS_DIR / "reports"


DATE_COL = "date"
SERIES_KEYS = ["restaurant_id", "menu_item_id"]
TARGET = "quantity"
TARGET_RAW = "quantity_raw"


TRAIN_END = "2025-06-30"
VAL_START, VAL_END = "2025-07-01", "2025-09-30"
TEST_START, TEST_END = "2025-10-01", "2025-12-31"

RANDOM_STATE = 42


OUTLIER_MAD_K = 8


SERVICE_LEVEL_Z = 1.65


LAGS = [1, 7, 14, 28]
ROLL_WINDOWS = [7, 28]

CATEGORICAL_FEATURES = ["restaurant_id", "menu_item_id", "category", "city", "precip_type"]

NUMERIC_FEATURES = [

    "day_of_week_num", "is_weekend", "month", "week_of_year", "day_of_month", "day_of_year", "year",

    "unit_price", "avg_temp_f", "precip_inches",
    "is_holiday", "is_holiday_tomorrow", "is_holiday_yesterday",
    "is_special_event", "is_promotion",

    *[f"lag_{k}" for k in LAGS],
    *[f"roll_mean_{w}" for w in ROLL_WINDOWS],
    *[f"roll_std_{w}" for w in ROLL_WINDOWS],
    "dow_mean_4w",
]

FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
