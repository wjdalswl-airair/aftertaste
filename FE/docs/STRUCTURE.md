# FE 폴더 구조

`src/` 아래 폴더·파일이 각각 어떤 역할을 하는지 정리한 문서. 새 코드를 어디에 둘지 헷갈릴 때 참고한다.

새 폴더/파일을 추가했으면 이 문서도 함께 갱신한다.

## 폴더별 역할

| 폴더 | 역할 |
|---|---|
| `pages/` | 라우트 하나당 화면 하나. `App.tsx`의 `<Route>`와 1:1로 대응한다. |
| `components/` | 여러 화면(또는 한 화면 안 여러 곳)에서 재사용하는 UI 조각. |
| `api/` | 백엔드 API 호출 함수. 함수 성공/실패 처리 로직이 여기 있고, 이 파일들만 유닛 테스트 대상이다. |
| `hooks/` | 여러 컴포넌트에서 재사용하는 상태·로직(브라우저 API 연동 등). |
| `store/` | Zustand 전역 상태(로그인 회원 정보, 언어 설정 등). |
| `lib/` | 외부 SDK(Firebase, 카카오) 연동 래퍼. API 호출이 아니라 SDK 자체를 다루는 코드. |
| `i18n/` | react-i18next 설정과 언어별 번역 문구. |
| `types/` | npm 타입 패키지가 없는 전역 SDK(카카오맵, 카카오 로그인)의 최소 타입 선언. |
| `assets/` | 폰트, 아이콘 등 정적 파일. |
| `test/` | Vitest 전역 설정. |

## 파일별 역할

### `src/pages/` — 화면

| 파일 | 라우트 | 역할 |
|---|---|---|
| `MainPage.tsx` | `/` | 메인 화면. `Hero`, `TopPlacesCarousel`, `RecommendedSpots` 등을 조립. |
| `LoginPage.tsx` | `/login` | 로그인 화면. Google(`signInWithPopup`)·Kakao(`authorize` 리다이렉트) 로그인 버튼, 약관 모달. |
| `SearchPage.tsx` | `/search` | 통합 검색(작품+명소), 최근 검색어, 인기 검색어. |
| `SpotDetailPage.tsx` | `/spots/:placeId` | 명소 상세 — 정보, 지도(카카오맵), 등장 작품, 주변 상권, 리뷰 요약. |
| `WorkDetailPage.tsx` | `/works/:workId` | 작품 상세 — 정보, 이 작품에 나온 명소 목록. |
| `ReviewListPage.tsx` | `/spots/:placeId/reviews` | 명소의 리뷰 더보기(전체 목록). |
| `ReviewDetailPage.tsx` | `/spots/:placeId/reviews/:reviewId` | 리뷰 상세, 좋아요, 신고, 본인 리뷰면 수정/삭제. |
| `ReviewFormPage.tsx` | `/spots/:placeId/reviews/new`, `/…/edit` | 리뷰 작성/수정 폼 (로그인 필요, `RequireAuth`로 보호). |
| `MyPage.tsx` | `/mypage` | 마이페이지 — 프로필 조회/수정, 즐겨찾기·내 리뷰 미리보기, 로그아웃, 회원탈퇴 (로그인 필요). |
| `BookmarksPage.tsx` | `/bookmarks` | 즐겨찾기 전체 목록 (로그인 필요). |

### `src/components/` — 재사용 UI

| 파일 | 역할 |
|---|---|
| `Hero.tsx` | 메인 화면 상단 캐러셀 — 명예의 전당 + 추천 명소 슬라이드, 없으면 배너로 대체. |
| `RecommendedSpots.tsx` | 메인 화면 "내 주변 명소" 섹션. 위치 허용 시 동 이름을 타이틀에 반영(`getDongName`). |
| `TopPlacesCarousel.tsx` | 메인 화면 Top10 명소 캐러셀. |
| `LocationPermissionModal.tsx` | 위치 권한을 브라우저 네이티브 팝업 전에 먼저 설명하는 커스텀 동의 모달. |
| `LanguageSheet.tsx` | 언어 선택 바텀시트. 선택 시 `useLocaleStore` + (로그인 상태면) 서버에도 저장. |
| `BottomNav.tsx` | 하단 탭바(홈/검색/프로필). |
| `FavoriteButton.tsx` | 명소 카드/상세에 붙는 즐겨찾기(별) 토글 버튼. 비로그인이면 로그인 화면으로 유도. |
| `RatingModal.tsx` | 별점 등록 모달 (리뷰 작성 진입점). |
| `RequireAuth.tsx` | 로그인 필요한 라우트를 감싸는 가드. 비로그인이면 안내와 함께 `/login`으로 리다이렉트. |
| `Modal.tsx` | 범용 모달 껍데기(제목 + 닫기 + children). |
| `Skeleton.tsx` | 로딩 중 표시하는 회색 스켈레톤 블록. |

