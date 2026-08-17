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
