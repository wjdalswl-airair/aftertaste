# Phase 11 — 기능 보완

## 목표

**그동안 미뤄뒀던 자잘한 기능 8가지를 마무리한다.**

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 로그인 이용약관 실제 내용 반영 | S-01 |
| 카카오 로그인 연결, 애플 로그인 제거 | S-01 |
| 로그인 화면 로고 추가 | S-01 |
| 배너 데이터 연동 확인 | S-02 |
| 위치 기반 권한 커스텀 모달 | S-04 |
| 명소·작품 콘텐츠 언어(`lang`) 파라미터 연동 | S-05, PRD 4장 |
| 리뷰 신고 기능 | S-07 |

> 모든 버튼 hover는 이번 범위에서 제외한다 — 프로젝트가 모바일 전용(데스크톱 미대응)이라 `:hover`가 실제로 눌리는 상황이 없다 (2026-09-04, 사용자 확인).

## 하는 일

### 1. 로그인 이용약관

- `pages/LoginPage.tsx`의 `Modal title="이용약관"` 안 "이용약관 내용은 추후 확정 예정입니다." placeholder를 사용자가 제공하는 실제 텍스트로 교체한다.
- 개인정보처리방침은 이번 범위에 없다(요청 항목 아님) — placeholder 유지.

### 2. 카카오 로그인 연결, 애플 로그인 제거

- BE가 `feature/be/kakao-login` 브랜치에 이미 구현해뒀다 (2026-09-04 기준 master 미머지 — 착수 전 머지 여부 확인).
- 로그인 흐름 (DETAIL_SPEC 5장 참고):
  1. Kakao JS SDK로 로그인 → `access_token` 획득
  2. `POST /api/account/kakao/token/`에 `{ access_token }` → `firebase_custom_token` 응답
  3. `signInWithCustomToken(auth, firebase_custom_token)`
  4. 그 결과 idToken으로 기존 `POST /api/account/login/` 호출 (Google과 동일 절차 재사용)
- `pages/LoginPage.tsx`의 Apple 버튼(`appleIcon`, `appleProvider`, `handleLogin(appleProvider)`)을 제거하고, 이미 있는 Kakao 버튼("카카오 로그인은 아직 준비 중이에요" placeholder)을 실제 동작으로 교체한다.
- `src/lib/firebase.ts`의 `appleProvider` export도 더 이상 안 쓰면 제거한다.
- `index.html`에 Kakao JS SDK `<script>` 태그 추가. 앱 키는 기존 `.env`의 `VITE_KAKAO_JS_KEY`를 그대로 쓸지, 별도 키가 필요한지 사용자가 카카오 개발자 콘솔에서 확인 후 알려주는 값을 쓴다.

### 3. 로그인 화면 로고

- `pages/LoginPage.tsx`의 로고 자리 placeholder(`<div className="h-20 w-20 rounded-full bg-ink-tertiary" />`)를 실제 로고 이미지로 교체한다.
- 로고 에셋(이미지 파일)은 사용자가 제공한다.

### 4. 배너 데이터 연동

- FE 코드(`src/api/main.ts`의 `getBanners`, `src/components/Hero.tsx`)는 이미 완성 상태다 (2026-09-04 재확인).
- 배포 서버에서 빈 배열이 오는 건 배포 DB에 배너 데이터가 없어서다 — FE 작업 불필요. 확인만 하고 넘어간다.

### 5. 위치 기반 권한 커스텀 모달 (완료 — 2026-09-04)

- Figma node-id `102:702` 기준으로 `src/components/LocationPermissionModal.tsx`를 만들었다.
- `src/hooks/useGeolocation.ts`가 더 이상 마운트 즉시 브라우저 네이티브 팝업을 안 띄우고, 모달에서 "허용"을 눌러야(`handleAllow`) `getCurrentPosition`을 호출한다. "거부"(`handleDeny`)는 브라우저 API를 아예 안 부르고 바로 `denied` 처리.
- 응답은 `localStorage`(`location-permission-consent`)에 저장 — 거부 시 재요청하지 않는 기존 규칙(PHASE2.md)을 모달 단계까지 확장했다.

