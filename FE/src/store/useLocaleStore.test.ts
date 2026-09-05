import { beforeEach, describe, expect, it } from 'vitest'
import { useLocaleStore } from './useLocaleStore'

describe('useLocaleStore', () => {
  beforeEach(() => {
    useLocaleStore.setState({ language: 'ko' })
  })

  it('초기 언어는 한국어다', () => {
    const state = useLocaleStore.getState()
    expect(state.language).toBe('ko')
  })

  it('setLocale로 언어를 저장한다', () => {
    useLocaleStore.getState().setLocale('ja')
    const state = useLocaleStore.getState()
    expect(state.language).toBe('ja')
  })
})
