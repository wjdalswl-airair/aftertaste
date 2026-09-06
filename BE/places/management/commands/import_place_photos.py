"""DB에 있는 명소(Place)를 돌면서 TourAPI에서 대표 사진(firstimage)을 찾아 photo_url에 채운다.

이름이 정확히 일치하고 좌표가 가까운 관광정보만 인정한다. 못 찾은 명소는 손대지 않고
넘어간다 ("존재하는 것만" 채운다). photo_url은 원래 관리자가 채우는 값이라, 비어 있는
명소만 기본 대상이고 이미 채워진 값은 --overwrite를 줄 때만 교체한다.

한 번 매칭한 명소는 TourAPI content_id를 PlaceSource(TOUR_API)에 저장해서, 다시 실행할 때
이름으로 재검색하지 않고 그 id로 바로 최신 이미지를 받는다.

TourAPI는 등록된 관광지·음식점 위주라, 소규모 카페 촬영지는 매칭이 안 되는 게 정상이다.
그런 명소 사진은 다른 소스(Google Places 등)나 관리자 입력으로 채워야 한다.

예)
  python manage.py import_place_photos                 # photo_url 빈 명소 전체
  python manage.py import_place_photos --place-id 3    # 한 명소만 (매칭 확인용)
  python manage.py import_place_photos --place-id 3 --content-id 126508   # content_id 수동 지정
  python manage.py import_place_photos --overwrite     # 이미 채워진 photo_url도 교체
  python manage.py import_place_photos --dry-run       # 저장하지 않고 매칭 결과만 출력
  python manage.py import_place_photos --limit 50 --sleep 0.3
"""

import time

from django.core.management.base import BaseCommand, CommandError

from places.models import Place, PlaceSource
from places.place_photo_enrichment import (
    PHOTO_MATCH_DISTANCE_METERS,
    TOUR_API_SOURCE,
    enrich_place_photo,
)
from places.sources import tour_api


class Command(BaseCommand):
    help = "DB의 명소를 한국관광공사 TourAPI의 대표 이미지(firstimage)로 채운다."

    def add_arguments(self, parser):
        parser.add_argument("--place-id", type=int, help="이 명소 하나만 처리한다.")
        parser.add_argument(
            "--content-id",
            help="--place-id와 함께 쓴다. 그 명소의 TourAPI content_id를 이 값으로 고정한다"
            " (검색·매칭 대신 직접 지정 — 오매칭을 바로잡을 때).",
        )
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
            default=0.1,
            help="명소 하나 처리할 때마다 이 초만큼 쉰다 (TourAPI 초당 제한 완화용, 기본 0.1).",
        )

    def handle(self, *args, **options):
        if options["content_id"]:
            if not options["place_id"]:
                raise CommandError("--content-id는 --place-id와 함께 써야 합니다.")
            self._pin_content_id(options["place_id"], options["content_id"])

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

        stopped_early = False
        for index, place in enumerate(places.iterator(), start=1):
            try:
                if dry_run:
                    status, url = self._dry_run_one(place, max_distance)
                else:
                    status, url = enrich_place_photo(
                        place, overwrite=overwrite, max_distance_meters=max_distance
                    )
            except tour_api.TourApiDailyLimitError as exc:
                # 일일 한도 초과. 남은 건을 계속 돌려봐야 전부 같은 오류라, 여기서 멈추고
                # 지금까지 채운 것만 남긴다. 다음 날 다시 실행하면 빈 것만 이어서 채운다.
                self.stderr.write(self.style.WARNING(f"\n중단: {exc}"))
                stopped_early = True
                break
            except Exception as exc:  # 한 건 실패해도 나머지는 계속 처리한다
                counts["error"] += 1
                self.stderr.write(f"[{place.id}] {place.name} - 오류: {exc}")
                continue

            counts[status] += 1
            if status == "matched":
                self.stdout.write(f"[{place.id}] {place.name} - {url}")

            if sleep_seconds and index < total:
                time.sleep(sleep_seconds)

        self._print_summary(counts, dry_run, stopped_early)

    def _pin_content_id(self, place_id, content_id):
        try:
            place = Place.objects.get(id=place_id)
        except Place.DoesNotExist:
            raise CommandError(f"명소 {place_id}이(가) 없습니다.")
        PlaceSource.objects.filter(place=place, source=TOUR_API_SOURCE).delete()
        PlaceSource.objects.update_or_create(
            source=TOUR_API_SOURCE, source_id=str(content_id), defaults={"place": place}
        )
        self.stdout.write(f"[{place.id}] {place.name} - TourAPI content_id {content_id}로 고정")

    def _dry_run_one(self, place, max_distance):
        """저장하지 않고 어떤 이미지가 매칭되는지만 본다."""
        from places.place_photo_enrichment import pick_photo_match

        known = PlaceSource.objects.filter(place=place, source=TOUR_API_SOURCE).first()
        if known is not None:
            detail = tour_api.get_detail(known.source_id)
            url = (detail or {}).get("first_image", "")
        else:
            candidates = tour_api.search_keyword(place.name)
            match = pick_photo_match(place, candidates, max_distance_meters=max_distance)
            url = match["first_image"] if match else ""
        if not url:
            return "no_match", None
        if place.photo_url == url:
            return "matched_no_change", None
        return "matched", url

    def _print_summary(self, counts, dry_run, stopped_early):
        verb = "매칭됨(저장 안 함)" if dry_run else "채움"
        headline = "일일 한도로 중단" if stopped_early else "완료"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{headline}\n"
                f"  {verb}: {counts['matched']}건\n"
                f"  매칭됐지만 바꿀 값 없음: {counts['matched_no_change']}건\n"
                f"  맞는 관광정보 없음: {counts['no_match']}건\n"
                f"  오류: {counts['error']}건"
            )
        )
