from django.db import models

from accounts.models import Member


class Place(models.Model):
    """촬영 명소 정보.

    이름/주소/위치는 공공데이터에서 가져와 채운다.
    설명/사진/영업시간은 관리자가 직접 채워 넣는 값이라, 공공데이터를 다시 가져와도 덮어쓰지 않는다.
    """

    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # 관리자가 직접 채우는 값 (가져오기로 덮어쓰지 않는다)
    description = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    business_hours = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PlaceSource(models.Model):
    """이 명소가 어느 공공데이터 출처에서 왔는지 기록하는 자리.

    서로 다른 출처(예: 한국문화정보원, 경기 데이터 드림)가 같은 물리적 장소를
    가리키는 경우가 있어서, 명소 하나(Place)가 출처를 여러 개 가질 수 있다.
    "같은 출처 + 같은 원본 번호"는 항상 같은 명소를 가리키므로 중복을 막는다.
    """

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="sources")
    source = models.CharField(max_length=50)
    # 경기 데이터 드림처럼 원본에 고유번호가 없는 출처는 여러 필드를 합친 문자열을 넣는다
    # (build_composite_source_id 참고). 그래서 일반적인 ID 필드보다 넉넉하게 잡는다.
    source_id = models.CharField(max_length=500)

    class Meta:
        unique_together = ("source", "source_id")

    def __str__(self):
        return f"{self.place} - {self.source}:{self.source_id}"


class Work(models.Model):
    """영화·드라마 작품 정보. 관리자가 직접 등록한다."""

    class Category(models.TextChoices):
        DRAMA = "DRAMA", "드라마"
        MOVIE = "MOVIE", "영화"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=10, choices=Category.choices)
    release_date = models.DateField(null=True, blank=True)
    main_cast = models.CharField(max_length=300, blank=True)
    director = models.CharField(max_length=100, blank=True)
    poster_url = models.URLField(blank=True)

    def __str__(self):
        return self.title


class PlaceWork(models.Model):
    """명소와 작품을 잇는 자리.

    한 명소에 여러 작품이, 한 작품에 여러 명소가 연결될 수 있어서 둘을 바로 연결하지 않고
    이 중간 테이블을 둔다. "이 명소가 이 작품의 어떤 장면에 나왔는지"는 명소나 작품 어느
    한쪽에만 속한 정보가 아니라 이 연결에 속한 정보라서 장면 설명도 여기에 붙는다.
    """

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="place_works")
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="place_works")
    scene_description = models.TextField(blank=True)

    class Meta:
        unique_together = ("place", "work")

    def __str__(self):
        return f"{self.place} - {self.work}"


class TranslationStatus(models.TextChoices):
    """번역 처리 상태. PlaceTranslation/WorkTranslation이 공통으로 쓴다 (DETAIL_SPEC 4-3·4-4)."""

    PENDING = "PENDING", "대기"
    SUCCESS = "SUCCESS", "성공"
    FAILED = "FAILED", "실패"


class PlaceTranslation(models.Model):
    """명소 이름·설명의 언어별 번역문.

    is_approved가 True인 것만 손님에게 보여준다 — 자동 번역이 뜻으로 옮겨버릴 수 있어서
    (예: 경복궁 → Scenery Palace) 관리자가 눈으로 확인해야 한다 (DETAIL_SPEC 4-3 (2)).
    status/translated_at은 번역 시도 결과를 남겨서, 실패한 것을 관리자 화면에서 찾아
    "다시 번역"할 수 있게 한다.
    """

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    is_approved = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=TranslationStatus.choices, default=TranslationStatus.PENDING)
    translated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("place", "language")

    def __str__(self):
        return f"{self.place} ({self.language})"


class WorkTranslation(models.Model):
    """작품 제목·설명의 언어별 번역문. 규칙은 PlaceTranslation과 같다."""

    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    is_approved = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=TranslationStatus.choices, default=TranslationStatus.PENDING)
    translated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("work", "language")

    def __str__(self):
        return f"{self.work} ({self.language})"


class SearchHistory(models.Model):
    """로그인한 사람이 검색한 말을 남긴다.

    Phase 2에서는 최근 검색어 표시에 쓰이고(DETAIL_SPEC 2-5), Phase 3의 검색 이력
    기반 추천 고도화에도 쓰인다. 비로그인 사용자의 검색어는 여기 남기지 않는다.
    """

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="search_histories")
    keyword = models.CharField(max_length=200)
    searched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.member} - {self.keyword}"
