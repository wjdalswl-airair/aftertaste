from django.db import models

from accounts.models import Member
from places.models import Place


class Favorite(models.Model):
    """누가 어떤 명소를 즐겨찾기 했는지 (docs/DETAIL_SPEC.md 2-4).

    같은 사람이 같은 명소를 두 번 저장할 수 없게 unique_together로 막는다.
    """

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="favorites")
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("member", "place")

    def __str__(self):
        return f"{self.member} - {self.place}"
