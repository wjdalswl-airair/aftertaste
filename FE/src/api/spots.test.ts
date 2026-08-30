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

  it('좌표가 없으면 쿼리스트링 없이 호출한다(BE가 랜덤 추천)', async () => {
    const { getRecommendedSpots } = await import('./spots')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ places: [spot] }) }),
    )

    await getRecommendedSpots()

    const calledUrl = vi.mocked(fetch).mock.calls[0][0] as string
    expect(calledUrl.endsWith('/api/places/recommend/')).toBe(true)
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
