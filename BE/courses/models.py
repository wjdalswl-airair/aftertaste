from django.db import models

from accounts.models import Member
from places.models import Place


class Course(models.Model):
    """근처 식당 1 + 카페 1 + 그 외 1로 구성된 추천 코스 (DETAIL_SPEC 6-1 #17, PRD F-08).

    특정 명소(place)를 기준(anchor)으로 시작하고, 실제로 코스에 들어가는 장소들은
    CoursePlace에 담긴다. 로그인한 사용자가 API로 만들거나, 관리자가 admin에서
    직접 등록할 수 있다 — 관리자가 만들면 creator가 비어있을 수 있다.
    """

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="courses")
    creator = models.ForeignKey(
        Member, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class CoursePlace(models.Model):
    """코스에 들어가는 장소 하나.

    카카오 카테고리 검색 결과를 코스를 만든 시점 그대로 스냅샷(이름·주소·좌표·카테고리)으로
    저장한다 (DETAIL_SPEC 6-1 #17). 가게가 나중에 폐업해도 자동으로 갱신하지 않는다 —
    코스를 만든 사람이나 관리자가 필요하면 직접 코스를 수정·삭제한다.
    """

    class Role(models.TextChoices):
        RESTAURANT = "RESTAURANT", "식당"
        CAFE = "CAFE", "카페"
        OTHER = "OTHER", "그 외"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="course_places")
    role = models.CharField(max_length=10, choices=Role.choices)
    # 코스 안에서 보여줄 순서. 코스를 만들 때 넘긴 장소 목록 순서를 그대로 저장한다.
    order = models.PositiveSmallIntegerField(default=0)

    # 카카오 장소 검색 API 응답 스냅샷 (places.serializers.NearbyPlaceSerializer와 같은 모양)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    road_address_name = models.CharField(max_length=300, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    category_name = models.CharField(max_length=200, blank=True)
    kakao_place_id = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        unique_together = ("course", "role")
        ordering = ["order"]

    def __str__(self):
        return f"{self.course} - {self.role}:{self.name}"
