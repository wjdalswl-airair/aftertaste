# Phase 1 — 로그인

## 목표

**소셜 로그인이 된다.** 이후 로그인이 필요한 모든 화면(즐겨찾기, 리뷰, 마이페이지 등)의 전제조건이라 가장 먼저 만든다.

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 소셜 로그인 (Google, Apple) | S-01 |
| 로그인 상태 유지 (재방문 시 자동 로그인) | S-01 |
| 로그인이 필요한 화면에 대한 공통 가드 | S-01 |

> Kakao 로그인은 PRD에서 이번 범위 제외로 결정됨 — **실제 로그인 기능은 만들지 않는다.**
> (2026-08-30 변경) 다만 BE DETAIL_SPEC 6-1 #19("프론트엔드가 이미 붙여 뒀으면 나중에 백엔드를 추가한다")에 맞춰, 버튼 UI만 미리 만들어뒀다. 눌러도 "카카오 로그인은 아직 준비 중이에요" 안내만 뜨고 실제 로그인은 안 됨 (Firebase Kakao 프로바이더도, BE 연동도 없음).
> 다른 화면(메인, 검색 등)은 아직 없으므로, 로그인 성공 후 이동할 화면은 임시로 처리해도 된다.
> (2026-08-30 추가) 로그인 화면 하단 "이용약관"/"개인정보처리방침" 문구를 각각 누르면 모달이 뜨지만, **내용은 "추후 확정 예정" 플레이스홀더**다. 실제 법적 문구는 개인정보보호법상 필수 항목(수집 항목·목적·보관기간·제3자 제공 등)이 있어 임의로 작성하지 않았다 — 팀에서 확정한 뒤 `src/pages/LoginPage.tsx`의 `Modal` 내용을 채워야 한다.

## 하는 일

### 1. Firebase 초기화 및 소셜 로그인 받기

- `src/lib/firebase.ts`에서 Firebase 앱을 초기화한다. API 키 등은 `.env`에서 읽고 코드에 직접 쓰지 않는다 (CLAUDE.md Security Rules).
- Google/Apple 로그인은 Firebase Auth SDK가 처리한다. 로그인 성공 시 Firebase가 idToken을 발급한다.
- `onAuthStateChanged`로 로그인 상태 변화를 감지해 `useAuthStore`에 반영한다.

### 2. 서버에 회원 등록/조회 요청

- 발급받은 idToken으로 `POST /api/account/login/`을 호출한다 (`src/api/auth.ts`).
- 이미 있는 회원이면 `agree_terms` 없이 호출한다 (200 응답).
- 처음 온 회원이면 약관 동의를 받은 뒤 `{ agree_terms: true }`와 함께 호출한다 (201 응답). 동의 없이 호출하면 400이 온다.
- 응답으로 받은 회원 정보(`MemberSerializer` 필드)를 `useAuthStore`에 저장한다.

### 3. 로그인 여부 판단하는 공통 장치

- 로그인이 필요한 라우트를 감싸는 `RequireAuth` 컴포넌트를 만든다.
- 비로그인 상태로 접근하면 "로그인이 필요한 기능입니다"를 보여준 뒤 `/login`으로 보낸다.
- 다른 화면(즐겨찾기, 리뷰 등)이 아직 없으므로, 이 장치는 만들어만 두고 실제로 어디에 씌울지는 다음 Phase에서 정한다.

## 진행 상황 (2026-08-19)

**구현 완료.** 아래 파일에 나눠서 만듦.

| 파일 | 역할 |
|---|---|
| `src/lib/firebase.ts` | Firebase 초기화, Google/Apple 프로바이더 |
| `src/api/auth.ts` | `POST /api/account/login/`, `GET /api/account/` 호출 |
| `src/store/useAuthStore.ts` | 로그인한 회원 정보(Zustand) |
| `src/hooks/useInitAuth.ts` | 앱 시작 시 Firebase 로그인 상태 감지 → 서버 회원 정보 동기화 |
| `src/components/RequireAuth.tsx` | 로그인 가드 |
| `src/pages/LoginPage.tsx` | Google/Apple 로그인 버튼 |
| `src/App.tsx`, `src/main.tsx` | 라우터 연결 (`/`, `/login`, 가드로 감싼 임시 `/mypage`) |
| `src/vite-env.d.ts` | `.env` 변수 타입 |

**Commands**
- `npm run lint`: passed
- `npm run build`: passed
- `npm run dev`로 실제 띄워서 모든 모듈이 에러 없이 로드되고 `.env` 값이 앱에 주입되는 것까지 확인함

**브라우저 확인 완료 (2026-08-29)**
- Google 로그인 버튼 → 팝업 로그인 성공, `POST /api/account/login/` 200/201 응답 확인
- 새로고침해도 로그인 상태 유지됨
- 비로그인 상태로 `/mypage` 접근 시 안내 후 `/login`으로 이동함