### 6. 명소·작품 콘텐츠 언어(`lang`) 파라미터 연동

- BE `resolve_language()`는 `쿼리파라미터 lang → 로그인 회원의 언어 → 한국어` 순으로 응답 언어를 정한다 (DETAIL_SPEC 7장).
- 로그인 사용자는 서버가 회원 `language`로 자동 처리하지만, **비로그인 사용자는 FE가 `lang` 파라미터를 직접 안 보내면 항상 한국어 원문**이 온다.
- `useLocaleStore`의 현재 언어 값을 명소·작품 관련 API 호출(`src/api/spots.ts`, `src/api/works.ts`, `src/api/search.ts` 등 `?lang=`을 이미 지원하는 엔드포인트)에 붙인다.
- **리뷰 번역은 이번 범위에서 제외한다.** BE `ReviewTranslation` 모델은 있지만 `reviews/views.py`가 아직 이를 조회/반환하지 않는다 (2026-09-04 확인) — BE 작업이 선행되어야 하므로 별도로 논의한다.

### 7. 리뷰 신고

- `POST /api/reviews/{id}/report/`는 이미 master에 구현·머지되어 있다 (로그인 필요, 같은 사람 중복 신고는 1건으로 카운트, 서로 다른 5명이 신고하면 자동 숨김).
- `src/api/reviews.ts`에 신고 API 함수를 추가한다.
- 리뷰 상세/카드(리뷰 더보기·상세 화면)에 신고 버튼을 추가한다. 비로그인 상태면 다른 로그인 필요 기능과 동일하게 "로그인이 필요한 기능입니다" 안내 후 `/login`으로 이동.
- 신고 성공 시 별도 문구 없이 조용히 처리(좋아요·즐겨찾기와 동일한 멱등 규약 — 이미 신고한 리뷰를 또 신고해도 에러 아님).

## 완료 기준 체크리스트

- [ ] 로그인 화면 이용약관 모달에 실제 텍스트가 보인다
- [x] 카카오 버튼을 누르면 authorize()로 인가 코드까지는 받아온다 — **다만 BE가 code→access_token 교환을 추가하기 전까지는 실제 로그인 완료는 안 됨** (GitHub 이슈 등록, BE 작업 대기 중)
- [ ] 로그인 화면에 로고 이미지가 보인다 (더 이상 회색 placeholder 아님)
- [x] 배너 데이터 연동 상태 확인 완료 (FE 코드 변경 없음 확인)
- [x] 위치 정보 요청 전 커스텀 설명 모달이 뜨고, 동의해야 네이티브 권한 팝업이 뜬다
- [x] 비로그인 상태에서 언어를 바꾸면 명소·작품 콘텐츠(설명 등)가 해당 언어로 보인다
- [x] 리뷰에 신고 버튼이 있고, 신고가 정상 접수된다
- [x] 관련 유닛 테스트(카카오 로그인 API 함수, 리뷰 신고 API 함수 성공/실패 처리) 통과 (Vitest)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- 카카오 로그인 BE 브랜치(`feature/be/kakao-login`)가 master에 머지됐는지 확인한다. 안 됐으면 BE 담당자에게 머지 일정을 확인한다.
- 리뷰 번역(사용자 작성 리뷰의 다국어 표시)은 BE 미구현이라 이번 Phase에서 다루지 않는다. PRD 4장 요구사항이 아직 완전히 충족되지 않았다는 걸 기억해둔다.
- 이 Phase는 기존 로드맵(Phase1~10)과 별개로, 미뤄뒀던 항목들을 모은 것이다. 완료 후 PRD/DETAIL_SPEC의 관련 절이 실제 구현과 맞는지 다시 확인한다.
