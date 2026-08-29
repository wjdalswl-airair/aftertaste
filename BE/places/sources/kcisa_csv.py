"""한국문화정보원 CSV 파일 파싱 — "미디어콘텐츠 영상 촬영지" 데이터.

API가 아니라 CSV 파일로만 받을 수 있다 (행정/공공기관만 API 사용 가능, 2026-08-17 확인).
파일은 CP949(EUC-KR 계열)로 인코딩돼 있다 — UTF-8로 읽으면 깨진다.
컬럼: 연번, 미디어타입, 제목, 장소명, 장소타입, 장소설명, 영업시간, 브레이크타임,
휴무일, 주소, 위도, 경도, 전화번호, 최종작성일 (docs/DETAIL_SPEC.md 7장 #1 참고).
"""

import csv

_ENCODING = "cp949"


def parse_filming_locations(file_path):
    """CSV 파일을 읽어서 한 줄당 하나의 dict로 돌려준다. 값 정제는 하지 않고 원본 그대로 담는다."""
    with open(file_path, encoding=_ENCODING, newline="") as f:
        reader = csv.DictReader(f)
        return [
            {
                "sequence_no": row.get("연번"),
                "media_type": row.get("미디어타입"),
                "title": row.get("제목"),
                "place_name": row.get("장소명"),
                "place_type": row.get("장소타입"),
                "description": row.get("장소설명"),
                "business_hours": row.get("영업시간"),
                "break_time": row.get("브레이크타임"),
                "closed_days": row.get("휴무일"),
                "address": row.get("주소"),
                "latitude": row.get("위도"),
                "longitude": row.get("경도"),
                "phone": row.get("전화번호"),
                "last_updated": row.get("최종작성일"),
            }
            for row in reader
        ]
