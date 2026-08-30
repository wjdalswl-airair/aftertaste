# Phase 6 — 리뷰

## 목표

**로그인한 사용자가 리뷰를 작성·수정·삭제할 수 있다.**

## 이 단계에서 만드는 것

| 기능 | PRD 번호 |
|---|---|
| 리뷰 작성 (별점·텍스트·사진) | S-07 |
| 내 리뷰 수정·삭제 | S-07 |
| 리뷰 더보기 목록, 리뷰 상세, 좋아요 | (Figma엔 있으나 PRD/원안엔 없던 화면, 2026-08-30 사용자 확인 후 포함) |

> 좋아요, 신고 기능은 이번 범위에 없다. Figma "메모"에 있던 항목이지만 PRD 결정상 아직 범위에 넣지 않기로 했다.
> (2026-08-30 변경) 사용자가 공유한 Figma 목업에 "리뷰 더보기"/"리뷰 상세" 화면이 있었고 좋아요(하트) UI가 포함돼 있었다. BE에 좋아요 API(`ReviewLikeView`)가 이미 구현돼 있어서, 사용자 확인 후 **좋아요는 이번 Phase에 포함**하기로 결정했다(신고는 목업에도 없어서 계속 범위 밖). 그래서 아래 "좋아요·신고 버튼은 화면에 없다" 체크 항목은 신고에만 해당한다.

## 하는 일

### 1. 리뷰 작성

- `POST /spots/{spotId}/reviews` (계획) 로 별점·텍스트·사진을 보낸다.
- 명소 상세(Phase4)의 리뷰 목록에 작성한 리뷰가 나타나도록 연결한다.

### 2. 내 리뷰 수정·삭제

- `PATCH /reviews/{reviewId}`, `DELETE /reviews/{reviewId}` (둘 다 계획).
- **본인이 쓴 리뷰에만** 수정·삭제 버튼을 보여준다. 남의 리뷰에는 버튼 자체를 노출하지 않는다 (서버도 403으로 막지만, 화면에서부터 막아 이중으로 방어한다).

## 진행 상황 (2026-08-30)

**구현 완료.** Figma 목업 5개(별점 등록/리뷰 등록/리뷰 더보기/리뷰 상세/리뷰 수정·삭제)를 사용자가 공유해줘서 그 기준으로 만들었다.

| 파일 | 역할 |
|---|---|
| `src/api/reviews.ts` | `getPlaceReviews`/`createReview`/`updateReview`/`deleteReview`/`likeReview`/`unlikeReview` |
| `src/lib/reviewPhotoUpload.ts` | 리뷰 사진 Firebase Storage 업로드 |
| `src/components/RatingModal.tsx` | "별점 등록" 모달 (별점만 고르고 작성 화면으로 이동) |
| `src/pages/ReviewFormPage.tsx` | 리뷰 작성/수정 겸용 (`/spots/:placeId/reviews/new`, `/spots/:placeId/reviews/:reviewId/edit`) |
| `src/pages/ReviewListPage.tsx` | 리뷰 더보기, 최신순/인기순 (`/spots/:placeId/reviews`) |
| `src/pages/ReviewDetailPage.tsx` | 리뷰 상세 + 수정/삭제 바텀시트 (`/spots/:placeId/reviews/:reviewId`) |

목업과 실제 BE 모델·API가 안 맞는 부분(별점 단독 등록 API 없음, 리뷰 단건 조회 API 없음, "내가 쓴 글인지" 필드 없음 등)은 `docs/DETAIL_SPEC.md` S-07에 자세히 기록해뒀다.

**브라우저 확인 못 함**: 로그인 필요한 흐름이라 이번 세션에서 Claude in Chrome 없이는 직접 확인 못 했다. 코드/테스트로만 확인했다.

## 완료 기준 체크리스트

- [x] (코드로 확인, 브라우저 확인 필요) 로그인한 사용자가 별점+텍스트로 리뷰를 작성할 수 있다
- [x] (코드로 확인, 브라우저 확인 필요) 사진을 첨부할 수 있다 (Firebase Storage 업로드)
- [x] (코드로 확인, 브라우저 확인 필요) 작성한 리뷰가 명소 상세의 리뷰 목록에 나타난다
- [x] (코드로 확인, 브라우저 확인 필요) 본인 리뷰에만 수정·삭제 버튼이 보인다 — 단, "본인 여부" 판단이 닉네임 비교라 정확하지 않음(DETAIL_SPEC 갭 참고)
- [x] 남의 리뷰에는 수정·삭제 버튼이 보이지 않는다 (위와 동일한 갭 있음)
- [x] 비로그인 상태에서 작성을 시도하면 "로그인이 필요한 기능입니다"가 뜬다 (`RequireAuth` + 버튼 클릭 시 체크)
- [x] 신고 버튼은 화면에 없다 (좋아요는 2026-08-30 사용자 확인 후 포함, 위 "이 단계에서 만드는 것" 참고)
- [x] 관련 유닛 테스트(리뷰 작성/수정/삭제/좋아요 API 함수 성공·실패 처리) 통과 (Vitest, 총 55개)
- [x] `npm run lint`, `npm run build` 통과

## 넘어가기 전 확인

- 리뷰 글자 수·사진 장수 제한은 BE가 이미 500자·5장으로 확정했다(`REVIEW_CONTENT_MAX_LENGTH`, `REVIEW_MAX_PHOTOS`, `reviews/models.py`) — 더 이상 미정 아님.
- 리뷰 번역 표시는 BE가 이미 번역해서 내려주는 값을 그대로 보여주면 된다. FE에서 다시 번역하지 않는다.
- "내가 쓴 리뷰인지" 판단을 닉네임 비교로 임시 처리했다 — 다음 Phase 전에 BE에 정확한 필드 추가를 요청할 것.
