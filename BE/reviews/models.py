from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.models import Member
from places.models import Place

# 리뷰 글자 수·사진 장수 제한 (docs/DETAIL_SPEC.md 6-1 #14).
# 2026-08-28 정정: 목업의 리뷰 작성 화면("14 / 500", "사진 첨부 0 / 5")에 맞춰 500자·5장으로 변경.
REVIEW_CONTENT_MAX_LENGTH = 500
REVIEW_MAX_PHOTOS = 5

# 한 리뷰에 서로 다른 사람이 이 수만큼 신고하면 자동으로 숨긴다 (docs/DETAIL_SPEC.md 6-1 #13, 2026-08-29).
# 같은 사람의 중복 신고는 ReviewReport.unique_together 때문에 1건으로만 센다.
REVIEW_REPORT_HIDE_THRESHOLD = 5


class Review(models.Model):
    """명소 후기. 별점·글·사진과 함께 원래 무슨 언어로 썼는지도 저장한다.

    "원래 언어"를 저장하는 이유: Phase 4에서 번역할 때, 보는 사람 언어와 원문 언어가
    같으면 번역을 건너뛰기 위해서다 (docs/DETAIL_SPEC.md 2-3).
    """

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="reviews")
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    content = models.TextField(max_length=REVIEW_CONTENT_MAX_LENGTH)
    # 리뷰를 쓸 때 사용한 언어 (예: "ko", "en"). 값 자체를 검증하는 지원 언어 목록은
    # 아직 안 정해졌다 (docs/DETAIL_SPEC.md 7장 #8) — 지금은 프론트가 보내는 값을 그대로 저장한다.
    language = models.CharField(max_length=10)
    # 관리자가 신고를 확인하고 감출 때 True로 바꾼다 (건수 자동 숨김 아님, 6-1 #13)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.place} - {self.member} ({self.rating}점)"


class ReviewPhoto(models.Model):
    """리뷰 사진. 최대 5장까지 붙을 수 있다 (개수 검증은 시리얼라이저에서 한다).

    사진이 여러 장이면 제출 순서상 첫 번째 장이 대표 이미지다 (명예의 전당 등에서 사용,
    docs/DETAIL_SPEC.md 2-3). 별도 순서 필드는 두지 않고 제출 순서대로 만들어 pk 오름차순이
    곧 제출 순서가 되게 한다 (ReviewWriteSerializer가 bulk_create를 순서대로 호출).

    Firebase Storage에 올린 파일의 URL만 저장한다 (docs/DETAIL_SPEC.md 6-1 #2, Place.photo_url과 같은 방식).
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="photos")
    photo_url = models.URLField()

    def __str__(self):
        return f"{self.review} 사진"


class ReviewLike(models.Model):
    """리뷰 좋아요. 한 사람이 같은 리뷰에 한 번만 누를 수 있다."""

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="likes")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="review_likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("review", "member")

    def __str__(self):
        return f"{self.member} -> {self.review}"


class ReviewReport(models.Model):
    """리뷰 신고. 한 사람이 같은 리뷰를 여러 번 신고해도 한 건만 접수한다.

    처리는 건수와 상관없이 관리자가 Django admin에서 수동으로 확인하고 Review.is_hidden을
    감춘다. 자동 임계치 숨김 기능은 만들지 않는다 (docs/DETAIL_SPEC.md 6-1 #13).
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="review_reports")
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("review", "member")

    def __str__(self):
        return f"{self.member} -> {self.review} 신고"


class ReviewTranslation(models.Model):
    """리뷰 번역문을 담을 자리. 실제 번역 로직/API는 Phase 4에서 만든다.

    "처음 열람될 때 만들어져서 저장 후 재사용된다"는 규칙(docs/DETAIL_SPEC.md 4-1)대로
    언어별로 한 번만 저장한다. PlaceTranslation/WorkTranslation과 같은 구조다.
    """

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    translated_content = models.TextField(blank=True)

    class Meta:
        unique_together = ("review", "language")

    def __str__(self):
        return f"{self.review} ({self.language})"
