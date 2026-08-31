# Phase 8 — 코스

## 목표

**명소와 엮인 코스를 보고, 로그인한 사용자는 직접 만들고 저장하고 공유할 수 있다.**

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 코스 상세 화면 | S-08 |
| 코스 생성 화면 | S-08 |
| 코스 저장(즐겨찾기) | S-08 |
| 코스 상세 공유(링크 복사) | S-09 |
| 명소 상세 → 코스 진입 연결 | S-08 |

> (2026-08-31 변경) 원래 "코스 생성 UI는 안 만든다"였으나, 사용자가 이번 Phase에 포함하기로 결정했다 (`docs/PRD.md` 5장 참고, Figma 목업 있음·BE 생성 API 이미 구현됨). "코스 상세 공유"도 원래 Phase9였으나 같이 당겨왔다 — Phase9는 "명소 상세 공유"(이미 Phase4에서 구현 완료된 상태였음)만 확인하는 정도로 남는다.
>
> "코스 AI 추천"(BE가 알아서 코스를 만들어주는 것)은 여전히 범위 밖이다. 이번에 만드는 건 **사용자가 직접** 맛집·카페·주변 명소를 골라 코스를 구성하는 화면이다.

## 하는 일

### 1. 코스 상세

- `GET /api/places/{place_id}/courses/`(명소 기준 코스 목록, 확정)로 명소 상세(Phase4)에서 코스로 진입한다.
- `GET /api/courses/{course_id}/`(코스 상세, 확정)로 코스 화면을 보여준다.
- 코스는 명소(anchor) + 식당 1 + 카페 1 + 그 외 1로 구성된다.

### 2. 코스 생성

- `POST /api/places/{place_id}/courses/`(확정, 로그인 필요)로 만든다. `course_places`에 식당(RESTAURANT) 1 + 카페(CAFE) 1 + 그 외(OTHER) 1, 정확히 3개가 있어야 한다(BE `CourseWriteSerializer.validate_course_places`).
- 후보 장소는 카카오맵 API로 그때그때 검색한 결과를 스냅샷(이름·주소·좌표·카테고리)으로 그대로 보낸다 — BE는 카카오를 다시 호출하지 않는다.
- 명소 상세(Phase4)의 "이 장소로 AI 코스 추천받기" 버튼(현재 비활성 상태)에서 진입한다.

### 3. 코스 저장(즐겨찾기)

- `POST/DELETE /api/courses/{course_id}/favorite/`(확정)로 저장/취소한다. 명소 즐겨찾기(Phase2)와 동일한 멱등 규칙.
- 저장한 코스는 즐겨찾기 목록(Phase5 `/bookmarks`, 마이페이지 Phase7 미리보기)에 명소와 함께 나타나도록 연결한다 — `GET /api/account/favorites/`가 이미 명소·코스를 함께 내려준다.
- 마이페이지의 "나만의 코스"(`GET /api/account/courses/`, 내가 만든 코스)와는 다른 목록이다 — 헷갈리지 않는다.

### 4. 코스 상세 공유

- 명소 상세와 동일한 방식(현재 URL을 클립보드로 복사)으로 구현한다. 별도 공유 전용 API는 없다(BE에 `/share` 엔드포인트 없음, 확인 완료).

## 진행 상황 (2026-08-31)

**구현 완료.** Figma 목업 4개(코스 생성 화면 2개, 나만의 코스 목록·코스 상세 2개)를 사용자가 공유해줘서 그 기준으로 만들었다.

| 파일 | 역할 |
|---|---|
| `src/api/courses.ts` | `getPlaceCourses`/`createCourse`/`getCourseDetail`/`deleteCourse`/`getMyCourses` |
| `src/utils/distance.ts` | haversine 거리 계산 (BE 응답에 거리 필드가 없어서 직접 계산) |
| `src/utils/courseCategory.ts` | `nearby_places`를 코스 생성 화면의 카테고리 탭 3개로 대략 분류 |
| `src/pages/CourseCreatePage.tsx` | 코스 생성 (`/spots/:placeId/courses/new`), 드래그 순서변경은 안 만듦(제거 후 재추가로 대체) |
| `src/pages/CourseDetailPage.tsx` | 코스 상세 + 지도 + 즐겨찾기 + 공유 + (작성자만) 삭제 (`/courses/:courseId`) |
| `src/pages/MyCourseListPage.tsx` | 나만의 코스 목록 (`/mycourses`) |
| `src/components/FavoriteButton.tsx` | `type="course"` prop 추가해서 명소/코스 즐겨찾기 겸용으로 확장 |
| `src/pages/BookmarksPage.tsx`, `MyPage.tsx` | 코스 즐겨찾기·나만의 코스 반영 |

목업과 실제 BE API 사이의 갭(카카오 후보 재사용, 거리·지역명 없음, 카테고리 분류 근사치, 드래그 미구현 등)은 `docs/DETAIL_SPEC.md` S-08에 자세히 기록해뒀다.

**브라우저 확인 못 함**: 로그인 필요한 흐름이라 이번 세션에서 Claude in Chrome 없이는 직접 확인 못 했다. 코드/테스트로만 확인했다.

## 완료 기준 체크리스트

- [x] 명소 상세 화면에서 코스로 진입할 수 있다
- [x] 코스에 명소+식당1+카페1+기타 구성이 보인다
- [x] (코드로 확인, 브라우저 확인 필요) 로그인한 사용자는 코스를 직접 만들 수 있다 (맛집·카페·주변 명소 후보 선택). 드래그 순서변경은 안 만들고 제거 후 재추가로 대체
- [x] (코드로 확인, 브라우저 확인 필요) 로그인한 사용자는 코스를 저장(즐겨찾기)할 수 있다
- [x] 저장한 코스가 즐겨찾기 목록·마이페이지에 보인다
- [x] 코스 상세에서 링크 복사로 공유할 수 있다
- [x] 관련 유닛 테스트(코스 조회/생성/삭제/즐겨찾기 API 함수 성공·실패 처리) 통과 (Vitest, 총 76개)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- 코스에 포함된 주변 상권 정보는 BE가 스냅샷으로 저장한다(생성 시점 카카오 응답을 그대로 복사) — 가게가 나중에 폐업해도 자동 갱신되지 않는다. Phase4의 "주변 상권은 저장 안 함(그때그때 받아옴)"과는 다른 결론이니 헷갈리지 않는다.
- 카카오 주변 상권 검색은 Phase4에서 이미 연동한 방식을 그대로 재사용했다 — 명소 상세 API의 `nearby_places`를 코스 생성 후보로 재사용, FE가 카카오를 따로 호출하지 않는다.
