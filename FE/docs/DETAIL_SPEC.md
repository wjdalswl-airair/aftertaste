# Aftertaste FE 상세 설계서 (DETAIL_SPEC)

## 0. 이 문서에 대하여

**PRD와 무엇이 다른가**

| | PRD | 이 문서 |
|---|---|---|
| 답하는 질문 | 화면에서 사용자가 무엇을 할 수 있는가 | 그 화면을 실제로 어떤 파일·컴포넌트·API로 만드는가 |
| 읽는 사람 | 팀 전체 | 프론트엔드 개발자 |
| 쓰는 시점 | 기획할 때 | 코딩 시작하기 직전 |

| 항목 | 내용 |
|---|---|
| 문서 버전 | v0.1 |
| 작성일 | 2026-08-18 |
| 기준 문서 | `docs/PRD.md`, `../BE/docs/DETAIL_SPEC.md` |

---

## 1. API 정보의 출처와 신뢰도

API 연동 정보는 세 곳에서 나왔고, **신뢰도가 다르다.**

| 출처 | 신뢰도 | 이유 |
|---|---|---|
| BE 실제 코드 (`../BE/accounts/`) | 확정 | 이미 구현되고 동작하는 코드. 로그인/내 정보 조회만 여기 해당 |
| 노션 "API 명세" 데이터베이스 | 계획(미구현) | 로그인 외 모든 화면의 API가 여기 정리돼 있지만, **아직 BE가 만들지 않았다.** 실제로 만들 때 경로·응답 형태가 바뀔 수 있다 |
| 이 문서에서 추정한 것 | 잠정 | 위 두 곳에 없는 부분을 화면 요구사항에서 역산한 것. BE와 반드시 재확인 필요 |

**노션 API 명세서에서 발견한 두 가지 오래된 부분** (Spec 작성 중 확인, PRD.md에도 기록됨):
1. 지도 관련 API(주변 상권·Top10·길찾기·코스추천)에 "구글맵"이라고 적혀 있으나, 실제 결정은 **카카오맵**이다. 이 문서에서는 카카오맵 기준으로 작성한다.
2. 로그인 관련 API(`GET /account/oauth/url/{platform}`, `GET /jwt/refresh`, `DELETE /account/logout`)는 자체 OAuth+JWT 방식인데, 실제 코드는 **Firebase ID 토큰을 그대로 검증**하는 방식이다. 이 문서는 실제 코드를 따른다.

구현 중 노션 명세와 실제 BE 동작이 다르면, **실제 BE 동작을 따르고 노션이 오래된 것으로 간주**한다. 그래도 헷갈리면 먼저 물어본다.

---

## 2. 프로젝트 구조

```
src/
  api/          # 도메인별 API 함수 (auth.ts, spots.ts, reviews.ts, bookmarks.ts, search.ts, courses.ts)
  components/   # 여러 화면에서 재사용하는 UI 조각 (Button, Card, BottomNav 등)
  pages/        # 화면 단위 컴포넌트. 라우트 하나당 파일 하나 (PRD의 S-01~S-11과 대응)
  store/        # Zustand 전역 상태 (useAuthStore, useLocaleStore)
  hooks/        # 재사용 로직 (useKakaoMap 등)
  i18n/         # react-i18next 설정과 언어별 번역 파일
  lib/          # firebase.ts(Firebase 초기화), kakaoMap.ts(SDK 로드) 등 외부 연동 준비 코드
  App.tsx       # 라우터 정의
  main.tsx      # 진입점
```

컴포넌트는 작게 유지한다 (CLAUDE.md 기준). 화면(`pages/`) 하나가 너무 커지면 `components/`로 쪼갠다.

---

## 3. 라우팅

React Router로 화면 단위 페이지를 분리한다 (PRD 6장 결정).

| 경로 | 화면 (PRD) | 로그인 필요 |
|---|---|---|
| `/login` | S-01 온보딩/로그인 | — |
| `/` | S-02 메인 | ❌ |
| `/search` | S-03 검색 결과 | ❌ |
| `/spots/:spotId` | S-05 명소 상세 | ❌ |
| `/bookmarks` | S-06 즐겨찾기 목록 | ✅ |
| `/spots/:spotId/reviews/new` | S-07 리뷰 작성 | ✅ |
| `/reviews/:reviewId/edit` | S-07 리뷰 수정 | ✅ |
| `/courses/:courseId` | S-08 코스 상세 | ❌ (저장은 ✅) |
| `/mypage` | S-10 마이페이지 | ✅ |

로그인이 필요한 경로는 공통 가드(`RequireAuth` 래퍼)로 감싸고, 비로그인 접근 시 "로그인이 필요한 기능입니다"를 보여준 뒤 `/login`으로 보낸다 (BE의 공통 예외 규칙과 동일, BE DETAIL_SPEC 5장).

