import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/firebase', () => ({
  auth: { currentUser: null },
}))

describe('getWorkDetail', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  const workDetail = {
    id: 1,
    title: '호텔 델루나',
    description: '엘리트 호텔리어가...',
    category: 'DRAMA' as const,
    release_date: '2019-07-13',
    main_cast: '이지은, 여진구',
    director: '오충환, 김정현',
    poster_url: 'https://a.com/1.png',
    places: [{ id: 1, name: '전주 한옥마을', address: '전북 전주', photo_url: 'https://a.com/2.png' }],
  }

  it('성공하면 작품 상세를 반환한다', async () => {
    const { getWorkDetail } = await import('./works')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => workDetail }),
    )

    const result = await getWorkDetail(1)

    expect(result).toEqual(workDetail)
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/works/1/'), expect.anything())
  })

  it('존재하지 않는 작품이면 에러를 던진다', async () => {
    const { getWorkDetail } = await import('./works')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ detail: '존재하지 않습니다' }),
      }),
    )

    await expect(getWorkDetail(999)).rejects.toThrow('존재하지 않습니다')
  })

  it('실패하면 에러를 던진다', async () => {
    const { getWorkDetail } = await import('./works')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: '서버 오류' }),
      }),
    )

    await expect(getWorkDetail(1)).rejects.toThrow('서버 오류')
  })
})
