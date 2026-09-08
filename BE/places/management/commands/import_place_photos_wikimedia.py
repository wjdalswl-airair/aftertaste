"""DB의 명소(Place)를 돌면서 한국어 위키백과 문서의 대표 이미지를 photo_url에 채운다.

TourAPI(import_place_photos)로 못 채운 명소를 보강하는 2순위 소스다. 기본 대상은
"photo_url이 비어 있고 + 아직 위키백과 매칭을 시도한 적 없는 명소"라, TourAPI로 이미
채운 명소는 건드리지 않고 TourAPI가 못 찾은 명소만 이어서 시도한다.

이름이 정확히 일치하고 좌표가 가까운 문서만 인정한다. 못 찾은 명소는 손대지 않고
넘어간다("존재하는 것만" 채운다). 위키백과는 호출 한도가 없어서 전체를 한 번에 돌려도 된다.

대표 이미지는 대부분 위키미디어 커먼즈 파일이고 라이선스는 CC-BY / CC-BY-SA(저작자
표시 필요) 또는 퍼블릭도메인이다. 지금은 URL만 저장한다 — 상업적 사용 시 저작자 표시
필요 (docs/DETAIL_SPEC.md 6-1 #31).

한 번 매칭한 명소는 문서 번호(pageid)를 PlaceSource(WIKIMEDIA)에 저장해서, 다시 실행할 때
이름으로 재검색하지 않고 그 번호로 바로 최신 이미지를 받는다.

예)
  python manage.py import_place_photos_wikimedia                  # photo_url 빈 명소 전체
  python manage.py import_place_photos_wikimedia --place-id 3      # 한 명소만 (매칭 확인용)
  python manage.py import_place_photos_wikimedia --place-id 3 --page-id 12345   # pageid 수동 지정
  python manage.py import_place_photos_wikimedia --overwrite       # 이미 채워진 photo_url도 교체
  python manage.py import_place_photos_wikimedia --dry-run         # 저장하지 않고 매칭 결과만 출력
  python manage.py import_place_photos_wikimedia --limit 100 --sleep 0.2
  python manage.py import_place_photos_wikimedia --name-contains 해수욕장,공원,궁,박물관,사,계곡
"""

import time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from places.models import Place, PlaceSource
from places.place_photo_enrichment import (
    NO_MATCH_PREFIX,
    PHOTO_MATCH_DISTANCE_METERS,
    WIKIMEDIA_SOURCE,
    enrich_place_photo_from_wikimedia,
    pick_photo_match,
)
from places.sources import wikimedia

# 이만큼 연속으로 호출이 실패하면 API가 죽은 것으로 보고 실행을 멈춘다.
_CONSECUTIVE_ERROR_LIMIT = 5


