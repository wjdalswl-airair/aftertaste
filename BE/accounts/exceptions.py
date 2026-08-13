from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if isinstance(exc, NotAuthenticated):
        response.data = {"detail": "로그인이 필요한 기능입니다"}
    elif isinstance(exc, AuthenticationFailed):
        response.data = {"detail": "다시 로그인하세요"}

    return response
