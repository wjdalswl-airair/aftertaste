"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.decorators import api_view
from rest_framework.response import Response

from favorites.views import MyFavoriteListView
from main.views import HallOfFameView, TopPlacesView
from reviews.views import MyReviewListView


@extend_schema(exclude=True)
@api_view(["GET"])
def health_check(request):
    return Response({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/account/", include("accounts.urls")),
    # 여운_API명세서의 "내 리뷰 조회"(/account/reviews), "내 즐겨찾기 조회"(/account/bookmarks →
    # 이 프로젝트 용어로는 favorites)와 경로를 맞춘다. accounts 앱이 reviews/favorites를
    # 알 필요는 없어서(방 분리), accounts.urls에 넣지 않고 여기서 바로 라우팅한다.
    path("api/account/reviews/", MyReviewListView.as_view(), name="my-reviews"),
    path("api/account/favorites/", MyFavoriteListView.as_view(), name="my-favorites"),
    path("api/banners/", include("main.urls")),
    # 명예의 전당·Top10은 배너와 달리 "메인 화면"에 속하는 별개 구성요소라
    # /api/banners/ 프리픽스를 쓰면 이름이 안 맞는다. main 앱 자체의 url 프리픽스가
    # 아직 없어서(main.urls는 /api/banners/에 묶여 있음), MyReviewListView/
    # MyFavoriteListView와 같은 방식으로 여기서 바로 라우팅한다 (PHASES/PHASE3.md 6번).
    path("api/main/hall-of-fame/", HallOfFameView.as_view(), name="hall-of-fame"),
    path("api/main/top-places/", TopPlacesView.as_view(), name="top-places"),
    path("api/places/", include("places.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
