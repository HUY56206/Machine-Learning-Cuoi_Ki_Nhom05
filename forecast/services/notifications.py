"""Danh sách thông báo hiển thị cho một người dùng (theo vai trò, cửa hàng và tùy chọn hồ sơ)."""
from forecast.models import Notification

HIDDEN_BY_PREF = {                       # tùy chọn hồ sơ tắt -> ẩn loại thông báo tương ứng
    'notify_new_plan': (Notification.Kind.SHORTAGE, Notification.Kind.PLAN),
    'remind_inventory': (Notification.Kind.REMINDER,),
}


def visible_for(user):
    profile = user.profile
    qs = Notification.objects.filter(role=profile.role)
    if profile.store_id:
        qs = qs.filter(store_id=profile.store_id)
    for pref, kinds in HIDDEN_BY_PREF.items():
        if not getattr(profile, pref):
            qs = qs.exclude(kind__in=kinds)
    return qs


def notify(kind, role, store, title, detail, link):
    """Mỗi (loại, vai trò, cửa hàng) chỉ giữ thông báo mới nhất."""
    Notification.objects.filter(kind=kind, role=role, store=store).delete()
    return Notification.objects.create(kind=kind, role=role, store=store, title=title, detail=detail, link=link)
