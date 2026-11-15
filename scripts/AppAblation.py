import sys

import matplotlib.pyplot as plt
import pandas as pd

from Connectors.Connector import Connector
from Models.QSRCatBoost import QSRCatBoost
from Utils import Config

GROUPS = {
    "Lịch sử bán (lag, rolling)": [c for c in Config.FEATURES if c.startswith(("lag_", "roll_")) or c == "dow_mean_4w"],
    "Lịch (thứ, tháng, năm...)": ["day_of_week_num", "is_weekend", "month", "week_of_year", "day_of_month", "day_of_year", "year"],
    "Ngày lễ": ["is_holiday", "is_holiday_tomorrow", "is_holiday_yesterday"],
    "Sự kiện đặc biệt": ["is_special_event"],
    "Khuyến mãi": ["is_promotion"],
    "Thời tiết": ["avg_temp_f", "precip_inches", "precip_type"],
    "Giá": ["unit_price"],
    "Định danh (cửa hàng, món, nhóm, thành phố)": ["restaurant_id", "menu_item_id", "category", "city"],
}

iterations = 300 if "--fast" in sys.argv else 3000 if "--full" in sys.argv else 1000

connector = Connector()
connector.connect()
model = QSRCatBoost(connector)
model.PARAMS = {**QSRCatBoost.PARAMS, "iterations": iterations, "verbose": 0}
model.execQSRHistory()
model.processFeatures()
model.splitTrainValTest()
model.printSplitInfo()
connector.disConnect()


def run(columns):
    model.processTrain(columns_input=columns)
    return model.evaluate("test")


rows = []
full = run(Config.FEATURES)
rows.append({"kịch bản": "Đầy đủ đặc trưng", "số đặc trưng": len(Config.FEATURES),
             "wMAPE": full.WMAPE, "MAE": full.MAE, "RMSE": full.RMSE, "R2": full.R2_SCORE})
print(rows[-1])

for name, cols in GROUPS.items():
    keep = [c for c in Config.FEATURES if c not in cols]
    r = run(keep)
    rows.append({"kịch bản": f"Bỏ: {name}", "số đặc trưng": len(keep),
                 "wMAPE": r.WMAPE, "MAE": r.MAE, "RMSE": r.RMSE, "R2": r.R2_SCORE})
    print(rows[-1])

out = pd.DataFrame(rows)
out["wMAPE tăng (điểm %)"] = ((out["wMAPE"] - full.WMAPE) * 100).round(2)
Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
Config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
out.to_csv(Config.REPORTS_DIR / "ablation.csv", index=False, encoding="utf-8-sig")
print(out.to_string(index=False))

plot = out.iloc[1:].sort_values("wMAPE tăng (điểm %)")
fig, ax = plt.subplots(figsize=(10, 5))
ax.barh(plot["kịch bản"], plot["wMAPE tăng (điểm %)"])
ax.set_xlabel("wMAPE tăng so với mô hình đầy đủ (điểm phần trăm)")
ax.set_title("Đóng góp của từng nhóm đặc trưng (tập test)")
ax.grid(alpha=0.3, axis="x")
fig.tight_layout()
fig.savefig(Config.FIGURES_DIR / "ablation.png", dpi=150)
print("Đã lưu ablation.csv và ablation.png")
