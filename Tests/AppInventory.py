"""USE MODEL: nạp mô hình tốt nhất -> dự báo 1 ngày -> tồn kho an toàn -> đề xuất lượng chuẩn bị.

Chạy: python -m Tests.AppInventory 2025-12-24 R01
      (mặc định: ngày 2025-12-24, tất cả nhà hàng)
"""
import sys

import pandas as pd

from Connectors.Connector import Connector
from Models.QSRInventory import QSRInventory
from Models.QSRMLModel import QSRMLModel
from Utils import Config

forecast_date = sys.argv[1] if len(sys.argv) > 1 else "2025-12-24"
restaurant_id = sys.argv[2] if len(sys.argv) > 2 else None

connector = Connector()
connector.connect()

# (10) Nạp mô hình đã lưu - không cần train lại
model = QSRMLModel(connector)
model.loadModel("best_model.joblib")
print("Mô hình:", model.model_name, "| train đến:", model.trainedmodel.trained_until)

# Chỉ cần 60 ngày lịch sử trước ngày dự báo để tạo lag / rolling
# (+1 ngày sau để biết ngày mai có phải ngày lễ - lịch lễ biết trước, không phải rò rỉ)
start = (pd.Timestamp(forecast_date) - pd.Timedelta(days=60)).date()
end = (pd.Timestamp(forecast_date) + pd.Timedelta(days=1)).date()
model.execQSRHistory(restaurant_id=restaurant_id, start=start, end=end)
model.processFeatures()

# (11) Dự báo + tồn kho
forecast = model.forecastDate(forecast_date, restaurant_id)
inventory = QSRInventory(model.trainedmodel)
plan = inventory.recommendOrder(forecast)

cols = ["restaurant_id", "menu_item_name", "predicted_qty", "safety_stock", "current_stock",
        "recommended_order", "is_stockout_risk", Config.TARGET_RAW]
print(plan[cols].head(20).to_string(index=False))
print(f"\nSố món có nguy cơ hết hàng: {plan['is_stockout_risk'].sum()} / {len(plan)}")

Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
plan.to_csv(Config.REPORTS_DIR / f"inventory_plan_{forecast_date}.csv", index=False)
print("Đã lưu vào bảng forecasts:", inventory.saveForecasts(connector, plan), "dòng")
connector.disConnect()
