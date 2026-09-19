from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CourseListPagination(PageNumberPagination):
    """GET /api/courses/(코스 탭 전체 코스 목록) 전용 페이지네이션.

    프로젝트에는 전역 DEFAULT_PAGINATION_CLASS가 없어서(reviews.pagination.ReviewFeedPagination과
    같은 이유) 다른 코스 목록 API(명소별, 내 코스)는 그대로 두고 이 엔드포인트에만 붙인다.
    AI 코스 추천을 누를 때마다 코스가 늘어나므로 페이지 단위로 나눠 받는다 (issue #74).
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        # 프로젝트의 다른 목록 응답과 이름을 맞추려고 "results" 대신 "courses" 키를 쓴다.
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "courses": data,
            }
        )
