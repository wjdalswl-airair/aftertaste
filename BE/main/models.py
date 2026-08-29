from django.db import models


class Banner(models.Model):
    """메인 화면 상단에 노출되는 슬라이드 배너. 관리자가 주간 콘텐츠를 입력한다."""

    image_url = models.URLField()
    link_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"배너 {self.id} (순서 {self.order})"
