from django.core.management.base import BaseCommand

from places.services import (
    build_composite_source_id,
    gyeonggi_div_to_category,
    link_place_to_work,
    save_place_from_source,
    to_decimal,
)
from places.sources import gyeonggi_data_dream, kakao_geocoding


class Command(BaseCommand):
    """경기 데이터 드림 "촬영지원 현황" API에서 명소 목록을 가져와 채운다.

    이 데이터셋에는 고유번호가 없다 (시군명·촬영연도·촬영구분명·작품명·촬영장소명만 제공).
    그래서 이 다섯 필드를 합친 문자열을 PlaceSource.source_id로 쓴다.
    좌표도 없어서, 촬영장소명을 카카오맵 키워드 검색으로 지오코딩해 좌표와 주소를 얻는다
    (docs/DETAIL_SPEC.md 7장 #1 참고).

    촬영구분명(POTOGRF_DIV_NM)이 영화·드라마로 분명한 행만 가져온다. 'TV'·'기타'나
    CF·MV·다큐 등은 명소 자체를 만들지 않는다 (gyeonggi_div_to_category, 6-1 #28).
    가져온 행은 작품명으로 Work를 찾거나 만들어 PlaceWork로 잇는다 — KCISA와 같은 방식.
    촬영연도는 방영연도가 아니라 "찍은 해"라서 저장하지 않는다.
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
        skipped_not_media_count = 0
        skipped_no_name_count = 0
        skipped_geocode_count = 0
        work_linked_count = 0
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

                # 영화·드라마로 분명한 촬영구분만 가져온다. 나머지는 지오코딩(카카오 호출)에
                # 들어가기 전에 걸러서 명소 자체를 만들지 않는다.
                category = gyeonggi_div_to_category(item.get("potogrf_div_nm"))
                if category is None:
                    skipped_not_media_count += 1
                    continue

                place_name = (item.get("potogrf_plc_nm") or "").strip()
                if not place_name:
                    skipped_no_name_count += 1
                    continue

                # 지오코딩 검색어에 시군명을 앞에 붙여 범위를 좁힌다. 다만 촬영장소명이
                # 이미 "파주시 ..."처럼 시군명으로 시작하는 경우가 많아(실데이터의 40% 이상),
                # 그대로 붙이면 "파주시 파주시 ..."가 되어 검색이 오히려 안 된다. 중복이면 붙이지 않는다.
                sigun = (item.get("sigun_nm") or "").strip()
                query = place_name if place_name.startswith(sigun) else f"{sigun} {place_name}".strip()
                candidates = kakao_geocoding.search_place(query, size=1)
                if not candidates:
                    skipped_geocode_count += 1
                    continue

                best_match = candidates[0]
                address = best_match.get("road_address_name") or best_match.get("address_name") or ""
                # 카카오 지오코딩이 준 좌표는 이미 float라 to_decimal이 실패할 일이 없다.
                # 그래서 다른 import 커맨드와 달리 성공여부(두 번째 반환값)는 확인하지 않는다.
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

                # 그 명소를 작품(Work)에 잇는다. 제목이 같으면 KCISA가 만든 Work와 합쳐진다.
                _, linked = link_place_to_work(
                    place, title=item.get("work_nm"), category=category
                )
                if linked:
                    work_linked_count += 1

            if fetched_count >= total_count:
                break
            page_index += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 새로 만듦 {created_count}건, 갱신 {updated_count}건, "
                f"좌표 100m 이내 기존 명소와 병합 {merged_count}건, "
                f"작품 연결 {work_linked_count}건, "
                f"영화·드라마 아니라 건너뜀 {skipped_not_media_count}건, "
                f"장소명 없어서 건너뜀 {skipped_no_name_count}건, "
                f"지오코딩 결과 없어서 건너뜀 {skipped_geocode_count}건 "
                f"(전체 {total_count}건 중 {fetched_count}건 조회)"
            )
        )
