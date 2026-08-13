from django.db import models


class Place(models.Model):
    """촬영 명소 정보.

    이름/주소/위치는 공공데이터에서 가져와 채운다.
    설명/사진/영업시간은 관리자가 직접 채워 넣는 값이라, 공공데이터를 다시 가져와도 덮어쓰지 않는다.
    """

    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # 공공데이터 원본 식별자. 여러 공공데이터 출처를 함께 쓸 수도 있어서,
    # 출처 이름(source)과 그 출처 안에서의 원본 번호(source_id)를 같이 저장한다.
    # 이 둘을 합쳐서 "같은 명소인지"를 판단하므로, 재수집해도 중복으로 쌓이지 않는다.
    source = models.CharField(max_length=50)
    source_id = models.CharField(max_length=100)

    # 관리자가 직접 채우는 값 (가져오기로 덮어쓰지 않는다)
    description = models.TextField(blank=True)
    photo_url = models.URLField(blank=True)
    business_hours = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("source", "source_id")

    def __str__(self):
        return self.name


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


class PlaceTranslation(models.Model):
    """명소 이름·설명의 언어별 번역문 자리. 실제 번역은 Phase 4에서 채운다."""

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("place", "language")

    def __str__(self):
        return f"{self.place} ({self.language})"


class WorkTranslation(models.Model):
    """작품 제목·설명의 언어별 번역문 자리. 실제 번역은 Phase 4에서 채운다."""

    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="translations")
    language = models.CharField(max_length=10)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("work", "language")

    def __str__(self):
        return f"{self.work} ({self.language})"
