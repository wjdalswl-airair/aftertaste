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
  api/          # 도메인별 API 함수 (auth.ts, spots.ts, works.ts, reviews.ts, bookmarks.ts, search.ts, courses.ts)
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
| `/works/:workId` | (PRD/Phase에 없음, 별도 정리 필요) 작품 상세 | ❌ |
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
| `useLocaleStore` | 선택한 언어 (Phase 2 구현, 2026-09-04 국적→언어 직접 선택으로 변경) | 메인/마이페이지 언어 선택 시. `zustand/persist`로 항상 localStorage에 저장하고, 로그인 상태면 `PATCH /api/account/locale/`도 함께 호출 |

화면별로만 쓰는 상태(검색어 입력값, 폼 값 등)는 전역 스토어에 넣지 않고 해당 페이지 컴포넌트 안에 둔다 (불필요한 전역화 금지, karpathy-guidlines 2번).

---

## 5. 인증 연동

- Firebase Auth SDK가 로그인 상태와 토큰을 자체 관리한다 (`onAuthStateChanged`). FE는 토큰을 직접 저장하지 않는다 (PRD 6장 결정).
- API 호출 시 `firebase.auth().currentUser.getIdToken()`으로 현재 idToken을 꺼내 `Authorization: Bearer <token>` 헤더에 붙인다.
- 로그인 흐름 (Google): Google 소셜 로그인 → Firebase idToken 발급 → `POST /api/account/login/` 호출.
  - 이미 있는 회원: `agree_terms` 없이 호출, 200 응답.
  - 처음 온 회원: `{ agree_terms: true }` 와 함께 호출, 201 응답. 약관 동의 없이 호출하면 400.
  - 토큰이 없거나 잘못됨: 401 → "다시 로그인하세요" 안내 후 `/login`으로.
- 로그인 흐름 (Kakao, Phase 11 — 2026-09-04, `src/pages/LoginPage.tsx`): Firebase 기본 제공자가 아니라서 한 단계를 더 거친다. Kakao JS SDK 공식 문서 확인 결과 `Kakao.Auth.login()`(팝업으로 access_token을 바로 받는 방식)은 더 이상 문서에 없고, **`Kakao.Auth.authorize()`(리다이렉트 + 인가 코드) 방식만 제공**된다 (2026-09-04 확인, 영문/국문 문서 둘 다 동일) — 사용자 확인 후 이 방식으로 구현했다.
  1. `Kakao.Auth.authorize({ redirectUri })` 호출 → 카카오 로그인 동의 화면으로 이동 (`redirectUri`는 로그인 화면 자기 자신, `${origin}/login`).
  2. 로그인 성공 시 카카오가 `redirectUri`로 `?code=...`를 붙여 돌려보낸다. `LoginPage`가 마운트 시 이 `code`를 읽어 이어받는다.
  3. `POST /api/account/kakao/token/`에 `{ code, redirect_uri }`를 보내 Firebase 커스텀 토큰(`firebase_custom_token`)을 받는다.
  4. `signInWithCustomToken(auth, firebase_custom_token)`으로 Firebase 로그인.
  5. Firebase가 내려준 idToken으로 위 `POST /api/account/login/`을 그대로 호출 — 여기서부터 Google과 같은 절차 (`useInitAuth`의 `onAuthStateChanged`가 자동으로 처리).
  - **⚠️ BE 의존성 미해결 (2026-09-04)**: 현재 master의 `KakaoCustomTokenView`는 이미 발급된 `access_token`을 받는 구조라(`{ access_token }` 요구), FE가 보내는 `{ code, redirect_uri }`를 받으면 400이 난다. **BE에 다음을 요청해야 한다**: `code`(+ `redirect_uri`)를 받아 카카오 REST API(`POST https://kauth.kakao.com/oauth/token`, `grant_type=authorization_code`, BE의 카카오 REST API 키 사용)로 `access_token`을 직접 교환한 뒤, 기존 로직(`get_kakao_user` 이하)을 그대로 잇는 방식으로 바꿔달라고. 그때까지 FE 카카오 로그인 버튼은 동작하지 않는다.
  - 카카오 개발자 콘솔에 이 `redirectUri`(로컬 `http://localhost:5173/login`, 배포 도메인의 `/login`)를 "카카오 로그인 > Redirect URI"에 등록해야 한다.
  - Kakao JS SDK는 지도 SDK와 별개(`https://t1.kakaocdn.net/kakao_js_sdk/2.8.3/kakao.min.js`, `window.Kakao`)라 `index.html`에 별도 `<script>`로 추가했다. 로더는 `src/lib/kakaoAuth.ts`(`kakaoMap.ts`와 동일한 패턴).
- 내 정보 조회: `GET /api/account/` (`MeView`). 응답 필드: `id, email, nickname, profile_image_url, provider, nationality, language, created_at`.
- Apple 로그인은 만들지 않는다 (2026-09-04, BE PRD 결정 변경에 맞춰 Kakao로 대체). `appleProvider`(`src/lib/firebase.ts`), `apple.svg` 에셋 제거함.

---

## 6. 지도 연동 (카카오맵)

