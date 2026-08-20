from django.urls import path

from courses.views import CourseDetailView
from favorites.views import CourseFavoriteView

urlpatterns = [
    path("<int:course_id>/", CourseDetailView.as_view(), name="course-detail"),
    path("<int:course_id>/favorite/", CourseFavoriteView.as_view(), name="course-favorite"),
]
