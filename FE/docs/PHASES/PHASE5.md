# Phase 5 — 즐겨찾기

## 목표

**로그인한 사용자가 명소를 저장하고, 저장한 목록을 볼 수 있다.**

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 명소 즐겨찾기 저장/취소 | S-06 |
| 즐겨찾기 목록 화면 | S-06 |

> 코스 즐겨찾기는 다루지 않는다. 명소만 이번 Phase의 범위다 (코스는 Phase8).

## 하는 일

### 1. 저장/취소 연결

- Phase2에서 즐겨찾기 버튼(`FavoriteButton`)에 `POST/DELETE /api/places/{id}/favorite/`를 이미 연결해뒀다.
- 이미 저장한 걸 또 저장하거나, 안 한 걸 취소해도 에러로 처리하지 않고 조용히 성공 취급한다 (BE DETAIL_SPEC 3-4).

### 2. 즐겨찾기 목록 화면

- `GET /api/account/favorites/` 로 저장한 명소 목록을 보여준다 (명소+코스가 섞여 와서 명소만 걸러냄).
- 저장한 게 없으면 빈 목록 (오류 아님).

## 진행 상황 (2026-08-30)

**구현 완료.** 저장/취소 자체는 Phase2에서 이미 끝나 있어서, 이번엔 목록 화면(`BookmarksPage.tsx`, `/bookmarks`)만 새로 만들었다.

| 파일 | 역할 |
|---|---|
| `src/api/bookmarks.ts` | `getMyFavorites()` 추가 (`GET /api/account/favorites/`) |
| `src/pages/BookmarksPage.tsx` | 즐겨찾기한 명소 목록. 명소/코스가 섞여 오는 응답에서 명소만 필터링 |
| `src/App.tsx` | `/bookmarks`를 `RequireAuth`로 감싸서 라우트 추가 |
| `src/api/bookmarks.test.ts` | addFavorite/removeFavorite/getMyFavorites 성공·실패 테스트 |

- `/mypage` 진입 링크는 아직 안 붙였다(사용자 확인, 2026-08-30) — 진짜 마이페이지(Phase7) 만들 때 연결.
- 중복 저장/미저장 취소를 에러로 처리하지 않는 건 BE가 이미 그렇게 동작해서(DETAIL_SPEC 3-4) FE가 따로 분기할 게 없다 — `addFavorite`/`removeFavorite`는 성공/실패만 구분하면 된다.
- 브라우저 실제 확인은 이번 세션에서 안 함(Claude in Chrome 미사용) — 코드/테스트로만 확인.

## 완료 기준 체크리스트

- [x] 로그인 상태에서 즐겨찾기 버튼을 누르면 저장되고 버튼 모양이 바뀐다 (Phase2에서 이미 확인됨)
- [x] 다시 누르면 취소되고 버튼이 원래대로 돌아온다 (Phase2에서 이미 확인됨)
- [x] 비로그인 상태에서 누르면 "로그인이 필요한 기능입니다" 안내가 뜬다 (Phase2에서 이미 확인됨)
- [x] (코드로 확인, 브라우저 확인 필요) 즐겨찾기 목록 화면에서 저장한 명소들이 보인다
- [x] (코드로 확인, 브라우저 확인 필요) 저장한 게 없으면 빈 목록이 오류 없이 보인다
- [x] 관련 유닛 테스트(즐겨찾기 저장/취소/목록 API 함수 성공·실패 처리) 통과 (Vitest) — 중복 저장/미저장 취소는 BE가 처리하므로 FE 테스트 대상 아님
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- 코스 즐겨찾기(PRD에 언급됨)는 이번 Phase에 안 넣는다. 코스 저장은 Phase8에서 별도로 다룬다.
- 저장 개수 제한, 폴더·태그 분류는 만들지 않는다 (PRD 결정, 추후 추가).
