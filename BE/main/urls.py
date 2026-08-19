from django.urls import path

from main.views import BannerListView

urlpatterns = [
    path("", BannerListView.as_view(), name="banner-list"),
]
