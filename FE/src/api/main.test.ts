import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/firebase', () => ({
  auth: { currentUser: null },
}))

describe('src/api/main.ts', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('getBanners', () => {
    it('성공하면 배너 배열을 반환한다', async () => {
      const { getBanners } = await import('./main')
      const banners = [{ id: 1, image_url: 'https://a.com/1.png', link_url: '', order: 0 }]
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ banners }) }),
      )

      const result = await getBanners()

      expect(result).toEqual(banners)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/banners/'), expect.anything())
    })

    it('실패하면 에러를 던진다', async () => {
      const { getBanners } = await import('./main')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          json: async () => ({ detail: '서버 오류' }),
        }),
      )

      await expect(getBanners()).rejects.toThrow('서버 오류')
    })
  })

  describe('getTopPlaces', () => {
    it('성공하면 명소 배열을 반환한다', async () => {
      const { getTopPlaces } = await import('./main')
      const places = [
        { id: 1, name: '경복궁', address: '서울', photo_url: 'https://a.com/1.png', favorite_count: 5 },
      ]
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places }) }),
      )

      const result = await getTopPlaces()

      expect(result).toEqual(places)
    })

    it('데이터가 없으면 빈 배열을 반환한다 (에러 아님)', async () => {
      const { getTopPlaces } = await import('./main')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places: [] }) }),
      )

      const result = await getTopPlaces()

      expect(result).toEqual([])
    })

    it('실패하면 에러를 던진다', async () => {
      const { getTopPlaces } = await import('./main')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          json: async () => ({ detail: '서버 오류' }),
        }),
      )

      await expect(getTopPlaces()).rejects.toThrow('서버 오류')
    })
  })
})
