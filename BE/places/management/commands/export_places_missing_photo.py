"""photo_url이 빈 명소를 CSV로 뽑아준다.

TourAPI·위키백과로도 못 채운 명소를 사람이 저작권 무료 사이트(Unsplash 등)에서
직접 찾아 채우기 위한 작업용 파일이다. photo_url/photo_credit 칸은 비운 채로 나가고,
사람이 그 칸을 채운 뒤 import_place_photos_manual 커맨드로 다시 읽어들인다.

예)
  python manage.py export_places_missing_photo
  python manage.py export_places_missing_photo --output places_missing_photo.csv
"""

import csv

from django.core.management.base import BaseCommand

from places.models import Place


class Command(BaseCommand):
    help = "photo_url이 빈 명소 목록을 CSV로 내보낸다 (수동으로 사진을 찾아 채우는 작업용)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="places_missing_photo.csv",
            help="CSV를 저장할 경로 (기본: places_missing_photo.csv)",
        )

    def handle(self, *args, **options):
        output_path = options["output"]
        places = Place.objects.filter(photo_url="").order_by("name")

        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "address", "photo_url", "photo_credit"])
            for place in places:
                writer.writerow([place.id, place.name, place.address, "", ""])

        self.stdout.write(self.style.SUCCESS(f"{places.count()}건 -> {output_path}"))
