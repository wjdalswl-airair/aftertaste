import json
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from places.models import Place, PlaceSource


class Command(BaseCommand):
    """로컬 JSON 파일에서 명소 목록을 가져와 채운다.

    같은 명소를 다시 가져와도 source + source_id로 이미 있는 PlaceSource를 찾아서
    그 명소의 이름/주소/위치만 갱신하고, 관리자가 채운 설명/사진/영업시간은 건드리지 않는다.

    실제로 어떤 공공데이터 API를 쓸지는 아직 안 정해졌다 (docs/DETAIL_SPEC.md 7장 #1 참고).
    한 API에서 필요한 정보를 다 못 가져와서 여러 API를 조합해야 하는 상황이라,
    API 호출 코드는 아직 만들지 않았다. 지금은 이미 내려받은 JSON 파일을 --file로
    넣는 방식만 지원한다. 실제 API가 정해지면 이 명령어에 호출 로직을 추가하면 된다.

    다른 출처가 같은 물리적 장소를 가리키는 경우(좌표 100m 이내)를 찾아서 하나로 합치는
    로직은 아직 없다 (docs/DETAIL_SPEC.md 7장 #1-(c) 참고). 지금은 source + source_id로만
    같은 명소인지 판단하므로, 처음 보는 출처는 항상 새 명소를 만든다.
    """

    help = "로컬 JSON 파일에서 촬영지 목록을 가져와 Place를 만들거나 갱신한다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="가져올 명소 목록이 담긴 로컬 JSON 파일 경로.",
        )
        parser.add_argument(
            "--source",
            required=True,
            help="이 데이터의 출처 이름 (예: KCISA_FILMING_LOCATION). Place.source에 저장된다.",
        )

    def handle(self, *args, **options):
        source_name = options["source"]
        items = self._load_from_file(options["file"])

        created_count = 0
        updated_count = 0
        skipped_count = 0
        coord_failed_count = 0

        for item in items:
            source_id = self._get_source_id(item)
            if not source_id:
                # 원본 번호가 없으면 나중에 같은 명소인지 구분할 수 없어서 건너뛴다.
                skipped_count += 1
                continue

            fields, coord_failed = self._parse_place_fields(item)
            if coord_failed:
                # 좌표가 숫자로 안 바뀌어도 명소 자체는 건너뛰지 않는다.
                # 이름/주소만이라도 저장하고, 실패 건수만 세어서 나중에 보여준다.
                coord_failed_count += 1

            place_source = PlaceSource.objects.select_related("place").filter(
                source=source_name, source_id=source_id
            ).first()

            if place_source is None:
                place = Place.objects.create(**fields)
                PlaceSource.objects.create(place=place, source=source_name, source_id=source_id)
                created_count += 1
            else:
                place = place_source.place
                # 공공데이터 쪽 정보(이름/주소/위치)만 최신값으로 갱신한다.
                # description, photo_url, business_hours는 관리자가 채운 값이라 그대로 둔다.
                # 새로 받은 값이 비어있으면(값이 없거나 좌표 파싱 실패) 기존 값을 지우지 않고 그대로 둔다.
                # 재수집 JSON에 일부 필드만 담겨 있을 수 있기 때문이다.
                for field_name, value in fields.items():
                    if value in (None, ""):
                        continue
                    setattr(place, field_name, value)
                place.save()
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"완료: 새로 만듦 {created_count}건, 갱신 {updated_count}건, "
                f"원본 번호 없어서 건너뜀 {skipped_count}건, "
                f"좌표 파싱 실패 {coord_failed_count}건"
            )
        )

    def _load_from_file(self, path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"JSON 형식이 올바르지 않습니다: {path} ({e})")

    def _get_source_id(self, item):
        # 어떤 API를 쓸지 아직 안 정해져서, 고유번호 필드명은 출처가 정해지면 맞춰야 한다.
        value = item.get("id") or item.get("고유번호")
        return str(value) if value else ""

    def _parse_place_fields(self, item):
        # 어떤 API를 쓸지 아직 안 정해져서, 필드명은 출처가 정해지면 맞춰야 한다.
        latitude, lat_ok = self._to_decimal(item.get("위도") or item.get("latitude"))
        longitude, lng_ok = self._to_decimal(item.get("경도") or item.get("longitude"))

        fields = {
            "name": item.get("장소명") or item.get("name") or "",
            "address": item.get("소재지") or item.get("address") or "",
            "latitude": latitude,
            "longitude": longitude,
        }
        # 값이 있었는데 숫자로 못 바꾼 경우에만 실패로 친다 (값이 아예 없는 건 실패가 아님).
        coord_failed = not lat_ok or not lng_ok
        return fields, coord_failed

    def _to_decimal(self, value):
        """값을 Decimal로 바꾼다. (바뀐 값, 성공 여부)를 돌려준다.

        값이 없으면(None/빈 문자열) 성공으로 치고 None을 돌려준다.
        "-", "정보없음"처럼 값은 있는데 숫자가 아니면 실패로 치고 None을 돌려준다.
        """
        if value is None or value == "":
            return None, True
        try:
            return Decimal(str(value)), True
        except InvalidOperation:
            return None, False
