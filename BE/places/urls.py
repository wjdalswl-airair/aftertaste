from django.urls import path

from places.views import SearchAutocompleteView, SearchView

urlpatterns = [
    path("search/", SearchView.as_view(), name="place-search"),
    path("search/autocomplete/", SearchAutocompleteView.as_view(), name="place-search-autocomplete"),
]
