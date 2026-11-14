import logging
from datetime import timedelta

from forecast.models import DailySale, Promotion, SystemConfig, WeatherEvent
from forecast.services import explain

logger = logging.getLogger(__name__)

WEEKDAYS = ['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật']


def line_insights(line, config=None):
    config = config or SystemConfig.get()
    plan, day = line.plan, line.plan.service_date
    factors = [['Ngày trong tuần', WEEKDAYS[day.weekday()]]]
    w = WeatherEvent.objects.filter(restaurant=plan.store, event_date=day).first()
    if w:
        sky = {'None': 'Khô ráo', 'Rain': 'Có mưa', 'Snow': 'Có tuyết'}.get(w.precip_type, w.precip_type)
        factors += [['Sự kiện', w.special_event_name if w.is_special_event else 'Không'],
                    ['Thời tiết', f'{sky}, khoảng {round((float(w.avg_temp_f) - 32) / 1.8)}°C'],
                    ['Ngày lễ', w.holiday_name if w.is_holiday else 'Không']]
    promo = Promotion.objects.filter(restaurant=plan.store, product=line.product, promo_date=day).exists()
    factors.append(['Khuyến mãi', 'Có' if promo else 'Không'])


    similar = []
    d = day - timedelta(days=7)
    while len(similar) < 4 and d >= config.operating_date - timedelta(days=60):
        if d <= config.operating_date:
            sale = DailySale.objects.filter(restaurant=plan.store, product=line.product, sale_date=d).first()
            if sale:
                similar.append({'date': d.strftime('%d/%m/%Y'), 'qty': sale.quantity})
        d -= timedelta(days=7)
    try:
        contrib = explain.manager_view(plan.store_id, day, line.product_id)
    except Exception:
        logger.exception('Không tính được SHAP: %s %s %s', plan.store_id, day, line.product_id)
        contrib = None
    return {'factors': factors, 'similar': similar, 'contrib': contrib}
