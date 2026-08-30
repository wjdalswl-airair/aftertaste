# Phase 2 — 메인 화면

## 목표

**로그인 없이 첫 화면(메인)을 볼 수 있다.** 배너, 국적 선택, 위치 기반 추천, Top10을 포함한다.

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 슬라이드 배너 | S-02 |
| 국적 선택 (언어 연동) | S-02 |
| 위치 기반 추천 | S-04 |
| 전국/지역 Top10 캐러셀 | S-02 |

> 명예의 전당은 자리만 만든다. "그 달 좋아요가 가장 많은 후기 사진"이 기준인데, 리뷰·좋아요 데이터가 아직 없다(BE Phase3에서 생김). 값이 없을 때의 빈 상태 화면만 준비한다.

## 하는 일

### 1. 배너

- `GET /banners` (계획) 호출해서 슬라이드로 보여준다.

### 2. 국적 선택

- 국적을 고르면 `useLocaleStore`를 갱신하고 `i18next.changeLanguage()`를 호출한다.
- 로그인 상태면 `PATCH /account/locale` (계획)로 서버에도 반영한다. 비로그인이면 기기에만 저장한다.
- 고르지 않으면 한국어가 기본값이다.

### 3. 위치 기반 추천

- 화면 진입 즉시 브라우저 위치 권한을 요청한다.
- 허용/거부에 따라 `GET /spots/recommend` (계획) 파라미터가 달라진다 (PRD F-04, DETAIL_SPEC §9).
- 추천 개수는 3개다.

### 4. Top10 캐러셀

- `GET /spots/top` (계획) 호출. 좌우로 넘겨 보는 캐러셀로 표시한다.

## 진행 상황 (2026-08-29)

**구현 완료.**

| 파일 | 역할 |
|---|---|
| `src/api/client.ts` | 로그인 선택(optional-auth) API 공용 fetch 헬퍼 (`publicFetch`) |
| `src/api/main.ts` | `GET /api/banners/`, `/api/main/hall-of-fame/`, `/api/main/top-places/` |
| `src/api/spots.ts` | `GET /api/places/recommend/` |
| `src/api/auth.ts` | `updateLocale()` 추가 (`PATCH /api/account/locale/`) |
| `src/store/useLocaleStore.ts` | 국적/언어 상태, `zustand/persist`로 localStorage 저장 |
| `src/i18n/` | react-i18next 설정, `ko.json`/`en.json` |
| `src/hooks/useGeolocation.ts` | 위치 권한 훅 |
| `src/components/RecommendedSpots.tsx`, `TopPlacesCarousel.tsx` | 메인 화면 카드 목록 |
| `src/pages/MainPage.tsx` | 위 컴포넌트 조합, `/` 라우트로 교체 |

국적 선택은 PRD상 "미정"이었으나, BE 번역 지원 언어가 영어만인 것에 맞춰 **한국 / 해외(영어) 2개만** 만들기로 결정 (2026-08-29, 사용자 확인). 자세한 내용은 `docs/DETAIL_SPEC.md` S-02 참고.

**리디자인 (2026-08-30)**: 사용자가 실제 Figma 화면 목업(`node-id=55-325`)을 공유해줘서, 처음 만든 UI 대신 그 목업에 맞춰 다시 만들었다. "여운 Design System" 스타일가이드 프레임은 참고하지 않고 실제 화면 프레임만 기준으로 삼았다 (컬러 팔레트는 예외적으로 그대로 사용 — 값이 실제 목업과 동일해서 문제 없음).

| 파일 | 역할 |
|---|---|
| `src/components/Hero.tsx` | `BannerSlider` + `HallOfFameCard` 병합. 명예의전당 있으면 그걸로, 없으면 배너로 대체 |
| `src/components/LanguageSheet.tsx` | `NationalityPicker` 대체. 헤더 지구본 아이콘 → 바텀시트(한국어/English) |
| `src/components/BottomNav.tsx` | 홈/검색/프로필 플로팅 네비 (신규, Figma에 있었지만 원래 계획엔 없던 요소) |
| `src/api/spots.ts`의 `getPlaceDetail()` | Hero 캡션용 명소 이름/작품명 보충 조회 (`GET /api/places/{id}/`, 1건만) |

