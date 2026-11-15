import shutil

import pandas as pd

from Models.QSRStatistic import QSRStatistic
from Utils import Config

metrics = pd.read_csv(Config.REPORTS_DIR / "metrics.csv")
print(metrics.sort_values(["split", "wMAPE"]).to_string(index=False))

val = metrics[metrics["split"] == "val"].sort_values("wMAPE")
best = val.iloc[0]["model"]
shutil.copy(Config.ASSETS_DIR / f"{best}.joblib", Config.ASSETS_DIR / "best_model.joblib")
print(f"\n=> Mô hình tốt nhất trên validation: {best} -> Assets/best_model.joblib")

chart = metrics.pivot(index="model", columns="split", values="wMAPE")[["val", "test"]] \
               .sort_values("val", ascending=False).reset_index()
QSRStatistic().visualizeMultiBarChart(chart, "model", "So sánh wMAPE các mô hình (càng thấp càng tốt)",
                                      savePath=Config.FIGURES_DIR / "model_comparison.png")
