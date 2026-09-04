import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/firebase', () => ({
  auth: { currentUser: null },
}))

const spot = { id: 1, name: '경복궁', address: '서울', photo_url: 'https://a.com/1.png' }

describe('getRecommendedSpots', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('좌표가 있으면 쿼리스트링에 lat/lng를 붙인다', async () => {
    const { getRecommendedSpots } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places: [spot] }) }),
    )

    const result = await getRecommendedSpots({ lat: 37.5, lng: 127.0 })

    expect(result).toEqual([spot])
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/places/recommend/?lat=37.5&lng=127'),
      expect.anything(),
    )
  })

  it('좌표가 없으면 lat/lng 없이 lang만 붙여 호출한다(BE가 랜덤 추천)', async () => {
    const { getRecommendedSpots } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places: [spot] }) }),
    )

    await getRecommendedSpots()

    const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string
    expect(calledUrl).not.toContain('lat=')
    expect(calledUrl).toContain('/api/places/recommend/?lang=')
  })

  it('실패하면 에러를 던진다', async () => {
    const { getRecommendedSpots } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: '서버 오류' }),
      }),
    )

    await expect(getRecommendedSpots()).rejects.toThrow('서버 오류')
  })
})

describe('getPlaceDetail', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const placeDetail = {
    id: 1,
    name: '경복궁',
    address: '서울',
    photo_url: 'https://a.com/1.png',
    business_hours: '09:00~18:00',
    recommended_time: '봄',
    photo_tips: '',
    etiquette: '',
    description: '',
    latitude: '37.5',
    longitude: '127.0',
    works: [],
    nearby_places: [],
    is_favorited: false,
    reviews: [],
    review_average_rating: null,
    review_count: 0,
  }

  it('성공하면 명소 상세를 반환한다', async () => {
    const { getPlaceDetail } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => placeDetail }),
    )

    const result = await getPlaceDetail(1)

    expect(result).toEqual(placeDetail)
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/places/1/'), expect.anything())
  })

  it('존재하지 않는 명소면 에러를 던진다', async () => {
    const { getPlaceDetail } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: '존재하지 않습니다' }),
      }),
    )

    await expect(getPlaceDetail(999)).rejects.toThrow('존재하지 않습니다')
  })

  it('실패하면 에러를 던진다', async () => {
    const { getPlaceDetail } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: '서버 오류' }),
      }),
    )

    await expect(getPlaceDetail(1)).rejects.toThrow('서버 오류')
  })
})