class Command(BaseCommand):
    help = "DB의 명소를 한국어 위키백과 문서의 대표 이미지로 채운다 (TourAPI 보강용)."

    def add_arguments(self, parser):
        parser.add_argument("--place-id", type=int, help="이 명소 하나만 처리한다.")
        parser.add_argument(
            "--page-id",
            help="--place-id와 함께 쓴다. 그 명소의 위키백과 문서 번호(pageid)를 이 값으로 고정한다"
            " (검색·매칭 대신 직접 지정 — 오매칭을 바로잡을 때).",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="이미 채워진 photo_url이 있어도 위키백과 이미지로 덮어쓴다 (기본: 빈 값만 채움).",
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
        parser.add_argument(
            "--name-contains",
            help="쉼표로 구분한 낱말 목록. 이름에 그중 하나라도 들어간 명소만 처리한다 (대소문자 무시).",
        )
        parser.add_argument("--limit", type=int, help="최대 이 개수만 처리한다.")
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.1,
            help="명소 하나 처리할 때마다 이 초만큼 쉰다 (위키백과 예의상, 기본 0.1).",
        )

    def handle(self, *args, **options):
        if options["page_id"]:
            if not options["place_id"]:
                raise CommandError("--page-id는 --place-id와 함께 써야 합니다.")
            self._pin_page_id(options["place_id"], options["page_id"])

        places = Place.objects.all().order_by("id")
        if options["place_id"]:
            places = places.filter(id=options["place_id"])
        elif options["overwrite"]:
            # 이미 채워진 것·실패로 기록된 것까지 전부 다시 시도한다.
            pass
        else:
            # 빈 photo_url + 아직 위키백과 매칭을 시도한 적 없는 명소만 (재실행 시 이어서).
            # 매칭 실패도 PlaceSource(__no_match__)로 기록돼 여기서 걸러진다.
            tried = PlaceSource.objects.filter(source=WIKIMEDIA_SOURCE).values("place_id")
            places = places.filter(photo_url="").exclude(id__in=tried)

        name_contains = options["name_contains"]
        if name_contains:
            words = [w.strip() for w in name_contains.split(",") if w.strip()]
            if words:
                name_filter = Q()
                for word in words:
                    name_filter |= Q(name__icontains=word)
                places = places.filter(name_filter)

        if options["limit"]:
            places = places[: options["limit"]]

        overwrite = options["overwrite"]
        dry_run = options["dry_run"]
        max_distance = options["distance"]
        sleep_seconds = options["sleep"]

        counts = {"matched": 0, "matched_no_change": 0, "no_match": 0, "error": 0}
        total = places.count()
        self.stdout.write(f"대상 명소 {total}건" + (" (dry-run)" if dry_run else ""))

        stop_reason = None
        consecutive_errors = 0
        for index, place in enumerate(places.iterator(), start=1):
            try:
                if dry_run:
                    status, url = self._dry_run_one(place, max_distance)
                else:
                    status, url = enrich_place_photo_from_wikimedia(
                        place, overwrite=overwrite, max_distance_meters=max_distance
                    )
            except Exception as exc:  # 한 건 실패해도 나머지는 계속 처리한다
                counts["error"] += 1
                consecutive_errors += 1
                self.stderr.write(f"[{place.id}] {place.name} - 오류: {exc}")
                # 연속으로 계속 실패하면 API가 죽었거나 네트워크가 끊긴 것 — 몇 시간을
                # 타임아웃으로 허비하지 않도록 멈춘다. 재실행하면 빈 것만 이어서 채운다.
                if consecutive_errors >= _CONSECUTIVE_ERROR_LIMIT:
                    stop_reason = f"{_CONSECUTIVE_ERROR_LIMIT}건 연속 실패 — API 응답 없음"
                    break
                continue

            consecutive_errors = 0
            counts[status] += 1
            if status == "matched":
                self.stdout.write(f"[{place.id}] {place.name} - {url}")

            if sleep_seconds and index < total:
                time.sleep(sleep_seconds)

        self._print_summary(counts, dry_run, stop_reason)

    def _pin_page_id(self, place_id, page_id):
        try:
            place = Place.objects.get(id=place_id)
        except Place.DoesNotExist:
            raise CommandError(f"명소 {place_id}이(가) 없습니다.")
        PlaceSource.objects.filter(place=place, source=WIKIMEDIA_SOURCE).delete()
        PlaceSource.objects.update_or_create(
            source=WIKIMEDIA_SOURCE, source_id=str(page_id), defaults={"place": place}
        )
        self.stdout.write(f"[{place.id}] {place.name} - 위키백과 pageid {page_id}로 고정")

    def _dry_run_one(self, place, max_distance):
        """저장하지 않고 어떤 이미지가 매칭되는지만 본다."""
        known = PlaceSource.objects.filter(place=place, source=WIKIMEDIA_SOURCE).first()
        if known is not None and known.source_id.startswith(NO_MATCH_PREFIX):
            return "no_match", None
        if known is not None:
            detail = wikimedia.get_detail(known.source_id)
            url = (detail or {}).get("first_image", "")
        else:
            candidates = wikimedia.search_keyword(place.name)
            match = pick_photo_match(place, candidates, max_distance_meters=max_distance)
            url = match["first_image"] if match else ""
        if not url:
            return "no_match", None
        if place.photo_url == url:
            return "matched_no_change", None
        return "matched", url

    def _print_summary(self, counts, dry_run, stop_reason):
        verb = "매칭됨(저장 안 함)" if dry_run else "채움"
        headline = f"중단 ({stop_reason})" if stop_reason else "완료"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{headline}\n"
                f"  {verb}: {counts['matched']}건\n"
                f"  매칭됐지만 바꿀 값 없음: {counts['matched_no_change']}건\n"
                f"  맞는 문서 없음: {counts['no_match']}건\n"
                f"  오류: {counts['error']}건"
            )
        )
