"""PREPARING DATA (bước 2-4, Slide 08): làm sạch dữ liệu thô rồi lưu vào MySQL.

Nguyên tắc chống rò rỉ dữ liệu:
- Mọi thống kê dùng để điền thiếu / phát hiện outlier chỉ tính trên tập TRAIN.
- Không xoá nhu cầu thật: ngày có promotion / holiday / special event không bị coi là outlier.
- Giữ giá trị gốc ở cột quantity_raw để đánh giá val/test trên số thật.
"""
import numpy as np
import pandas as pd

from Utils import Config

DOW_KEYS = Config.SERIES_KEYS + ["day_of_week_num"]
EVENT_FLAGS = ["is_promotion", "is_holiday", "is_special_event"]


class QSRDataCleaning:
    def __init__(self, connector=None):
        self.connector = connector
        self.df = None

    def loadRawDataset(self, path=Config.RAW_FILE):
        # keep_default_na=False: chuỗi "None" ở precip_type nghĩa là "không mưa", không phải missing
        self.df = pd.read_csv(path, parse_dates=[Config.DATE_COL], keep_default_na=False,
                              na_values={"quantity": [""]}, low_memory=False)
        self.df["quantity"] = pd.to_numeric(self.df["quantity"], errors="coerce")
        return self.df

    def checkStructure(self):
        """Loại trùng lặp và kiểm tra lưới (ngày x nhà hàng x món) đầy đủ."""
        keys = [Config.DATE_COL] + Config.SERIES_KEYS
        n_dup = self.df.duplicated(keys).sum()
        self.df = self.df.drop_duplicates(keys)

        n_dates = self.df[Config.DATE_COL].nunique()
        n_series = self.df.groupby(Config.SERIES_KEYS).ngroups
        expected = (self.df[Config.DATE_COL].max() - self.df[Config.DATE_COL].min()).days + 1
        if n_dates != expected or len(self.df) != n_dates * n_series:
            raise ValueError(f"Chuỗi thời gian không liên tục: {len(self.df)} dòng, kỳ vọng {expected * n_series}")
        print(f"Trùng lặp đã loại: {n_dup} | {n_series} chuỗi x {n_dates} ngày = {len(self.df):,} dòng")

    def fitDowStatistics(self):
        """Median & MAD theo (nhà hàng, món, thứ) - chỉ trên train, chỉ ngày thường."""
        train = self.df[self.df[Config.DATE_COL] <= Config.TRAIN_END]
        normal_days = train[train[EVENT_FLAGS].sum(axis=1) == 0]
        grp = normal_days.groupby(DOW_KEYS)["quantity"]
        stats = grp.median().rename("dow_median").to_frame()
        stats["dow_mad"] = grp.apply(lambda s: (s - s.median()).abs().median())
        return stats.reset_index()

    def processCleaning(self):
        self.checkStructure()
        df = self.df
        df.loc[df["quantity"] < 0, "quantity"] = np.nan
        for col in ["holiday_name", "special_event_name"]:
            df[col] = df[col].replace("", None)
        df["precip_type"] = df["precip_type"].replace("", "None")

        df = df.merge(self.fitDowStatistics(), on=DOW_KEYS, how="left")
        df[Config.TARGET_RAW] = df["quantity"]
        df["is_imputed"] = df["quantity"].isna().astype("int8")

        upper = df["dow_median"] + Config.OUTLIER_MAD_K * 1.4826 * df["dow_mad"].clip(lower=1)
        is_event_day = df[EVENT_FLAGS].sum(axis=1) > 0
        df["is_outlier"] = ((df["quantity"] > upper) & ~is_event_day).astype("int8")

        # Giá trị thiếu và outlier (lỗi ghi nhận) được thay bằng median cùng thứ trong tuần
        replace = (df["is_imputed"] == 1) | (df["is_outlier"] == 1)
        df.loc[replace, "quantity"] = df.loc[replace, "dow_median"].round()
        df["quantity"] = df["quantity"].astype("int32")

        df = (df.drop(columns=["dow_median", "dow_mad"])
                .sort_values([Config.DATE_COL] + Config.SERIES_KEYS)
                .reset_index(drop=True))
        df.insert(0, "sale_id", np.arange(1, len(df) + 1))
        self.df = df
        return df

    def printCleaningReport(self):
        d = self.df[Config.DATE_COL]
        periods = {"train": d <= Config.TRAIN_END,
                   "val": d.between(Config.VAL_START, Config.VAL_END),
                   "test": d.between(Config.TEST_START, Config.TEST_END)}
        for name, mask in periods.items():
            sub = self.df[mask]
            print(f"{name:5s}: {len(sub):>9,} dòng | imputed={sub['is_imputed'].sum():>5,}"
                  f" | outlier={sub['is_outlier'].sum():>5,}")
        print(f"Giá trị thiếu còn lại: {int(self.df['quantity'].isna().sum())}")

    # ------------------------------------------------------------ lưu vào MySQL
    def splitTables(self):
        """Tách bảng phẳng thành 5 bảng theo đúng độ chi tiết của từng thực thể."""
        df = self.df
        return {
            "stores": df[["restaurant_id", "restaurant_name", "city", "state"]].drop_duplicates(),
            "products": df[["menu_item_id", "menu_item_name", "category", "unit_price"]].drop_duplicates(),
            "weather_events": df[["restaurant_id", "date", "avg_temp_f", "precip_inches", "precip_type",
                                  "is_holiday", "holiday_name", "is_special_event", "special_event_name"]]
                              .drop_duplicates(["restaurant_id", "date"]),
            "promotions": df.loc[df["is_promotion"] == 1, ["restaurant_id", "menu_item_id", "date"]],
            "daily_sales": df[["sale_id", "date", "restaurant_id", "menu_item_id",
                               "quantity", "quantity_raw", "is_imputed", "is_outlier"]]
                           .astype({"quantity_raw": "Int64"}),
        }

    INSERT_SQL = {
        "stores": "INSERT INTO stores VALUES (%s, %s, %s, %s)",
        "products": "INSERT INTO products VALUES (%s, %s, %s, %s)",
        "weather_events": "INSERT INTO weather_events VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        "promotions": "INSERT INTO promotions (restaurant_id, menu_item_id, promo_date) VALUES (%s, %s, %s)",
        "daily_sales": "INSERT INTO daily_sales VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
    }

    @staticmethod
    def toRows(df):
        """DataFrame -> list tuple kiểu Python thuần (NaN -> NULL, Timestamp -> date)."""
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.date
        df = df.astype(object).where(df.notna(), None)
        return list(df.itertuples(index=False, name=None))

    def saveToMySQL(self):
        """Ghi 5 bảng theo thứ tự đúng ràng buộc khoá ngoại."""
        for name, table in self.splitTables().items():
            n = self.connector.executeMany(self.INSERT_SQL[name], self.toRows(table))
            print(f"{name:15s}: {n:>9,} dòng")
