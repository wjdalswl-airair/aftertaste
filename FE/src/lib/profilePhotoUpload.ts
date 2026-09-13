import { deleteObject, getDownloadURL, ref, uploadBytes } from 'firebase/storage'
import { compressImage, PhotoTooLargeError } from './compressImage'
import { auth, storage } from './firebase'

// Storage 보안 규칙(profile/{uid}/**의 request.resource.size 제한)과 반드시 같은 값으로 맞춘다 —
// 안 맞으면 여기선 통과시켰는데 규칙에서 막혀 storage/unauthorized로 실패한다(이슈 #45).
const MAX_UPLOAD_BYTES = 5 * 1024 * 1024

// 프로필 사진을 Firebase Storage에 올리고 다운로드 URL을 돌려준다.
// BE는 업로드된 사진 URL만 받는 구조라(MemberProfileUpdateSerializer의 profile_image_url),
// 실제 파일 업로드는 FE가 여기서 직접 처리한다.
export async function uploadProfilePhoto(file: File): Promise<string> {
  const uid = auth.currentUser?.uid
  if (!uid) {
    throw new Error('로그인이 필요합니다')
  }

  const compressed = await compressImage(file)
  if (compressed.size > MAX_UPLOAD_BYTES) {
    throw new PhotoTooLargeError(`${compressed.size} bytes > ${MAX_UPLOAD_BYTES}`)
  }
  const path = `profile/${uid}/${Date.now()}-${file.name}`
  const fileRef = ref(storage, path)
  // reviewPhotoUpload.ts와 같은 이유로 영구 캐시 — 경로가 항상 새로 생겨서 안전하다.
  await uploadBytes(fileRef, compressed, { cacheControl: 'public, max-age=31536000, immutable' })
  return getDownloadURL(fileRef)
}

// 더는 안 쓰는 프로필 사진(재선택으로 버려진 임시본, 저장 성공 후의 예전 사진)을 Storage에서 지운다.
export async function deleteProfilePhoto(photoUrl: string): Promise<void> {
  await deleteObject(ref(storage, photoUrl)).catch((error) => {
    console.error('프로필 사진 정리 실패', error)
  })
}
