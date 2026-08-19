from django.urls import path

from places.views import PlaceDetailView, RecommendationView, SearchAutocompleteView, SearchView

urlpatterns = [
    path("search/", SearchView.as_view(), name="place-search"),
    path("search/autocomplete/", SearchAutocompleteView.as_view(), name="place-search-autocomplete"),
    path("recommend/", RecommendationView.as_view(), name="place-recommend"),
    path("<int:place_id>/", PlaceDetailView.as_view(), name="place-detail"),
]
