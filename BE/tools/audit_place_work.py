"""명소·작품·연결 데이터의 기계적 점검 스크립트 (웹 확인 불필요).

무엇을 찾나:
  1. 좌표 이상   - 한국 범위 밖이거나 비어 있는 명소
  2. 작품 중복   - 표기만 다르고 사실상 같은 작품 (구두점·공백 무시하면 제목이 같음)
  3. 명소 중복   - 같은 이름이 여러 Place로 쪼개진 것
  4. TMDB 오보강 의심 - 감독 값이 한국 작품답지 않은 것(로마자·한자 한 단어 등)
  5. 예능/MV 누수 - 영화·드라마가 아닌 제목이 작품으로 들어온 것
  6. 고아 행     - 촬영지가 하나도 안 붙은 작품

실행: BE 디렉터리에서
  PYTHONUTF8=1 .venv/Scripts/python.exe manage.py shell -c "import tools.audit_place_work as a; a.run()"
또는
  PYTHONUTF8=1 .venv/Scripts/python.exe -m tools.audit_place_work   (django.setup 포함)
"""

import math
import os
import re
import sys


def _bootstrap_django():
    """manage.py shell 밖에서 직접 실행할 때 Django를 초기화한다."""
    import django

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


# 한국 육지·근해를 넉넉하게 감싼 사각형. 이 밖이면 좌표가 잘못됐을 가능성이 높다.
KOREA_LAT_MIN, KOREA_LAT_MAX = 32.5, 39.5
KOREA_LNG_MIN, KOREA_LNG_MAX = 124.0, 132.5

# 제목 비교용: 괄호·구두점·공백을 모두 지우고 소문자로. (work_enrichment.normalize_title_for_match와 같은 취지)
_TITLE_NOISE = set(" \t　()[]{}<>「」『』:;,.·・…!?\"'`~-–—/\\")


def norm_title(title):
    return "".join(ch for ch in (title or "").casefold() if ch not in _TITLE_NOISE)


# 감독 필드가 이런 모양이면 사람 이름(특히 한국 감독)이 아닐 가능성이 크다.
_LATIN_ONLY = re.compile(r"^[A-Za-z][A-Za-z.\-]*$")          # "Llama", "Chang" 처럼 로마자 한 단어
_HAS_HANZA = re.compile(r"[一-鿿]")                   # 桐华, 青木琴美 처럼 한자
_YEAR_IN_TITLE = re.compile(r"(19|20)\d{2}")

# 예능·뮤직비디오·다큐로 의심되는 제목 신호 (KCISA media_type 필터가 놓친 경우)
_VARIETY_HINTS = ("예능", "뮤직비디오", "M/V", "MV", "콘서트", "라이브", "다큐", "메이킹")


def _print_section(title, rows, columns):
    print(f"\n{'=' * 70}\n{title}  ({len(rows)}건)\n{'=' * 70}")
    if not rows:
        print("  (없음)")
        return
    print("  " + " | ".join(columns))
    for row in rows:
        print("  " + " | ".join(str(c) for c in row))


def check_coordinates(Place):
    bad = []
    for p in Place.objects.all().only("id", "name", "latitude", "longitude"):
        if p.latitude is None or p.longitude is None:
            bad.append((p.id, p.name, "NULL", "NULL"))
            continue
        lat, lng = float(p.latitude), float(p.longitude)
        if not (KOREA_LAT_MIN <= lat <= KOREA_LAT_MAX and KOREA_LNG_MIN <= lng <= KOREA_LNG_MAX):
            bad.append((p.id, p.name, lat, lng))
    _print_section("1. 좌표 이상 (한국 범위 밖 / 비어 있음)", bad, ["id", "name", "lat", "lng"])
    return bad


def check_duplicate_works(Work, PlaceWork):
    from collections import defaultdict

    from django.db.models import Count

    groups = defaultdict(list)
    for w in Work.objects.all().only("id", "title", "category"):
        groups[(w.category, norm_title(w.title))].append(w)

    link_count = {
        row["work"]: row["n"]
        for row in PlaceWork.objects.values("work").annotate(n=Count("id"))
    }

    dup = []
    for (category, key), works in sorted(groups.items()):
        if len(works) < 2 or not key:
            continue
        detail = ", ".join(f'#{w.id}"{w.title}"({link_count.get(w.id, 0)}곳)' for w in works)
        dup.append((category, key, detail))
    _print_section("2. 작품 중복 (구두점·공백 무시하면 같은 제목)", dup, ["category", "norm_key", "works(연결 촬영지 수)"])
    return dup


def check_duplicate_places(Place):
    from collections import defaultdict

    groups = defaultdict(list)
    for p in Place.objects.all().only("id", "name", "address", "latitude", "longitude"):
        groups[p.name.strip()].append(p)

    dup = []
    for name, places in sorted(groups.items()):
        if len(places) < 2:
            continue
        coords = "; ".join(
            f"#{p.id}({float(p.latitude):.4f},{float(p.longitude):.4f})" if p.latitude is not None else f"#{p.id}(NULL)"
            for p in places
        )
        dup.append((name, len(places), coords))
    _print_section("3. 명소 중복 (같은 이름이 여러 Place)", dup, ["name", "count", "ids(좌표)"])
    return dup


