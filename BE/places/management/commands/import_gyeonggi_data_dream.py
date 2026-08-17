from django.core.management.base import BaseCommand

from places.services import build_composite_source_id, save_place_from_source, to_decimal
from places.sources import gyeonggi_data_dream, kakao_geocoding


class Command(BaseCommand):
    """경기 데이터 드림 "촬영지원 현황" API에서 명소 목록을 가져와 채운다.

    이 데이터셋에는 고유번호가 없다 (시군명·촬영연도·촬영구분명·작품명·촬영장소명만 제공).
    그래서 이 다섯 필드를 합친 문자열을 PlaceSource.source_id로 쓴다.
    좌표도 없어서, 촬영장소명을 카카오맵 키워드 검색으로 지오코딩해 좌표와 주소를 얻는다
    (docs/DETAIL_SPEC.md 7장 #1 참고).
    """

    help = "경기 데이터 드림 API에서 촬영지원 현황 목록을 가져와 Place를 만들거나 갱신한다."

    SOURCE_NAME = "GYEONGGI_DATA_DREAM"

    def add_arguments(self, parser):
        parser.add_argument("--page-size", type=int, default=1000)
        parser.add_argument(
            "--max-pages",
            type=int,
            default=100,
            help="API가 이상 동작해서 끝없이 반복되는 걸 막는 안전장치.",
        )

    def handle(self, *args, **options):
        page_size = options["page_size"]
        max_pages = options["max_pages"]

        created_count = 0
        updated_count = 0
        merged_count = 0
        skipped_no_name_count = 0
        skipped_geocode_count = 0
        fetched_count = 0
        total_count = None
        page_index = 1

        while True:
            if page_index > max_pages:
                self.stderr.write(
                    self.style.WARNING(
                        f"페이지 상한({max_pages})에 도달해 중단합니다. "
                        f"지금까지 {fetched_count}건 처리 (전체 {total_count}건 중)."
                    )
                )
                break

            result = gyeonggi_data_dream.fetch_photography_support(page_index=page_index, page_size=page_size)
            if total_count is None:
                total_count = result["total_count"]

            items = result["items"]
            if not items:
                break

            for item in items:
                fetched_count += 1

                place_name = (item.get("potogrf_plc_nm") or "").strip()
                if not place_name:
                    skipped_no_name_count += 1
                    continue

                query = f"{item.get('sigun_nm') or ''} {place_name}".strip()
                candidates = kakao_geocoding.search_place(query, size=1)
                if not candidates:
                    skipped_geocode_count += 1
                    continue

                best_match = candidates[0]
                address = best_match.get("road_address_name") or best_match.get("address_name") or ""
                latitude, _ = to_decimal(best_match.get("latitude"))
                longitude, _ = to_decimal(best_match.get("longitude"))

                source_id = build_composite_source_id(
                    item.get("sigun_nm"),
                    item.get("potogrf_yy"),
                    item.get("potogrf_div_nm"),
                    item.get("work_nm"),
                    item.get("potogrf_plc_nm"),
                )
                place, created, matched_by = save_place_from_source(
                    source=self.SOURCE_NAME,
                    source_id=source_id,
                    name=place_name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                )
                if created:
                    created_count += 1
                elif matched_by == "distance":
                    merged_count += 1
                else:
                    updated_count += 1

            if fetched_count >= total_count:
                break
            page_index += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 새로 만듦 {created_count}건, 갱신 {updated_count}건, "
                f"좌표 100m 이내 기존 명소와 병합 {merged_count}건, "
                f"장소명 없어서 건너뜀 {skipped_no_name_count}건, "
                f"지오코딩 결과 없어서 건너뜀 {skipped_geocode_count}건 "
                f"(전체 {total_count}건 중 {fetched_count}건 조회)"
            )
        )
