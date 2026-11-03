"""Huấn luyện LightGBM.   Chạy: python -m Tests.AppLightGBM   (thêm --fast để chạy thử 300 vòng)"""
import sys

from Connectors.Connector import Connector
from Models.QSRLightGBM import QSRLightGBM
from Utils import Config

connector = Connector()
connector.connect()
model = QSRLightGBM(connector, fast="--fast" in sys.argv)

# (5) Filter & load data
model.execQSRHistory()
model.processFeatures()
model.splitTrainValTest()
model.printSplitInfo()

# (6)(7) Chọn giải thuật & train (early stopping trên validation)
model.processTrain()
print("best_iteration:", model.trainedmodel.params["best_iteration"])

# (8) Đánh giá
print(model.evaluate("val"))
print(model.evaluate("test"))
model.saveMetricsReport()
model.visualizeActualAndPredictResult("R01", "M01", savePath=Config.FIGURES_DIR / "pred_lightgbm_R01_M01.png")

# (11) Dùng thử: dự báo ngày 24/12/2025 cho nhà hàng R01
print(model.forecastDate("2025-12-24", "R01").head(10))

# (9) Lưu mô hình
ret = model.saveModel("lightgbm.joblib")
print("ret save model =", ret)
connector.disConnect()
