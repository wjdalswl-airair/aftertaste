"""여러 앱이 공유하는 값. 한 개념이 앱마다 다른 숫자로 박혀 있던 것을 모은다."""

# language 필드(회원 언어 설정, 명소·작품·리뷰 번역 언어)의 최대 길이.
# BCP-47 언어 태그는 "en"(2자)~"zh-Hant-TW"(10자) 정도지만, 지역·변형 서브태그가
# 더 붙는 경우까지 감안해 넉넉히 35로 잡는다.
# (0830_test.md §3-4: Member.language=20, 나머지 번역 모델=10으로 갈려 있던 것을 통일.)
LANGUAGE_CODE_MAX_LENGTH = 35

# 사진·이미지 URL 필드(리뷰 사진, 프로필 사진, 명소·작품 이미지, 배너)의 최대 길이.
# Firebase Storage 다운로드 URL은 버킷명 + 사용자 uid + 토큰(UUID)이 붙어 200자를 쉽게
# 넘는다(한글 파일명이면 URL 인코딩으로 더 길어진다). Django URLField 기본값 200으로는
# bulk_create 때 DB에서 "value too long"으로 저장이 통째로 실패했다. 넉넉히 500으로 잡는다.
PHOTO_URL_MAX_LENGTH = 500
