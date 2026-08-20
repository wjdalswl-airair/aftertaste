from django.urls import path

from reviews.views import ReviewDetailView, ReviewLikeView, ReviewReportView

urlpatterns = [
    path("<int:review_id>/", ReviewDetailView.as_view(), name="review-detail"),
    path("<int:review_id>/like/", ReviewLikeView.as_view(), name="review-like"),
    path("<int:review_id>/report/", ReviewReportView.as_view(), name="review-report"),
]
