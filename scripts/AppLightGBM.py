import sys

from Connectors.Connector import Connector
from Models.QSRLightGBM import QSRLightGBM
from Utils import Config

connector = Connector()
connector.connect()
model = QSRLightGBM(connector, fast="--fast" in sys.argv)


model.execQSRHistory()
model.processFeatures()
model.splitTrainValTest()
model.printSplitInfo()


model.processTrain()
print("best_iteration:", model.trainedmodel.params["best_iteration"])


print(model.evaluate("val"))
print(model.evaluate("test"))
model.saveMetricsReport()
model.visualizeActualAndPredictResult("R01", "M01", savePath=Config.FIGURES_DIR / "pred_lightgbm_R01_M01.png")


print(model.forecastDate("2025-12-24", "R01").head(10))


ret = model.saveModel("lightgbm.joblib")
print("ret save model =", ret)
connector.disConnect()
