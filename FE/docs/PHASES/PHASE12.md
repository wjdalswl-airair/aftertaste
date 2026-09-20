# Phase 12 — 날씨 위젯

## 목표

**메인 화면(내 위치)과 명소 상세 화면(명소 위치)에 날씨 위젯을 추가한다.**

이 결정은 `../BE/docs/PRD.md` #87, `../BE/docs/DETAIL_SPEC.md` #24에 2026-08-28에 이미 "홈 화면 날씨 위젯은 백엔드 작업 없이 FE가 위치 정보로 날씨 API를 직접 호출한다"고 기록돼 있었지만, 그동안 어느 Phase에도 포함되지 않고 있었다. 이번에 그 결정을 실제로 구현하면서, 명소 상세 화면까지 범위를 넓힌다.

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 메인 화면 날씨 위젯(내 위치, 위치 거부 시 서울로 대체) | S-02 |
| 명소 상세 날씨 칩(명소 위치) | S-05 |

## 상세 설계

`docs/DETAIL_SPEC.md` S-02 "날씨 위젯" 항목, S-05 "날씨 칩" 항목 참고.

- 신규 파일: `src/api/weather.ts`, `src/api/weather.test.ts`, `src/hooks/useWeather.ts`, `src/components/WeatherWidget.tsx`
- 수정 파일: `src/pages/MainPage.tsx`(위치 권한 요청을 여기서 한 번만 소유하도록 리팩터), `src/components/RecommendedSpots.tsx`(자체 `useGeolocation` 호출 제거, props로 전환), `src/pages/SpotDetailPage.tsx`(날씨 칩 추가)
- 새 env 키 **`VITE_OPENWEATHER_API_KEY`** 필요 — `.env`는 직접 수정하지 않으므로 사용자가 https://openweathermap.org 에서 무료 키를 발급받아 직접 추가해야 한다. 키가 없으면 위젯이 조용히 안 보인다(에러 없이 화면은 정상).

## 완료 기준 체크리스트

- [x] 메인 화면에 위치 허용 시 실제 좌표 기준 날씨가 보인다
- [x] 메인 화면에서 위치를 거부해도(또는 아직 응답 전이어도) 위젯이 사라지지 않고 서울 날씨를 보여준다
- [x] 명소 상세 화면 이름/별점 줄 옆에 날씨 칩이 보인다(좌표 없는 명소는 칩이 안 보임)
- [x] `RecommendedSpots`의 기존 동작(위치 거부 시 섹션 숨김, 동 이름 표시 등)이 그대로 유지된다 — 위치 권한 요청을 `MainPage`로 옮기는 리팩터 이후에도 동일하게 동작
- [x] 위치 권한 동의 모달이 중복으로 뜨지 않는다(메인 화면에 딱 한 번만)
- [x] 관련 유닛 테스트(`weather.test.ts`: 성공 매핑, condition code 그룹 매핑, 키 없음/실패 시 에러) 통과 (Vitest)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- `.env`에 `VITE_OPENWEATHER_API_KEY`를 넣어야 브라우저에서 실제 날씨 데이터로 확인할 수 있다 — 키 발급 및 추가는 사용자 몫.
- API 키가 FE 번들에 노출되는 구조를 사용자가 인지하고 동의함(2026-09-20). 이후 키 남용·쿼터 문제가 생기면 백엔드 프록시로 전환을 재검토한다(원 결정문 참고).
