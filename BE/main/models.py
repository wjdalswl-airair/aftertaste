from django.db import models

from config.constants import PHOTO_URL_MAX_LENGTH


class Banner(models.Model):
    """메인 화면 상단에 노출되는 슬라이드 배너. 관리자가 주간 콘텐츠를 입력한다."""

    # 다른 이미지 URL 필드와 길이를 맞춘다 (config.constants.PHOTO_URL_MAX_LENGTH 주석 참고).
    image_url = models.URLField(max_length=PHOTO_URL_MAX_LENGTH)
    link_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"배너 {self.id} (순서 {self.order})"
