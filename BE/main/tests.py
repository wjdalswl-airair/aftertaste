"""
메인 화면(Phase 2-2) 완료 기준 체크리스트를 검증하는 테스트. docs/PHASES/PHASE2.md 2-2 참고.

배너: 로그인 없이 활성 배너만 order 순서대로 보이는지 확인한다.
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from main.models import Banner

BANNER_URL = "/api/banners/"


class BannerListViewTests(TestCase):
    """GET /api/banners/"""

    def setUp(self):
        self.client = APIClient()

    def test_main_screen_opens_without_login(self):
        """로그인 없이 메인 화면(배너 목록)이 열린다."""
        response = self.client.get(BANNER_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_active_banner_content_is_visible(self):
        """관리자가 넣은 배너 콘텐츠가 보인다."""
        banner = Banner.objects.create(
            image_url="http://example.com/banner1.png",
            link_url="http://example.com/event1",
            order=0,
            is_active=True,
        )

        response = self.client.get(BANNER_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["banners"]), 1)
        self.assertEqual(response.data["banners"][0]["id"], banner.id)
        self.assertEqual(response.data["banners"][0]["image_url"], "http://example.com/banner1.png")
        self.assertEqual(response.data["banners"][0]["link_url"], "http://example.com/event1")

    def test_inactive_banner_is_excluded(self):
        """비활성 배너는 응답에서 빠진다."""
        Banner.objects.create(image_url="http://example.com/active.png", order=0, is_active=True)
        Banner.objects.create(image_url="http://example.com/inactive.png", order=1, is_active=False)

        response = self.client.get(BANNER_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["banners"]), 1)
        self.assertEqual(response.data["banners"][0]["image_url"], "http://example.com/active.png")

    def test_banners_are_ordered_by_order_field(self):
        """order 값 순서대로 정렬되어 나온다."""
        Banner.objects.create(image_url="http://example.com/third.png", order=2, is_active=True)
        Banner.objects.create(image_url="http://example.com/first.png", order=0, is_active=True)
        Banner.objects.create(image_url="http://example.com/second.png", order=1, is_active=True)

        response = self.client.get(BANNER_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        image_urls = [item["image_url"] for item in response.data["banners"]]
        self.assertEqual(
            image_urls,
            [
                "http://example.com/first.png",
                "http://example.com/second.png",
                "http://example.com/third.png",
            ],
        )

    def test_no_banners_returns_empty_list(self):
        """배너가 하나도 없으면 빈 리스트가 온다."""
        response = self.client.get(BANNER_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["banners"], [])

    def test_banner_without_link_url_is_returned(self):
        """link_url(선택값)이 없는 배너도 정상적으로 응답된다."""
        Banner.objects.create(image_url="http://example.com/no-link.png", order=0, is_active=True)

        response = self.client.get(BANNER_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["banners"][0]["link_url"], "")


# ---------------------------------------------------------------------------
# Phase 3 사이클 B (명예의 전당 / Top10 채우기) checklist tests. See docs/PHASES/PHASE3.md 6번,
# main/views.py HallOfFameView, TopPlacesView 참고.
# ---------------------------------------------------------------------------

from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from accounts.firebase import InvalidFirebaseToken
from accounts.models import Member
from favorites.models import Favorite
from places.models import Place
from reviews.models import Review, ReviewLike, ReviewPhoto

HALL_OF_FAME_URL = "/api/main/hall-of-fame/"
TOP_PLACES_URL = "/api/main/top-places/"


def create_member(uid, nickname="테스터"):
    return Member.objects.create(
        firebase_uid=uid,
        provider=Member.Provider.GOOGLE,
        nickname=nickname,
        agreed_terms_at="2026-01-01T00:00:00Z",
    )


def create_place(name):
    return Place.objects.create(name=name)


def create_review_with_photo(member, place, rating=5, content="좋아요", is_hidden=False):
    review = Review.objects.create(
        member=member, place=place, rating=rating, content=content, language="ko", is_hidden=is_hidden
    )
    ReviewPhoto.objects.create(review=review, photo_url="https://example.com/photo.jpg")
    return review


def add_likes(review, count, uid_prefix):
    for i in range(count):
        liker = create_member(f"{uid_prefix}-{i}")
        ReviewLike.objects.create(review=review, member=liker)


class HallOfFameViewTest(TestCase):
    """GET /api/main/hall-of-fame/"""

    def setUp(self):
        self.client = APIClient()
        self.place = create_place("명예의전당명소")

    def test_review_with_most_likes_this_month_is_selected(self):
        author1 = create_member("hof-author-1")
        low_like_review = create_review_with_photo(author1, self.place)
        add_likes(low_like_review, 1, "hof-low")

        author2 = create_member("hof-author-2")
        high_like_review = create_review_with_photo(author2, self.place)
        add_likes(high_like_review, 3, "hof-high")

        response = self.client.get(HALL_OF_FAME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["review"]["id"], high_like_review.id)

    def test_review_without_photo_is_excluded(self):
        author = create_member("hof-nophoto")
        no_photo_review = Review.objects.create(
            member=author, place=self.place, rating=5, content="사진없음", language="ko"
        )
        add_likes(no_photo_review, 5, "hof-nophoto-like")

        response = self.client.get(HALL_OF_FAME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["review"])

    def test_hidden_review_is_excluded_even_with_more_likes(self):
        hidden_author = create_member("hof-hidden-author")
        hidden_review = create_review_with_photo(hidden_author, self.place, is_hidden=True)
        add_likes(hidden_review, 10, "hof-hidden-like")

        visible_author = create_member("hof-visible-author")
        visible_review = create_review_with_photo(visible_author, self.place, is_hidden=False)
        add_likes(visible_review, 1, "hof-visible-like")

        response = self.client.get(HALL_OF_FAME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["review"]["id"], visible_review.id)

    def test_no_reviews_this_month_returns_null_review_not_error(self):
        response = self.client.get(HALL_OF_FAME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["review"])

    def test_last_month_review_is_excluded(self):
        author = create_member("hof-lastmonth")
        last_month_review = create_review_with_photo(author, self.place)
        add_likes(last_month_review, 5, "hof-lastmonth-like")
        past_date = timezone.now() - timedelta(days=40)
        Review.objects.filter(pk=last_month_review.id).update(created_at=past_date)

        response = self.client.get(HALL_OF_FAME_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["review"])

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_does_not_return_401(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(HALL_OF_FAME_URL, HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TopPlacesViewTest(TestCase):
    """GET /api/main/top-places/"""

    def setUp(self):
        self.client = APIClient()

    def test_places_ordered_by_favorite_count_descending(self):
        place_low = create_place("즐겨찾기적은명소")
        place_high = create_place("즐겨찾기많은명소")
        member_low = create_member("top-low-0")
        Favorite.objects.create(member=member_low, place=place_low)
        for i in range(3):
            member = create_member(f"top-high-{i}")
            Favorite.objects.create(member=member, place=place_high)

        response = self.client.get(TOP_PLACES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [p["name"] for p in response.data["places"]]
        self.assertEqual(names[0], "즐겨찾기많은명소")
        self.assertEqual(names[1], "즐겨찾기적은명소")

    def test_no_favorites_returns_empty_list_not_error(self):
        create_place("즐겨찾기없는명소")

        response = self.client.get(TOP_PLACES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["places"], [])

    def test_exactly_ten_places_are_returned_and_eleventh_is_excluded(self):
        for rank in range(1, 12):
            place = create_place(f"명소순위{rank}")
            for i in range(rank):
                member = create_member(f"top-rank{rank}-fav-{i}")
                Favorite.objects.create(member=member, place=place)

        response = self.client.get(TOP_PLACES_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["places"]), 10)
        names = [p["name"] for p in response.data["places"]]
        self.assertNotIn("명소순위1", names)
        self.assertIn("명소순위11", names)
        self.assertIn("명소순위2", names)

    @patch("accounts.authentication.verify_id_token")
    def test_invalid_token_does_not_return_401(self, mock_verify):
        mock_verify.side_effect = InvalidFirebaseToken("expired")

        response = self.client.get(TOP_PLACES_URL, HTTP_AUTHORIZATION="Bearer fake-token")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
