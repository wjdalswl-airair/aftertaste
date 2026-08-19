from django.contrib import admin

from main.models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "is_active", "image_url", "link_url")
    list_editable = ("order", "is_active")
