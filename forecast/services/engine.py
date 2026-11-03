"""Cầu nối giữa web và pipeline ML (Models/, Connectors/): nạp mô hình đã train và dự báo một cửa hàng / một ngày."""
import threading

import pandas as pd

from Connectors.Connector import Connector
from Models.QSRInventory import QSRInventory
from Models.QSRMLModel import QSRMLModel
from Utils import Config
from Utils.FileUtil import FileUtil

MODEL_FILE = 'best_model.joblib'
HISTORY_DAYS = 60          # đủ để tạo lag_28 / roll_28 (xem Tests/AppInventory.py)

_lock = threading.Lock()
_trained = None


class NoForecastData(Exception):
    """Không có dữ liệu đầu vào (bán hàng / thời tiết) cho ngày được chọn."""


def trained_model():
    """Nạp best_model.joblib một lần cho cả tiến trình (file lớn, nạp lại mỗi request sẽ rất chậm)."""
    global _trained
    with _lock:
        if _trained is None:
            _trained = FileUtil.loadModel(MODEL_FILE)
            if _trained is None:
                raise RuntimeError(f'Không nạp được mô hình {MODEL_FILE}')
        return _trained


def forecast_store(store_id, service_date, z=Config.SERVICE_LEVEL_Z):
    """Trả về DataFrame mỗi món một dòng: predicted_qty, safety_stock, baseline (TB 7 ngày trước)."""
    tm = trained_model()
    connector = Connector()
    if not connector.connect():
        raise RuntimeError('Không kết nối được MySQL')
    try:
        model = QSRMLModel(connector)
        model.trainedmodel = tm
        model.model_name = tm.model_name
        service_date = pd.Timestamp(service_date)
        start = (service_date - pd.Timedelta(days=HISTORY_DAYS)).date()
        end = (service_date + pd.Timedelta(days=1)).date()
        df = model.execQSRHistory(restaurant_id=store_id, start=start, end=end)
        if df is None or df.empty or service_date not in set(df[Config.DATE_COL]):
            raise NoForecastData(str(service_date.date()))
        model.processFeatures()
        try:
            forecast = model.forecastDate(service_date, store_id)
        except ValueError as exc:
            raise NoForecastData(str(exc)) from exc

        # "Bình thường" = trung bình 7 ngày liền trước ngày phục vụ
        prior = df[(df[Config.DATE_COL] < service_date) &
                   (df[Config.DATE_COL] >= service_date - pd.Timedelta(days=7))]
        base = prior.groupby('menu_item_id')[Config.TARGET].mean().rename('baseline_qty')
        forecast = forecast.merge(base, on='menu_item_id', how='left')

        plan = QSRInventory(tm, z=z).calcSafetyStock(forecast)
        plan['model_name'] = tm.model_name
        return plan
    finally:
        connector.disConnect()


def save_raw_forecasts(plan_df, current_stock, recommended):
    """Ghi vào bảng `forecasts` (hợp đồng cũ của pipeline) để các công cụ khác vẫn đọc được."""
    connector = Connector()
    if not connector.connect():
        return 0
    try:
        out = plan_df.copy()
        out['current_stock'] = current_stock
        out['recommended_order'] = recommended
        return QSRInventory(trained_model()).saveForecasts(connector, out)
    finally:
        connector.disConnect()


def accuracy_by_day(store_id, start, end):
    """Sai số wMAPE (%) theo ngày trong [start, end] tại một cửa hàng, gộp theo món.

    Dùng quantity_raw và bỏ dòng is_imputed như Tests/AppCompareModels (đánh giá trên số liệu gốc).
    Trả về list[(date, wmape_percent)] chỉ cho các ngày có số bán thực tế.
    """
    tm = trained_model()
    connector = Connector()
    if not connector.connect():
        raise RuntimeError('Không kết nối được MySQL')
    try:
        model = QSRMLModel(connector)
        model.trainedmodel = tm
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        df = model.execQSRHistory(restaurant_id=store_id, start=(start - pd.Timedelta(days=HISTORY_DAYS)).date(),
                                  end=(end + pd.Timedelta(days=1)).date())
        if df is None or df.empty:
            return []
        feats = model.processFeatures()
        part = feats[(feats[Config.DATE_COL] >= start) & (feats[Config.DATE_COL] <= end) & (feats['is_imputed'] == 0)
                     & feats[Config.TARGET_RAW].notna()].copy()
        if part.empty:
            return []
        part['pred'] = model.predict(part)
        out = []
        for day, g in part.groupby(Config.DATE_COL):
            denom = g[Config.TARGET_RAW].abs().sum()
            if denom:
                out.append((day.date(), round(float((g['pred'] - g[Config.TARGET_RAW]).abs().sum() / denom * 100), 1)))
        return out
    finally:
        connector.disConnect()
