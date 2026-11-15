from Connectors.Connector import Connector
from Models.QSRRidgeRegression import QSRRidgeRegression
from Utils import Config

connector = Connector()
connector.connect()
model = QSRRidgeRegression(connector)


model.execQSRHistory()
model.processFeatures()
model.splitTrainValTest()
model.printSplitInfo()


model.processTrain()
print("Tham số:", model.trainedmodel.params)


print(model.evaluate("val"))
print(model.evaluate("test"))
model.saveMetricsReport()
model.visualizeActualAndPredictResult("R01", "M01", savePath=Config.FIGURES_DIR / "pred_ridge_R01_M01.png")


print(model.forecastDate("2025-12-24", "R01").head(10))


ret = model.saveModel("ridge.joblib")
print("ret save model =", ret)
connector.disConnect()
