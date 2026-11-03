"""Thống kê & trực quan hoá dữ liệu bán hàng từ MySQL.

Chạy: python -m Tests.AppStatistic          (biểu đồ lưu vào Assets/figures/)
"""
from Connectors.Connector import Connector
from Models.QSRStatistic import QSRStatistic
from Utils import Config

Config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
fig = lambda name: Config.FIGURES_DIR / name

connector = Connector()
connector.connect()
qs = QSRStatistic(connector)
qs.execQSRHistory()
qs.printHead()
qs.printInfo()

# 1. Tỉ trọng số lượng bán theo nhóm món
df = qs.processCategoryDistribution()
print(df)
qs.visualizePieChart(df, "category", "quantity", "Tỉ trọng số lượng bán theo nhóm món",
                     savePath=fig("01_category_distribution.png"))

# 2. Doanh thu theo nhóm món
df = qs.processRevenueByCategory()
print(df)
qs.visualizeBarChart(df, "category", "revenue", "Doanh thu theo nhóm món", savePath=fig("02_revenue_category.png"))

# 3. Doanh thu theo chi nhánh
df = qs.processSalesByStore()
print(df)
qs.visualizeBarChart(df, "restaurant_name", "revenue", "Doanh thu theo nhà hàng", horizontal=True,
                     savePath=fig("03_revenue_store.png"))

# 4. Top 10 món bán chạy nhất / chậm nhất
df = qs.processTopItems(10)
print(df)
qs.visualizeBarChart(df, "menu_item_name", "quantity", "Top 10 món bán chạy nhất", horizontal=True,
                     savePath=fig("04_top_items.png"))
df = qs.processTopItems(10, ascending=True)
print(df)
qs.visualizeBarChart(df, "menu_item_name", "quantity", "10 món bán chậm nhất", horizontal=True,
                     savePath=fig("05_bottom_items.png"))

# 5. Ngày thường vs cuối tuần
df = qs.processDayOfWeekSales()
print(df)
qs.visualizeBarChart(df, "day_of_week", "quantity", "Số lượng bán trung bình theo thứ",
                     savePath=fig("06_day_of_week.png"))

# 6. Biến động doanh số theo tháng / theo năm-tháng
df = qs.processMonthlySales()
print(df)
qs.visualizeLinePlotChart(df, "month", "revenue", "Biến động doanh thu theo tháng",
                          savePath=fig("07_monthly.png"))
df = qs.processYearMonthSales()
qs.visualizeLinePlotChart(df, "month", "revenue", "Doanh thu theo năm và tháng", hue="year",
                          savePath=fig("08_year_month.png"))

# 7. Tác động của khuyến mãi / ngày lễ / sự kiện
for i, factor in enumerate(["is_promotion", "is_holiday", "is_special_event"]):
    print(qs.processUpliftByFactor(factor))
    df = qs.processUpliftByCategory(factor)
    print(df)
    qs.visualizeBarChart(df, "category", "uplift_pct", f"Mức tăng lượng bán (%) khi {factor} theo nhóm món",
                         savePath=fig(f"09_{i}_uplift_{factor}.png"))

# 8. Tác động của thời tiết
df = qs.processWeatherImpact()
print(df)
qs.visualizeBarChart(df, "precip_type", "quantity", "Số lượng bán trung bình theo thời tiết",
                     savePath=fig("10_weather.png"))
df = qs.processTemperatureImpact()
print(df)
qs.visualizeMultiBarChart(df, "temp_range", "Số lượng bán trung bình theo nhiệt độ và nhóm món",
                          savePath=fig("11_temperature.png"))

connector.disConnect()
print("Đã lưu biểu đồ vào", Config.FIGURES_DIR)
