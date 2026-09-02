"""DB에 있는 명소(Place)를 돌면서 TourAPI에서 대표 사진(firstimage)을 찾아 photo_url에 채운다.

이름이 정확히 일치하고 좌표가 가까운 관광정보만 인정한다. 못 찾은 명소는 손대지 않고
넘어간다 ("존재하는 것만" 채운다). photo_url은 원래 관리자가 채우는 값이라, 비어 있는
명소만 기본 대상이고 이미 채워진 값은 --overwrite를 줄 때만 교체한다.

TourAPI는 등록된 관광지·음식점 위주라, 소규모 카페 촬영지는 매칭이 안 되는 게 정상이다.
그런 명소 사진은 다른 소스(Google Places 등)나 관리자 입력으로 채워야 한다.

예)
  python manage.py import_place_photos                 # photo_url 빈 명소 전체
  python manage.py import_place_photos --only-missing  # (기본과 동일, 명시용)
  python manage.py import_place_photos --place-id 3    # 한 명소만 (매칭 확인용)
  python manage.py import_place_photos --overwrite     # 이미 채워진 photo_url도 교체
  python manage.py import_place_photos --dry-run       # 저장하지 않고 매칭 결과만 출력
  python manage.py import_place_photos --sleep 0.2     # 호출 간격 0.2초
"""

import time

from django.core.management.base import BaseCommand

from places.models import Place
from places.place_photo_enrichment import (
    PHOTO_MATCH_DISTANCE_METERS,
    pick_photo_match,
)
from places.sources import tour_api


class Command(BaseCommand):
    help = "DB의 명소를 한국관광공사 TourAPI의 대표 이미지(firstimage)로 채운다."

    def add_arguments(self, parser):
        parser.add_argument("--place-id", type=int, help="이 명소 하나만 처리한다.")
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="photo_url이 비어 있는 명소만 처리한다 (아무 옵션도 없을 때의 기본 동작).",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="이미 채워진 photo_url이 있어도 TourAPI 이미지로 덮어쓴다 (기본: 빈 값만 채움).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="저장하지 않고 어떤 명소에 어떤 이미지가 매칭되는지만 출력한다.",
        )
        parser.add_argument(
            "--distance",
            type=int,
            default=PHOTO_MATCH_DISTANCE_METERS,
            help=f"이름이 같아도 좌표가 이 거리(m)보다 멀면 다른 장소로 본다 (기본: {PHOTO_MATCH_DISTANCE_METERS}).",
        )
        parser.add_argument("--limit", type=int, help="최대 이 개수만 처리한다.")
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.0,
            help="명소 하나 처리할 때마다 이 초만큼 쉰다 (TourAPI 호출 간격 조절용).",
        )

    def handle(self, *args, **options):
        places = Place.objects.all().order_by("id")

        if options["place_id"]:
            places = places.filter(id=options["place_id"])
        elif not options["overwrite"]:
            # --overwrite가 아니면 항상 빈 photo_url만 대상이다 (--only-missing은 명시용).
            places = places.filter(photo_url="")
        if options["limit"]:
            places = places[: options["limit"]]

        overwrite = options["overwrite"]
        dry_run = options["dry_run"]
        max_distance = options["distance"]
        sleep_seconds = options["sleep"]

        counts = {"matched": 0, "matched_no_change": 0, "no_match": 0, "error": 0}
        total = places.count()
        self.stdout.write(f"대상 명소 {total}건" + (" (dry-run)" if dry_run else ""))

        for index, place in enumerate(places.iterator(), start=1):
            try:
                candidates = tour_api.search_keyword(place.name)
                match = pick_photo_match(place, candidates, max_distance_meters=max_distance)
            except Exception as exc:  # 한 건 실패해도 나머지는 계속 처리한다
                counts["error"] += 1
                self.stderr.write(f"[{place.id}] {place.name} - 오류: {exc}")
                continue

            if match is None:
                counts["no_match"] += 1
            elif place.photo_url == match["first_image"]:
                counts["matched_no_change"] += 1
            else:
                counts["matched"] += 1
                self.stdout.write(f"[{place.id}] {place.name} - {match['first_image']}")
                if not dry_run:
                    place.photo_url = match["first_image"]
                    place.save(update_fields=["photo_url"])

            if sleep_seconds and index < total:
                time.sleep(sleep_seconds)

        verb = "매칭됨(저장 안 함)" if dry_run else "채움"
        self.stdout.write(
            self.style.SUCCESS(
                "\n완료\n"
                f"  {verb}: {counts['matched']}건\n"
                f"  매칭됐지만 같은 값이라 그대로: {counts['matched_no_change']}건\n"
                f"  맞는 관광정보 없음: {counts['no_match']}건\n"
                f"  오류: {counts['error']}건"
            )
        )
