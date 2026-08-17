from django.contrib import admin

from places.models import Place, PlaceSource, PlaceTranslation, PlaceWork, Work, WorkTranslation


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


@admin.register(PlaceTranslation)
class PlaceTranslationAdmin(admin.ModelAdmin):
    list_display = ("place", "language", "name")


@admin.register(WorkTranslation)
class WorkTranslationAdmin(admin.ModelAdmin):
    list_display = ("work", "language", "title")