- 카카오 공식 JS SDK를 `index.html`에 `<script>` 태그로 직접 로드한다 (PRD 6장 결정). API 키는 `.env`에 두고 코드에 직접 쓰지 않는다 (CLAUDE.md Security Rules).
- 명소 상세(S-05)에서 명소 좌표로 지도를 띄우고 마커를 표시한다.
- 길찾기는 직접 구현하지 않고 카카오맵 링크(`https://map.kakao.com/link/to/{name},{lat},{lng}`)로 연결한다. 카카오맵 앱이 있으면 앱으로, 없으면 모바일 웹으로 자동 대체된다 (BE PRD F-05, 조사 완료).
- **알려진 한계**: 지도 배경의 도로명·상호명 라벨은 한글 위주다. 명소 이름·주소·설명 등 사용자가 실제로 읽는 정보는 지도 라벨이 아니라 우리 화면 UI 텍스트(번역 적용됨, 7장 참고)로 보여주므로 별도 처리가 필요 없다.

---

## 7. 다국어 처리 (react-i18next)

- 지원 언어: **ko(한국어) / en(English) / ja(日本語) / zh-CN(简体中文) / zh-TW(繁體中文)** — 5개 (2026-09-04 확정, BE 합의로 영어 하나에서 확장).
- UI 고정 문구(버튼, 라벨 등)는 `src/i18n/locales/{ko,en,ja,zh-CN,zh-TW}.json`으로 관리하고 `react-i18next`로 렌더링한다 (`src/i18n/index.ts`에 5개 모두 등록).
  - **ja/zh-CN/zh-TW는 Claude가 en.json 기준으로 기계번역한 초안이다 (2026-09-04).** 사용자 검토·수정 전이라 표현이 어색하거나 부정확할 수 있음 — 정식 배포 전에 검수 필요.
