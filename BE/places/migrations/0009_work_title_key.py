"""Work에 title_key(제목 비교용 키)를 넣고, 표기만 다른 중복 작품을 하나로 합친다.

지금까지 작품 동일성은 "공백만 정리한 제목"으로 판정해서, 촬영지·영화 데이터를 다시
수집할 때 같은 작품이 띄어쓰기·구두점 차이로 여러 개 생겼다
(예: "여름 향기" / "여름향기", "위대한 유혹자" / "위대한유혹자").

이 마이그레이션은:
  1. title_key 컬럼 추가 (services.normalize_work_title = 괄호·구두점·공백 제거 + 소문자)
  2. 기존 작품의 title_key를 채우고, (title_key, category)가 같은 그룹을 하나로 병합
     - 정본: 연결된 촬영지(PlaceWork)가 가장 많은 작품, 같으면 id가 낮은 작품
     - 중복 작품의 PlaceWork·WorkTranslation을 정본으로 옮기고(이미 있으면 버림) 중복 작품 삭제

(title_key, category) 유일 제약은 0010에서 건다 — 같은 트랜잭션에서 행을 지운 뒤 제약을
추가하면 Postgres가 "pending trigger events" 오류를 내므로 마이그레이션을 나눈다.
"""

from collections import defaultdict

from django.db import migrations, models

# services.normalize_work_title와 같은 규칙. 마이그레이션은 과거 시점에 고정돼야 하므로 값을 복제해 둔다.
_NOISE_CHARS = set(" \t　()[]{}<>「」『』:;,.·・…!?\"'`~-–—/\\")


def _title_key(title):
    return "".join(ch for ch in (title or "").casefold() if ch not in _NOISE_CHARS)


def populate_and_merge(apps, schema_editor):
    Work = apps.get_model("places", "Work")
    PlaceWork = apps.get_model("places", "PlaceWork")
    WorkTranslation = apps.get_model("places", "WorkTranslation")

    groups = defaultdict(list)
    works = list(Work.objects.all())
    for work in works:
        work.title_key = _title_key(work.title)
        groups[(work.category, work.title_key)].append(work)
    Work.objects.bulk_update(works, ["title_key"], batch_size=500)

    link_count = defaultdict(int)
    for work_id in PlaceWork.objects.values_list("work_id", flat=True):
        link_count[work_id] += 1

    merged = 0
    for (category, key), group in groups.items():
        if not key or len(group) < 2:
            continue
        group.sort(key=lambda w: (-link_count[w.id], w.id))
        canonical, *dups = group
        canonical_places = set(
            PlaceWork.objects.filter(work=canonical).values_list("place_id", flat=True)
        )
        canonical_langs = set(
            WorkTranslation.objects.filter(work=canonical).values_list("language", flat=True)
        )
        for dup in dups:
            for pw in PlaceWork.objects.filter(work=dup):
                if pw.place_id in canonical_places:
                    pw.delete()
                else:
                    pw.work = canonical
                    pw.save(update_fields=["work"])
                    canonical_places.add(pw.place_id)
            for wt in WorkTranslation.objects.filter(work=dup):
                if wt.language in canonical_langs:
                    wt.delete()
                else:
                    wt.work = canonical
                    wt.save(update_fields=["work"])
                    canonical_langs.add(wt.language)
            dup.delete()
            merged += 1

    if merged:
        print(f"  병합한 중복 작품 {merged}건")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("places", "0008_alter_placetranslation_language_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="work",
            name="title_key",
            field=models.CharField(default="", editable=False, max_length=200),
            preserve_default=False,
        ),
        migrations.RunPython(populate_and_merge, noop),
    ]
