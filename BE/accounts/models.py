from django.db import models


class Member(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "GOOGLE", "Google"
        APPLE = "APPLE", "Apple"

    firebase_uid = models.CharField(max_length=128, unique=True)
    provider = models.CharField(max_length=10, choices=Provider.choices)
    email = models.EmailField(null=True, blank=True)
    nickname = models.CharField(max_length=100, null=True, blank=True)
    profile_image_url = models.URLField(null=True, blank=True)

    # 자리만 만들어 둔다. 실제로 값을 채우는 화면은 Phase 2.
    nationality = models.CharField(max_length=50, null=True, blank=True)
    language = models.CharField(max_length=20, null=True, blank=True)

    agreed_terms_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    # 자리만 만들어 둔다. 실제 탈퇴 기능은 Phase 3.
    is_withdrawn = models.BooleanField(default=False)
    withdrawn_at = models.DateTimeField(null=True, blank=True)

    # DRF의 IsAuthenticated가 request.user.is_authenticated를 확인하므로 필요하다.
    is_authenticated = True

    def __str__(self):
        return self.nickname or self.email or self.firebase_uid
