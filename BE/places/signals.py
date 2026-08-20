"""명소·작품이 새로 만들어지면 자동으로 번역을 건다.

트리거 시점을 "새로 만들어질 때(post_save, created=True)"로 정했다. 이유:
- 관리자 화면(admin)뿐 아니라 관리 명령어(import 스크립트, 예: import_kcisa)로도
  Place/Work가 만들어진다. 두 경로가 공통으로 지나가는 지점이 모델 저장이라서, admin의
  save_model()만 오버라이드하는 방식보다 신호(signal)를 쓰는 쪽이 두 경로를 다 잡는다.
- "등록할 때"만 번역하고, 그 뒤에 관리자가 설명(description)을 채우는 등 내용을 고치는
  것까지 자동으로 다시 번역하지는 않는다. 이유는 두 가지: (1) DETAIL_SPEC이 실패 시
  "자동 재시도 없음, 관리자가 수동으로 다시 번역"이라 명시하고 있어서, 내용이 바뀔 때마다
  자동으로 다시 부르면 이 규칙과 어긋난다. (2) 관리자가 business_hours 같은 번역과 무관한
  필드만 고쳐도 저장할 때마다 번역 API를 부르게 되면 비용이 계속 나간다.
  대신 admin에 "다시 번역" 액션(places/admin.py)을 만들어서, 등록 후 설명을 채웠거나
  번역이 실패했을 때 관리자가 직접 다시 걸 수 있게 한다.

번역은 외부 API를 부르는 느린 작업이라, DB 트랜잭션이 실제로 끝난 뒤에 실행되도록
transaction.on_commit으로 미룬다. (예: import 스크립트의 100m 거리매칭 새 명소 생성은
transaction.atomic() 블록 안에서 일어나는데, 그 블록이 롤백될 수도 있으므로 커밋 전에
번역부터 실행하면 만들어지지도 않을 명소를 번역하는 상황이 생길 수 있다.)
"""

import logging

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from places.models import Place, Work
from places.translation import translate_place_all_languages, translate_work_all_languages

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Place)
def _translate_new_place(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: translate_place_all_languages(instance))


@receiver(post_save, sender=Work)
def _translate_new_work(sender, instance, created, **kwargs):
    if not created:
        return
    transaction.on_commit(lambda: translate_work_all_languages(instance))
