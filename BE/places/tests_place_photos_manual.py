"""feature/be/place-photo-manual: 저작권 무료 사이트에서 수동으로 찾은 사진을 CSV로 채우는 흐름.

- export_places_missing_photo: photo_url이 빈 명소만 CSV로 나가는지
- import_place_photos_manual: CSV의 photo_url/photo_credit로 채우는지, 빈 행/이미 채워진 명소를
  건너뛰는지, --overwrite/--dry-run이 동작하는지
"""

import csv
import os
import tempfile

from django.core.management import call_command
from django.test import TestCase

from places.models import Place


class ExportPlacesMissingPhotoCommandTest(TestCase):
    def test_exports_only_places_missing_photo(self):
        empty = Place.objects.create(name="빈명소", address="서울")
        Place.objects.create(name="채워진명소", address="부산", photo_url="https://example.com/a.jpg")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = os.path.join(tmp_dir, "out.csv")
            call_command("export_places_missing_photo", "--output", output_path)

            with open(output_path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], str(empty.id))
        self.assertEqual(rows[0]["name"], "빈명소")
        self.assertEqual(rows[0]["photo_url"], "")


class ImportPlacePhotosManualCommandTest(TestCase):
    def _write_csv(self, tmp_dir, rows):
        path = os.path.join(tmp_dir, "in.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "address", "photo_url", "photo_credit"])
            writer.writerows(rows)
        return path

    def test_fills_photo_url_and_credit(self):
        place = Place.objects.create(name="명소")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_csv(
                tmp_dir, [[place.id, place.name, "", "https://example.com/a.jpg", "홍길동 / Unsplash"]]
            )
            call_command("import_place_photos_manual", "--file", path)

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "https://example.com/a.jpg")
        self.assertEqual(place.photo_credit, "홍길동 / Unsplash")

    def test_skips_row_with_empty_photo_url(self):
        place = Place.objects.create(name="아직못찾음")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_csv(tmp_dir, [[place.id, place.name, "", "", ""]])
            call_command("import_place_photos_manual", "--file", path)

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "")

    def test_skips_already_filled_place_by_default(self):
        place = Place.objects.create(name="명소", photo_url="https://example.com/old.jpg")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_csv(tmp_dir, [[place.id, place.name, "", "https://example.com/new.jpg", ""]])
            call_command("import_place_photos_manual", "--file", path)

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "https://example.com/old.jpg")

    def test_overwrite_replaces_existing_photo(self):
        place = Place.objects.create(name="명소", photo_url="https://example.com/old.jpg")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_csv(tmp_dir, [[place.id, place.name, "", "https://example.com/new.jpg", ""]])
            call_command("import_place_photos_manual", "--file", path, "--overwrite")

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "https://example.com/new.jpg")

    def test_dry_run_does_not_save(self):
        place = Place.objects.create(name="명소")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_csv(tmp_dir, [[place.id, place.name, "", "https://example.com/a.jpg", ""]])
            call_command("import_place_photos_manual", "--file", path, "--dry-run")

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "")

    def test_unknown_id_is_reported_and_others_still_processed(self):
        place = Place.objects.create(name="명소")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = self._write_csv(
                tmp_dir,
                [
                    [99999, "없는명소", "", "https://example.com/x.jpg", ""],
                    [place.id, place.name, "", "https://example.com/a.jpg", ""],
                ],
            )
            call_command("import_place_photos_manual", "--file", path)

        place.refresh_from_db()
        self.assertEqual(place.photo_url, "https://example.com/a.jpg")
