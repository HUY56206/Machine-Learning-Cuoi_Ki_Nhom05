"""Quản trị tồn kho từ kết quả dự báo (USE MODEL - bước 11).

    Safety Stock      = z x RMSE(nhà hàng, món) x sqrt(lead time)    (z = 1.65 <-> mức phục vụ 95%)
    Lượng cần chuẩn bị = max(0, Dự báo + Safety Stock - Tồn hiện tại)
    Cảnh báo          : Tồn hiện tại < Safety Stock  -> nguy cơ hết hàng (tô đỏ trên giao diện)

RMSE lấy riêng cho từng (nhà hàng, món) trên tập validation thay vì một con số chung,
vì món bán ít mà dùng sai số chung sẽ bị trữ dư rất nhiều.
"""
import numpy as np
import pandas as pd

from Utils import Config

UPSERT_FORECAST_SQL = """
    INSERT INTO forecasts (forecast_date, restaurant_id, menu_item_id, predicted_qty,
                           safety_stock, current_stock, recommended_order, model_name)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE predicted_qty = VALUES(predicted_qty), safety_stock = VALUES(safety_stock),
        current_stock = VALUES(current_stock), recommended_order = VALUES(recommended_order),
        created_at = CURRENT_TIMESTAMP
"""


class QSRInventory:
    def __init__(self, trainedmodel, z=Config.SERVICE_LEVEL_Z, lead_time_days=1):
        self.trainedmodel = trainedmodel
        self.z = z
        self.lead_time_days = lead_time_days

    def calcSafetyStock(self, forecast_df):
        rmse = self.trainedmodel.residual_rmse
        out = forecast_df.merge(rmse, on=Config.SERIES_KEYS, how="left")
        # Chuỗi chưa có sai số riêng -> dùng trung vị sai số của các chuỗi khác
        out["residual_rmse"] = out["residual_rmse"].fillna(rmse["residual_rmse"].median())
        out["safety_stock"] = np.round(self.z * out["residual_rmse"] * np.sqrt(self.lead_time_days), 2)
        return out

    @staticmethod
    def simulateCurrentStock(forecast_df, random_state=Config.RANDOM_STATE):
        """Dataset không có tồn kho thực tế -> mô phỏng tồn hiện tại trong khoảng 0-120% dự báo.
        Khi triển khai thật, giá trị này lấy từ hệ thống quản lý kho của nhà hàng."""
        rng = np.random.default_rng(random_state)
        return np.floor(forecast_df["predicted_qty"] * rng.uniform(0, 1.2, len(forecast_df))).astype(int)

    def recommendOrder(self, forecast_df, current_stock=None):
        out = self.calcSafetyStock(forecast_df)
        out["current_stock"] = self.simulateCurrentStock(out) if current_stock is None else current_stock
        need = out["predicted_qty"] + out["safety_stock"] - out["current_stock"]
        out["recommended_order"] = np.ceil(need.clip(lower=0)).astype(int)
        out["is_stockout_risk"] = (out["current_stock"] < out["safety_stock"]).astype(int)
        return out

    def saveForecasts(self, connector, plan_df):
        rows = [
            (pd.Timestamp(r.date).date(), r.restaurant_id, r.menu_item_id, float(r.predicted_qty),
             float(r.safety_stock), int(r.current_stock), int(r.recommended_order),
             self.trainedmodel.model_name)
            for r in plan_df.itertuples(index=False)
        ]
        connector.executeMany(UPSERT_FORECAST_SQL, rows)
        return len(rows)    # rowcount của MySQL đếm 2 cho mỗi dòng bị UPDATE nên không dùng
