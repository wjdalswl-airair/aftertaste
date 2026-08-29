from django.db import models
from django.db.models import Q

from accounts.models import Member
from places.models import Place


class Favorite(models.Model):
    """누가 어떤 명소 또는 코스를 즐겨찾기 했는지 (docs/DETAIL_SPEC.md 2-4, PHASES/PHASE4.md 코스).

    place/course 둘 중 정확히 하나만 채워져 있어야 한다 — 즐겨찾기 하나가 명소도 되고
    코스도 되는 걸 막기 위해 CheckConstraint로 강제한다. 같은 사람이 같은 명소(또는 코스)를
    두 번 저장할 수 없게 unique_together로 막는다. place/course가 nullable이라 unique_together는
    "값이 채워진 쪽끼리만" 비교한다 — NULL은 서로 다른 값으로 취급되기 때문에, course만 채운
    row가 여러 개 있어도 (member, place) 쪽 유니크 제약과는 충돌하지 않는다.
    """

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="favorites")
    place = models.ForeignKey(
        Place, on_delete=models.CASCADE, related_name="favorited_by", null=True, blank=True
    )
    # 문자열로 참조해서 courses 앱이 favorites 앱을 몰라도 되게 한다 (courses가 favorites를
    # import하지 않아도 되는 방향, 순환 참조 방지).
    course = models.ForeignKey(
        "courses.Course", on_delete=models.CASCADE, related_name="favorited_by", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("member", "place"), ("member", "course")]
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(place__isnull=False) & Q(course__isnull=True))
                    | (Q(place__isnull=True) & Q(course__isnull=False))
                ),
                name="favorite_exactly_one_of_place_or_course",
            )
        ]

    def __str__(self):
        return f"{self.member} - {self.place or self.course}"
