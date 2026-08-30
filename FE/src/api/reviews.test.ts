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

const review = {
  id: 1,
  place: 1,
  author_nickname: '테스트닉네임',
  rating: 5,
  content: '정말 좋았어요',
  language: 'ko',
  photos: [],
  like_count: 0,
  is_liked_by_me: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('src/api/reviews.ts', () => {
  beforeEach(() => {
    mockAuth.currentUser = { getIdToken }
    getIdToken.mockResolvedValue('fake-id-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('getPlaceReviews', () => {
    it('성공하면 리뷰 목록을 반환한다', async () => {
      const { getPlaceReviews } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ reviews: [review] }) }),
      )

      const result = await getPlaceReviews(1)

      expect(result).toEqual([review])
    })

    it('리뷰가 없으면 빈 배열을 반환한다 (에러 아님)', async () => {
      const { getPlaceReviews } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ reviews: [] }) }),
      )

      const result = await getPlaceReviews(1)

      expect(result).toEqual([])
    })

    it('실패하면 에러를 던진다', async () => {
      const { getPlaceReviews } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(getPlaceReviews(1)).rejects.toThrow('서버 오류')
    })
  })

  describe('createReview', () => {
    it('성공하면 생성된 리뷰 id를 반환한다', async () => {
      const { createReview } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => ({ reviewId: 1 }) }),
      )

      const result = await createReview(1, { rating: 5, content: '좋았어요', language: 'ko', photo_urls: [] })

      expect(result).toEqual({ reviewId: 1 })
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/places/1/reviews/'),
        expect.objectContaining({ method: 'POST' }),
      )
    })

    it('실패하면 에러를 던진다', async () => {
      const { createReview } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 400, json: async () => ({ detail: '별점 범위 오류' }) }),
      )

      await expect(
        createReview(1, { rating: 6, content: '좋았어요', language: 'ko', photo_urls: [] }),
      ).rejects.toThrow('별점 범위 오류')
    })
  })

  describe('updateReview', () => {
    it('성공하면 PATCH로 수정한다', async () => {
      const { updateReview } = await import('./reviews')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => null }))

      await updateReview(1, { rating: 4, content: '수정된 후기', language: 'ko', photo_urls: [] })

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/reviews/1/'),
        expect.objectContaining({ method: 'PATCH' }),
      )
    })

    it('작성자가 아니면 에러를 던진다', async () => {
      const { updateReview } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 403, json: async () => ({ detail: '권한이 없습니다' }) }),
      )

      await expect(
        updateReview(1, { rating: 4, content: '수정', language: 'ko', photo_urls: [] }),
      ).rejects.toThrow('권한이 없습니다')
    })
  })

  describe('deleteReview', () => {
    it('성공하면 DELETE로 삭제한다', async () => {
      const { deleteReview } = await import('./reviews')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await deleteReview(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/reviews/1/'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })

    it('실패하면 에러를 던진다', async () => {
      const { deleteReview } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(deleteReview(1)).rejects.toThrow('서버 오류')
    })
  })

  describe('likeReview / unlikeReview', () => {
    it('좋아요는 POST로 요청한다', async () => {
      const { likeReview } = await import('./reviews')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 201, json: async () => null }))

      await likeReview(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/reviews/1/like/'),
        expect.objectContaining({ method: 'POST' }),
      )
    })

    it('좋아요 취소는 DELETE로 요청한다', async () => {
      const { unlikeReview } = await import('./reviews')
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))

      await unlikeReview(1)

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/reviews/1/like/'),
        expect.objectContaining({ method: 'DELETE' }),
      )
    })

    it('실패하면 에러를 던진다', async () => {
      const { likeReview } = await import('./reviews')
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ detail: '서버 오류' }) }),
      )

      await expect(likeReview(1)).rejects.toThrow('서버 오류')
    })
  })
})
