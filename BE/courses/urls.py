from django.urls import path

from courses.views import CourseDetailView, CourseListView
from favorites.views import CourseFavoriteView

urlpatterns = [
    path("", CourseListView.as_view(), name="course-list"),
    path("<int:course_id>/", CourseDetailView.as_view(), name="course-detail"),
    path("<int:course_id>/favorite/", CourseFavoriteView.as_view(), name="course-favorite"),
]
