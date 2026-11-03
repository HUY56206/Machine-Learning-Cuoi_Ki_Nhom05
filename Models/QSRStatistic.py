"""Thống kê & trực quan hoá dữ liệu bán hàng QSR (nạp trực tiếp từ MySQL)."""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from Utils import Config

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

HISTORY_SQL = """
    SELECT s.sale_date AS date, s.restaurant_id, st.restaurant_name, st.city,
           s.menu_item_id, p.menu_item_name, p.category, p.unit_price,
           s.quantity, s.quantity_raw, s.is_imputed, s.is_outlier,
           w.avg_temp_f, w.precip_inches, w.precip_type,
           w.is_holiday, w.is_special_event,
           (pr.promotion_id IS NOT NULL) AS is_promotion
    FROM daily_sales s
    JOIN stores st  ON st.restaurant_id = s.restaurant_id
    JOIN products p ON p.menu_item_id  = s.menu_item_id
    JOIN weather_events w ON w.restaurant_id = s.restaurant_id AND w.event_date = s.sale_date
    LEFT JOIN promotions pr ON pr.restaurant_id = s.restaurant_id
                           AND pr.menu_item_id  = s.menu_item_id
                           AND pr.promo_date    = s.sale_date
"""


class QSRStatistic:
    def __init__(self, connector=None):
        self.connector = connector
        self.df = None

    # ================================================================ nạp dữ liệu
    def execQSRHistory(self, restaurant_id=None, start=None, end=None):
        """Nạp lịch sử bán hàng (join 5 bảng) từ MySQL thành một DataFrame phẳng."""
        sql, params = HISTORY_SQL + " WHERE 1=1", []
        if restaurant_id:
            sql += " AND s.restaurant_id = %s"; params.append(restaurant_id)
        if start:
            sql += " AND s.sale_date >= %s"; params.append(start)
        if end:
            sql += " AND s.sale_date <= %s"; params.append(end)
        df = self.connector.queryDataset(sql, tuple(params))

        df[Config.DATE_COL] = pd.to_datetime(df[Config.DATE_COL])
        for col in ["unit_price", "avg_temp_f", "precip_inches", "quantity_raw"]:
            df[col] = df[col].astype(float)            # DECIMAL -> float
        df["day_of_week_num"] = df[Config.DATE_COL].dt.day_of_week
        df["is_weekend"] = (df["day_of_week_num"] >= 5).astype("int8")
        df["month"] = df[Config.DATE_COL].dt.month
        df["year"] = df[Config.DATE_COL].dt.year
        df["revenue"] = df["quantity"] * df["unit_price"]
        self.df = df.sort_values([Config.DATE_COL] + Config.SERIES_KEYS).reset_index(drop=True)
        return self.df

    def printHead(self, row=5):
        print(self.df.head(row))

    def printTail(self, row=5):
        print(self.df.tail(row))

    def printInfo(self):
        self.df.info()

    def printDescribe(self):
        print(self.df.describe())

    # ================================================================ thống kê
    def processCategoryDistribution(self):
        """Tỉ trọng số lượng bán theo nhóm món."""
        return self.df.groupby("category", as_index=False)["quantity"].sum() \
                      .sort_values("quantity", ascending=False)

    def processRevenueByCategory(self):
        return self.df.groupby("category", as_index=False)["revenue"].sum() \
                      .sort_values("revenue", ascending=False)

    def processSalesByStore(self):
        """Doanh số theo chi nhánh - hỗ trợ điều chỉnh kinh doanh theo khu vực."""
        return self.df.groupby(["restaurant_id", "restaurant_name"], as_index=False)[["quantity", "revenue"]] \
                      .sum().sort_values("revenue", ascending=False)

    def processTopItems(self, n=10, ascending=False):
        """Top n món bán chạy nhất (ascending=True: bán chậm nhất)."""
        return self.df.groupby("menu_item_name", as_index=False)["quantity"].sum() \
                      .sort_values("quantity", ascending=ascending).head(n)

    def processDayOfWeekSales(self):
        """Số lượng bán trung bình mỗi món theo thứ trong tuần."""
        out = self.df.groupby("day_of_week_num", as_index=False)["quantity"].mean()
        out["day_of_week"] = out["day_of_week_num"].map(dict(enumerate(DAY_NAMES)))
        return out

    def processMonthlySales(self):
        """Biến động doanh số chung theo tháng (cộng dồn các năm)."""
        return self.df.groupby("month", as_index=False)[["quantity", "revenue"]].sum()

    def processYearMonthSales(self):
        """Biến động doanh số theo năm và theo tháng."""
        return self.df.groupby(["year", "month"], as_index=False)["revenue"].sum()

    def processUpliftByFactor(self, factor):
        """So sánh lượng bán trung bình có / không có một yếu tố (is_promotion, is_holiday, ...)."""
        out = self.df.groupby(factor, as_index=False)["quantity"].mean()
        base = out.loc[out[factor] == 0, "quantity"].iloc[0]
        out["uplift_pct"] = (out["quantity"] / base - 1) * 100
        return out

    def processUpliftByCategory(self, factor):
        """Mức tăng (%) khi có yếu tố, tách theo nhóm món."""
        pv = self.df.pivot_table(index="category", columns=factor, values="quantity", aggfunc="mean")
        return ((pv[1] / pv[0] - 1) * 100).rename("uplift_pct").reset_index() \
                                          .sort_values("uplift_pct", ascending=False)

    def processWeatherImpact(self):
        """Lượng bán trung bình theo loại thời tiết."""
        return self.df.groupby("precip_type", as_index=False)["quantity"].mean()

    def processTemperatureImpact(self, bins=(-30, 32, 50, 70, 120)):
        labels = [f"{bins[i]}-{bins[i + 1]}°F" for i in range(len(bins) - 1)]
        temp = pd.cut(self.df["avg_temp_f"], bins=bins, labels=labels)
        return self.df.groupby([temp, "category"], observed=True)["quantity"].mean() \
                      .unstack().reset_index().rename(columns={"avg_temp_f": "temp_range"})

    # ================================================================ trực quan hoá
    @staticmethod
    def _show(fig, savePath):
        fig.tight_layout()
        if savePath:
            Path(savePath).parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(savePath, dpi=120)
            plt.close(fig)
        else:
            plt.show()

    def visualizePieChart(self, df, columnLabel, columnStatistic, title, legend=True, savePath=None):
        fig, ax = plt.subplots(figsize=(8, 6))
        explode = [0.08] + [0] * (len(df) - 1)
        ax.pie(df[columnStatistic], labels=df[columnLabel], autopct="%1.2f%%", explode=explode)
        if legend:
            ax.legend(df[columnLabel], loc="center left", bbox_to_anchor=(1, 0.5))
        ax.set_title(title)
        self._show(fig, savePath)

    def visualizeBarChart(self, df, columnX, columnY, title, horizontal=False, savePath=None):
        fig, ax = plt.subplots(figsize=(10, 6))
        (ax.barh if horizontal else ax.bar)(df[columnX].astype(str), df[columnY])
        ax.set_title(title)
        ax.set_xlabel(columnY if horizontal else columnX)
        ax.set_ylabel(columnX if horizontal else columnY)
        if horizontal:
            ax.invert_yaxis()
        else:
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        self._show(fig, savePath)

    def visualizeLinePlotChart(self, df, columnX, columnY, title, hue=None, savePath=None):
        fig, ax = plt.subplots(figsize=(10, 6))
        groups = df.groupby(hue) if hue else [(None, df)]
        for name, part in groups:
            ax.plot(part[columnX], part[columnY], marker="o", label=name)
        if hue:
            ax.legend(title=hue)
        ax.set_title(title)
        ax.set_xlabel(columnX)
        ax.set_ylabel(columnY)
        ax.grid(alpha=0.3)
        self._show(fig, savePath)

    def visualizeMultiBarChart(self, df, columnX, title, savePath=None):
        """Biểu đồ cột nhóm: mỗi cột còn lại của df là một nhóm."""
        fig, ax = plt.subplots(figsize=(11, 6))
        df.set_index(columnX).plot(kind="bar", ax=ax)
        ax.set_title(title)
        plt.setp(ax.get_xticklabels(), rotation=0)
        self._show(fig, savePath)
