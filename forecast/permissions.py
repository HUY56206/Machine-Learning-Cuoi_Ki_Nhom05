"""Phân quyền theo vai trò (Profile.role)."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import render

from forecast.models import Role

HOME = {Role.MANAGER: 'forecast:dashboard', Role.STAFF: 'forecast:staff_prep', Role.ADMIN: 'forecast:data'}


def _role(request):
    profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    return profile.role if profile else None


def role_required(*roles):
    """Trang HTML: chưa đăng nhập -> /login/; sai vai trò -> trang 'Không có quyền truy cập'."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path(), 'forecast:login')
            role = _role(request)
            if role in (Role.MANAGER, Role.STAFF) and not request.user.profile.store_id:
                role = None                                        # chưa được gán cửa hàng -> coi như không có quyền
            if role not in roles:
                return render(request, 'forecast/no_access.html', {'role': role or Role.MANAGER, 'active_menu': 'none'}, status=403)
            return view(request, *args, **kwargs)
        return wrapper
    return deco


def api_role_required(*roles):
    """API JSON: trả 401/403 thay vì chuyển hướng."""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'ok': False, 'error': 'unauthenticated', 'message': 'Chưa đăng nhập.'}, status=401)
            role = _role(request)
            if role in (Role.MANAGER, Role.STAFF) and not request.user.profile.store_id:
                role = None
            if role not in roles:
                return JsonResponse({'ok': False, 'error': 'forbidden', 'message': 'Không có quyền truy cập.'}, status=403)
            return view(request, *args, **kwargs)
        return wrapper
    return deco