### `src/api/` — 백엔드 호출

| 파일 | 역할 |
|---|---|
| `client.ts` | `publicFetch` 정의 — 로그인 여부와 무관하게 부르는 공용 fetch 래퍼(있으면 토큰 붙이고, 없어도 에러 안 남). |
| `auth.ts` | `authorizedFetch`(로그인 필수 API용, idToken 없으면 에러), Firebase 로그인↔서버 회원 동기화(`loginWithFirebase`), 카카오 토큰 교환(`kakaoLogin`), 프로필 수정/탈퇴/로그아웃/언어 저장. |
| `main.ts` | 메인 화면용 — 배너(`getBanners`), 명예의 전당(`getHallOfFame`), Top10 명소(`getTopPlaces`). |
| `spots.ts` | 명소 관련 — 추천 명소(`getRecommendedSpots`), 명소 상세(`getPlaceDetail`). |
| `works.ts` | 작품 상세 및 작품에 연결된 명소 목록. |
| `search.ts` | 통합 검색, 인기 검색어. |
| `reviews.ts` | 리뷰 작성/수정/삭제/좋아요/신고, 리뷰 목록·상세 조회. |
| `bookmarks.ts` | 즐겨찾기 추가/삭제/목록 조회. |
| `*.test.ts` | 각 API 함수의 성공/실패 처리 테스트 (Vitest). |

### `src/hooks/`

| 파일 | 역할 |
|---|---|
| `useGeolocation.ts` | 위치 권한 상태 관리. 커스텀 동의 모달 → 허용 시에만 브라우저 네이티브 `getCurrentPosition` 호출, 응답은 `localStorage`에 저장해 재요청 안 함. |
| `useInitAuth.ts` | 앱 시작 시 Firebase 로그인 상태(`onAuthStateChanged`)를 감지해서 서버 회원 정보(`loginWithFirebase`)와 동기화, `useAuthStore`에 반영. |
| `useRecentSearches.ts` | 최근 검색어를 `localStorage`에 저장/조회(로그인 여부 무관, 기기 저장). |

### `src/store/` — Zustand 전역 상태

| 파일 | 역할 |
|---|---|
| `useAuthStore.ts` | 로그인 회원 정보(`member`)와 로딩 상태. `useInitAuth`가 채워준다. |
| `useLocaleStore.ts` | 현재 언어 설정(`ko`/`en`/`ja`/`zh-CN`/`zh-TW`). `persist`로 `localStorage`에 저장. |
| `*.test.ts` | 스토어 로직 테스트. |

### `src/lib/` — 외부 SDK 연동

| 파일 | 역할 |
|---|---|
| `firebase.ts` | Firebase 앱 초기화, `auth`/`storage` 인스턴스, `googleProvider`. |
| `kakaoMap.ts` | 카카오맵 JS SDK 로더(`loadKakaoMaps`, `autoload=false`라 직접 로딩 대기). 좌표→동 이름 변환(`getDongName`, `services` 라이브러리). |
| `kakaoAuth.ts` | 카카오 로그인 JS SDK 로더(`loadKakaoAuth`, `window.Kakao`). |
| `profilePhotoUpload.ts` | 프로필 사진을 Firebase Storage에 업로드하고 다운로드 URL 반환. |
| `reviewPhotoUpload.ts` | 리뷰 사진을 Firebase Storage에 업로드하고 다운로드 URL 반환. |

### `src/i18n/`

| 파일 | 역할 |
|---|---|
| `index.ts` | i18next 초기화. `useLocaleStore`의 현재 언어를 초기값으로 사용. |
| `locales/{ko,en,ja,zh-CN,zh-TW}.json` | 언어별 번역 문구. |

### `src/types/` — 전역 타입 선언

| 파일 | 역할 |
|---|---|
| `kakao.d.ts` | 카카오맵 JS SDK(`window.kakao`) 최소 타입 — `Map`, `Marker`, `LatLng`, `services.Geocoder` 등 실제 쓰는 것만. |
| `kakaoAuth.d.ts` | 카카오 로그인 JS SDK(`window.Kakao`) 최소 타입. |

### 그 외 최상위 파일

| 파일 | 역할 |
|---|---|
| `App.tsx` | 라우트 정의(`<Routes>`), 앱 시작 시 `useInitAuth()` 호출. |
| `main.tsx` | React 진입점. `BrowserRouter`로 앱 감싸기. |
| `index.css` | Tailwind 설정 + `@theme` 디자인 토큰(색상·간격·radius). |
| `vite-env.d.ts` | `.env`의 `VITE_*` 환경변수 타입 선언. |
| `test/setup.ts` | Vitest 전역 설정(`@testing-library/jest-dom`). |
