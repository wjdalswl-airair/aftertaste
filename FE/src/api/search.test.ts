import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/firebase', () => ({
  auth: { currentUser: null },
}))

describe('src/api/search.ts', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('searchPlaces', () => {
    it('성공하면 장소/작품 결과를 반환한다', async () => {
      const { searchPlaces } = await import('./search')
      const places = [{ id: 1, name: '해운대 해변', address: '부산', photo_url: 'https://a.com/1.png' }]
      const works = [{ id: 1, title: '오징어게임', category: 'DRAMA' as const, poster_url: 'https://a.com/2.png' }]
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places, works }) }),
      )

      const result = await searchPlaces('오징어게임')

      expect(result).toEqual({ places, works })
      const [calledUrl] = vi.mocked(fetch).mock.calls[0]
      const requestUrl = new URL(calledUrl as string)
      expect(requestUrl.pathname).toBe('/api/places/search/')
      expect(requestUrl.searchParams.get('q')).toBe('오징어게임')
    })

    it('type을 지정하면 쿼리 파라미터에 포함된다', async () => {
      const { searchPlaces } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places: [], works: [] }) }),
      )

      await searchPlaces('도깨비', 'DRAMA')

      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('type=DRAMA'), expect.anything())
    })

    it('결과가 없으면 message가 함께 온다', async () => {
      const { searchPlaces } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: true,
          status: 200,
          json: async () => ({ places: [], works: [], message: '검색결과가 존재하지 않습니다' }),
        }),
      )

      const result = await searchPlaces('없는검색어')

      expect(result.message).toBe('검색결과가 존재하지 않습니다')
    })

    it('실패하면 에러를 던진다', async () => {
      const { searchPlaces } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: false,
          status: 400,
          json: async () => ({ detail: '검색어를 입력해주세요' }),
        }),
      )

      await expect(searchPlaces('')).rejects.toThrow('검색어를 입력해주세요')
    })
  })

  describe('getAutocomplete', () => {
    it('성공하면 후보 배열을 반환한다', async () => {
      const { getAutocomplete } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ suggestions: ['도깨비'] }) }),
      )

      const result = await getAutocomplete('도깨')

      expect(result).toEqual(['도깨비'])
    })

    it('실패하면 에러를 던진다', async () => {
      const { getAutocomplete } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(getAutocomplete('도깨')).rejects.toThrow('서버 오류')
    })
  })

  describe('getPopularKeywords', () => {
    it('성공하면 인기 검색어 배열을 반환한다', async () => {
      const { getPopularKeywords } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ keywords: ['도깨비', '사랑나무'] }) }),
      )

      const result = await getPopularKeywords()

      expect(result).toEqual(['도깨비', '사랑나무'])
    })

    it('기록이 없으면 빈 배열을 반환한다 (에러 아님)', async () => {
      const { getPopularKeywords } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ keywords: [] }) }),
      )

      const result = await getPopularKeywords()

      expect(result).toEqual([])
    })

    it('실패하면 에러를 던진다', async () => {
      const { getPopularKeywords } = await import('./search')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(getPopularKeywords()).rejects.toThrow('서버 오류')
    })
  })
})