- 명소·작품 설명, 리뷰처럼 **서버에서 오는 콘텐츠 번역**은 UI 문구와 다르다. 이건 리소스 파일이 아니라 BE 응답 자체가 이미 번역된 텍스트로 온다 (BE DETAIL_SPEC 4장 — 서버가 언어별로 번역해서 내려줌). FE는 그 값을 그대로 표시하면 된다.
- **화면 언어는 국적이 아니라 직접 선택한다 (2026-09-04 변경, PRD 3장 S-02 참고).** 헤더의 지구본 아이콘(`LanguageSheet`)에서 5개 언어 중 하나를 고르면 `useLocaleStore`가 바뀌고, `i18next.changeLanguage()`를 호출해 UI 문구도 함께 바뀐다. `useLocaleStore`엔 더 이상 `nationality` 필드가 없다 — BE `Member.nationality`는 선택 필드라 안 보내도 문제없다(BE DETAIL_SPEC 6-1 #10).
- 언어를 고르지 않은 사용자는 한국어가 기본값이다.
- **명소·작품 콘텐츠의 실제 언어 결정**: BE `places/translation.py`의 `resolve_language()`가 `쿼리파라미터 lang → 로그인 회원의 언어 → 한국어(None)` 순서로 정한다. FE는 `spots.ts`/`works.ts`/`search.ts`의 API 호출마다 `useLocaleStore`의 현재 언어를 `?lang=`으로 항상 붙인다 (Phase 11, 2026-09-04 연동 완료) — 비로그인 사용자도 언어를 바꾸면 명소·작품 콘텐츠가 바뀐다.
- **리뷰 번역은 아직 BE에 연결 안 됨 (2026-09-04 확인)**: `ReviewTranslation` 모델은 있지만 `reviews/views.py`가 이를 조회/반환하지 않는다. PRD 4장의 "사용자가 작성한 리뷰도 번역 대상" 요구사항은 BE 작업이 선행되어야 한다.

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
- 컴포넌트: 로고, 소셜 로그인 버튼(Google, Kakao), 약관 동의 텍스트
- API: `POST /api/account/login/` (확정), Kakao는 `POST /api/account/kakao/token/` 선행 (5장 참고)
- 상태: 로그인 성공 시 `useAuthStore` 갱신 후 이전 화면 또는 `/`로 이동
- Apple 버튼은 Phase 11(2026-09-04)에서 제거, Kakao 버튼으로 교체했다 (5장 참고).

### S-02. 메인 — `pages/MainPage.tsx` (Phase 2, 구현 완료 — 2026-08-30 Figma 실제 목업에 맞춰 리디자인)
- 컴포넌트: `Hero`(배너+명예의전당 병합), `LanguageSheet`(언어 선택 바텀시트), `BottomNav`(홈/검색/프로필), `TopPlacesCarousel`, `RecommendedSpots`
- API (전부 확정, 실제 BE 코드로 확인함 — 2026-08-29):
  - `GET /api/banners/` → `{ banners: [{ id, image_url, link_url, order }] }`
  - `GET /api/main/hall-of-fame/` → `{ review: {...} | null }` (없으면 `null`, 200 정상 응답)
  - `GET /api/main/top-places/` → `{ places: [{ id, name, address, photo_url, favorite_count }] }`
  - `PATCH /api/account/locale/` → `{ nationality?, language? }` 요청, `{ language }` 응답. 로그인 불필요(선택), 비로그인이면 검증만 하고 저장은 프론트가 `useLocaleStore`(localStorage)로 한다.
- 처음엔 BE 번역 지원 언어가 영어만으로 결정된 것에 맞춰 국적 선택(한국(ko)/해외(en) 2개)으로 만들었으나(2026-08-29), **2026-09-04부터 국적이 아니라 화면 언어를 직접 고르는 방식**으로 바꿨다 — 지원 언어가 5개(ko/en/ja/zh-CN/zh-TW)로 늘면서 국적↔언어 1:1 매핑이 안 맞아서다 (BE 합의, 7장 참고). UI는 Figma처럼 헤더 지구본 아이콘 → 바텀시트, 이제 5개 언어 목록이 뜬다.
- 명예의전당·Top10은 BE 자체 문서엔 "Phase3 전엔 못 채운다"고 되어 있지만, 실제 코드는 스텁이 아니라 진짜 랭킹 로직이 이미 구현돼 있다. 데이터가 없으면 각각 `null`/`[]`을 정상 응답하므로 그 값 그대로 빈 상태 UI를 보여준다.
- **Hero(배너+명예의전당 병합, 2026-08-30 캐러셀로 확장)**: "금주의 명예의 전당"(`GET /api/main/hall-of-fame/`)과 "이 장소, 어떠세요?"(`GET /api/places/recommend/`의 첫 번째 결과) 두 슬라이드를 4초마다 자동 전환 + 손가락 스와이프로 넘겨볼 수 있는 캐러셀로 보여준다. 둘 다 없으면 `GET /api/banners/`로 대체하고, 그마저 없으면 아무것도 안 보인다.
- **배너 데이터 연동은 FE 쪽엔 이미 완성돼 있다 (2026-09-04 재확인)**. 배포 서버(`/api/banners/`)가 빈 배열을 돌려주는 건 코드 문제가 아니라 배포 DB에 배너 데이터(관리자 등록)가 아직 없어서다 — FE에서 추가로 할 일 없음, BE/운영 쪽에서 데이터만 채우면 된다.
- **즐겨찾기 (2026-08-30 추가, `src/api/bookmarks.ts`)**: Top10·추천 카드 썸네일 위에 별 아이콘. `POST/DELETE /api/places/{id}/favorite/` 연동, 로그인 필요(`authorizedFetch` 재사용, `auth.ts`에서 export). 비로그인 상태로 누르면 `/login`으로 이동하며 "로그인이 필요한 기능입니다" 안내.
  - **제약**: 목록 API(추천/Top10) 응답에 즐겨찾기 여부(`is_favorited`)가 없어서, 카드 별은 항상 빈 별로 시작한다. 이미 즐겨찾기한 명소를 다시 봐도 화면상으론 빈 별로 보임 — BE가 목록 응답에 `is_favorited`를 추가해주면 고칠 것.
- **지역별 Top10 (예정, 착수 전 — 2026-09-05 논의)**: 위치 권한을 거부한 사용자에게 상단 전국 Top10(`TopPlacesCarousel`) 아래로, 특정 지역에 결과가 쏠리지 않게 "지역 안배된" Top10 리스트를 하나 더 보여주는 안을 논의했다.
  - 전국 Top10은 `TopPlacesView`(`BE/main/views.py`)가 즐겨찾기 수 내림차순 상위 10곳을 지역 구분 없이 반환하는 방식(기존과 동일, 변경 없음).
  - 지역 단위는 **시/도(17개 광역)** 기준으로 하기로 함(시/군/구 단위는 지역 수가 많아 "안배" 효과가 옅어져서 제외).
  - `Place` 모델에 지역 필드가 없어(`address` 문자열, `latitude`/`longitude`만 있음) 주소 파싱 또는 역지오코딩으로 지역을 얻어야 하는 BE 작업이 선행돼야 한다. "지역 안배" 알고리즘(예: 지역별 1위를 먼저 채우고 남는 자리는 즐겨찾기 수 순으로 채우는 방식 등)도 아직 미확정.
  - BE 작업과 알고리즘 확정 모두 보류 상태 — 착수 전 이 문서를 먼저 갱신하고 진행한다.
- **BE 데이터가 없어서 생긴 제약 — BE 확인 필요 (2026-08-30)**:
  1. Top10/추천 카드의 부제(작품명)를 Figma는 보여주지만, 두 API 응답에 작품명이 없어 **`address`로 대신 표시** 중이다.
  2. 추천 카드의 거리 뱃지(예: "거리 1.2km")도 Figma엔 있지만, API 응답에 좌표가 없어 만들지 못했다.
  3. Hero 캡션의 명소/작품명은 `review.place`(id)로 `GET /api/places/{id}/`를 한 번 더 호출해서 채운다. 이 상세 응답의 `works` 필드 정확한 구조를 아직 검증 못 해서(`src/api/spots.ts`의 `PlaceDetail` 타입이 추정치), 실제로 작품명이 안 나올 수 있다 — 필드가 없으면 명소 이름만 보인다.

### S-03. 검색 결과 — `pages/SearchPage.tsx` (Phase 3, 구현 완료 — 2026-08-30)
- 컴포넌트: 검색창(자동완성), 전체/드라마/영화 필터 칩, 작품/명소 섹션, 추천 검색어, 최근 검색어
- API (전부 확정, 실제 BE 코드로 확인함):
  - `GET /api/places/search/?q=&type=&lang=` → `{ places: [{id,name,address,photo_url}], works: [{id,title,category,poster_url}], message? }`. `q` 없으면 400, `type`(`WORK`/`DRAMA`/`MOVIE`)이 잘못돼도 400. 로그인 상태면 BE가 자동으로 검색 기록을 남긴다.
  - `GET /api/places/search/autocomplete/?q=` → `{ suggestions: string[] }`
  - `GET /api/search/popular/` (라우팅이 `/api/places/` 밑이 아니라 루트 바로 밑, `config/urls.py` 참고) → `{ keywords: string[] }`, 최근 30일 집계 상위 5개. PHASE3.md 원안엔 없었지만 이미 BE에 구현돼 있어 함께 넣기로 함(2026-08-30, 사용자 확인).
- `lang` 파라미터는 `useLocaleStore`의 현재 언어를 항상 붙인다 (Phase 11, 2026-09-04 변경 — 이전엔 안 보냈으나, 그러면 비로그인 사용자는 언어를 바꿔도 검색 결과가 계속 한국어로 왔다).
- **최근 검색어는 로그인 여부와 상관없이 localStorage에만 저장한다.** PRD엔 "비로그인 사용자만 기기 저장"이라고 되어 있었지만, BE에 로그인 사용자의 검색 기록을 다시 조회하는 API가 없다(`SearchHistory`는 인기 검색어 집계·개인화 추천에만 쓰임) — 그래서 로그인해도 동일하게 기기 저장으로 처리했다(2026-08-30, 사용자 확인).
- 필터 칩(전체/드라마/영화) UI는 Figma 목업(node-id `102:1265`)에 없어서 직접 구성했다. 스타일은 `LanguageSheet.tsx`의 선택 표시(`font-bold text-primary`)와 동일하게 맞춤. 위치는 "작품에서 검색됨" 타이틀 바로 아래(2026-08-30, 사용자 확인).
- **필터는 API를 다시 안 부르고 FE에서만 걸러 보여준다.** 검색 API에 `type`을 넘기면 BE가 명소 결과를 아예 비워버려서(`SearchView`), 필터를 누를 때마다 "명소에서 검색됨" 섹션까지 같이 사라지는 문제가 있었다. 그래서 검색은 항상 `type` 없이(통합검색) 한 번만 부르고, 필터 클릭 시엔 이미 받아온 `works` 배열을 화면에서 `category`로 걸러서 보여준다. `places`는 필터와 무관하게 항상 그대로 보인다(2026-08-30, 사용자 확인).
- 검색 결과 카드(장소/작품)는 클릭해도 이동하지 않는다 — 명소 상세(Phase4)가 아직 없어서, 메인 화면의 Top10/추천 카드와 동일하게 임시로 비워둠.
- 예외: 결과 없음 → "검색결과가 존재하지 않습니다" (`message` 필드 또는 FE에서 빈 결과 판단)

### S-04. 추천 (위치 기반) — 메인 화면(S-02) 내부 기능, Phase 2 구현 완료
- API: `GET /api/places/recommend/` (확정, `src/api/spots.ts`의 `getRecommendedSpots`)
  - `lat`, `lng` 쿼리 파라미터(선택). 없거나 잘못되면 BE가 랜덤 3곳을 돌려준다.
  - `lang` 쿼리 파라미터는 항상 붙인다 (Phase 11, 2026-09-04 — 7장 참고).
  - 항상 3개, `{ places: [{ id, name, address, photo_url }] }`
- 위치 권한 허용/거부는 `src/hooks/useGeolocation.ts`가 판단. 거부해도 재요청하지 않는다.
- **위치 권한 커스텀 모달 (Phase 11, 2026-09-04 구현 완료)**: Figma node-id `102:702` 기준. `src/components/LocationPermissionModal.tsx` — "허용"을 눌러야 그때 `useGeolocation`이 브라우저 네이티브 권한 팝업(`getCurrentPosition`)을 띄운다. 응답(허용/거부)은 `localStorage`(`location-permission-consent`)에 저장해 다음 방문부터는 모달을 다시 안 띄운다. 안내/약관/처리방침 3줄 텍스트는 Figma 목업에 실제 이동 경로가 없어서(연결된 페이지 없음) 텍스트로만 두고 링크는 안 걸었다 — 필요해지면 별도 논의.
- **추천 타이틀 동 이름 표시 (Phase 11, 2026-09-05 구현 완료)**: 좌표를 받으면 카카오맵 JS SDK `services` 라이브러리의 `coord2RegionCode`로 행정동 이름을 구해(`src/lib/kakaoMap.ts`의 `getDongName`) 타이틀을 "역삼동 근처 명소"처럼 보여준다(BE 변경 없음, 클라이언트에서만 처리). 동 이름을 못 가져오면(SDK 미로딩, API 실패 등) 기존 "내 주변 명소" 문구로 폴백한다.

### S-05. 명소 상세 — `pages/SpotDetailPage.tsx` (Phase 4, 구현 완료 — 2026-08-30)
- 컴포넌트: 카카오맵(+주변 상권 마커), 명소 정보, 작품 정보, 리뷰 목록, 즐겨찾기 버튼(`FavoriteButton` 재사용)
- API: `GET /api/places/{place_id}/` **하나로 전부 해결** (확정, 실제 BE 코드로 확인함 — `places/views.py` `PlaceDetailView`). 명소 기본 정보 + 등장 작품(장면 설명 포함) + 주변 상권(카카오 API 프록시, 저장 안 함) + 리뷰 목록/평균 별점 + 로그인 시 즐겨찾기 여부(`is_favorited`)를 한 번에 준다. 로그인 없어도 호출 가능, 없는 명소는 404.
- 즐겨찾기 등록/해제는 Phase2에서 이미 구현된 `POST/DELETE /api/places/{id}/favorite/`(`src/api/bookmarks.ts`)를 그대로 쓴다 — Phase4 계획엔 "표시만"이라고 돼 있었지만 실제로 이미 동작한다.
- Figma 실제 목업(node-id `102:712`)을 사용자가 공유해줘서 그 기준으로 만들었다. 다만 목업과 실제 데이터 모델이 안 맞는 부분이 있어 아래처럼 처리했다(2026-08-30, 사용자 확인):
  1. 목업의 "입장료" 행 — `Place` 모델에 필드 자체가 없어서 **뺐다**.
  2. 모델의 `photo_tips`(사진 팁) — 목업엔 없지만 실제 데이터라 정보 카드에 추가했다.
  3. 목업 "주요 촬영작"은 등장 작품 제목만 콤마로 나열한다. API는 작품별 `scene_description`(장면 설명)도 주지만, 목업에 보여줄 자리가 없어서 **화면엔 아직 안 넣었다** — 필요하면 나중에 UI 추가.
  4. "이 장소로 AI 코스 추천받기" CTA, 지도 위 "주변 코스 추천받기" 라벨은 코스(S-08, 훨씬 뒤 Phase)라 정적으로만 보이고 실제 동작 없음.
  5. "별점 남기기"/"리뷰 남기기" 버튼은 로그인 여부만 확인(비로그인 시 `/login`). 실제 작성 기능은 Phase5.
  6. **`latitude`/`longitude`는 문자열로 온다** — `Place` 모델이 `DecimalField`라 DRF가 정밀도 보존을 위해 숫자가 아니라 문자열(`"37.579617"`)로 직렬화한다(테스트용 데이터로 직접 확인). `NearbyPlace`의 좌표는 `FloatField`라 그대로 숫자로 온다 — 같은 화면 안에서 좌표 타입이 다르니 헷갈리지 않게 `SpotDetailPage.tsx`에서 `Number()`로 변환해서 쓴다.
- **카카오맵 키**: `.env`의 `VITE_KAKAO_JS_KEY`(JS 키, `VITE_KAKAO_...` 이름은 이번에 새로 정함 — BE의 `KAKAO_API_KEY`는 REST 키라 다른 키다)를 `index.html`에서 Vite `%ENV%` 치환으로 읽는다. 키가 없으면 `src/lib/kakaoMap.ts`의 `loadKakaoMaps()`가 `null`을 돌려줘서, 지도 자리에 "지도를 표시할 수 없어요" 폴백을 보여주고 나머지 화면은 정상 동작한다.
- 카카오맵 SDK는 npm 타입 패키지가 없어 `src/types/kakao.d.ts`에 실제 쓰는 만큼만(`Map`/`Marker`/`LatLng`/`InfoWindow`/`load`) 최소 ambient 타입을 직접 선언했다.
- 명소 상세로 이동하는 진입점: 메인 화면 Top10/추천 카드(`RecommendedSpots.tsx`, `TopPlacesCarousel.tsx`), 검색 결과의 명소 카드(`SearchPage.tsx`)를 이번에 `/spots/{id}`로 연결했다 (Phase2/3 때 "Phase4 끝나면 연결" 하기로 했던 부분).
- 예외: 없는 명소 → "존재하지 않습니다"

### 작품 상세 — `pages/WorkDetailPage.tsx` (`/works/:workId`, 2026-08-30 구현)
**PRD/Phase 문서에 없는 화면이다.** Figma엔 "작품 상세"(node-id `102:1174`, 작품 정보 + 그 작품의 촬영지 목록) 목업이 있는데, 사용자가 "라우트는 FE에서 정하면 되니까 먼저 만들고 API는 나중에 BE와 상의하겠다"고 해서 FE(라우트+화면+API 함수)만 먼저 만들었다. 나중에 어느 Phase에 넣을지는 별도로 정리해야 한다.
- API: `GET /api/works/{work_id}/` — **BE에 아직 없다.** `src/api/works.ts`의 `getWorkDetail()`이 이 경로로 스펙대로 호출하도록만 만들어뒀고, BE가 구현하면 FE 수정 없이 바로 동작한다. 그 전까지는 항상 실패 → "존재하지 않습니다"로 보인다(정상).
- 응답 스펙(안): `{ id, title, description, category, release_date, main_cast, director, poster_url, places: [{id,name,address,photo_url}] }`
- Figma 목업과 실제 `Work` 모델이 안 맞는 부분:
  1. 목업의 "극본" 행 — `Work` 모델에 해당 필드가 없어서 **뺐다**.
  2. 목업의 "방영날짜"는 시작~종료 범위지만, `Work.release_date`는 날짜 하나뿐이라 **시작일만** 보여준다.
  3. 목업엔 히어로 이미지에 북마크(즐겨찾기) 아이콘이 있지만, PRD상 즐겨찾기는 명소/코스에만 있는 기능이라(작품 즐겨찾기 자체가 없음) **넣지 않았다**.
- "자세히 보러가기" 버튼은 목적지가 따로 없어서, 작품 제목으로 구글 검색하는 링크(`https://www.google.com/search?q={제목}`)로 연결한다(2026-08-30, 사용자 확인).
- 진입점: 검색 결과의 작품 카드(`SearchPage.tsx`), 명소 상세의 작품 태그(`SpotDetailPage.tsx`)를 `/works/{id}`로 연결했다.
- 예외: 없는 작품 → "존재하지 않습니다"

### S-06. 즐겨찾기 목록 — `pages/BookmarksPage.tsx` (Phase 5, 구현 완료 — 2026-08-30)
- 저장/취소는 Phase2에서 이미 구현됨(`FavoriteButton`, `POST/DELETE /api/places/{id}/favorite/`) — 이번 Phase에서 새로 만든 건 목록 화면뿐.
- API: `GET /api/account/favorites/`(확정, 실제 BE 코드로 확인함 — `favorites/views.py` `MyFavoriteListView`) → `{ favorites: [{ id, type: 'PLACE'|'COURSE', place: {id,name,address,photo_url}|null, course: {...}|null, created_at }] }`. 문서엔 `GET /account/bookmarks`로 돼 있었는데 실제 경로가 다르다.
- 명소·코스 즐겨찾기가 한 응답에 섞여서 온다. 이번 Phase는 명소만 다루므로(코스는 Phase8) `type === 'PLACE'`인 것만 걸러서 보여준다. **(2026-08-31, Phase8) 코스 즐겨찾기(`type === 'COURSE'`)도 같이 보여주도록 확장했다** — 코스는 사진이 없어서 플레이스홀더 박스 + 코스명 + `place_name`으로 표시.
- Figma 목업 없어서 기존 명소 카드 스타일(썸네일+이름+주소, `SearchPage.tsx`의 명소 `ResultRow`와 동일한 마크업)로 만들었다. 각 항목 오른쪽에 `FavoriteButton`을 얹어서 목록에서 바로 취소도 가능하다(단, 취소해도 목록에서 즉시 안 사라짐 — 다시 들어오면 반영됨. 실시간 제거는 이번 범위 밖).
- `/mypage`(진짜 마이페이지, Phase7)에 진입 링크를 아직 안 넣었다 — 사용자 확인 후 이번엔 화면/로직만 먼저 만들고 진입 동선은 나중에 연결하기로 함(2026-08-30).
- 예외: 비로그인 시도 → `RequireAuth`가 "로그인이 필요한 기능입니다" 안내 후 `/login`으로. 저장한 게 없으면 빈 상태(오류 아님).

### S-07. 리뷰 작성/수정/삭제 — `pages/ReviewFormPage.tsx`, `ReviewListPage.tsx`, `ReviewDetailPage.tsx` (Phase 6, 구현 완료 — 2026-08-30)
- API (전부 확정, 실제 BE 코드로 확인함 — `reviews/views.py`):
  - `GET/POST /api/places/{place_id}/reviews/` — 목록(로그인 불필요)/작성(로그인 필요, `rating` 1~5·`content` 필수 최대 500자·`language`·`photo_urls`).
  - `PATCH/DELETE /api/reviews/{id}/` — 수정/삭제, 작성자 본인만(403). 삭제는 이미 없는 리뷰도 204(조용히 성공).
  - `POST/DELETE /api/reviews/{id}/like/` — 좋아요/취소.
  - `POST /api/reviews/{id}/report/` — 신고, 로그인 필요. 같은 사람이 여러 번 신고해도 1건만 접수(새 접수 201, 중복 200). 서로 다른 5명이 신고하면 자동 숨김 (Phase 11, 2026-09-04 연동).
- **좋아요 UI를 이번 Phase에 포함시켰다.** `PHASE6.md` 원안엔 "좋아요·신고 버튼은 화면에 없다"고 돼 있었지만, Figma 목업(리뷰 더보기/상세 화면)에 하트가 있고 BE API도 이미 구현돼 있어서 사용자 확인 후 포함했다(2026-08-30). 신고 버튼은 Phase 11에서 추가.
- `content`가 BE 모델에서 필수(빈 값 불가)라 **별점만 단독으로 등록하는 API 자체가 없다.** 그래서 "별점 등록" 모달(`RatingModal.tsx`)은 서버에 아무것도 안 보내고 고른 별점 값만 들고 리뷰 작성 화면으로 이동하며, 거기서 텍스트까지 채워야 최종 등록(POST)된다.
- Figma "리뷰 등록" 목업엔 별점 UI가 안 보였지만, `rating`이 없으면 제출 자체가 불가능해서 작성 화면에도 별점 줄을 추가했다(모달에서 값 넘어오면 미리 선택됨, 직접 바꿀 수도 있음). 같은 화면에 명확한 "등록" 버튼도 캡처에 안 잡혀서 하단에 직접 추가했다.
- **`GET /api/reviews/{id}/`(리뷰 단건 조회)가 없다.** "리뷰 더보기"/"리뷰 상세" 화면은 명소별 목록(`GET /api/places/{id}/reviews/`)에서 해당 id를 찾아 쓰는 방식으로 우회했다 — 그래서 라우트를 `/spots/:placeId/reviews`, `/spots/:placeId/reviews/:reviewId`처럼 명소 하위로 중첩했다.
- **`ReviewSerializer`에 "내가 쓴 글인지" 여부 필드가 없다** (즐겨찾기의 `is_favorited`, 좋아요의 `is_liked_by_me` 같은 필드가 리뷰엔 없음). 지금은 로그인한 회원의 닉네임과 `author_nickname` 문자열을 비교하는 걸로 임시 처리했다 — 닉네임이 겹치면 오작동할 수 있어 정확한 방법이 아니다. BE에 `is_mine` 같은 필드 추가를 요청해야 한다.
- 리뷰 더보기의 "최신순/인기순"은 서버를 다시 안 부르고 이미 받아온 목록을 클라이언트에서 `created_at`/`like_count` 기준으로 정렬한다.
- 사진은 Firebase Storage에 먼저 업로드(`src/lib/reviewPhotoUpload.ts`, `reviews/{uid}/{timestamp}-{filename}` 경로)한 뒤 URL을 `photo_urls`로 보낸다. `src/lib/firebase.ts`에 `storage` export를 새로 추가했다.
- 명소 상세의 "방문자 리뷰" 섹션에 "더보기" 링크와 카드별 상세 링크를 추가했다(목업엔 명시된 진입 동선이 없어서 직접 추가).

### S-08. 코스 — `pages/CourseDetailPage.tsx`, `CourseCreatePage.tsx`, `MyCourseListPage.tsx` (Phase 8, 구현 완료 — 2026-08-31)
- (2026-08-31 변경) 원래 "코스 생성 UI는 안 만든다"(PRD 5장)였으나, 사용자가 이번 Phase에서 생성 화면까지 포함하기로 결정했다. `docs/PRD.md` 5장에 이 결정 기록해둠.
- API (전부 확정, 실제 BE 코드로 확인함 — `courses/views.py`, `favorites/views.py`):
  - `GET/POST /api/places/{place_id}/courses/` — 명소 기준 코스 목록(로그인 불필요)/생성(로그인 필요). 생성 시 `course_places`가 정확히 식당(RESTAURANT) 1 + 카페(CAFE) 1 + 그 외(OTHER) 1이어야 한다.
  - `GET/PATCH/DELETE /api/courses/{id}/` — 상세(로그인 불필요)/수정(안 만듦)/삭제(작성자만).
  - `GET /api/account/courses/` — 내가 만든 코스 목록 (`MyCourseListPage.tsx`, `/mycourses`). Phase7에서 마이페이지에 빈 자리로만 뒀던 걸 이번에 연동.
  - `POST/DELETE /api/courses/{id}/favorite/` — 코스 즐겨찾기. 명소 즐겨찾기와 같은 멱등 규칙, `FavoriteButton`에 `type="course"` prop을 추가해서 재사용.
- **후보 장소는 카카오 API를 FE가 직접 안 부른다.** 명소 상세(`GET /api/places/{id}/`)가 서버에서 이미 받아온 `nearby_places`를 그대로 코스 생성 후보 목록으로 재사용한다. 이 값엔 거리·카카오place_id가 없어서, 거리는 `src/utils/distance.ts`(haversine)로 직접 계산하고 `kakao_place_id`는 항상 `null`로 보낸다.
- **카테고리 탭(맛집·카페/체험·공방/주변명소) 분류는 대략적인 추정이다** (`src/utils/courseCategory.ts`). 카카오 `category_name` 문자열에 "음식점"/"카페"/"체험"/"공방"/"교육" 포함 여부로 나눈 것 — 정확한 카카오 카테고리 코드 기준이 아니라서 잘못 분류될 수 있다.
- **드래그로 순서 바꾸기는 안 만들었다.** Figma엔 있지만, 후보를 뺐다 다시 추가하는 것만으로 3개 구성을 바꿀 수 있어서 별도 드래그 라이브러리 없이 MVP로 갔다.
- `CourseSerializer`엔 사진 필드가 없다 — 코스 카드/썸네일은 전부 색 배경 플레이스홀더(`bg-accent/15`)다.
- `CoursePlace`에도 거리·anchor place 좌표가 없어서, 코스 상세 화면은 `getCourseDetail`과 별개로 `getPlaceDetail(course.place_id)`를 추가로 불러서 anchor 좌표·주소·작품명을 채운다.
- 코스 상세의 "지역" 표시(예: "경기 수원")는 anchor place `address`의 앞 두 토큰을 자른 임시 값이다 — BE에 지역명 필드가 따로 없다. `MyCourseListPage`(내가 만든 코스 목록)는 이 추가 조회(N+1)까지는 안 하고 대신 `place_name`을 보여준다(Phase7 "내가 쓴 리뷰" 갭과 같은 타협).
- "내가 만든 코스인지" 판단은 리뷰와 동일하게 닉네임 비교로 임시 처리했다(`creator_nickname === member.nickname`) — 정확한 방법 아님, 기존 갭과 동일.
- 명소 상세(Phase4)의 "이 장소로 AI 코스 추천받기" 버튼을 활성화했다: 이 명소에 이미 코스가 있으면(로그인 불필요) 첫 번째 코스 상세로, 없으면 로그인 확인 후 생성 화면으로 보낸다.

### S-09. 공유 — 명소 상세/코스 화면 내부 기능 (Phase 4·8에서 이미 구현됨, Phase9은 확인만)
- 링크 복사만 구현 (PRD 5장). 별도 공유 API 없음 — `navigator.clipboard.writeText(location.href)`.

### S-10. 마이페이지 — `pages/MyPage.tsx` (Phase 7, 구현 완료 — 2026-08-31)
- API (전부 확정, 실제 BE 코드로 확인함 — `accounts/views.py`, `reviews/views.py`):
  - `GET /api/account/` — 내 정보(프로필, `reviewed_places_count`, `created_courses_count` 포함).
  - `PATCH /api/account/` — 닉네임·프로필 사진 수정, 204. 닉네임 20자 제한은 서버가 자동 검증(400).
  - `GET /api/account/reviews/` — 내가 쓴 리뷰 목록. `GET /api/account/favorites/`(Phase5에서 이미 구현)와 같은 방식으로 재사용.
- Figma 목업(node 102-1323, 102-1477) 기준으로 프로필/즐겨찾기/내 리뷰/나만의 코스/로그아웃 섹션 구성.
- **"내가 쓴 리뷰" 카드에 장소명을 보여준다.** `GET /api/account/reviews/`가 `ReviewSerializer`를 그대로 쓰는데, `place`가 ID로만 온다(이름·썸네일 없음, S-07 갭과 동일) — 처음엔 이름 없이 리뷰 내용만 보여주기로 했다가(2026-08-31 오전), 사용자가 장소명도 같이 보고 싶다고 해서 리뷰에 쓰인 장소들만 중복 제거해서 `getPlaceDetail`로 따로 조회하는 방식으로 바꿨다(2026-08-31 오후). 장소당 한 번만 호출되긴 하지만, `getPlaceDetail`이 명소 상세 전체(주변 상권·리뷰 목록 포함)를 돌려주는 무거운 API라 이름 하나 얻으려고 쓰기엔 과하다 — BE에 "장소 이름만" 주는 가벼운 API나, `ReviewSerializer`에 `place_name` 필드 추가를 요청하면 더 나아질 수 있다. 클릭하면 `/spots/{place}/reviews/{id}`(이미 있는 라우트)로 이동한다.
- **"나만의 코스" 섹션은 Phase7 당시엔 빈 자리만 만들었다가, Phase8에서 `GET /api/account/courses/`로 실제 연동했다** — 즐겨찾기/내 리뷰 섹션과 동일한 가로 스크롤 미리보기 + "더보기"(`/mycourses`, S-08 참고). "내가 저장한 명소" 섹션도 Phase8에서 코스 즐겨찾기까지 같이 보여주도록 확장됨(S-06 참고).
- 프로필 사진은 리뷰 사진과 동일하게 Firebase Storage에 먼저 업로드(`src/lib/profilePhotoUpload.ts`, `profile/{uid}/{timestamp}-{filename}` 경로)한 뒤 URL을 `profile_image_url`로 보낸다.
- **`LanguageSheet`이 Figma대로 5개 언어(한국어/English/日本語/简体中文/繁體中文)를 지원하도록 확장했다 (2026-09-04, BE 합의)** — 자세한 내용은 7장 참고.

### S-11. 회원탈퇴 — 마이페이지 내부 기능 (Phase 7, 구현 완료 — 2026-08-31)
- API: `DELETE /api/account/` (확정, `MeView.delete`) — 204. 회원 row는 안 지우고 개인정보만 비우는 방식(BE 처리, FE는 신경쓸 필요 없음).
- Figma 목업엔 탈퇴 버튼/화면이 없어서, 로그아웃 버튼 아래 작은 텍스트 링크("탈퇴하기")로 최소한만 추가했다. 클릭하면 `ReviewDetailPage`의 삭제 확인 바텀시트와 동일한 스타일의 확인 시트가 뜨고, 확인 시 탈퇴 처리 후 로그아웃하고 메인으로 이동한다.

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
