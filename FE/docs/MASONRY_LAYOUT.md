# 리뷰 피드 매스너리(핀터레스트 스타일) 레이아웃

리뷰 탭(`ReviewFeedPage.tsx`)의 사진 목록을 핀터레스트처럼 카드 높이가 들쭉날쭉한 레이아웃으로 만든 과정과 이유를 기록한다. (2026-09-13)

## 목적

하단 탭 "리뷰"(전체 명소 리뷰 피드)의 사진 목록을 사용자가 제공한 참고 이미지(핀터레스트 UI 목업)처럼 만들기 위함. 원래는 3열 정사각형 그리드(`grid grid-cols-3` + `aspect-square`)였는데, 이걸 카드마다 높이가 다르게 어긋나며 쌓이는 매스너리(waterfall) 레이아웃으로 바꿨다.

## 기능 선택 이유

- **사진 원본 비율 유지**: 정사각형으로 자르지 않고 원본 비율 그대로 보여줄 수 있다.
- **콘텐츠 특성과 어울림**: 여러 명소의 리뷰 사진이 섞여 나오는 화면이라, 다양한 비율의 사진이 자연스럽게 섞여 나오는 매스너리가 더 잘 맞는다.
- **새 라이브러리 없이 구현 가능해야 함**: `CLAUDE.md` 규칙상 새 라이브러리는 승인 후 추가해야 해서, 처음부터 라이브러리 없이 되는 방법을 우선 검토했다.

## 구현 방법

### 1차 시도 — CSS `columns-2` (다단 레이아웃)

```tsx
<div className="columns-2 gap-2">
  {reviews.map((review) => (
    <Link className="relative mb-2 block break-inside-avoid overflow-hidden rounded-md">
      <img className="block h-auto w-full object-cover" ... />
    </Link>
  ))}
</div>
```

- `columns-2`: 신문 지면처럼 내용을 2개 세로줄로 자동으로 흘려보낸다.
- `h-auto`(이미지에 고정 높이를 안 줌): 사진 원본 비율이 그대로 나와 카드마다 높이가 달라진다.
- `break-inside-avoid`: 카드 하나가 단 경계에서 잘려 다음 줄로 이어지는 걸 막는다.
- CSS Grid로는 이 효과를 못 낸다 — Grid는 같은 행의 칸 높이를 서로 맞추려는 성질이 있어서, 칸을 자유롭게 다른 높이로 어긋나게 쌓을 수 없다(Firefox의 실험적 `grid-template-rows: masonry`는 다른 브라우저 미지원).

**한계**: `columns`는 전체 내용의 높이를 다시 계산해서 두 단에 "균형 있게" 나누는 방식이라, "더보기"로 리뷰가 追加될 때마다 이미 화면에 있던 카드까지 재배치되며 흔들린다. 리뷰(사진) 개수가 앞으로 계속 늘어날 예정이라 이 문제가 더 자주, 더 크게 나타날 것으로 판단해 방식을 바꿨다.

### 2차 시도(최종) — 인덱스 기반 2칸 고정 배치

```tsx
const columns = [0, 1].map((columnIndex) =>
  reviews.filter((_, index) => index % 2 === columnIndex)
)

<div className="flex gap-2">
  {columns.map((column, columnIndex) => (
    <div key={columnIndex} className="flex flex-1 flex-col gap-2">
      {column.map((review) => <ReviewFeedCard key={review.id} review={review} />)}
    </div>
  ))}
</div>
```

- 리뷰 배열을 `index % 2`로 두 배열(칸)에 미리 나눈 뒤, 각 칸을 `flex flex-col`로 세로로 쌓는 평범한 2단 레이아웃.
- 새 리뷰는 자기 인덱스에 따라 항상 정해진 칸의 **끝에만** 추가되므로, 이미 렌더링된 카드는 절대 위치가 안 바뀐다 — "더보기"를 아무리 눌러도 기존 카드가 안 흔들린다.
- 트레이드오프: 진짜 매스너리(그 순간 제일 짧은 칸에 새 카드를 넣는 방식)만큼 두 칸의 높이가 정교하게 안 맞을 수 있다. 대신 안정성(재배치 없음)을 우선했다.

## 라이브러리를 검토했지만 안 쓴 이유

- **`react-masonry-css` / `react-plock`**: 실제로는 이미지 높이를 측정하지 않고 순서대로 칸에 나눠 넣는 라운드로빈 방식이다 — 지금 구현한 "인덱스 기반 2칸 고정 배치"와 배치 결과가 사실상 동일하다. 반응형 브레이크포인트별 칸 수 설정 등 API는 편해지지만, 이번 규모에서는 도입 실익이 없다고 판단했다.
- **`masonry-layout`(원조 Masonry.js) + `imagesloaded`**: 이미지가 실제로 로드된 뒤 높이를 측정해서 그 순간 제일 짧은 칸에 배치하는, 진짜 정교한 매스너리다. 대신 jQuery 시절의 imperative(DOM 직접 조작) 라이브러리라 React에 물리려면 별도 wrapper가 필요하고 무게도 더 나간다 — 리뷰 피드 하나 때문에 들이기엔 과하다고 판단해 채택하지 않았다.

## 해결한 문제

| 문제 | 해결 |
|---|---|
| 정사각형 크롭으로 사진이 잘림 | 이미지에 `h-auto`를 줘서 원본 비율 그대로 표시 |
| `columns-2`가 "더보기" 때마다 기존 카드까지 재배치함 | 인덱스(`index % 2`) 기반으로 칸을 미리 나눠 고정 배치 |
| 새 라이브러리 추가 승인 절차 없이 구현 | 순수 CSS(1차) → 순수 React 로직(2차)만으로 완성, `package.json` 변경 없음 |

## 관련 파일

- `FE/src/pages/ReviewFeedPage.tsx` — `ReviewFeedCard`(카드 하나), `ReviewFeedSkeleton`(로딩 스켈레톤도 같은 2칸 구조)
