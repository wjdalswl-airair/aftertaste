import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

// vi.mock은 파일 최상단으로 끌어올려지므로, 그 안에서 쓸 값은 vi.hoisted로 만든다.
const { mockAuth, getIdToken } = vi.hoisted(() => {
  const getIdToken = vi.fn()
  return {
    mockAuth: { currentUser: null as null | { getIdToken: typeof getIdToken } },
    getIdToken,
  }
})

vi.mock('../lib/firebase', () => ({
  auth: mockAuth,
}))

const course = {
  id: 1,
  place_id: 1,
  place_name: '경복궁',
  creator_nickname: '테스트닉네임',
  title: '경복궁 코스',
  description: '',
  course_places: [],
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('src/api/courses.ts', () => {
  beforeEach(() => {
    mockAuth.currentUser = { getIdToken }
    getIdToken.mockResolvedValue('fake-id-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('getPlaceCourses', () => {
    it('성공하면 코스 목록을 반환한다', async () => {
      const { getPlaceCourses } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ courses: [course] }) }),
      )

      const result = await getPlaceCourses(1)

      expect(result).toEqual([course])
    })

    it('코스가 없으면 빈 배열을 반환한다 (에러 아님)', async () => {
      const { getPlaceCourses } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ courses: [] }) }),
      )

      const result = await getPlaceCourses(1)

      expect(result).toEqual([])
    })

    it('실패하면 에러를 던진다', async () => {
      const { getPlaceCourses } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: '존재하지 않습니다' }) }),
      )

      await expect(getPlaceCourses(1)).rejects.toThrow('존재하지 않습니다')
    })
  })

  describe('createCourse', () => {
    const input = {
      title: '경복궁 코스',
      description: '',
      course_places: [
        {
          role: 'RESTAURANT' as const,
          name: '맛집',
          address: '서울',
          road_address_name: '',
          latitude: 37.5,
          longitude: 127,
          category_name: '음식점',
          kakao_place_id: null,
        },
      ],
    }

    it('성공하면 생성된 코스를 반환한다', async () => {
      const { createCourse } = await import('./courses')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => course }))

      const result = await createCourse(1, input)

      expect(result).toEqual(course)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/places/1/courses/'),
        expect.objectContaining({ method: 'POST' }),
      )
    })

    it('구성이 맞지 않으면 에러를 던진다', async () => {
      const { createCourse } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: false,
          status: 400,
          json: async () => ({ detail: '식당 1 + 카페 1 + 그 외 1이 모두 있어야 합니다' }),
        }),
      )

      await expect(createCourse(1, input)).rejects.toThrow('식당 1 + 카페 1 + 그 외 1이 모두 있어야 합니다')
    })
  })

  describe('getCourseDetail', () => {
    it('성공하면 코스 상세를 반환한다', async () => {
      const { getCourseDetail } = await import('./courses')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => course }))

      const result = await getCourseDetail(1)

      expect(result).toEqual(course)
    })

    it('존재하지 않으면 에러를 던진다', async () => {
      const { getCourseDetail } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => ({ detail: '존재하지 않습니다' }) }),
      )

      await expect(getCourseDetail(1)).rejects.toThrow('존재하지 않습니다')
    })
  })

  describe('deleteCourse', () => {
    it('성공하면 DELETE로 삭제한다', async () => {
      const { deleteCourse } = await import('./courses')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await deleteCourse(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/courses/1/'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })

    it('작성자가 아니면 에러를 던진다', async () => {
      const { deleteCourse } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({ detail: '권한이 없습니다' }) }),
      )

      await expect(deleteCourse(1)).rejects.toThrow('권한이 없습니다')
    })
  })

  describe('getMyCourses', () => {
    it('성공하면 내가 만든 코스 목록을 반환한다', async () => {
      const { getMyCourses } = await import('./courses')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ courses: [course] }) }),
      )

      const result = await getMyCourses()

      expect(result).toEqual([course])
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/account/courses/'),
        expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer fake-id-token' }) }),
      )
    })

    it('로그인 안 되어 있으면 에러를 던진다', async () => {
      const { getMyCourses } = await import('./courses')
      mockAuth.currentUser = null
      const fetchSpy = vi.fn()
      vi.stubGlobal('fetch', fetchSpy)

      await expect(getMyCourses()).rejects.toThrow('로그인이 필요합니다')
      expect(fetchSpy).not.toHaveBeenCalled()
    })
  })
})
