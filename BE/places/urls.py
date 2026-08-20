from django.urls import path

from courses.views import PlaceCourseListCreateView
from favorites.views import PlaceFavoriteView
from places.views import PlaceDetailView, RecommendationView, SearchAutocompleteView, SearchView
from reviews.views import PlaceReviewListCreateView

urlpatterns = [
    path("search/", SearchView.as_view(), name="place-search"),
    path("search/autocomplete/", SearchAutocompleteView.as_view(), name="place-search-autocomplete"),
    path("recommend/", RecommendationView.as_view(), name="place-recommend"),
    path("<int:place_id>/", PlaceDetailView.as_view(), name="place-detail"),
    path("<int:place_id>/reviews/", PlaceReviewListCreateView.as_view(), name="place-reviews"),
    path("<int:place_id>/favorite/", PlaceFavoriteView.as_view(), name="place-favorite"),
    path("<int:place_id>/courses/", PlaceCourseListCreateView.as_view(), name="place-courses"),
]
