import { beforeEach, describe, expect, it } from 'vitest'
import { useLocaleStore } from './useLocaleStore'

describe('useLocaleStore', () => {
  beforeEach(() => {
    useLocaleStore.setState({ nationality: null, language: 'ko' })
  })

  it('초기 상태는 국적 미선택, 언어는 한국어다', () => {
    const state = useLocaleStore.getState()
    expect(state.nationality).toBeNull()
    expect(state.language).toBe('ko')
  })

  it('setLocale로 국적/언어를 저장한다', () => {
    useLocaleStore.getState().setLocale('OTHER', 'en')
    const state = useLocaleStore.getState()
    expect(state.nationality).toBe('OTHER')
    expect(state.language).toBe('en')
  })
})
