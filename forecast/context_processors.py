from forecast.models import SystemConfig
from forecast.services import plans
from forecast.services.notifications import visible_for


def qsr(request):
    user = request.user
    profile = getattr(user, 'profile', None) if user.is_authenticated else None
    if not profile:
        return {}
    config = SystemConfig.get()
    first, last = plans.forecast_range()
    unread = visible_for(user).exclude(read_by=user)
    return {
        'role': profile.role,
        'profile_obj': profile,
        'my_store': profile.store,
        'operating_date': config.operating_date,
        'forecast_min': first.isoformat(),
        'forecast_max': last.isoformat(),
        'unread_count': unread.count(),
    }