**보류 (2026-08-29)**
- Apple 로그인: Firebase 콘솔에서 활성화하려면 Apple Developer Program 가입(연 $99)이 필요함을 확인. 실제로 버튼을 누르면 `auth/operation-not-allowed` 에러가 남 (계정 없음 → Firebase 콘솔에서 Apple 프로바이더 활성화 자체가 안 된 상태). 버튼/코드는 이미 만들어져 있으니 Apple Developer 계정이 생기면 Firebase 콘솔에서 활성화만 하면 됨. 이 단계에서는 Google 로그인만으로 완료 처리하고 넘어가기로 결정.

**결정 완료 (2026-08-29)**
- 약관 동의는 "로그인 버튼 = 동의"로 암묵 처리하기로 결정. 별도 체크박스/동의 화면 없음.
- 코드는 이미 이 방식으로 구현되어 있었음(`src/api/auth.ts`의 `loginWithFirebase()`가 항상 `agree_terms: true` 전송, `LoginPage.tsx`에 안내 문구 있음). 추가 구현 불필요.
- 이 결정에 따라 "약관 동의 없이 진행 시 400 처리" 체크리스트 항목은 해당 없음(N/A) — 항상 동의 상태로 보내므로 이 케이스 자체가 발생하지 않음.

**유닛 테스트 작성 완료 (2026-08-29)**
- Vitest, jsdom, @testing-library/react, @testing-library/jest-dom 설치
- `src/store/useAuthStore.test.ts`: 초기 상태, `setMember`, `setLoading`
- `src/api/auth.test.ts`: 로그인 성공, idToken 없을 때 에러, 서버 실패 응답 처리, `getMe`
- `src/components/RequireAuth.test.tsx`: 로딩 중 / 비로그인 시 `/login` 리다이렉트 / 로그인 시 보호된 화면 노출
- `npm run test`: 11개 테스트 통과

**남은 일**
- (보류) Apple Developer 계정 생기면 Firebase 콘솔에서 Apple 로그인 활성화 후 브라우저 확인

## 완료 기준 체크리스트

- [x] Google 계정으로 로그인하면 서버에 회원이 생성되거나 조회된다 (2026-08-29 브라우저 확인)
- [ ] Apple 계정으로 로그인하면 서버에 회원이 생성되거나 조회된다 (보류: Apple Developer 계정 필요, 연 $99. 코드는 완료됨)
- [x] 처음 로그인하는 사용자는 약관 동의 화면을 거치고, 동의해야만 가입이 완료된다 (로그인 버튼 클릭 = 동의로 암묵 처리, 로그인 화면에 안내 문구 있음)
- [x] N/A — 약관 동의 없이 진행하는 케이스 자체가 없음 (버튼 클릭이 곧 동의이므로 항상 `agree_terms: true` 전송)
- [x] Kakao 로그인 기능은 만들지 않았다 (2026-08-30: 버튼 UI만 추가, 클릭해도 실제 로그인은 안 됨 — 위 참고)
- [x] 로그인한 뒤 새로고침해도 로그인 상태가 유지된다 (Firebase `onAuthStateChanged` 기준) (2026-08-29 브라우저 확인)
- [x] 토큰을 `localStorage` 등에 직접 저장하는 코드가 없다 (Firebase SDK가 자체 관리)
- [x] 로그인이 필요한 라우트에 비로그인 상태로 접근하면 "로그인이 필요한 기능입니다" 안내 후 `/login`으로 이동한다 (2026-08-29 브라우저 확인)
- [x] 관련 유닛 테스트(인증 API 함수 성공/실패, `useAuthStore`, `RequireAuth` 가드) 통과 (Vitest, 2026-08-29, 11개 통과)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- **Firebase 로그인 성공 ≠ 우리 서비스 회원가입 완료.** Firebase 인증(구글/애플이 이 사람이 맞다고 확인)과 `POST /api/account/login/` 호출(우리 서버에 회원으로 등록)은 별개 단계다. Firebase 로그인만 되고 서버 호출을 빠뜨리면, 이후 화면에서 "로그인은 됐는데 내 정보가 없는" 상태가 된다.
- 이 단계에서는 로그인 성공 후 보여줄 진짜 메인 화면이 아직 없다. 확인은 로그인 자체(서버 응답, 상태 저장)로만 하고, 화면 전환은 임시 화면으로 대체해도 된다.
- 국적·언어 선택 화면(S-02)은 아직 없다. 로그인 직후 국적을 묻지 않는다 — PRD 기준 국적 선택은 메인 화면(Phase 2)의 몫이다.