BE 데이터가 없어서 못 채운 부분 3가지(카드 부제=작품명 대신 주소, 추천 카드 거리 뱃지 없음, Hero 작품명 필드 미검증)는 `docs/DETAIL_SPEC.md` S-02에 "BE 확인 필요"로 기록해뒀다.

**리디자인 브라우저 확인 (2026-08-30)**: 헤더 로고+지구본, 지구본 → 바텀시트(한국어/English) 전환, 카드 레이아웃, 하단 플로팅 네비까지 정상 동작 확인함.

**Commands**
- `npm run test`: 21개 테스트 통과 (Phase 1 것 포함, Phase 2에서 10개 추가)
- `npm run lint`: passed
- `npm run build`: passed

**브라우저 확인 (2026-08-29)**
- 배너/Top10: `GET /api/banners/`, `GET /api/main/top-places/` 둘 다 200 응답에 빈 배열(`{ banners: [] }`, `{ places: [] }`) 확인함 — API 연동은 정상, 단지 BE에 아직 실제 데이터(관리자가 등록한 배너, 즐겨찾기된 명소)가 없어서 화면에 안 보이는 것. 예상된 정상 동작.
  - 배너: 관리자가 Django admin에서 배너를 등록해야 실제로 보임 (데이터 넣으면 검증 가능)
  - Top10: 즐겨찾기 데이터 자체가 BE Phase3 기능이라, 지금은 실제 데이터로 검증 불가능 — Phase3 이후 재확인

**아직 확인 안 됨 (브라우저에서 직접 확인해야 함)**
- 국적 선택 시 화면 문구 언어가 실제로 바뀌는지
- 위치 권한 허용/거부 각각 추천 3곳이 뜨는지
- 명예의 전당 빈 상태(데이터 없을 때) 확인

## 완료 기준 체크리스트

- [ ] 배너가 보인다 (API 연동 확인됨, 관리자가 배너를 등록해야 실제 렌더링 검증 가능 — 2026-08-29)
- [x] 국적을 선택하면 화면 UI 문구의 언어가 바뀐다 (2026-08-29 브라우저 확인)
- [x] 국적을 선택하지 않으면 한국어로 보인다 (`useLocaleStore` 기본값 `ko`, `i18next` 기본 `lng: 'ko'`)
- [x] 위치 권한을 허용하면 위치 기반 추천이 보인다 (2026-08-29 브라우저 확인)
- [x] 위치 권한을 거부해도 화면이 깨지지 않고 대체 추천이 보인다 (2026-08-29 브라우저 확인)
- [ ] Top10 캐러셀이 좌우로 넘어간다 (API 연동 확인됨, 즐겨찾기 데이터가 BE Phase3 기능이라 실제 데이터로는 그 이후 검증 — 2026-08-29)
- [x] 명예의 전당 자리가 있고, 데이터가 없어도 에러 없이 빈 상태로 보인다 (2026-08-29 브라우저 확인)
- [x] 관련 유닛 테스트(배너/추천/Top10 API 함수 성공·실패 처리, `useLocaleStore`) 통과 (Vitest, 2026-08-29)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- 명예의 전당·Top10의 실제 데이터는 BE에 아직 없다(BE Phase3에서 채워짐). "데이터 없음"을 오류로 처리하지 않는다.
- 위치 권한 거부는 정상적인 사용자 선택이다. 거부했다고 화면이 멈추거나 강제로 다시 물어보게 만들지 않는다.
- 명소 상세 화면(Phase4)이 아직 없다. Top10·추천 항목을 클릭했을 때 이동할 곳은 임시로 처리해도 된다.
