from forecast.models import SystemConfig
from forecast.services.notifications import visible_for


def qsr(request):
    """Biến dùng chung cho base.html: vai trò, cửa hàng, ngày vận hành, số thông báo chưa đọc."""
    user = request.user
    profile = getattr(user, 'profile', None) if user.is_authenticated else None
    if not profile:
        return {}
    config = SystemConfig.get()
    unread = visible_for(user).exclude(read_by=user)
    return {
        'role': profile.role,
        'profile_obj': profile,
        'my_store': profile.store,
        'operating_date': config.operating_date,
        'unread_count': unread.count(),
    }
