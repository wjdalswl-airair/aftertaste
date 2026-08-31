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

describe('src/api/bookmarks.ts', () => {
  beforeEach(() => {
    mockAuth.currentUser = { getIdToken }
    getIdToken.mockResolvedValue('fake-id-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('addFavorite', () => {
    it('성공하면 POST로 즐겨찾기를 등록한다', async () => {
      const { addFavorite } = await import('./bookmarks')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await addFavorite(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/places/1/favorite/'),
        expect.objectContaining({ method: 'POST' }),
      )
    })

    it('실패하면 에러를 던진다', async () => {
      const { addFavorite } = await import('./bookmarks')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(addFavorite(1)).rejects.toThrow('서버 오류')
    })
  })

  describe('removeFavorite', () => {
    it('성공하면 DELETE로 즐겨찾기를 취소한다', async () => {
      const { removeFavorite } = await import('./bookmarks')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await removeFavorite(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/places/1/favorite/'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })

    it('실패하면 에러를 던진다', async () => {
      const { removeFavorite } = await import('./bookmarks')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(removeFavorite(1)).rejects.toThrow('서버 오류')
    })
  })

  describe('addCourseFavorite', () => {
    it('성공하면 POST로 코스 즐겨찾기를 등록한다', async () => {
      const { addCourseFavorite } = await import('./bookmarks')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await addCourseFavorite(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/courses/1/favorite/'),
        expect.objectContaining({ method: 'POST' }),
      )
    })
  })

  describe('removeCourseFavorite', () => {
    it('성공하면 DELETE로 코스 즐겨찾기를 취소한다', async () => {
      const { removeCourseFavorite } = await import('./bookmarks')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await removeCourseFavorite(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/courses/1/favorite/'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  describe('getMyFavorites', () => {
    it('성공하면 즐겨찾기 목록을 반환한다', async () => {
      const { getMyFavorites } = await import('./bookmarks')
      const favorites = [
        {
          id: 1,
          type: 'PLACE' as const,
          place: { id: 1, name: '경복궁', address: '서울', photo_url: 'https://a.com/1.png' },
          course: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ]
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ favorites }) }),
      )

      const result = await getMyFavorites()

      expect(result).toEqual(favorites)
    })

    it('저장한 게 없으면 빈 배열을 반환한다 (에러 아님)', async () => {
      const { getMyFavorites } = await import('./bookmarks')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ favorites: [] }) }),
      )

      const result = await getMyFavorites()

      expect(result).toEqual([])
    })

    it('실패하면 에러를 던진다', async () => {
      const { getMyFavorites } = await import('./bookmarks')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(getMyFavorites()).rejects.toThrow('서버 오류')
    })
  })
})
