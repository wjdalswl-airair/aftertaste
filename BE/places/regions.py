"""주소에서 시/도(17개 광역) 이름을 뽑는다 (이슈 #75 지역별 Top10의 선행 작업).

공공데이터마다 주소 표기가 달라서(예: "경기 파주시", "경기도 파주시", "경기도고양시",
옛 이름 "강원도") 그대로 묶으면 같은 지역이 여러 개로 갈라진다.
그래서 항상 현재 공식 명칭 하나로 통일해서 돌려준다.
"""

# 공식 명칭 -> (정식/옛 명칭들, 약칭들)
_REGIONS = {
    "서울특별시": (("서울특별시",), ("서울",)),
    "부산광역시": (("부산광역시",), ("부산",)),
    "대구광역시": (("대구광역시",), ("대구",)),
    "인천광역시": (("인천광역시",), ("인천",)),
    "광주광역시": (("광주광역시",), ("광주",)),
    "대전광역시": (("대전광역시",), ("대전",)),
    "울산광역시": (("울산광역시",), ("울산",)),
    "세종특별자치시": (("세종특별자치시",), ("세종",)),
    "경기도": (("경기도",), ("경기",)),
    "강원특별자치도": (("강원특별자치도", "강원도"), ("강원",)),
    "충청북도": (("충청북도",), ("충북",)),
    "충청남도": (("충청남도",), ("충남",)),
    "전북특별자치도": (("전북특별자치도", "전라북도"), ("전북",)),
    "전라남도": (("전라남도",), ("전남",)),
    "경상북도": (("경상북도",), ("경북",)),
    "경상남도": (("경상남도",), ("경남",)),
    "제주특별자치도": (("제주특별자치도", "제주도"), ("제주",)),
}

# 첫 단어가 이 이름과 "똑같을 때만" 인정한다.
# 약칭은 앞부분만 비교하면 "광주시"(경기도)를 광주광역시로 잘못 잡기 때문이다.
_EXACT_NAMES = {}
# 정식/옛 명칭은 "경기도고양시"처럼 뒤에 붙어 있어도 앞부분이 같으면 인정한다.
_PREFIX_NAMES = []
for _official, (_full_names, _short_names) in _REGIONS.items():
    for _name in _full_names:
        _EXACT_NAMES[_name] = _official
        _PREFIX_NAMES.append((_name, _official))
    for _name in _short_names:
        _EXACT_NAMES[_name] = _official
# 긴 이름부터 비교한다(예: "강원특별자치도"가 "강원도"보다 먼저).
_PREFIX_NAMES.sort(key=lambda pair: len(pair[0]), reverse=True)


def extract_region(address):
    """주소 앞부분에서 시/도 공식 명칭을 돌려준다. 못 찾으면 빈 문자열."""
    words = (address or "").split()
    if not words:
        return ""
    first_word = words[0]

    if first_word in _EXACT_NAMES:
        return _EXACT_NAMES[first_word]
    for name, official in _PREFIX_NAMES:
        if first_word.startswith(name):
            return official
    return ""
