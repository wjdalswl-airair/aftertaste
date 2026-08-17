from django.urls import path

from accounts.views import LocaleView, LoginView, MeView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    # 여운_API명세서 "국적/언어 설정"(PATCH /account/locale)과 경로를 맞춘다.
    path("locale/", LocaleView.as_view(), name="locale"),
    # 여운_API명세서 "내 정보 조회"(GET /account)와 경로를 맞춘다.
    path("", MeView.as_view(), name="account"),
]
