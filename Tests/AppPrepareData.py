"""PREPARING DATA: làm sạch CSV thô -> tạo CSDL qsr_db -> nạp 5 bảng.

Chạy: python -m Tests.AppPrepareData
CẢNH BÁO: lệnh này xoá và tạo lại toàn bộ bảng trong qsr_db (kể cả bảng forecasts).
"""
from Connectors.Connector import Connector
from Models.QSRDataCleaning import QSRDataCleaning
from Utils import Config

cleaning = QSRDataCleaning()
cleaning.loadRawDataset()
cleaning.processCleaning()
cleaning.printCleaningReport()

# Tạo schema (kết nối chưa chọn database)
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
