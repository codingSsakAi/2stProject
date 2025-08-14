from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    """
    관리자 권한이 필요한 뷰에 적용하는 데코레이터
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '로그인이 필요합니다.')
            return redirect('accounts:login')
        
        if not request.user.is_staff:
            messages.error(request, '관리자 권한이 필요합니다.')
            raise PermissionDenied("관리자 권한이 필요합니다.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def user_required(view_func):
    """
    일반 사용자 권한이 필요한 뷰에 적용하는 데코레이터
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '로그인이 필요합니다.')
            return redirect('accounts:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def chatbot_access_required(view_func):
    """
    챗봇 접근 권한이 필요한 뷰에 적용하는 데코레이터
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '챗봇 이용을 위해 로그인이 필요합니다.')
            return redirect('accounts:login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
