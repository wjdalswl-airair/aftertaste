import { deleteObject, getDownloadURL, ref, uploadBytes } from 'firebase/storage'
import { compressImage, PhotoTooLargeError } from './compressImage'
import { auth, storage } from './firebase'

// Storage 보안 규칙(reviews/{uid}/**의 request.resource.size 제한)과 반드시 같은 값으로 맞춘다 —
// 안 맞으면 여기선 통과시켰는데 규칙에서 막혀 storage/unauthorized로 실패한다(이슈 #45).
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

// 리뷰 사진을 Firebase Storage에 올리고 다운로드 URL을 돌려준다.
// BE는 이미 업로드된 사진 URL만 받는 구조라(ReviewWriteSerializer의 photo_urls),
// 실제 파일 업로드는 FE가 여기서 직접 처리한다.
export async function uploadReviewPhoto(file: File): Promise<string> {
  const uid = auth.currentUser?.uid
  if (!uid) {
    throw new Error('로그인이 필요합니다')
  }

  const compressed = await compressImage(file)
  if (compressed.size > MAX_UPLOAD_BYTES) {
    // 압축해도(또는 압축이 원본 폴백으로 끝나서) 여전히 규칙 제한을 넘는 경우 —
    // Storage에 던져서 permission-denied로 실패하게 두지 않고 여기서 먼저 막는다.
    throw new PhotoTooLargeError(`${compressed.size} bytes > ${MAX_UPLOAD_BYTES}`)
  }
  const path = `reviews/${uid}/${Date.now()}-${file.name}`
  const fileRef = ref(storage, path)
  // 파일명에 타임스탬프가 붙어 절대 덮어쓰지 않으므로(매번 새 경로), 브라우저가 영구 캐시해도
  // 안전하다 — 피드·상세를 오갈 때마다 같은 사진을 다시 받아오지 않아 다운로드(egress) 비용이 준다.
  await uploadBytes(fileRef, compressed, { cacheControl: 'public, max-age=31536000, immutable' })
  return getDownloadURL(fileRef)
}

// 리뷰 작성 중 첨부했다가 제출 전에 뺀 사진을 Storage에서 지운다 — 아직 어느 리뷰에도
// 저장되지 않아서 지워도 안전하다. 이미 저장된 리뷰의 사진을 지우는 건 이 함수의 역할이 아니다
// (그건 BE가 리뷰 수정/삭제 시 실제 Storage 파일도 지우게 고쳐야 하는 별도 이슈).
export async function deleteReviewPhoto(photoUrl: string): Promise<void> {
  await deleteObject(ref(storage, photoUrl)).catch((error) => {
    console.error('리뷰 사진 정리 실패', error)
  })
}
