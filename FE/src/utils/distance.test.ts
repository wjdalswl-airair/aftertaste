import { describe, expect, it } from 'vitest'
import { getDistanceKm } from './distance'

describe('getDistanceKm', () => {
  it('같은 좌표면 거리는 0이다', () => {
    expect(getDistanceKm(37.5665, 126.978, 37.5665, 126.978)).toBeCloseTo(0, 5)
  })

  it('서울시청과 경복궁 사이 거리를 대략 계산한다 (약 2.4km)', () => {
    const distance = getDistanceKm(37.5665, 126.978, 37.5796, 126.977)
    expect(distance).toBeGreaterThan(1)
    expect(distance).toBeLessThan(3)
  })
})
