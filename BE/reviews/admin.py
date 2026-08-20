from django.contrib import admin

from reviews.models import Review, ReviewLike, ReviewPhoto, ReviewReport, ReviewTranslation


class ReviewPhotoInline(admin.TabularInline):
    model = ReviewPhoto
    extra = 1


class ReviewReportInline(admin.TabularInline):
    """리뷰 관리 화면에서 신고 내역을 바로 보고, 감출지 판단할 수 있게 한다."""

    model = ReviewReport
    extra = 0
    readonly_fields = ("member", "reason", "created_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("place", "member", "rating", "is_hidden", "created_at")
    list_filter = ("is_hidden",)
    search_fields = ("place__name", "member__nickname", "content")
    inlines = [ReviewPhotoInline, ReviewReportInline]


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ("review", "member", "reason", "created_at")


@admin.register(ReviewLike)
class ReviewLikeAdmin(admin.ModelAdmin):
    list_display = ("review", "member", "created_at")


@admin.register(ReviewTranslation)
class ReviewTranslationAdmin(admin.ModelAdmin):
    list_display = ("review", "language")
