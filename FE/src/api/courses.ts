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

// 내가 만든 코스 목록 (마이페이지).
export function getMyCourses(): Promise<Course[]> {
  return authorizedFetch<{ courses: Course[] }>('/api/account/courses/').then((res) => res.courses)
}
