import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { detectInitialLanguage, useLocaleStore } from './useLocaleStore'

describe('useLocaleStore', () => {
  beforeEach(() => {
    useLocaleStore.setState({ language: 'ko' })
  })

  it('setLocale로 언어를 저장한다', () => {
    useLocaleStore.getState().setLocale('ja')
    const state = useLocaleStore.getState()
    expect(state.language).toBe('ja')
  })
})

describe('detectInitialLanguage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('기기 언어가 한국어면 ko를 쓴다', () => {
    vi.stubGlobal('navigator', { language: 'ko-KR' })
    expect(detectInitialLanguage()).toBe('ko')
  })

  it('기기 언어가 일본어면 ja를 쓴다', () => {
    vi.stubGlobal('navigator', { language: 'ja-JP' })
    expect(detectInitialLanguage()).toBe('ja')
  })

  it('기기 언어가 중국(간체)이면 zh-CN을 쓴다', () => {
    vi.stubGlobal('navigator', { language: 'zh-CN' })
    expect(detectInitialLanguage()).toBe('zh-CN')
  })

  it('기기 언어가 대만/홍콩(번체)이면 zh-TW를 쓴다', () => {
    vi.stubGlobal('navigator', { language: 'zh-TW' })
    expect(detectInitialLanguage()).toBe('zh-TW')
    vi.stubGlobal('navigator', { language: 'zh-HK' })
    expect(detectInitialLanguage()).toBe('zh-TW')
  })

  it('지원하지 않는 언어권이면 en으로 폴백한다', () => {
    vi.stubGlobal('navigator', { language: 'fr-FR' })
    expect(detectInitialLanguage()).toBe('en')
  })
})
