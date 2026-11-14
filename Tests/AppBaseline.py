from Connectors.Connector import Connector
from Models.QSRBaselineModel import QSRBaselineModel

connector = Connector()
connector.connect()

model = QSRBaselineModel(connector, method="seasonal_naive")
model.execQSRHistory()
model.processFeatures()
model.splitTrainValTest()
model.printSplitInfo()
model.saveDatasets()

for method in ("seasonal_naive", "moving_average"):
    baseline = QSRBaselineModel(connector, method=method)
    baseline.train, baseline.val, baseline.test = model.train, model.val, model.test
    baseline.processTrain()
    print(baseline.evaluate("val"))
    print(baseline.evaluate("test"))
    baseline.saveMetricsReport()
    print("ret save model =", baseline.saveModel(f"{baseline.model_name}.joblib"))

connector.disConnect()
