from django.db import transaction
from rest_framework import serializers

from courses.models import Course, CoursePlace

# 코스 하나에 반드시 있어야 하는 역할 조합 (DETAIL_SPEC 6-1 #17, PRD F-08).
REQUIRED_ROLES = {CoursePlace.Role.RESTAURANT, CoursePlace.Role.CAFE, CoursePlace.Role.OTHER}


class CoursePlaceSerializer(serializers.ModelSerializer):
    """코스에 들어있는 장소 하나를 보여줄 때 쓰는 읽기 전용 표현."""

    class Meta:
        model = CoursePlace
        fields = [
            "id",
            "role",
            "order",
            "name",
            "address",
            "road_address_name",
            "latitude",
            "longitude",
            "category_name",
            "kakao_place_id",
        ]
        read_only_fields = fields


class CourseSerializer(serializers.ModelSerializer):
    """코스 조회(목록·상세)용 읽기 전용 표현."""

    course_places = CoursePlaceSerializer(many=True, read_only=True)
    place_id = serializers.IntegerField(source="place.id", read_only=True)
    place_name = serializers.CharField(source="place.name", read_only=True)
    creator_nickname = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "place_id",
            "place_name",
            "creator_nickname",
            "title",
            "description",
            "course_places",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_creator_nickname(self, obj):
        # 관리자가 admin에서 만든 코스는 creator가 없을 수 있다.
        if obj.creator is None:
            return None
        # 탈퇴한 사람이 만든 코스는 작성자 자리에 "탈퇴한 사용자"로 보인다 (DETAIL_SPEC 5장 공통 규칙).
        return "탈퇴한 사용자" if obj.creator.is_withdrawn else obj.creator.nickname


class CoursePlaceWriteSerializer(serializers.ModelSerializer):
    """코스 생성·수정 요청에서 장소 하나(식당/카페/그 외)를 받는 입력.

    프론트가 카카오 주변 상권 검색 결과 중 고른 장소의 스냅샷 데이터를 그대로 보낸다고
    가정한다 — 서버는 카카오를 다시 호출하지 않는다.
    """

    class Meta:
        model = CoursePlace
        fields = [
            "role",
            "name",
            "address",
            "road_address_name",
            "latitude",
            "longitude",
            "category_name",
            "kakao_place_id",
        ]


class CourseWriteSerializer(serializers.ModelSerializer):
    """코스 생성·수정에 쓰는 시리얼라이저.

    course_places는 반드시 식당(RESTAURANT) 1 + 카페(CAFE) 1 + 그 외(OTHER) 1,
    정확히 3개여야 한다(완료 기준 "식당 1 + 카페 1 + 그 외 1로 구성된 코스가 만들어진다").
    """

    course_places = CoursePlaceWriteSerializer(many=True)

    class Meta:
        model = Course
        fields = ["title", "description", "course_places"]

    def validate_course_places(self, value):
        roles = [item["role"] for item in value]
        if len(roles) != 3 or set(roles) != REQUIRED_ROLES:
            raise serializers.ValidationError("식당 1 + 카페 1 + 그 외 1이 모두 있어야 합니다")
        return value

    def create(self, validated_data):
        course_places_data = validated_data.pop("course_places")
        with transaction.atomic():
            course = Course.objects.create(**validated_data)
            CoursePlace.objects.bulk_create(
                [
                    CoursePlace(course=course, order=order, **item)
                    for order, item in enumerate(course_places_data)
                ]
            )
        return course

    def update(self, instance, validated_data):
        course_places_data = validated_data.pop("course_places", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if course_places_data is not None:
            with transaction.atomic():
                instance.course_places.all().delete()
                CoursePlace.objects.bulk_create(
                    [
                        CoursePlace(course=instance, order=order, **item)
                        for order, item in enumerate(course_places_data)
                    ]
                )
        return instance
