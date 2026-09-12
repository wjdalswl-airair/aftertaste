from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ReviewFeedPagination(PageNumberPagination):
    """GET /api/reviews/(전체 명소 리뷰 피드) 전용 페이지네이션.

    프로젝트에는 전역 DEFAULT_PAGINATION_CLASS가 없다 — 다른 목록 API(명소별 리뷰, 내 리뷰 등)가
    갑자기 페이지네이션 응답 형태로 바뀌는 걸 막으려고 이 엔드포인트에만 붙인다 (DETAIL_SPEC 6-1 #32).
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        # 프로젝트의 다른 목록 응답과 이름을 맞추려고 "results" 대신 "reviews" 키를 쓴다.
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "reviews": data,
            }
        )
