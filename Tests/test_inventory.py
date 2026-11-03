"""Kiểm thử module tồn kho.   Chạy: python -m pytest Tests/ -v"""
import numpy as np
import pandas as pd
import pytest

from Models.QSRInventory import QSRInventory
from Models.TrainedModel import TrainedModel


@pytest.fixture
def inventory():
    tm = TrainedModel(model_name="test")
    tm.residual_rmse = pd.DataFrame({"restaurant_id": ["R01", "R01"], "menu_item_id": ["M01", "M02"],
                                     "residual_rmse": [10.0, 2.0]})
    return QSRInventory(tm)


def forecast(*items):
    return pd.DataFrame({"date": pd.Timestamp("2025-12-24"), "restaurant_id": "R01",
                         "menu_item_id": [i[0] for i in items], "predicted_qty": [i[1] for i in items]})


def test_safety_stock_per_series(inventory):
    out = inventory.calcSafetyStock(forecast(("M01", 50), ("M02", 20)))
    assert list(out["safety_stock"]) == [16.5, 3.3]          # 1.65 x RMSE riêng từng món


def test_unknown_series_uses_median_rmse(inventory):
    out = inventory.calcSafetyStock(forecast(("M99", 30)))
    assert out["safety_stock"].iloc[0] == pytest.approx(1.65 * 6.0)


def test_recommend_order_formula(inventory):
    # M01: 50 + 16.5 - 20 = 46.5 -> 47 ; M02: 20 + 3.3 - 40 < 0 -> 0
    out = inventory.recommendOrder(forecast(("M01", 50), ("M02", 20)), current_stock=[20, 40])
    assert list(out["recommended_order"]) == [47, 0]
    assert list(out["is_stockout_risk"]) == [0, 0]


def test_residual_rmse_ignores_stockout_and_outlier_days():
    from Models.QSRMLModel import QSRMLModel
    df = pd.DataFrame({"restaurant_id": "R01", "menu_item_id": "M01",
                       "quantity_raw": [10.0, 12.0, 0.0, 60.0], "is_outlier": [0, 0, 0, 1]})
    mask = np.array([True, True, True, True])
    out = QSRMLModel.processResidualRMSE(df, np.array([11.0, 11.0, 11.0, 11.0]), mask)
    assert out["residual_rmse"].iloc[0] == pytest.approx(1.0)   # chỉ tính 2 ngày bình thường


def test_stockout_warning(inventory):
    out = inventory.recommendOrder(forecast(("M01", 50)), current_stock=[5])
    assert out["is_stockout_risk"].iloc[0] == 1               # 5 < 16.5