def _distance_m(a, b):
    if None in (a.latitude, a.longitude, b.latitude, b.longitude):
        return None
    R = 6371000
    la1, lo1, la2, lo2 = (math.radians(float(v)) for v in (a.latitude, a.longitude, b.latitude, b.longitude))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def check_same_address_far_coords(Place, threshold_m=150):
    """주소는 같은데 좌표가 멀리 떨어진 Place 쌍. 좌표가 잘못됐거나, 100m 매칭이 놓친 중복."""
    from collections import defaultdict

    groups = defaultdict(list)
    for p in Place.objects.exclude(address="").only("id", "name", "address", "latitude", "longitude"):
        groups[" ".join(p.address.split())].append(p)

    rows = []
    for addr, places in groups.items():
        if len(places) < 2:
            continue
        for i in range(len(places)):
            for j in range(i + 1, len(places)):
                d = _distance_m(places[i], places[j])
                if d is None or d > threshold_m:
                    rows.append((f"#{places[i].id} {places[i].name}", f"#{places[j].id} {places[j].name}",
                                 "NULL" if d is None else round(d), addr[:40]))
    _print_section(f"7. 같은 주소인데 좌표가 {threshold_m}m 넘게 떨어진 Place 쌍", rows,
                   ["a", "b", "거리(m)", "address"])
    return rows


def check_tmdb_enrichment(Work):
    suspect = []
    for w in Work.objects.exclude(director="").only("id", "title", "category", "director", "release_date"):
        d = w.director.strip()
        reasons = []
        # 감독이 여러 명이면 ", "로 이어지므로, 한 명일 때만 의심
        if "," not in d:
            if _LATIN_ONLY.match(d) and len(d) <= 12:
                reasons.append("로마자 한 단어")
            if _HAS_HANZA.search(d):
                reasons.append("한자 포함")
        # 제목에 연도가 있는데 방영일 연도와 다르면 의심
        m = _YEAR_IN_TITLE.search(w.title)
        if m and w.release_date and str(w.release_date.year) != m.group(0):
            reasons.append(f"제목연도 {m.group(0)} ≠ 방영 {w.release_date.year}")
        if reasons:
            suspect.append((w.id, w.category, w.title, d, str(w.release_date or ""), " / ".join(reasons)))
    _print_section("4. TMDB 오보강 의심 (감독 값이 한국 작품답지 않음)", suspect,
                   ["id", "cat", "title", "director", "release", "이유"])
    return suspect


def check_variety_leak(Work, PlaceWork):
    hits = []
    linked_ids = set(PlaceWork.objects.values_list("work", flat=True))
    for w in Work.objects.only("id", "title", "category"):
        if any(h.lower() in w.title.lower() for h in _VARIETY_HINTS):
            hits.append((w.id, w.category, w.title, "촬영지연결" if w.id in linked_ids else "-"))
    _print_section("5. 예능/MV 누수 의심 (제목 신호)", hits, ["id", "cat", "title", "연결"])
    return hits


def check_orphans(Work, PlaceWork):
    linked_ids = set(PlaceWork.objects.values_list("work", flat=True))
    orphan = [
        (w.id, w.category, w.title)
        for w in Work.objects.only("id", "title", "category")
        if w.id not in linked_ids
    ]
    _print_section("6. 고아 작품 (연결된 촬영지 0)", orphan[:100], ["id", "cat", "title"])
    if len(orphan) > 100:
        print(f"  ... 외 {len(orphan) - 100}건")
    return orphan


def top_linked_works(Work, PlaceWork, n=30):
    from django.db.models import Count

    rows = (
        PlaceWork.objects.values("work__id", "work__title", "work__category")
        .annotate(n=Count("id")).order_by("-n")[:n]
    )
    data = [(r["work__id"], r["work__category"], r["work__title"], r["n"]) for r in rows]
    _print_section(f"참고: 연결 촬영지 많은 작품 Top {n} (웹 표본조사 우선 대상)", data,
                   ["id", "cat", "title", "촬영지수"])
    return data


def run():
    from places.models import Place, PlaceWork, Work

    print(f"\nPlace {Place.objects.count()} / Work {Work.objects.count()} / PlaceWork {PlaceWork.objects.count()}")

    results = {
        "bad_coords": check_coordinates(Place),
        "dup_works": check_duplicate_works(Work, PlaceWork),
        "dup_places": check_duplicate_places(Place),
        "same_addr_far": check_same_address_far_coords(Place),
        "tmdb_suspect": check_tmdb_enrichment(Work),
        "variety_leak": check_variety_leak(Work, PlaceWork),
        "orphans": check_orphans(Work, PlaceWork),
    }
    top_linked_works(Work, PlaceWork)

    print(f"\n{'=' * 70}\n요약\n{'=' * 70}")
    for key, rows in results.items():
        print(f"  {key}: {len(rows)}건")
    return results


if __name__ == "__main__":
    _bootstrap_django()
    run()
