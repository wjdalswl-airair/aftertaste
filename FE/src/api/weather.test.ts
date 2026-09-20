import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

describe('getWeather', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_OPENWEATHER_API_KEY', 'test-key')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
  })

  function stubFetch(owmResponse: unknown, ok = true) {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok, json: async () => owmResponse }))
  }

  it('성공하면 날씨 정보를 반환한다', async () => {
    const { getWeather } = await import('./weather')
    stubFetch({
      weather: [{ id: 800, description: '맑음' }],
      main: { temp: 24.6 },
      name: 'Seoul',
    })

    const result = await getWeather(37.5665, 126.978)

    expect(result).toEqual({
      locationName: 'Seoul',
      tempC: 25,
      condition: 'clear',
      description: '맑음',
    })
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('https://api.openweathermap.org/data/2.5/weather?'),
    )
  })

  it.each([
    [210, 'thunderstorm'],
    [310, 'drizzle'],
    [500, 'rain'],
    [600, 'snow'],
    [741, 'fog'],
    [801, 'clouds'],
  ] as const)('condition code %i는 %s로 매핑한다', async (code, expected) => {
    const { getWeather } = await import('./weather')
    stubFetch({ weather: [{ id: code, description: '' }], main: { temp: 20 }, name: 'Seoul' })

    const result = await getWeather(37.5665, 126.978)

    expect(result.condition).toBe(expected)
  })

  it('API 키가 없으면 에러를 던진다', async () => {
    vi.unstubAllEnvs()
    const { getWeather } = await import('./weather')

    await expect(getWeather(37.5665, 126.978)).rejects.toThrow('날씨 API 키가 설정되지 않았어요')
  })

  it('실패하면 에러를 던진다', async () => {
    const { getWeather } = await import('./weather')
    stubFetch({}, false)

    await expect(getWeather(37.5665, 126.978)).rejects.toThrow('날씨 정보를 가져오지 못했어요')
  })
})
