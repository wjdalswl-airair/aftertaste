"""export_places_missing_photo가 뽑은 CSV를 다시 읽어 Place.photo_url/photo_credit을 채운다.

사람이 저작권 무료 사이트에서 직접 찾아 CSV의 photo_url(선택: photo_credit) 칸을
채워둔 뒤 이 커맨드로 불러온다. photo_url 칸이 비어있는 행(아직 못 찾은 명소)은
그냥 건너뛴다 — CSV를 계속 갱신하면서 이어서 실행하면 된다.

photo_url은 원래 관리자가 채우는 값이라(models.py 참고), 비어 있는 명소만 기본
대상이고 이미 채워진 값은 --overwrite를 줄 때만 교체한다.

예)
  python manage.py import_place_photos_manual --file places_missing_photo.csv
  python manage.py import_place_photos_manual --file places_missing_photo.csv --dry-run
  python manage.py import_place_photos_manual --file places_missing_photo.csv --overwrite
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from places.models import Place


class Command(BaseCommand):
    help = "CSV(id, photo_url, photo_credit)를 읽어 명소 사진을 수동으로 채운다."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="import할 CSV 경로.")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="이미 채워진 photo_url이 있어도 CSV 값으로 덮어쓴다 (기본: 빈 값만 채움).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="저장하지 않고 어떤 명소가 채워질지만 출력한다.",
        )

    def handle(self, *args, **options):
        overwrite = options["overwrite"]
        dry_run = options["dry_run"]

        try:
            f = open(options["file"], newline="", encoding="utf-8-sig")
        except OSError as exc:
            raise CommandError(f"CSV를 열 수 없습니다: {exc}")

        counts = {"filled": 0, "skipped_empty": 0, "skipped_has_photo": 0, "not_found": 0, "error": 0}
        with f:
            for row in csv.DictReader(f):
                photo_url = (row.get("photo_url") or "").strip()
                if not photo_url:
                    counts["skipped_empty"] += 1
                    continue

                place_id = row.get("id")
                try:
                    place = Place.objects.get(id=place_id)
                except (Place.DoesNotExist, ValueError, TypeError):
                    counts["not_found"] += 1
                    self.stderr.write(f"[{place_id}] 명소를 찾을 수 없습니다.")
                    continue

                if place.photo_url and not overwrite:
                    counts["skipped_has_photo"] += 1
                    continue

                photo_credit = (row.get("photo_credit") or "").strip()
                self.stdout.write(f"[{place.id}] {place.name} - {photo_url}")
                if dry_run:
                    counts["filled"] += 1
                    continue

                try:
                    place.photo_url = photo_url
                    place.photo_credit = photo_credit
                    place.save(update_fields=["photo_url", "photo_credit"])
                    counts["filled"] += 1
                except Exception as exc:
                    counts["error"] += 1
                    self.stderr.write(f"[{place.id}] {place.name} - 오류: {exc}")

        verb = "채워짐(저장 안 함)" if dry_run else "채움"
        self.stdout.write(
            self.style.SUCCESS(
                f"\n완료\n"
                f"  {verb}: {counts['filled']}건\n"
                f"  photo_url 빈 행(건너뜀): {counts['skipped_empty']}건\n"
                f"  이미 채워짐(건너뜀): {counts['skipped_has_photo']}건\n"
                f"  명소 못 찾음: {counts['not_found']}건\n"
                f"  오류: {counts['error']}건"
            )
        )
