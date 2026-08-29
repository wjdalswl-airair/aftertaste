from django.contrib import admin

from places.models import (
    Place,
    PlaceSource,
    PlaceTranslation,
    PlaceWork,
    SearchHistory,
    Work,
    WorkTranslation,
)
from places.translation import translate_place, translate_work


class PlaceWorkInline(admin.TabularInline):
    """명소 관리 화면에서 바로 작품을 연결하고 장면 설명을 쓸 수 있게 한다."""

    model = PlaceWork
    extra = 1


class PlaceSourceInline(admin.TabularInline):
    """명소 관리 화면에서 이 명소가 어느 출처들에서 왔는지 바로 확인할 수 있게 한다."""

    model = PlaceSource
    extra = 1


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "created_at")
    search_fields = ("name", "address")
    inlines = [PlaceSourceInline, PlaceWorkInline]


@admin.register(PlaceSource)
class PlaceSourceAdmin(admin.ModelAdmin):
    list_display = ("place", "source", "source_id")
    search_fields = ("source", "source_id", "place__name")


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "release_date", "director")
    search_fields = ("title", "director", "main_cast")
    inlines = [PlaceWorkInline]


@admin.action(description="선택한 번역 다시 번역하기")
def retranslate_places(modeladmin, request, queryset):
    for translation in queryset:
        translate_place(translation.place, translation.language)
    modeladmin.message_user(request, f"{queryset.count()}건 다시 번역했습니다.")


@admin.action(description="선택한 번역 다시 번역하기")
def retranslate_works(modeladmin, request, queryset):
    for translation in queryset:
        translate_work(translation.work, translation.language)
    modeladmin.message_user(request, f"{queryset.count()}건 다시 번역했습니다.")


@admin.register(PlaceTranslation)
class PlaceTranslationAdmin(admin.ModelAdmin):
    # is_approved를 목록에서 바로 체크할 수 있게 한다. status로 필터링하면 FAILED만 골라
    # "실패 목록"으로 볼 수 있다 (PHASES/PHASE4.md 4-3 완료 기준).
    list_display = ("place", "language", "name", "status", "is_approved")
    list_display_links = ("place",)
    list_editable = ("is_approved",)
    list_filter = ("status", "language", "is_approved")
    search_fields = ("place__name", "name")
    actions = [retranslate_places]


@admin.register(WorkTranslation)
class WorkTranslationAdmin(admin.ModelAdmin):
    list_display = ("work", "language", "title", "status", "is_approved")
    list_display_links = ("work",)
    list_editable = ("is_approved",)
    list_filter = ("status", "language", "is_approved")
    search_fields = ("work__title", "title")
    actions = [retranslate_works]


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("member", "keyword", "searched_at")
    search_fields = ("keyword", "member__nickname")
