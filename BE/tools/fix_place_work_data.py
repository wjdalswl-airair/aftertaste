"""감사(tools/audit_place_work.py + docs/place-work-audit*.md)에서 확정된 데이터 오류를 고친다.

일회성 정리 스크립트다. 로컬 DB에서 한 번 실행하고, 그 결과를 시드로 덤프한다.
여러 번 실행해도 안전하도록(idempotent) 만들었다.

실행: BE 디렉터리에서
  PYTHONUTF8=1 .venv/Scripts/python.exe manage.py shell -c "import tools.fix_place_work_data as f; f.run()"

하는 일:
  1. 고아 작품 삭제  - 연결된 촬영지가 하나도 없는 Work (전부 2026-09 갱신 때 import_kmdb로
     들어온 촬영지 없는 영화 카탈로그: 성인물·외국 공연실황·교육용 단편 등)
  2. 명소 중복 병합  - 라베니체 마치에비뉴(좌표 조작 7건), 철도박물관(KCISA 좌표 오류)
  3. TMDB 감독 오염 제거 - TMDB 보강 드라마의 director 비우기. TMDB의 created_by(TV 제작자)를
     감독으로 넣는데 한국 드라마는 여기에 작가(극본)가 들어와서 대부분 틀림 (영화는 정상이라 유지)
"""

import os
import sys


def _bootstrap_django():
    import django

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


def delete_orphan_works():
    from places.models import PlaceWork, Work

    linked = set(PlaceWork.objects.values_list("work_id", flat=True))
    orphans = Work.objects.exclude(id__in=linked)
    count = orphans.count()
    orphans.delete()  # WorkTranslation은 CASCADE로 함께 삭제됨
    print(f"1. 고아 작품 삭제: {count}건")


def _merge_places(canonical_id, duplicate_ids, *, coords=None):
    """duplicate_ids의 Place를 canonical_id로 합친다. PlaceSource·PlaceWork·PlaceTranslation 이전.

    coords=(lat, lng)를 주면 정본 좌표를 그 값으로 맞춘다.
    """
    from places.models import Place, PlaceSource, PlaceTranslation, PlaceWork

    duplicate_ids = [i for i in duplicate_ids if i != canonical_id and Place.objects.filter(id=i).exists()]
    if not Place.objects.filter(id=canonical_id).exists():
        print(f"   (정본 #{canonical_id} 없음 — 건너뜀)")
        return 0

    canonical = Place.objects.get(id=canonical_id)
    existing_src = set(PlaceSource.objects.filter(place=canonical).values_list("source", "source_id"))
    existing_work = set(PlaceWork.objects.filter(place=canonical).values_list("work_id", flat=True))
    existing_lang = set(PlaceTranslation.objects.filter(place=canonical).values_list("language", flat=True))

    for dup_id in duplicate_ids:
        for src in PlaceSource.objects.filter(place_id=dup_id):
            if (src.source, src.source_id) in existing_src:
                src.delete()
            else:
                src.place = canonical
                src.save(update_fields=["place"])
                existing_src.add((src.source, src.source_id))
        for pw in PlaceWork.objects.filter(place_id=dup_id):
            if pw.work_id in existing_work:
                pw.delete()
            else:
                pw.place = canonical
                pw.save(update_fields=["place"])
                existing_work.add(pw.work_id)
        for pt in PlaceTranslation.objects.filter(place_id=dup_id):
            if pt.language in existing_lang:
                pt.delete()
            else:
                pt.place = canonical
                pt.save(update_fields=["place"])
                existing_lang.add(pt.language)
        Place.objects.filter(id=dup_id).delete()

    if coords:
        canonical.latitude, canonical.longitude = coords
        canonical.save(update_fields=["latitude", "longitude"])
    return len(duplicate_ids)


def merge_duplicate_places():
    from places.models import Place

    merged = 0
    # 라베니체 마치에비뉴 — 좌표가 base(37.640646, 126.678802)에 +1~+6 더한 값으로 조작됨.
    # 주소는 전부 "경기도 김포시 김포한강4로 12". 정본 #1592(base 좌표, 실제 위치와 일치)로 통합.
    laveniche = list(
        Place.objects.filter(name="라베니체 마치에비뉴").order_by("id").values_list("id", flat=True)
    )
    if 1592 in laveniche and len(laveniche) > 1:
        merged += _merge_places(1592, laveniche, coords=(37.640646, 126.678802))

    # 철도박물관 — #1712(KCISA)의 좌표가 20km 어긋남. #2725(경기데이터드림)가 의왕 실제 위치.
    # 주소 동일("의왕시 철도박물관로 142"). 정본은 #1712로 두되 좌표를 #2725 값으로 교정.
    if Place.objects.filter(id=1712).exists() and Place.objects.filter(id=2725).exists():
        right = Place.objects.get(id=2725)
        merged += _merge_places(1712, [2725], coords=(right.latitude, right.longitude))

    print(f"2. 명소 중복 병합: {merged}건 (라베니체 + 철도박물관)")


# director 값에 이런 말이 들어 있으면 사람이 아니라 제작사·기획사다 (TMDB created_by 오염).
_COMPANY_MARKERS = ("스튜디오", "ENM", "미디어", "픽쳐스", "픽처스", "이엔티", "엔터", "컴퍼니",
                    "프로덕션", "필름", "Studio", "Media", "Pictures", "Entertainment")


def clear_polluted_drama_directors():
    from django.db.models import Q

    from places.models import Work

    company_q = Q()
    for marker in _COMPANY_MARKERS:
        company_q |= Q(director__icontains=marker)

    polluted = (
        Work.objects.filter(category=Work.Category.DRAMA)
        .filter(Q(poster_url__icontains="image.tmdb.org") | company_q)
        .exclude(director="")
    )
    count = polluted.count()
    polluted.update(director="")
    print(f"3. TMDB 보강 드라마 director 비우기: {count}건")


def run():
    from django.db import transaction

    with transaction.atomic():
        delete_orphan_works()
        merge_duplicate_places()
        clear_polluted_drama_directors()
    print("완료.")


if __name__ == "__main__":
    _bootstrap_django()
    run()
