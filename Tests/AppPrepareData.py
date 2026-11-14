from Connectors.Connector import Connector
from Models.QSRDataCleaning import QSRDataCleaning
from Utils import Config

cleaning = QSRDataCleaning()
cleaning.loadRawDataset()
cleaning.processCleaning()
cleaning.printCleaningReport()


connector = Connector(database="")
connector.connect()
connector.executeScript(Config.SCHEMA_FILE)
connector.disConnect()
print("Đã tạo schema", Config.DB_DATABASE)

connector = Connector()
connector.connect()
cleaning.connector = connector
cleaning.saveToMySQL()
print(connector.queryDataset("SELECT COUNT(*) AS n_sales, MIN(sale_date) AS tu_ngay, "
                             "MAX(sale_date) AS den_ngay FROM daily_sales"))
connector.disConnect()