추천(S-04)과 공유(S-09)는 별도 화면이 아니라 메인/명소 상세 화면 안의 기능이므로 자체 경로가 없다.

---

## 4. 전역 상태 (Zustand)

| 스토어 | 담는 것 | 채워지는 시점 |
|---|---|---|
| `useAuthStore` | 로그인한 회원 정보 (`GET /account` 응답), 로그인 여부 | Firebase `onAuthStateChanged` 콜백에서 |
| `useLocaleStore` | 선택한 국적/언어 (Phase 2 구현 완료) | 메인 화면 국적 선택 시. `zustand/persist`로 항상 localStorage에 저장하고, 로그인 상태면 `PATCH /api/account/locale/`도 함께 호출 |

화면별로만 쓰는 상태(검색어 입력값, 폼 값 등)는 전역 스토어에 넣지 않고 해당 페이지 컴포넌트 안에 둔다 (불필요한 전역화 금지, karpathy-guidlines 2번).

---

## 5. 인증 연동

- Firebase Auth SDK가 로그인 상태와 토큰을 자체 관리한다 (`onAuthStateChanged`). FE는 토큰을 직접 저장하지 않는다 (PRD 6장 결정).
- API 호출 시 `firebase.auth().currentUser.getIdToken()`으로 현재 idToken을 꺼내 `Authorization: Bearer <token>` 헤더에 붙인다.
- 로그인 흐름: Google/Apple 소셜 로그인 → Firebase idToken 발급 → `POST /api/account/login/` 호출.
  - 이미 있는 회원: `agree_terms` 없이 호출, 200 응답.
  - 처음 온 회원: `{ agree_terms: true }` 와 함께 호출, 201 응답. 약관 동의 없이 호출하면 400.
  - 토큰이 없거나 잘못됨: 401 → "다시 로그인하세요" 안내 후 `/login`으로.
- 내 정보 조회: `GET /api/account/` (`MeView`). 응답 필드: `id, email, nickname, profile_image_url, provider, nationality, language, created_at`.
- Kakao 로그인은 이번 범위에서 만들지 않는다 (PRD 결정, Google/Apple만).

---

## 6. 지도 연동 (카카오맵)

- 카카오 공식 JS SDK를 `index.html`에 `<script>` 태그로 직접 로드한다 (PRD 6장 결정). API 키는 `.env`에 두고 코드에 직접 쓰지 않는다 (CLAUDE.md Security Rules).
- 명소 상세(S-05)에서 명소 좌표로 지도를 띄우고 마커를 표시한다.
- 길찾기는 직접 구현하지 않고 카카오맵 링크(`https://map.kakao.com/link/to/{name},{lat},{lng}`)로 연결한다. 카카오맵 앱이 있으면 앱으로, 없으면 모바일 웹으로 자동 대체된다 (BE PRD F-05, 조사 완료).
- **알려진 한계**: 지도 배경의 도로명·상호명 라벨은 한글 위주다. 명소 이름·주소·설명 등 사용자가 실제로 읽는 정보는 지도 라벨이 아니라 우리 화면 UI 텍스트(번역 적용됨, 7장 참고)로 보여주므로 별도 처리가 필요 없다.

---

## 7. 다국어 처리 (react-i18next)

- UI 고정 문구(버튼, 라벨 등)는 `src/i18n/`의 언어별 리소스 파일로 관리하고 `react-i18next`로 렌더링한다.
- 명소·작품 설명, 리뷰처럼 **서버에서 오는 콘텐츠 번역**은 UI 문구와 다르다. 이건 리소스 파일이 아니라 BE 응답 자체가 이미 번역된 텍스트로 온다 (BE DETAIL_SPEC 4장 — 서버가 언어별로 번역해서 내려줌). FE는 그 값을 그대로 표시하면 된다.
- 국적 선택(S-02)과 화면 언어는 하나로 묶인다 (PRD N-01). 국적을 선택하면 `useLocaleStore`가 바뀌고, `i18next.changeLanguage()`를 호출해 UI 문구도 함께 바뀐다.
- 언어를 고르지 않은 사용자는 한국어가 기본값이다.

---

## 8. 디자인 토큰

Figma "Yeoun Design System" 프레임(node `102:1772`) 기준으로 `src/index.css`의 `@theme`에 이미 반영되어 있다.

