from django.urls import path

from accounts.views import KakaoCustomTokenView, LocaleView, LoginView, MeView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    # 카카오는 Firebase 기본 제공자가 아니라 이 단계를 먼저 거쳐야 한다 (accounts/views.py
    # KakaoCustomTokenView 참고). 응답으로 받은 커스텀 토큰으로 signInWithCustomToken한 뒤,
    # 그 결과 ID 토큰으로 위 login/을 호출해야 회원 조회/가입이 끝난다.
    path("kakao/token/", KakaoCustomTokenView.as_view(), name="kakao-token"),
    # 여운_API명세서 "국적/언어 설정"(PATCH /account/locale)과 경로를 맞춘다.
    path("locale/", LocaleView.as_view(), name="locale"),
    # 여운_API명세서 "내 정보 조회"(GET /account), "프로필 수정"(PATCH /account),
    # "회원 탈퇴"(DELETE /account)와 경로를 맞춘다. 세 메서드 다 MeView에서 처리한다.
    path("", MeView.as_view(), name="account"),
]
