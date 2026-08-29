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
| `src/components/BannerSlider.tsx`, `NationalityPicker.tsx`, `RecommendedSpots.tsx`, `TopPlacesCarousel.tsx`, `HallOfFameCard.tsx` | 메인 화면 구성 요소 |
| `src/pages/MainPage.tsx` | 위 컴포넌트 조합, `/` 라우트로 교체 |

국적 선택은 PRD상 "미정"이었으나, BE 번역 지원 언어가 영어만인 것에 맞춰 **한국 / 해외(영어) 2개만** 만들기로 결정 (2026-08-29, 사용자 확인). 자세한 내용은 `docs/DETAIL_SPEC.md` S-02 참고.

**Commands**
- `npm run test`: 21개 테스트 통과 (Phase 1 것 포함, Phase 2에서 10개 추가)
- `npm run lint`: passed
- `npm run build`: passed

**아직 확인 안 됨 (브라우저에서 직접 확인해야 함)**
- 배너가 실제로 보이는지 (관리자가 등록한 배너 콘텐츠가 있어야 함 — 없으면 안 보이는 게 정상)
- 국적 선택 시 화면 문구 언어가 실제로 바뀌는지
- 위치 권한 허용/거부 각각 추천 3곳이 뜨는지
- Top10 캐러셀 좌우 스크롤
- 명예의 전당 빈 상태(데이터 없을 때) 확인

## 완료 기준 체크리스트

- [ ] 배너가 보인다 (브라우저 확인 필요)
- [ ] 국적을 선택하면 화면 UI 문구의 언어가 바뀐다 (브라우저 확인 필요)
- [x] 국적을 선택하지 않으면 한국어로 보인다 (`useLocaleStore` 기본값 `ko`, `i18next` 기본 `lng: 'ko'`)
- [ ] 위치 권한을 허용하면 위치 기반 추천이 보인다 (브라우저 확인 필요)
- [ ] 위치 권한을 거부해도 화면이 깨지지 않고 대체 추천이 보인다 (브라우저 확인 필요)
- [ ] Top10 캐러셀이 좌우로 넘어간다 (브라우저 확인 필요)
- [ ] 명예의 전당 자리가 있고, 데이터가 없어도 에러 없이 빈 상태로 보인다 (브라우저 확인 필요)
- [x] 관련 유닛 테스트(배너/추천/Top10 API 함수 성공·실패 처리, `useLocaleStore`) 통과 (Vitest, 2026-08-29)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- 명예의 전당·Top10의 실제 데이터는 BE에 아직 없다(BE Phase3에서 채워짐). "데이터 없음"을 오류로 처리하지 않는다.
- 위치 권한 거부는 정상적인 사용자 선택이다. 거부했다고 화면이 멈추거나 강제로 다시 물어보게 만들지 않는다.
- 명소 상세 화면(Phase4)이 아직 없다. Top10·추천 항목을 클릭했을 때 이동할 곳은 임시로 처리해도 된다.