| 토큰 | 값 | Tailwind 클래스 예시 |
|---|---|---|
| `--color-primary` | `#F47C5C` | `bg-primary`, `text-primary` |
| `--color-accent` | `#F8B08B` | `bg-accent` |
| `--color-background` | `#FFFFFF` | `bg-background` (2026-08-30 변경) |
| `--color-ink` / `-secondary` / `-tertiary` | `#2B2320` / `#9C8AB0` / `#C9BAB0` | `text-ink`, `text-ink-secondary` |
| `--color-divider` | `#F0E4DC` | `border-divider` |
| `--radius-xs`~`--radius-2xl` | 8~28px | `rounded-lg` 등 |
| `--font-sans` | IBM Plex Sans KR (자체 호스팅) | 본문 기본값. 폰트 파일은 `src/assets/fonts/`, 등록은 `src/index.css`의 `@font-face` (2026-08-30) |
| `--font-brand` | 푸른숲체 (유한킴벌리, 자체 호스팅) | 로고/브랜드 텍스트에만 `font-brand`. 폰트 파일은 `src/assets/fonts/`, 등록은 `src/index.css`의 `@font-face` (2026-08-30) |

새 색상·radius가 필요하면 Figma가 먼저 바뀌어야 하고, 코드에서 임의로 값을 추가하지 않는다.

아이콘은 `lucide-react`를 사용하고, Figma에 명시된 대로 Rounded Outline 스타일(20~28px)을 유지한다.

---

## 9. 화면별 상세

각 화면은 PRD `docs/PRD.md` 3장의 사용자 행동 요구사항을 그대로 구현 대상으로 삼는다. API 열의 `(계획)` 표시는 노션 API 명세 기준으로 BE가 아직 구현하지 않은 것이다.

### S-01. 온보딩 / 로그인 — `pages/LoginPage.tsx`
- 컴포넌트: 소셜 로그인 버튼(Google, Apple), 약관 동의 텍스트
- API: `POST /api/account/login/` (확정)
- 상태: 로그인 성공 시 `useAuthStore` 갱신 후 이전 화면 또는 `/`로 이동

### S-02. 메인 — `pages/MainPage.tsx` (Phase 2, 구현 완료 — 2026-08-30 Figma 실제 목업에 맞춰 리디자인)
- 컴포넌트: `Hero`(배너+명예의전당 병합), `LanguageSheet`(국적/언어 바텀시트), `BottomNav`(홈/검색/프로필), `TopPlacesCarousel`, `RecommendedSpots`
- API (전부 확정, 실제 BE 코드로 확인함 — 2026-08-29):
  - `GET /api/banners/` → `{ banners: [{ id, image_url, link_url, order }] }`
  - `GET /api/main/hall-of-fame/` → `{ review: {...} | null }` (없으면 `null`, 200 정상 응답)
  - `GET /api/main/top-places/` → `{ places: [{ id, name, address, photo_url, favorite_count }] }`
  - `PATCH /api/account/locale/` → `{ nationality?, language? }` 요청, `{ language }` 응답. 로그인 불필요(선택), 비로그인이면 검증만 하고 저장은 프론트가 `useLocaleStore`(localStorage)로 한다.
- 국적 선택은 PRD상 "미정"이었으나, BE 번역 지원 언어가 영어만으로 결정된 것에 맞춰 **한국(ko) / 해외(en) 2개만** 만들었다 (2026-08-29, 사용자 확인). UI는 Figma처럼 헤더 지구본 아이콘 → 바텀시트.
- 명예의전당·Top10은 BE 자체 문서엔 "Phase3 전엔 못 채운다"고 되어 있지만, 실제 코드는 스텁이 아니라 진짜 랭킹 로직이 이미 구현돼 있다. 데이터가 없으면 각각 `null`/`[]`을 정상 응답하므로 그 값 그대로 빈 상태 UI를 보여준다.
- **Hero(배너+명예의전당 병합, 2026-08-30 캐러셀로 확장)**: "금주의 명예의 전당"(`GET /api/main/hall-of-fame/`)과 "이 장소, 어떠세요?"(`GET /api/places/recommend/`의 첫 번째 결과) 두 슬라이드를 4초마다 자동 전환 + 손가락 스와이프로 넘겨볼 수 있는 캐러셀로 보여준다. 둘 다 없으면 `GET /api/banners/`로 대체하고, 그마저 없으면 아무것도 안 보인다.
- **즐겨찾기 (2026-08-30 추가, `src/api/bookmarks.ts`)**: Top10·추천 카드 썸네일 위에 별 아이콘. `POST/DELETE /api/places/{id}/favorite/` 연동, 로그인 필요(`authorizedFetch` 재사용, `auth.ts`에서 export). 비로그인 상태로 누르면 `/login`으로 이동하며 "로그인이 필요한 기능입니다" 안내.
  - **제약**: 목록 API(추천/Top10) 응답에 즐겨찾기 여부(`is_favorited`)가 없어서, 카드 별은 항상 빈 별로 시작한다. 이미 즐겨찾기한 명소를 다시 봐도 화면상으론 빈 별로 보임 — BE가 목록 응답에 `is_favorited`를 추가해주면 고칠 것.
