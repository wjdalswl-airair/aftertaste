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

  describe('getHallOfFame', () => {
    it('리뷰가 있으면 review와 place를 함께 반환한다', async () => {
      const { getHallOfFame } = await import('./main')
      const review = {
        id: 1,
        place: 10,
        author_nickname: '익명',
        rating: 5,
        content: '좋아요',
        language: 'ko',
        photos: [{ id: 1, photo_url: 'https://a.com/1.png' }],
        like_count: 3,
        is_liked_by_me: false,
        created_at: '2026-09-01T00:00:00Z',
        updated_at: '2026-09-01T00:00:00Z',
      }
      const place = { id: 10, name: '경복궁', work: { title: '작품명', category: 'DRAMA' as const } }
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ review, place }) }),
      )

      const result = await getHallOfFame()

      expect(result).toEqual({ review, place })
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/main/hall-of-fame/'), expect.anything())
    })

    it('이번 주 후보가 없으면 null을 반환한다', async () => {
      const { getHallOfFame } = await import('./main')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ review: null, place: null }) }),
      )

      const result = await getHallOfFame()

      expect(result).toBeNull()
    })

    it('실패하면 에러를 던진다', async () => {
      const { getHallOfFame } = await import('./main')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          json: async () => ({ detail: '서버 오류' }),
        }),
      )

      await expect(getHallOfFame()).rejects.toThrow('서버 오류')
    })
  })

  describe('getTopPlaces', () => {
    it('성공하면 명소 배열을 반환한다', async () => {
      const { getTopPlaces } = await import('./main')
      const places = [
        {
          id: 1,
          name: '경복궁',
          address: '서울',
          photo_url: 'https://a.com/1.png',
          favorite_count: 5,
          is_favorited: false,
        },
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
