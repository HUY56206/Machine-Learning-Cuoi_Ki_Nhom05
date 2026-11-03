"""Huấn luyện Ridge Regression.   Chạy: python -m Tests.AppRidgeRegression"""
from Connectors.Connector import Connector
from Models.QSRRidgeRegression import QSRRidgeRegression
from Utils import Config

connector = Connector()
connector.connect()
model = QSRRidgeRegression(connector)

# (5) Filter & load data
model.execQSRHistory()
model.processFeatures()
model.splitTrainValTest()
model.printSplitInfo()

# (6)(7) Chọn giải thuật & train
model.processTrain()
print("Tham số:", model.trainedmodel.params)

# (8) Đánh giá
print(model.evaluate("val"))
print(model.evaluate("test"))
model.saveMetricsReport()
model.visualizeActualAndPredictResult("R01", "M01", savePath=Config.FIGURES_DIR / "pred_ridge_R01_M01.png")

# (11) Dùng thử: dự báo ngày 24/12/2025 cho nhà hàng R01
print(model.forecastDate("2025-12-24", "R01").head(10))

# (9) Lưu mô hình
ret = model.saveModel("ridge.joblib")
print("ret save model =", ret)
connector.disConnect()
