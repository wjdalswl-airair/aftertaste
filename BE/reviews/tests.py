"""Phase 3 사이클 A 리뷰 체크리스트를 검증하는 테스트.

DETAIL_SPEC.md 2-3, 3-5, 6-1 #13,#14 / PHASES/PHASE3.md 2번(리뷰) 완료 기준 체크리스트를 근거로 만들었다.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.firebase import InvalidFirebaseToken
from accounts.models import Member
from places.models import Place
from reviews.models import REVIEW_CONTENT_MAX_LENGTH, REVIEW_MAX_PHOTOS, Review, ReviewLike, ReviewReport


def reviews_url(place_id):
    return f"/api/places/{place_id}/reviews/"


def review_detail_url(review_id):
    return f"/api/reviews/{review_id}/"


def review_like_url(review_id):
    return f"/api/reviews/{review_id}/like/"


def review_report_url(review_id):
    return f"/api/reviews/{review_id}/report/"


def place_detail_url(place_id):
    return f"/api/places/{place_id}/"


MY_REVIEWS_URL = "/api/account/reviews/"


def make_decoded_token(uid):
    return {
        "uid": uid,
        "email": f"{uid}@example.com",
        "name": "테스터",
        "picture": "http://example.com/pic.jpg",
        "firebase": {"sign_in_provider": "google.com"},
    }


def create_member(uid, nickname="회원"):
    return Member.objects.create(
        firebase_uid=uid,
        provider=Member.Provider.GOOGLE,
        nickname=nickname,
        agreed_terms_at="2026-01-01T00:00:00Z",
    )


class ReviewListReadTests(TestCase):
    """비로그인도 리뷰 목록을 볼 수 있어야 한다 (DETAIL_SPEC 3-5)."""

    def setUp(self):
        self.client = APIClient()
        self.member = create_member("review-reader-uid")
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")

    def test_anonymous_can_list_reviews(self):
        Review.objects.create(member=self.member, place=self.place, rating=5, content="좋아요", language="ko")

        response = self.client.get(reviews_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["reviews"]), 1)

    def test_anonymous_can_list_reviews_when_empty(self):
        response = self.client.get(reviews_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reviews"], [])

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_can_still_list_reviews(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")
        Review.objects.create(member=self.member, place=self.place, rating=5, content="좋아요", language="ko")

        response = self.client.get(reviews_url(self.place.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["reviews"]), 1)

    def test_listing_reviews_of_nonexistent_place_returns_404(self):
        response = self.client.get(reviews_url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReviewWriteAuthTests(TestCase):
    """작성, 좋아요, 신고는 로그인이 필요하다."""

    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.member = create_member("review-writer-uid")
        self.review = Review.objects.create(
            member=self.member, place=self.place, rating=4, content="괜찮아요", language="ko"
        )

    def test_anonymous_cannot_write_review(self):
        response = self.client.post(
            reviews_url(self.place.id), {"rating": 5, "content": "좋아요", "language": "ko"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    def test_anonymous_cannot_like_review(self):
        response = self.client.post(review_like_url(self.review.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")

    def test_anonymous_cannot_report_review(self):
        response = self.client.post(review_report_url(self.review.id), {"reason": "부적절"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["detail"], "로그인이 필요한 기능입니다")


class ReviewWriteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.auth_header = {"HTTP_AUTHORIZATION": "Bearer fake-token"}
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.member = create_member("review-writer-uid")

    @patch("accounts.authentication.verify_id_token")
    def test_can_write_review_with_rating_content_photos(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id),
            {
                "rating": 5,
                "content": "정말 좋았어요",
                "language": "ko",
                "photo_urls": ["http://example.com/1.jpg", "http://example.com/2.jpg"],
            },
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(pk=response.data["reviewId"])
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, "정말 좋았어요")
        self.assertEqual(review.photos.count(), 2)

    @patch("accounts.authentication.verify_id_token")
    def test_language_field_is_saved(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id),
            {"rating": 3, "content": "그냥그래요", "language": "en"},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(pk=response.data["reviewId"])
        self.assertEqual(review.language, "en")

    @patch("accounts.authentication.verify_id_token")
    def test_can_write_multiple_reviews_for_same_place(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        first = self.client.post(
            reviews_url(self.place.id), {"rating": 5, "content": "첫 리뷰", "language": "ko"}, format="json", **self.auth_header
        )
        second = self.client.post(
            reviews_url(self.place.id), {"rating": 3, "content": "두번째 리뷰", "language": "ko"}, format="json", **self.auth_header
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.filter(member=self.member, place=self.place).count(), 2)

    @patch("accounts.authentication.verify_id_token")
    def test_writing_review_for_nonexistent_place_returns_404(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(999999), {"rating": 5, "content": "좋아요", "language": "ko"}, format="json", **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 별점 범위 검증 (엣지 케이스)

    @patch("accounts.authentication.verify_id_token")
    def test_rating_zero_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id), {"rating": 0, "content": "글", "language": "ko"}, format="json", **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.authentication.verify_id_token")
    def test_rating_six_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id), {"rating": 6, "content": "글", "language": "ko"}, format="json", **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.authentication.verify_id_token")
    def test_rating_negative_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id), {"rating": -1, "content": "글", "language": "ko"}, format="json", **self.auth_header
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 글자 수 제한 (경계값 포함)

    @patch("accounts.authentication.verify_id_token")
    def test_content_at_max_length_is_accepted(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id),
            {"rating": 5, "content": "가" * REVIEW_CONTENT_MAX_LENGTH, "language": "ko"},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("accounts.authentication.verify_id_token")
    def test_content_over_max_length_is_rejected_not_db_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")

        response = self.client.post(
            reviews_url(self.place.id),
            {"rating": 5, "content": "가" * (REVIEW_CONTENT_MAX_LENGTH + 1), "language": "ko"},
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Review.objects.count(), 0)

    # 사진 장수 제한 (경계값 포함)

    @patch("accounts.authentication.verify_id_token")
    def test_photos_at_max_count_is_accepted(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")
        photo_urls = [f"http://example.com/{i}.jpg" for i in range(REVIEW_MAX_PHOTOS)]

        response = self.client.post(
            reviews_url(self.place.id),
            {
                "rating": 5,
                "content": "사진 최대 장수",
                "language": "ko",
                "photo_urls": photo_urls,
            },
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get(pk=response.data["reviewId"])
        self.assertEqual(review.photos.count(), REVIEW_MAX_PHOTOS)

    @patch("accounts.authentication.verify_id_token")
    def test_photos_over_max_count_is_rejected(self, mock_verify):
        mock_verify.return_value = make_decoded_token("review-writer-uid")
        photo_urls = [f"http://example.com/{i}.jpg" for i in range(REVIEW_MAX_PHOTOS + 1)]

        response = self.client.post(
            reviews_url(self.place.id),
            {
                "rating": 5,
                "content": "사진 초과",
                "language": "ko",
                "photo_urls": photo_urls,
            },
            format="json",
            **self.auth_header,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Review.objects.filter(place=self.place).count(), 0)


class ReviewEditDeleteTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.owner = create_member("owner-uid")
        self.other = create_member("other-uid")
        self.review = Review.objects.create(
            member=self.owner, place=self.place, rating=4, content="원래 글", language="ko"
        )

    @patch("accounts.authentication.verify_id_token")
    def test_owner_can_edit_own_review(self, mock_verify):
        mock_verify.return_value = make_decoded_token("owner-uid")

        response = self.client.patch(
            review_detail_url(self.review.id),
            {"content": "고친 글"},
            format="json",
            HTTP_AUTHORIZATION="Bearer fake-token",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.content, "고친 글")

    @patch("accounts.authentication.verify_id_token")
    def test_owner_can_delete_own_review(self, mock_verify):
        mock_verify.return_value = make_decoded_token("owner-uid")

        response = self.client.delete(
            review_detail_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Review.objects.filter(pk=self.review.id).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_other_member_cannot_edit_review(self, mock_verify):
        mock_verify.return_value = make_decoded_token("other-uid")

        response = self.client.patch(
            review_detail_url(self.review.id),
            {"content": "몰래 고침"},
            format="json",
            HTTP_AUTHORIZATION="Bearer fake-token",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.review.refresh_from_db()
        self.assertEqual(self.review.content, "원래 글")

    @patch("accounts.authentication.verify_id_token")
    def test_other_member_cannot_delete_review(self, mock_verify):
        mock_verify.return_value = make_decoded_token("other-uid")

        response = self.client.delete(
            review_detail_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Review.objects.filter(pk=self.review.id).exists())

    @patch("accounts.authentication.verify_id_token")
    def test_deleting_already_deleted_review_is_not_an_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("owner-uid")
        review_id = self.review.id
        self.review.delete()

        response = self.client.delete(
            review_detail_url(review_id), HTTP_AUTHORIZATION="Bearer fake-token"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch("accounts.authentication.verify_id_token")
    def test_editing_nonexistent_review_returns_404(self, mock_verify):
        mock_verify.return_value = make_decoded_token("owner-uid")

        response = self.client.patch(
            review_detail_url(999999), {"content": "x"}, format="json", HTTP_AUTHORIZATION="Bearer fake-token"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReviewLikeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.owner = create_member("like-owner-uid")
        self.liker1 = create_member("liker1-uid")
        self.liker2 = create_member("liker2-uid")
        self.review = Review.objects.create(
            member=self.owner, place=self.place, rating=5, content="좋아요 테스트", language="ko"
        )

    @patch("accounts.authentication.verify_id_token")
    def test_liking_twice_counts_once_in_db(self, mock_verify):
        mock_verify.return_value = make_decoded_token("liker1-uid")

        first = self.client.post(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")
        second = self.client.post(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(ReviewLike.objects.filter(review=self.review, member=self.liker1).count(), 1)

    @patch("accounts.authentication.verify_id_token")
    def test_unlike_then_unlike_again_is_not_an_error(self, mock_verify):
        mock_verify.return_value = make_decoded_token("liker1-uid")
        ReviewLike.objects.create(review=self.review, member=self.liker1)

        first = self.client.delete(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")
        second = self.client.delete(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(first.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(second.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ReviewLike.objects.filter(review=self.review, member=self.liker1).exists())

    def test_liking_nonexistent_review_returns_404(self):
        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("liker1-uid")
            response = self.client.post(review_like_url(999999), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_members_like_independently(self):
        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("liker1-uid")
            self.client.post(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")

        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("liker2-uid")
            self.client.post(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(ReviewLike.objects.filter(review=self.review).count(), 2)
        self.assertTrue(ReviewLike.objects.filter(review=self.review, member=self.liker1).exists())
        self.assertTrue(ReviewLike.objects.filter(review=self.review, member=self.liker2).exists())

        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("liker1-uid")
            self.client.delete(review_like_url(self.review.id), HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertFalse(ReviewLike.objects.filter(review=self.review, member=self.liker1).exists())
        self.assertTrue(ReviewLike.objects.filter(review=self.review, member=self.liker2).exists())


class ReviewReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.owner = create_member("report-owner-uid")
        self.reporter1 = create_member("reporter1-uid")
        self.reporter2 = create_member("reporter2-uid")
        self.review = Review.objects.create(
            member=self.owner, place=self.place, rating=1, content="신고 테스트", language="ko"
        )

    @patch("accounts.authentication.verify_id_token")
    def test_reporting_same_review_twice_counts_once(self, mock_verify):
        mock_verify.return_value = make_decoded_token("reporter1-uid")

        first = self.client.post(
            review_report_url(self.review.id), {"reason": "광고"}, format="json", HTTP_AUTHORIZATION="Bearer fake-token"
        )
        second = self.client.post(
            review_report_url(self.review.id), {"reason": "다른 이유"}, format="json", HTTP_AUTHORIZATION="Bearer fake-token"
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ReviewReport.objects.filter(review=self.review, member=self.reporter1).count(), 1)

    def test_reporting_nonexistent_review_returns_404(self):
        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("reporter1-uid")
            response = self.client.post(
                review_report_url(999999), {"reason": "x"}, format="json", HTTP_AUTHORIZATION="Bearer fake-token"
            )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multiple_members_report_independently(self):
        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("reporter1-uid")
            self.client.post(
                review_report_url(self.review.id), {"reason": "광고"}, format="json", HTTP_AUTHORIZATION="Bearer fake-token"
            )

        with patch("accounts.authentication.verify_id_token") as mock_verify:
            mock_verify.return_value = make_decoded_token("reporter2-uid")
            self.client.post(
                review_report_url(self.review.id), {"reason": "욕설"}, format="json", HTTP_AUTHORIZATION="Bearer fake-token"
            )

        self.assertEqual(ReviewReport.objects.filter(review=self.review).count(), 2)


class HiddenReviewTests(TestCase):
    """관리자가 감춘 리뷰는 목록, 평균 별점에서 제외된다 (DETAIL_SPEC 3-5, 6-1 #13)."""

    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.member1 = create_member("hidden-test-uid1")
        self.member2 = create_member("hidden-test-uid2")

    def test_hidden_review_excluded_from_list(self):
        Review.objects.create(member=self.member1, place=self.place, rating=5, content="보임", language="ko")
        Review.objects.create(
            member=self.member2, place=self.place, rating=1, content="감춰짐", language="ko", is_hidden=True
        )

        response = self.client.get(reviews_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["reviews"]), 1)
        self.assertEqual(response.data["reviews"][0]["content"], "보임")

    def test_hidden_review_excluded_from_average_rating(self):
        Review.objects.create(member=self.member1, place=self.place, rating=5, content="보임", language="ko")
        Review.objects.create(
            member=self.member2, place=self.place, rating=1, content="감춰짐", language="ko", is_hidden=True
        )

        response = self.client.get(place_detail_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["review_average_rating"], 5.0)
        self.assertEqual(response.data["review_count"], 1)
        self.assertEqual(len(response.data["reviews"]), 1)


class MyReviewListTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.member = create_member("my-reviews-uid")

    def test_anonymous_cannot_see_my_reviews(self):
        response = self.client.get(MY_REVIEWS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("accounts.authentication.verify_id_token")
    def test_logged_in_member_sees_own_reviews(self, mock_verify):
        mock_verify.return_value = make_decoded_token("my-reviews-uid")
        Review.objects.create(member=self.member, place=self.place, rating=5, content="내 리뷰", language="ko")

        response = self.client.get(MY_REVIEWS_URL, HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["reviews"]), 1)


class PlaceDetailReviewSummaryTests(TestCase):
    """명소 상세에 리뷰 목록, 평균 별점, 리뷰 개수가 반영되는지 확인 (DETAIL_SPEC 3-3, 3-5)."""

    def setUp(self):
        self.client = APIClient()
        self.place = Place.objects.create(name="경복궁", address="서울시 종로구")
        self.member1 = create_member("summary-uid1")
        self.member2 = create_member("summary-uid2")

    def test_no_reviews_gives_empty_list_and_null_average(self):
        response = self.client.get(place_detail_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reviews"], [])
        self.assertIsNone(response.data["review_average_rating"])
        self.assertEqual(response.data["review_count"], 0)

    def test_reviews_and_average_reflected_in_place_detail(self):
        Review.objects.create(member=self.member1, place=self.place, rating=4, content="좋음", language="ko")
        Review.objects.create(member=self.member2, place=self.place, rating=2, content="별로", language="ko")

        response = self.client.get(place_detail_url(self.place.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["reviews"]), 2)
        self.assertEqual(response.data["review_average_rating"], 3.0)
        self.assertEqual(response.data["review_count"], 2)
