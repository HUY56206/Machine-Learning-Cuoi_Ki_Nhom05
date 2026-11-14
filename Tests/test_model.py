import numpy as np
import pandas as pd
import pytest

from Models.QSRBaselineModel import QSRBaselineModel
from Models.QSRMLModel import QSRMLModel
from Utils import Config


def make_history(start="2025-05-01", end="2025-12-31"):
    dates = pd.date_range(start, end)
    rows = []
    for store, offset in (("R01", 0), ("R02", 1000)):
        for i, d in enumerate(dates):
            rows.append({
                "date": d, "restaurant_id": store, "menu_item_id": "M01", "category": "Burgers",
                "city": "Chicago", "precip_type": "None", "quantity": offset + i,
                "quantity_raw": float(offset + i), "is_imputed": int(i == 200),
                "is_holiday": int(i == 50), "day_of_week_num": d.day_of_week,
            })
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def model():
    m = QSRMLModel()
    m.df = make_history()
    m.processFeatures()
    return m


def row(model, store, date):
    f = model.df_features
    return f[(f["restaurant_id"] == store) & (f["date"] == pd.Timestamp(date))].iloc[0]


def test_lag_uses_only_past(model):
    r = row(model, "R01", "2025-06-29")
    assert r["quantity"] == 59
    assert (r["lag_1"], r["lag_7"], r["lag_28"]) == (58, 52, 31)


def test_rolling_excludes_current_day(model):
    r = row(model, "R01", "2025-06-29")
    assert r["roll_mean_7"] == pytest.approx(np.mean(range(52, 59)))
    assert r["roll_mean_28"] == pytest.approx(np.mean(range(31, 59)))


def test_lags_do_not_cross_series(model):
    r02 = model.df_features[model.df_features["restaurant_id"] == "R02"]
    assert (r02["lag_28"] >= 1000).all()


def test_holiday_neighbours(model):
    holiday = pd.Timestamp("2025-05-01") + pd.Timedelta(days=50)
    assert row(model, "R01", holiday - pd.Timedelta(days=1))["is_holiday_tomorrow"] == 1
    assert row(model, "R01", holiday + pd.Timedelta(days=1))["is_holiday_yesterday"] == 1


def test_time_split_has_no_overlap(model):
    train, val, test = model.splitTrainValTest()
    assert train["date"].max() < val["date"].min() <= val["date"].max() < test["date"].min()
    assert test["date"].min() == pd.Timestamp(Config.TEST_START)


def test_evaluate_excludes_imputed_rows(model):
    baseline = QSRBaselineModel(method="seasonal_naive")
    baseline.train, baseline.val, baseline.test = model.splitTrainValTest()
    baseline.processTrain()
    result = baseline.evaluate("test")
    test = baseline.test
    assert result.n_rows == int((test["is_imputed"] == 0).sum())

    assert result.MAE == pytest.approx(7)
    assert result.BIAS < 0
