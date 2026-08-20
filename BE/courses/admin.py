from django.contrib import admin

from courses.models import Course, CoursePlace


class CoursePlaceInline(admin.TabularInline):
    """코스 관리 화면에서 식당/카페/그 외 장소를 바로 채워 넣을 수 있게 한다."""

    model = CoursePlace
    extra = 3  # 식당 1 + 카페 1 + 그 외 1을 채워야 하므로 기본 3칸을 보여준다


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "place", "creator", "created_at")
    search_fields = ("title", "place__name", "creator__nickname")
    inlines = [CoursePlaceInline]
