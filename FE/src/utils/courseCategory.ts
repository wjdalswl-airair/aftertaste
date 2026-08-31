import type { CoursePlaceRole } from '../api/courses'

// 코스 생성 화면의 카테고리 탭 3개. BE가 준 nearby_places(카카오 카테고리 문자열)를
// 이 탭들로 나눠 보여준다 — 정확한 매핑 기준은 없어서 카테고리 문자열 키워드로 대략 분류한다.
export type CourseCategoryTab = 'FOOD_CAFE' | 'EXPERIENCE' | 'NEARBY'

export function classifyNearbyPlace(categoryName: string | null): CourseCategoryTab {
  const name = categoryName ?? ''
  if (name.includes('음식점') || name.includes('카페')) {
    return 'FOOD_CAFE'
  }
  if (name.includes('체험') || name.includes('공방') || name.includes('교육')) {
    return 'EXPERIENCE'
  }
  return 'NEARBY'
}

// 후보를 실제로 코스에 추가할 때 어떤 role(RESTAURANT/CAFE/OTHER)로 들어갈지 정한다.
// "체험·공방"/"주변 명소" 탭에서 고른 건 전부 OTHER로 들어간다(코스는 역할이 3개뿐이라서).
export function getCoursePlaceRole(categoryName: string | null): CoursePlaceRole {
  const name = categoryName ?? ''
  if (name.includes('카페')) {
    return 'CAFE'
  }
  if (name.includes('음식점')) {
    return 'RESTAURANT'
  }
  return 'OTHER'
}
