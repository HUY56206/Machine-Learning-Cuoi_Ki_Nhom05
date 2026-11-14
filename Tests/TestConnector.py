from Connectors.Connector import Connector

connector = Connector()
conn = connector.connect()
print("connection is successful!" if conn else "connection failed!")

print("Tables:", connector.getTablesName())
df = connector.queryDataset("""
    SELECT 'stores' AS tbl, COUNT(*) AS n FROM stores
    UNION ALL SELECT 'products', COUNT(*) FROM products
    UNION ALL SELECT 'weather_events', COUNT(*) FROM weather_events
    UNION ALL SELECT 'promotions', COUNT(*) FROM promotions
    UNION ALL SELECT 'daily_sales', COUNT(*) FROM daily_sales
    UNION ALL SELECT 'forecasts', COUNT(*) FROM forecasts""")
print(df)
connector.disConnect()
