from django.core.management.base import BaseCommand, CommandError

from places.models import Work
from places.services import get_or_create_work, parse_yyyymmdd
from places.sources import kmdb


class Command(BaseCommand):
    """KMDB(한국영상자료원) API에서 영화를 검색해 Work를 만든다.

    title/director/keyword로 검색된 영화를 종류(극영화·문화영화·TV영화 등) 구분 없이
    그대로 다 가져온다 (2026-09-01 결정). 이미 있는 작품(제목+category가 같음)은 KMDB
    데이터로 덮어쓰지 않는다 — 관리자가 고친 값을 지키기 위해서다 (docs/DETAIL_SPEC.md 6-1 #28).
    """

    help = "KMDB API에서 영화를 검색해 Work를 만든다."

    def add_arguments(self, parser):
        parser.add_argument("--title", help="검색할 영화 제목")
        parser.add_argument("--director", help="검색할 감독 이름")
        parser.add_argument("--keyword", help="검색할 키워드")

    def handle(self, *args, **options):
        title, director, keyword = options.get("title"), options.get("director"), options.get("keyword")
        if not (title or director or keyword):
            raise CommandError("--title, --director, --keyword 중 하나는 있어야 합니다.")

        movies = kmdb.search_movies(title=title, director=director, keyword=keyword)

        created_count = 0
        skipped_count = 0
        skipped_no_title_count = 0

        for movie in movies:
            if not movie["title"]:
                skipped_no_title_count += 1
                continue

            release_date, _ = parse_yyyymmdd(movie["release_date"])

            work, created = get_or_create_work(
                movie["title"],
                Work.Category.MOVIE,
                create_only_fields={
                    "director": movie["director"],
                    "main_cast": movie["main_cast"],
                    "release_date": release_date,
                    "poster_url": movie["poster_url"],
                    "description": movie["description"],
                },
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 새로 만듦 {created_count}건, 이미 있어서 건너뜀 {skipped_count}건, "
                f"제목 없어서 건너뜀 {skipped_no_title_count}건"
            )
        )
