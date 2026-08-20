from django.contrib import admin

from favorites.models import Favorite


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("member", "place", "created_at")
    search_fields = ("member__nickname", "place__name")