- **BE 데이터가 없어서 생긴 제약 — BE 확인 필요 (2026-08-30)**:
  1. Top10/추천 카드의 부제(작품명)를 Figma는 보여주지만, 두 API 응답에 작품명이 없어 **`address`로 대신 표시** 중이다.
  2. 추천 카드의 거리 뱃지(예: "거리 1.2km")도 Figma엔 있지만, API 응답에 좌표가 없어 만들지 못했다.
  3. Hero 캡션의 명소/작품명은 `review.place`(id)로 `GET /api/places/{id}/`를 한 번 더 호출해서 채운다. 이 상세 응답의 `works` 필드 정확한 구조를 아직 검증 못 해서(`src/api/spots.ts`의 `PlaceDetail` 타입이 추정치), 실제로 작품명이 안 나올 수 있다 — 필드가 없으면 명소 이름만 보인다.

### S-03. 검색 결과 — `pages/SearchPage.tsx`
- 컴포넌트: 검색창(자동완성), 드라마/영화 필터, 장소/작품 섹션
- API: `GET /api/places/search/`, `GET /api/places/search/autocomplete/` (BE 구현 완료, FE는 아직 이 화면을 만들지 않음 — 별도 Phase)
- 예외: 결과 없음 → "검색결과가 존재하지 않습니다"

### S-04. 추천 (위치 기반) — 메인 화면(S-02) 내부 기능, Phase 2 구현 완료
- API: `GET /api/places/recommend/` (확정, `src/api/spots.ts`의 `getRecommendedSpots`)
  - `lat`, `lng` 쿼리 파라미터(선택). 없거나 잘못되면 BE가 랜덤 3곳을 돌려준다.
  - 항상 3개, `{ places: [{ id, name, address, photo_url }] }`
- 위치 권한 허용/거부는 `src/hooks/useGeolocation.ts`가 판단. 거부해도 재요청하지 않는다.

### S-05. 명소 상세 — `pages/SpotDetailPage.tsx`
- 컴포넌트: 카카오맵, 명소 정보, 작품 정보, 리뷰 목록, 주변 상권, 즐겨찾기 버튼
- API: `GET /spots/{spotId}` (계획), `GET /spots/{spotId}/reviews` (계획), `GET /spots/{spotId}/nearby` (계획, 카카오맵으로 교체)
- 예외: 없는 명소 → "존재하지 않습니다"

### S-06. 즐겨찾기 목록 — `pages/BookmarksPage.tsx`
- API: `GET /account/bookmarks`, `POST /spots/{spotId}/bookmark`, `DELETE /spots/{spotId}/bookmark` (전부 계획)
- 예외: 비로그인 시도 → "로그인이 필요한 기능입니다"

### S-07. 리뷰 작성/수정 — `pages/ReviewFormPage.tsx`
- 컴포넌트: 별점, 텍스트, 사진 업로드
- API: `POST /spots/{spotId}/reviews`, `PATCH /reviews/{reviewId}`, `DELETE /reviews/{reviewId}` (전부 계획)

### S-08. 코스 — `pages/CoursePage.tsx`
- API: `GET /spots/{spotId}/courses` (계획), `GET /courses/{courseId}/share` (계획)
- 이번 범위에서 코스 생성 UI는 만들지 않는다 (PRD 5장, MVP 아님)

### S-09. 공유 — 명소 상세/코스 화면 내부 기능
- 링크 복사만 구현 (PRD 5장)

### S-10. 마이페이지 — `pages/MyPage.tsx`
- 컴포넌트: 프로필, 즐겨찾기 목록, 내가 쓴 리뷰, 국적/언어 설정
- API: `GET /api/account/` (확정), `GET /account/reviews` (계획), `PATCH /api/account/`(프로필 수정, 계획)

### S-11. 회원탈퇴 — 마이페이지 내부 기능
- API: `DELETE /account` (계획)

---

## 10. 공통 예외 처리

BE DETAIL_SPEC 5장과 동일한 기준을 화면에도 그대로 적용한다.

| 상황 | 화면 처리 |
|---|---|
| 로그인이 필요한데 안 함 | "로그인이 필요한 기능입니다" 안내 후 `/login`으로 |
| 남의 것을 고치거나 지우려 함 (403) | "권한이 없습니다" |
| 없는 것을 열려고 함 (404) | "존재하지 않습니다" |
| 서버 응답이 원문(번역 실패 등) | 그대로 보여준다 (FE에서 추가 처리 없음) |
| 이미 한 일을 또 함 (중복 즐겨찾기 등) | 에러로 처리하지 않고 조용히 성공 취급 |

---

## 11. 이번 Spec에서 정하지 않는 것

- 노션 API 명세의 정확한 요청/응답 스키마 (BE가 실제로 만들 때 확정)
- 신고 UI, 방문 인증 등 PRD에서 제외한 기능
- 배포 환경 변수·도메인 (Phase 5 대상)
