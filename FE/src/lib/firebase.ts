import { initializeApp } from 'firebase/app'
import { GoogleAuthProvider, OAuthProvider, getAuth } from 'firebase/auth'
import { getStorage } from 'firebase/storage'

// Firebase 프로젝트 설정값. 실제 값은 .env에서 읽는다 (코드에 직접 쓰지 않음).
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

export const firebaseApp = initializeApp(firebaseConfig)
export const auth = getAuth(firebaseApp)
export const storage = getStorage(firebaseApp)

// PRD 결정: 로그인은 Google/Apple만 지원한다 (Kakao는 이번 범위에서 제외).
export const googleProvider = new GoogleAuthProvider()
export const appleProvider = new OAuthProvider('apple.com')
