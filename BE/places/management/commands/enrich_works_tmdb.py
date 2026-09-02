"""DB에 있는 작품(Work)을 돌면서 TMDB에서 줄거리·감독·방영일자·포스터를 채운다.

제목이 정확히 일치하는 TMDB 작품을 찾은 것만 채운다. 못 찾은 작품은 손대지 않고
넘어간다 ("존재하는 것만" 채운다). 관리자가 이미 채운 값도 기본적으로 덮어쓰지 않는다.

예)
  python manage.py enrich_works_tmdb                  # 전체
  python manage.py enrich_works_tmdb --category DRAMA  # 드라마만
  python manage.py enrich_works_tmdb --only-missing    # 네 필드가 다 빈 작품만
  python manage.py enrich_works_tmdb --work-id 1       # 한 작품만 (매칭 확인용)
  python manage.py enrich_works_tmdb --overwrite       # 이미 채워진 값도 TMDB 값으로 교체
"""

import time

from django.core.management.base import BaseCommand

from places.models import Work
from places.work_enrichment import FILLABLE_FIELDS, enrich_work


class Command(BaseCommand):
    help = "DB의 작품을 TMDB 정보(줄거리·감독·방영일자·포스터)로 보강한다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--category",
            choices=[Work.Category.DRAMA, Work.Category.MOVIE],
            help="이 종류만 처리한다 (기본: 전체).",
        )
        parser.add_argument("--work-id", type=int, help="이 작품 하나만 처리한다.")
        parser.add_argument(
            "--only-missing",
            action="store_true",
            help="줄거리·감독·방영일자·포스터가 모두 비어 있는 작품만 처리한다.",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="관리자가 채운 값이 있어도 TMDB 값으로 덮어쓴다 (기본: 빈 값만 채움).",
        )
        parser.add_argument(
            "--allow-foreign",
            action="store_true",
            help="원어가 한국어가 아닌 TMDB 작품도 매칭 대상에 넣는다 (기본: 한국 제작물만).",
        )
        parser.add_argument("--limit", type=int, help="최대 이 개수만 처리한다.")
        parser.add_argument(
            "--sleep",
            type=float,
            default=0.0,
            help="작품 하나 처리할 때마다 이 초만큼 쉰다 (TMDB 호출 간격 조절용).",
        )

    def handle(self, *args, **options):
        works = Work.objects.all().order_by("id")

        if options["category"]:
            works = works.filter(category=options["category"])
        if options["work_id"]:
            works = works.filter(id=options["work_id"])
        if options["only_missing"]:
            # 문자열 필드는 빈 문자열, 날짜 필드(release_date)는 NULL이 "비어 있음"이다.
            works = works.filter(
                description="", director="", poster_url="", release_date__isnull=True
            )
        if options["limit"]:
            works = works[: options["limit"]]

        overwrite = options["overwrite"]
        require_korean = not options["allow_foreign"]
        sleep_seconds = options["sleep"]

        counts = {"matched": 0, "matched_no_change": 0, "no_match": 0, "unsupported": 0, "error": 0}
        filled_field_counts = dict.fromkeys(FILLABLE_FIELDS, 0)
        total = works.count()
        self.stdout.write(f"대상 작품 {total}건")

        for index, work in enumerate(works.iterator(), start=1):
            try:
                status, filled = enrich_work(work, overwrite=overwrite, require_korean=require_korean)
            except Exception as exc:  # 한 건 실패해도 나머지는 계속 처리한다
                counts["error"] += 1
                self.stderr.write(f"[{work.id}] {work.title} - 오류: {exc}")
                continue

            counts[status] += 1
            for field in filled:
                filled_field_counts[field] += 1

            if status == "matched":
                self.stdout.write(f"[{work.id}] {work.title} - 채움: {', '.join(filled)}")

            if sleep_seconds and index < total:
                time.sleep(sleep_seconds)

        self.stdout.write(
            self.style.SUCCESS(
                "\n완료\n"
                f"  매칭·보강: {counts['matched']}건\n"
                f"  매칭됐지만 채울 것 없음: {counts['matched_no_change']}건\n"
                f"  일치하는 TMDB 작품 없음: {counts['no_match']}건\n"
                f"  TMDB 대상 아님(카테고리): {counts['unsupported']}건\n"
                f"  오류: {counts['error']}건\n"
                "  채운 필드별 건수: "
                + ", ".join(f"{field} {n}" for field, n in filled_field_counts.items())
            )
        )
