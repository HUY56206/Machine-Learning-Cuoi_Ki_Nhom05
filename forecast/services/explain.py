import threading
import time

from forecast.models import Product
from forecast.services import engine
from forecast.services.units import unit_for

CACHE_SECONDS, CACHE_MAX = 600, 32
_cache, _lock = {}, threading.Lock()


G_RECENT, G_DOW, G_SEASON, G_HOLIDAY, G_EVENT, G_PROMO, G_WEATHER, G_ITEM = (
    'Lượng bán gần đây', 'Thứ trong tuần', 'Thời điểm trong năm', 'Ngày lễ', 'Sự kiện đặc biệt', 'Khuyến mãi', 'Thời tiết',
    'Đặc điểm món và cửa hàng')
FEATURES = {
    'lag_1': ('Lượng bán hôm trước', G_RECENT), 'lag_7': ('Lượng bán cùng thứ tuần trước', G_RECENT),
    'lag_14': ('Lượng bán cùng thứ 2 tuần trước', G_RECENT), 'lag_28': ('Lượng bán cùng thứ 4 tuần trước', G_RECENT),
    'roll_mean_7': ('Lượng bán trung bình 7 ngày gần đây', G_RECENT), 'roll_mean_28': ('Lượng bán trung bình 28 ngày gần đây', G_RECENT),
    'roll_std_7': ('Độ dao động lượng bán 7 ngày', G_RECENT), 'roll_std_28': ('Độ dao động lượng bán 28 ngày', G_RECENT),
    'dow_mean_4w': ('Trung bình 4 tuần cùng thứ', G_RECENT),
    'day_of_week_num': ('Thứ trong tuần', G_DOW), 'is_weekend': ('Cuối tuần', G_DOW),
    'month': ('Tháng', G_SEASON), 'week_of_year': ('Tuần trong năm', G_SEASON), 'day_of_month': ('Ngày trong tháng', G_SEASON),
    'day_of_year': ('Ngày trong năm', G_SEASON), 'year': ('Năm', G_SEASON),
    'is_holiday': ('Ngày lễ', G_HOLIDAY), 'is_holiday_tomorrow': ('Mai là ngày lễ', G_HOLIDAY), 'is_holiday_yesterday': ('Hôm qua là ngày lễ', G_HOLIDAY),
    'is_special_event': ('Sự kiện đặc biệt', G_EVENT), 'is_promotion': ('Khuyến mãi', G_PROMO),
    'avg_temp_f': ('Nhiệt độ', G_WEATHER), 'precip_inches': ('Lượng mưa', G_WEATHER), 'precip_type': ('Loại mưa/tuyết', G_WEATHER),
    'restaurant_id': ('Cửa hàng', G_ITEM), 'city': ('Thành phố', G_ITEM), 'menu_item_id': ('Món', G_ITEM),
    'category': ('Nhóm món', G_ITEM), 'unit_price': ('Giá bán', G_ITEM),
}


def store_explanation(store_id, service_date):
    key, now = (store_id, str(service_date)), time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    result = engine.explain_store(store_id, service_date)
    with _lock:
        if len(_cache) >= CACHE_MAX:
            _cache.pop(min(_cache, key=lambda k: _cache[k][0]), None)
        _cache[key] = (now, result)
    return result


def _round(x):
    return round(x, 1)


def _show(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return str(v)
    return str(int(f)) if f == int(f) else str(round(f, 1))


def manager_view(store_id, service_date, product_id, top=5):
    base, rows = store_explanation(store_id, service_date)
    row = rows.get(product_id)
    if row is None:
        return None
    groups = {}
    for col, v in row['shap'].items():
        g = FEATURES.get(col, (col, col))[1]
        groups[g] = groups.get(g, 0) + v
    items = sorted(({'label': g, 'value': _round(v)} for g, v in groups.items()), key=lambda x: -abs(x['value']))
    return {'base': _round(base), 'predicted': _round(max(0.0, row['predicted'])), 'items': [i for i in items[:top] if abs(i['value']) >= 0.05]}


def admin_view(store_id, service_date, product_id=None, top=10):
    base, rows = store_explanation(store_id, service_date)
    n = max(len(rows), 1)
    by_feat, by_group = {}, {}
    for row in rows.values():
        for col, v in row['shap'].items():
            by_feat[col] = by_feat.get(col, 0) + abs(v) / n
        gsum = {}
        for col, v in row['shap'].items():
            g = FEATURES.get(col, (col, col))[1]
            gsum[g] = gsum.get(g, 0) + v
        for g, v in gsum.items():
            by_group[g] = by_group.get(g, 0) + abs(v) / n
    total_g, total_f = sum(by_group.values()) or 1, sum(by_feat.values()) or 1
    out = {
        'base': _round(base), 'items_count': len(rows),
        'importance_groups': [{'label': g, 'value': _round(v), 'share': round(v / total_g * 100)}
                              for g, v in sorted(by_group.items(), key=lambda x: -x[1])],
        'importance_features': [{'column': c, 'label': FEATURES.get(c, (c,))[0], 'value': _round(v), 'share': round(v / total_f * 100)}
                                for c, v in sorted(by_feat.items(), key=lambda x: -x[1])[:top]],
        'item': None,
    }
    if product_id:
        row = rows.get(product_id)
        if row is not None:
            out['item'] = {
                'product': product_id, 'unit': unit_for(Product.objects.filter(pk=product_id).first()), 'predicted': _round(max(0.0, row['predicted'])),
                'features': [{'column': c, 'label': FEATURES.get(c, (c,))[0], 'group': FEATURES.get(c, (c, c))[1],
                              'value': _show(row['values'][c]), 'shap': _round(v)}
                             for c, v in sorted(row['shap'].items(), key=lambda x: -abs(x[1]))]}
    return out
