from django.core.management.base import BaseCommand, CommandError

from places.services import link_place_to_work, media_type_to_category, save_place_from_source, to_decimal
from places.sources import kcisa_csv


class Command(BaseCommand):
    """한국문화정보원 CSV 파일에서 미디어콘텐츠 영상 촬영지 목록을 가져와 채운다.

    영업시간(business_hours)은 공공데이터로 들어있지만, Place.business_hours는 원래
    관리자가 직접 채우는 값으로 설계됐다 (models.py 참고). 그래서 명소를 새로 만들 때만
    시작값으로 채우고, 그 뒤로는(재수집이든 100m 거리 병합이든) 절대 건드리지 않는다 —
    관리자가 나중에 고친 값을 지키기 위해서다. 장소설명은 아예 가져오지 않는다 — 이건
    처음부터 끝까지 관리자가 채우는 값이다.

    미디어타입이 drama/movie인 행만 가져온다. 우리 서비스는 영화·드라마 촬영지라서
    show(예능)·artist(뮤직비디오) 행은 명소 자체를 만들지 않는다. 경복궁처럼 예능과
    드라마 양쪽에 나오는 장소는 드라마 행이 만들어주므로 목록에서 빠지지 않는다.
    가져온 drama/movie 행은 그 자리에서 작품(Work)을 찾거나 만들어 PlaceWork로 잇는다.
    """

    help = "한국문화정보원 CSV 파일에서 촬영지 목록을 가져와 Place를 만들거나 갱신한다."

    SOURCE_NAME = "KCISA"

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="한국문화정보원 CSV 파일 경로.")

    def handle(self, *args, **options):
        file_path = options["file"]
        try:
            rows = kcisa_csv.parse_filming_locations(file_path)
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {file_path}")

        created_count = 0
        updated_count = 0
        merged_count = 0
        skipped_no_id_count = 0
        skipped_not_media_count = 0
        coord_failed_count = 0
        work_linked_count = 0

        for row in rows:
            # 영화·드라마 촬영지만 가져온다. 예능·뮤직비디오 행은 명소 자체를 만들지 않는다.
            if media_type_to_category(row.get("media_type")) is None:
                skipped_not_media_count += 1
                continue

            # 연번이 재다운로드할 때마다 안정적으로 유지되는지는 확인되지 않았지만,
            # 지금 쓸 수 있는 유일한 식별자다.
            source_id = (row.get("sequence_no") or "").strip()
            if not source_id:
                skipped_no_id_count += 1
                continue

            latitude, lat_ok = to_decimal(row.get("latitude"))
            longitude, lng_ok = to_decimal(row.get("longitude"))
            if not lat_ok or not lng_ok:
                coord_failed_count += 1

            place, created, matched_by = save_place_from_source(
                source=self.SOURCE_NAME,
                source_id=source_id,
                name=row.get("place_name") or "",
                address=row.get("address") or "",
                latitude=latitude,
                longitude=longitude,
                create_only_fields={"business_hours": row.get("business_hours") or ""},
            )
            if created:
                created_count += 1
            elif matched_by == "distance":
                merged_count += 1
            else:
                updated_count += 1

            # matched_by가 무엇이든(새로 만듦/거리 병합/갱신) 그 명소를 작품에 잇는다.
            _, linked = link_place_to_work(
                place, title=row.get("title"), media_type=row.get("media_type")
            )
            if linked:
                work_linked_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 새로 만듦 {created_count}건, 갱신 {updated_count}건, "
                f"좌표 100m 이내 기존 명소와 병합 {merged_count}건, "
                f"작품 연결 {work_linked_count}건, "
                f"영화·드라마 아니라 건너뜀 {skipped_not_media_count}건, "
                f"연번 없어서 건너뜀 {skipped_no_id_count}건, "
                f"좌표 파싱 실패 {coord_failed_count}건"
            )
        )
