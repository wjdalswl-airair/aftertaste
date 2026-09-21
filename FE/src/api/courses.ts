import { authorizedFetch } from './auth'
import { publicFetch } from './client'

export type CoursePlaceRole = 'RESTAURANT' | 'CAFE' | 'OTHER'

export type CoursePlace = {
  id: number
  role: CoursePlaceRole
  order: number
  name: string
  address: string
  road_address_name: string
  latitude: number
  longitude: number
  category_name: string
  kakao_place_id: string | null
}

export type Course = {
  id: number
  place_id: number
  place_name: string
  creator_nickname: string | null
  title: string
  description: string
  course_places: CoursePlace[]
  created_at: string
  updated_at: string
}

export type CoursePlaceInput = {
  role: CoursePlaceRole
  name: string
  address: string
  road_address_name: string
  latitude: number
  longitude: number
  category_name: string
  kakao_place_id: string | null
}

export type CourseInput = {
  title: string
  description: string
  course_places: CoursePlaceInput[]
}

// 명소 기준 코스 목록. 로그인 여부와 상관없이 조회 가능.
export function getPlaceCourses(placeId: number): Promise<Course[]> {
  return publicFetch<{ courses: Course[] }>(`/api/places/${placeId}/courses/`).then((res) => res.courses)
}

export function createCourse(placeId: number, input: CourseInput): Promise<Course> {
  return authorizedFetch<Course>(`/api/places/${placeId}/courses/`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

// 코스 상세. 로그인 여부와 상관없이 조회 가능.
export function getCourseDetail(courseId: number): Promise<Course> {
  return publicFetch<Course>(`/api/courses/${courseId}/`)
}

// 작성자 본인만 삭제 가능(403). 리뷰와 달리 이미 지워진 코스를 또 지우면 404를 그대로 던진다.
export function deleteCourse(courseId: number): Promise<void> {
  return authorizedFetch<void>(`/api/courses/${courseId}/`, { method: 'DELETE' })
}

// 작성자 본인만 수정 가능(403). 성공하면 본문 없이 204 — 최신 코스는 getCourseDetail로 다시 받는다.
export function updateCourse(courseId: number, input: CourseInput): Promise<void> {
  return authorizedFetch<void>(`/api/courses/${courseId}/`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

// 내가 만든 코스 목록 (마이페이지).
export function getMyCourses(): Promise<Course[]> {
  return authorizedFetch<{ courses: Course[] }>('/api/account/courses/').then((res) => res.courses)
}

// 코스 탭 전체 목록용 요약 표현 (issue #74). 코스 자체엔 좌표가 없어서 기준 명소(anchor place)의
// 좌표를 그대로 쓴다. 상세 화면(Course)과 달리 course_places는 안 온다 — 목록에선 안 씀.
export type CourseSummary = {
  id: number
  title: string
  place_id: number
  place_name: string
  latitude: number | null
  longitude: number | null
  favorite_count: number
  created_at: string
}

export type CourseFeedPage = {
  count: number
  next: string | null
  previous: string | null
  courses: CourseSummary[]
}

// 코스 탭 전체 코스 목록. 페이지당 20개, 최신순, 로그인 불필요 (issue #74).
export function getCourseFeed(page = 1): Promise<CourseFeedPage> {
  const params = new URLSearchParams({ page: String(page) })
  return publicFetch<CourseFeedPage>(`/api/courses/?${params}`)
}

// AI(Claude)가 주변 상권 중에서 식당 1 + 카페 1 + 그 외 1을 골라 코스를 만들어준다. 로그인 필요.
// 실패하면 BE가 상황별 한국어 메시지를 detail로 준다(400 이미 코스 있음 / 422 후보 부족 / 503 AI 호출 실패) —
// authorizedFetch가 그 메시지를 그대로 Error.message로 던지므로 호출부에서 그대로 보여주면 된다.
export function aiRecommendCourse(placeId: number): Promise<Course> {
  return authorizedFetch<Course>(`/api/places/${placeId}/courses/ai-recommend/`, { method: 'POST' })
}
