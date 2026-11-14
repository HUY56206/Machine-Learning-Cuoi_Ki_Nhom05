from forecast.models import Notification

HIDDEN_BY_PREF = {
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
    Notification.objects.filter(kind=kind, role=role, store=store).delete()
    return Notification.objects.create(kind=kind, role=role, store=store, title=title, detail=detail, link=link)
