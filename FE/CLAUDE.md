# 프로젝트 개요

사용자에게 영화/드라마 촬영 명소에 대한 추천과 정보를 제공하는 웹서비스.
촬영 명소 주변의 상권들을 포함한 추천 관광코스를 추천하는 웹서비스.

서비스 전체 배경은 `../BE/docs/PRD.md` 1장(서비스 개요)을 참고한다. 이 문서와 `docs/` 아래 문서는 **프론트엔드 관점**의 기준 문서다.

# 내 담당 범위

- 나는 이 프로젝트에서 **프론트엔드**를 담당한다.
- 백엔드(Django/DRF)는 다른 팀원(과거 세션)이 담당했으므로, 요청받지 않는 한 `../BE` 아래 코드는 작성하거나 수정하지 않는다.
- 백엔드 API 스펙은 `../BE/docs/DETAIL_SPEC.md`, `../BE/docs/PHASES/`를 참고용으로 확인한다. 실제 엔드포인트가 문서와 다르면 임의로 맞추지 말고 먼저 확인한다.

# 기준 문서

- `docs/PRD.md` — 무엇을 만들지 정한 문서. FE 화면·사용자 행동 관점의 기능 목록, 로그인 필요 여부.
- `docs/DETAIL_SPEC.md` — 어떻게 만들지 정한 문서. 화면 구성, 컴포넌트, API 연동, 상태 관리 규칙.
- `docs/PHASES/PHASE*.md` — 어떤 순서로 만들지 정한 문서. 단계별 작업 범위와 완료 기준 체크리스트.
- `docs/compound-log.md` — 반복된 실수와 하네스 개선 이력을 누적 기록한 문서. 같은 실수를 반복하지 않으려면 이 문서도 함께 확인한다.
- `../BE/karpathy-guidlines.md` — LLM 코딩 행동 지침. BE와 공유한다.

구현 전에 위 문서를 먼저 확인한다. 문서와 다르게 만들어야 할 이유가 생기면 임의로 진행하지 말고 먼저 물어본다.
결정이 바뀌면 코드보다 문서를 먼저 고친다.

## PHASES 사용 규칙

- 지금 어느 Phase를 하는지 먼저 확인하고, **그 Phase 범위 밖의 기능은 만들지 않는다.**
- 작업이 끝나면 해당 Phase 문서의 완료 기준 체크리스트로 확인한다. 체크리스트를 통과하지 못한 상태로 다음 Phase로 넘어가지 않는다.
- 체크 항목을 직접 확인하지 않고 "된 것 같다"로 표시하지 않는다.

# 기술 스택

- Frontend: React 19 + TypeScript, Vite
- 라우팅: React Router (화면 단위 페이지 분리)
- 상태 관리: Zustand
- 스타일: Tailwind CSS (색상·간격·radius는 Figma "Yeoun Design System"의 토큰을 `src/index.css`의 `@theme`에 반영)
- 아이콘: lucide-react
- 지도: 카카오맵 공식 JS SDK (`<script>` 태그로 직접 로드)
- 다국어: react-i18next
- Lint: oxlint
- Backend: Django REST Framework (별도 저장소 위치: `../BE`)
- 인증: Firebase Authentication. 토큰은 Firebase Auth SDK가 자체 관리(`onAuthStateChanged`)하며, FE에서 직접 저장하지 않는다.
- 화면 지원 범위: 모바일 전용 (데스크톱 대응 안 함)

# Commands

- install: `npm install`
- dev: `npm run dev`
- build: `npm run build`
- lint: `npm run lint`
- preview: `npm run preview`

테스트 러너는 아직 미도입 상태다. 테스트 프레임워크 도입은 별도로 논의하고 결정한 뒤 이 섹션을 갱신한다.

# Code Style

- TypeScript를 사용한다. `any`는 꼭 필요한 경우가 아니면 쓰지 않는다.
- 컴포넌트는 작게 유지한다.
- API 호출은 `src/api`에 작성한다.
- 공통 로직은 `src/utils` 또는 `src/hooks`에 분리한다.
- 코드 주석은 비전공자/신입 팀원도 이해할 수 있도록 쉬운 단어로 간결하게 작성한다.

# Security Rules

- `.env` 파일은 수정하지 않는다.
- 인증키·API 키는 코드에 직접 작성하지 않는다.
- 새로운 라이브러리는 승인 후 추가한다.
- 배포 명령은 명시적 승인 없이 실행하지 않는다.

# Workflow Rules

0. `../BE/karpathy-guidlines.md`에 명시된 가이드라인을 반드시 준수한다.
1. 지시받은 것 외의 어떤 것도 임의로 정하거나 진행하지 않는다.
2. 명확하지 않은 문제나 선택지가 있으면 먼저 사용자에게 물어보고 진행한다.
3. 구현 전에 반드시 관련 문서를 읽는다.
4. 구현 전에 먼저 Plan을 작성한다.
5. 한 번에 하나의 Phase만 구현한다.
6. 구현 후 lint와 build를 실행한다.
7. 변경 사항은 문서에 기록한다.
8. 기존 기능을 수정해야 하면 먼저 이유를 설명하고 승인을 받는다.
9. 사용자에게 코드나 결정사항을 설명할 때도 쉬운 단어로 단순명료하게 설명한다.
