# 로컬 시드 데이터 안내

`places_seed.json`은 현재 개발 DB에 들어있는 **명소·작품 데이터를 그대로 덤프한 파일**이다.
공공데이터 수집(`import_kcisa`, `import_gyeonggi_data_dream`)을 각자 돌리지 않아도
팀원이 로컬에서 같은 데이터를 볼 수 있게 하려고 만들었다.

담긴 것 (총 38,636건):

| 모델 | 건수 | 설명 |
|---|---|---|
| `places.Place` | 2,900 | 촬영 명소 |
| `places.PlaceSource` | 8,417 | 명소의 원본 출처(어느 공공데이터에서 왔는지) |
| `places.Work` | 1,505 | 영화/드라마 작품 (TMDB로 포스터·줄거리·방영일자 보강) |
| `places.PlaceWork` | 8,194 | 명소↔작품 연결 |
| `places.PlaceTranslation` | 11,600 | 명소 번역 (en·ja·zh-CN·zh-TW, 이름뿐이라 전부 승인됨) |
| `places.WorkTranslation` | 6,020 | 작품 번역 (en·ja·zh-CN·zh-TW; 설명 있는 작품 1,038개는 검수 대기) |
| `places.WorkSource` | 0 | 작품의 외부 API 고유번호(KMDB DOCID·TMDB id). 재수집 때 채워진다 |

리뷰·즐겨찾기·코스·회원 같은 사용자 생성 데이터는 들어있지 않다(현재 DB에도 없음).

`feature/be/db-reinforce`(2026-09)에서 데이터 정리: 고아 작품 1,544건 삭제, 표기 차이
중복 작품 98건 병합, 명소 중복 7건 병합, TMDB가 잘못 넣은 드라마 감독 695건 제거.
`feature/be/multi-language-content`에서 4개 언어 번역(`translate_content` 명령).
자세한 내용은 `docs/place-work-audit.md`.

## 적재 시 주의 — 번역 시그널 끊기

`loaddata`는 명소·작품 생성마다 `post_save`로 번역 API를 부른다(약 4,400회, 유료).
시드에 번역이 이미 들어 있으므로 시그널을 끊고 로드한다:

```bash
PYTHONUTF8=1 python manage.py shell -c "from django.db.models.signals import post_save; from places import signals; from places.models import Place, Work; post_save.disconnect(signals._translate_new_place, sender=Place); post_save.disconnect(signals._translate_new_work, sender=Work); from django.core.management import call_command; call_command('loaddata', 'places_seed')"
```

## 불러오기

DB 컨테이너가 떠 있고 마이그레이션이 끝난 상태에서:

```bash
# Windows PowerShell
$env:PYTHONUTF8=1; python manage.py loaddata places_seed

# macOS / Linux
PYTHONUTF8=1 python manage.py loaddata places_seed
```

- `PYTHONUTF8=1`은 한글이 깨지지 않게 하는 옵션이다. 빼먹으면 Windows에서 인코딩 에러가 난다.
- `loaddata`는 PK 기준으로 덮어쓰기(있으면 갱신, 없으면 추가)라서 여러 번 돌려도 안전하다.

## 다시 만들기 (데이터가 바뀌었을 때)

```bash
# macOS / Linux
PYTHONUTF8=1 python manage.py dumpdata places -e places.searchhistory --indent 2 -o places/fixtures/places_seed.json
```

`searchhistory`는 회원(Member)에 딸린 검색 기록이라 뺀다 — 회원 데이터는 이 파일에 없다.
