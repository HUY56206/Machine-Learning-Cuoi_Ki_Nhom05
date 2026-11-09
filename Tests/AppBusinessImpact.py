"""Mô phỏng tác động kinh doanh của kế hoạch chuẩn bị hàng trên tập test.

Chạy: python -m Tests.AppBusinessImpact   (sau khi đã huấn luyện các mô hình)

Với mỗi dòng test (ngày, cửa hàng, món): lượng chuẩn bị = dự báo + z x RMSE(cửa hàng, món).
So với nhu cầu thực tế quantity_raw:
    thiếu hàng = max(0, thực tế - chuẩn bị)      thừa hàng = max(0, chuẩn bị - thực tế)
So sánh CatBoost, LightGBM, Ridge và hai baseline ở nhiều mức phục vụ (mặc định nhấn mạnh 95 %).
Kết quả ghi vào Assets/reports/business_impact.csv và Assets/figures/business_impact.png.
"""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from Connectors.Connector import Connector
from Models.QSRMLModel import QSRMLModel
from Utils import Config

MODELS = {
    "SeasonalNaive_7": "SeasonalNaive_7.joblib",
    "MovingAverage_7": "MovingAverage_7.joblib",
    "ridge": "ridge.joblib",
    "lightgbm": "lightgbm.joblib",
    "catboost": "catboost.joblib",
}
Z_LEVELS = {"90%": 1.28, "95%": Config.SERVICE_LEVEL_Z, "99%": 2.33}

connector = Connector()
connector.connect()
base = QSRMLModel(connector)
base.execQSRHistory()
base.processFeatures()
base.splitTrainValTest()
connector.disConnect()

rows = []
for name, file in MODELS.items():
    m = QSRMLModel()
    m.df_features, m.train, m.val, m.test = base.df_features, base.train, base.val, base.test
    if m.loadModel(file) is None:
        print(f"Bỏ qua {name}: không nạp được {file}")
        continue
    m.evaluate("val")                    # tính lại RMSE theo (cửa hàng, món) trên validation

    test = m.test[m.test["is_imputed"] == 0].copy()
    test["pred"] = m.predict(test)
    rmse = m.trainedmodel.residual_rmse
    test = test.merge(rmse, on=Config.SERIES_KEYS, how="left")
    test["residual_rmse"] = test["residual_rmse"].fillna(rmse["residual_rmse"].median())
    demand = test[Config.TARGET_RAW].to_numpy()

    for label, z in {"0 (không dự phòng)": 0.0, **Z_LEVELS}.items():
        prepared = np.ceil(test["pred"].to_numpy() + z * test["residual_rmse"].to_numpy())
        short = np.clip(demand - prepared, 0, None)
        waste = np.clip(prepared - demand, 0, None)
        rows.append({
            "mô hình": name, "mức phục vụ": label, "z": z,
            "tỷ lệ dòng thiếu hàng (%)": round(float((short > 0).mean() * 100), 2),
            "fill rate (%)": round(float((1 - short.sum() / demand.sum()) * 100), 2),
            "tổng lượng thiếu": int(short.sum()),
            "tổng lượng thừa": int(waste.sum()),
            "thừa / chuẩn bị (%)": round(float(waste.sum() / prepared.sum() * 100), 2),
            "tổng chuẩn bị": int(prepared.sum()),
        })

out = pd.DataFrame(rows)
Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
Config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
out.to_csv(Config.REPORTS_DIR / "business_impact.csv", index=False, encoding="utf-8-sig")
print(out.to_string(index=False))

focus = out[out["mức phục vụ"] == "95%"].set_index("mô hình")
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
focus["tổng lượng thiếu"].plot.bar(ax=axes[0], color="#d9534f")
axes[0].set_title("Tổng lượng thiếu hàng (mức phục vụ 95%)")
focus["tổng lượng thừa"].plot.bar(ax=axes[1], color="#f0ad4e")
axes[1].set_title("Tổng lượng thừa hàng (mức phục vụ 95%)")
for ax in axes:
    ax.set_xlabel("")
    ax.grid(alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=30)
fig.tight_layout()
fig.savefig(Config.FIGURES_DIR / "business_impact.png", dpi=150)
print("Đã lưu business_impact.csv và business_impact.png")
