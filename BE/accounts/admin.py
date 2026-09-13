from django.contrib import admin

from accounts.models import Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    """관리자 화면에서 가입한 회원 목록을 볼 수 있게 등록한다."""

    list_display = ("id", "nickname", "email", "provider", "is_withdrawn", "created_at")
    list_filter = ("provider", "is_withdrawn")
    search_fields = ("nickname", "email", "firebase_uid")
