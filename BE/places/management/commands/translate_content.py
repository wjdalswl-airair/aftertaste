"""명소·작품을 지원 언어(en·ja·zh-CN·zh-TW)로 번역해 PlaceTranslation·WorkTranslation에 채운다.

과거에 유효한 Google Translate 키 없이 돌려 번역이 전부 실패(status=FAILED)로 남아 있어서,
전수 재번역이 필요할 때 쓴다. 중간에 끊겨도 다시 실행하면 이미 성공한 것은 건너뛴다.

예)
  python manage.py translate_content                      # 전체 언어·모델, 성공한 것 건너뜀
  python manage.py translate_content --language ja        # 일본어만
  python manage.py translate_content --model work         # 작품만
  python manage.py translate_content --overwrite          # 성공한 것도 다시 번역
  python manage.py translate_content --limit 20 --sleep 0.2
"""

import time

from django.core.management.base import BaseCommand

from places.models import Place, PlaceTranslation, TranslationStatus, Work, WorkTranslation
from places.translation import SUPPORTED_LANGUAGES, translate_place, translate_work


class Command(BaseCommand):
    help = "명소·작품을 지원 언어로 번역한다 (실패분 재시도, 중단 후 재개 가능)."

    def add_arguments(self, parser):
        parser.add_argument("--language", choices=SUPPORTED_LANGUAGES, help="이 언어만 (기본: 전체).")
        parser.add_argument("--model", choices=["place", "work"], help="이 모델만 (기본: 둘 다).")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="이미 성공(SUCCESS)한 번역도 다시 번역한다 (기본: 건너뜀).",
        )
        parser.add_argument("--limit", type=int, help="모델·언어별 최대 이 개수만 처리한다.")
        parser.add_argument(
            "--sleep", type=float, default=0.1, help="한 건 처리 후 쉬는 초 (기본 0.1)."
        )

    def handle(self, *args, **options):
        languages = [options["language"]] if options["language"] else SUPPORTED_LANGUAGES
        models = [options["model"]] if options["model"] else ["place", "work"]
        overwrite = options["overwrite"]
        limit = options["limit"]
        sleep_seconds = options["sleep"]

        for model_name in models:
            for language in languages:
                self._run_one(model_name, language, overwrite, limit, sleep_seconds)

    def _run_one(self, model_name, language, overwrite, limit, sleep_seconds):
        if model_name == "place":
            model, trans_model, trans_fk, translate = Place, PlaceTranslation, "place", translate_place
        else:
            model, trans_model, trans_fk, translate = Work, WorkTranslation, "work", translate_work

        objects = model.objects.all().order_by("id")
        if not overwrite:
            done_ids = trans_model.objects.filter(
                language=language, status=TranslationStatus.SUCCESS
            ).values_list(f"{trans_fk}_id", flat=True)
            objects = objects.exclude(id__in=done_ids)
        if limit:
            objects = objects[:limit]

        total = objects.count()
        self.stdout.write(f"[{model_name} / {language}] 대상 {total}건")

        ok = failed = 0
        for index, obj in enumerate(objects.iterator(), start=1):
            try:
                result = translate(obj, language)
            except Exception as exc:  # 한 건 실패해도 계속
                failed += 1
                self.stderr.write(f"  [{obj.id}] 오류: {exc}")
            else:
                if result.status == TranslationStatus.SUCCESS:
                    ok += 1
                else:
                    failed += 1
            if index % 200 == 0:
                self.stdout.write(f"  ...{index}/{total} (성공 {ok} / 실패 {failed})")
            if sleep_seconds:
                time.sleep(sleep_seconds)

        self.stdout.write(
            self.style.SUCCESS(f"[{model_name} / {language}] 완료 — 성공 {ok} / 실패 {failed}")
        )
