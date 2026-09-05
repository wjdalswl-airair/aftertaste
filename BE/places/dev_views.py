"""개발 중 눈으로 확인하는 용도의 페이지. 제품 기능이 아니다.

촬영지(Place)와 거기 연결된 작품(Work)이 실제로 이어져 있는지,
명소 상세 API(GET /api/places/<id>/)가 작품 정보를 제대로 내려주는지
브라우저에서 카드 클릭으로 확인하기 위한 임시 페이지다.

- settings.DEBUG가 False면 접근할 수 없다(운영 배포에 노출되지 않게).
- 명소 목록은 이 뷰가 DB에서 직접 뽑아 화면에 그린다(목록 API가 아직 없어서).
- 카드를 누르면 자바스크립트가 실제 명소 상세 API를 호출해 작품 정보를 보여준다.
"""

import json

from django.conf import settings
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.utils.html import escape

from places.models import Place, PlaceWork, Work

# 한 번에 화면에 그리는 명소 카드 수. 2,300여 개를 다 그리면 느려서 잘라 보여준다.
PLACE_CARD_LIMIT = 120


def place_work_verify_page(request):
    if not settings.DEBUG:
        raise Http404

    keyword = (request.GET.get("q") or "").strip()

    places = Place.objects.annotate(work_count=Count("place_works"))
    if keyword:
        places = places.filter(name__icontains=keyword)
    places = places.order_by("-work_count", "name")[:PLACE_CARD_LIMIT]

    stats = {
        "places": Place.objects.count(),
        "works": Work.objects.count(),
        "links": PlaceWork.objects.count(),
    }

    cards = "".join(
        f"""
        <button class="card" data-id="{place.id}">
          <span class="card-name">{escape(place.name)}</span>
          <span class="card-addr">{escape(place.address or "(주소 없음)")}</span>
          <span class="card-badge">작품 {place.work_count}</span>
        </button>
        """
        for place in places
    )
    if not cards:
        cards = '<p class="empty">검색 결과가 없습니다.</p>'

    html = _PAGE_TEMPLATE.format(
        keyword=escape(keyword),
        stats_places=stats["places"],
        stats_works=stats["works"],
        stats_links=stats["links"],
        card_limit=PLACE_CARD_LIMIT,
        cards=cards,
        category_labels=json.dumps(dict(Work.Category.choices), ensure_ascii=False),
    )
    return HttpResponse(html)


_PAGE_TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>촬영지 ↔ 작품 연결 확인</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: system-ui, "Malgun Gothic", sans-serif; color: #1a1a1a; background: #f4f4f5; }}
  header {{ padding: 16px 20px; background: #fff; border-bottom: 1px solid #e4e4e7; }}
  header h1 {{ margin: 0 0 6px; font-size: 18px; }}
  header .stats {{ font-size: 13px; color: #52525b; }}
  header .stats b {{ color: #1a1a1a; }}
  .layout {{ display: flex; gap: 16px; padding: 16px 20px; align-items: flex-start; }}
  .list-pane {{ flex: 1 1 60%; min-width: 0; }}
  .detail-pane {{ flex: 1 1 40%; position: sticky; top: 16px; background: #fff;
                  border: 1px solid #e4e4e7; border-radius: 10px; padding: 16px; min-height: 200px; }}
  form.search {{ margin-bottom: 12px; display: flex; gap: 8px; }}
  form.search input {{ flex: 1; padding: 8px 10px; border: 1px solid #d4d4d8; border-radius: 8px; font-size: 14px; }}
  form.search button {{ padding: 8px 14px; border: 0; border-radius: 8px; background: #2563eb; color: #fff; font-size: 14px; cursor: pointer; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }}
  .card {{ text-align: left; background: #fff; border: 1px solid #e4e4e7; border-radius: 10px;
           padding: 12px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; font: inherit; }}
  .card:hover {{ border-color: #2563eb; }}
  .card.active {{ border-color: #2563eb; box-shadow: 0 0 0 2px #bfdbfe; }}
  .card-name {{ font-weight: 600; font-size: 14px; }}
  .card-addr {{ font-size: 12px; color: #71717a; }}
  .card-badge {{ font-size: 11px; color: #3730a3; background: #e0e7ff; border-radius: 999px;
                 padding: 2px 8px; align-self: flex-start; }}
  .empty {{ color: #71717a; }}
  .detail-pane h2 {{ margin: 0 0 4px; font-size: 16px; }}
  .detail-pane .addr {{ font-size: 13px; color: #71717a; margin-bottom: 12px; }}
  .work {{ border: 1px solid #e4e4e7; border-radius: 8px; padding: 10px; margin-bottom: 8px; }}
  .work .title {{ font-weight: 600; }}
  .work .cat {{ font-size: 11px; color: #166534; background: #dcfce7; border-radius: 999px; padding: 2px 8px; margin-left: 6px; }}
  .work .scene {{ font-size: 13px; color: #52525b; margin-top: 4px; }}
  .warn {{ color: #b91c1c; font-size: 13px; }}
  .hint {{ color: #a1a1aa; font-size: 13px; }}
  .api {{ font-family: ui-monospace, monospace; font-size: 12px; color: #71717a; margin-top: 12px; word-break: break-all; }}
</style>
</head>
<body>
<header>
  <h1>촬영지 ↔ 작품 연결 확인 <span class="hint">(개발용, DEBUG 전용)</span></h1>
  <div class="stats">
    명소 <b>{stats_places}</b>개 · 작품 <b>{stats_works}</b>개 · 연결 <b>{stats_links}</b>건
    &nbsp;|&nbsp; 아래 목록은 작품 많은 순 최대 {card_limit}개
  </div>
</header>
<div class="layout">
  <div class="list-pane">
    <form class="search" method="get">
      <input type="text" name="q" value="{keyword}" placeholder="명소 이름으로 검색 (예: 카페, 해수욕장, 역)">
      <button type="submit">검색</button>
    </form>
    <div class="grid">
      {cards}
    </div>
  </div>
  <div class="detail-pane" id="detail">
    <p class="hint">왼쪽에서 촬영지 카드를 누르면 여기에 그 명소의 작품 정보가 나옵니다.</p>
  </div>
</div>
<script>
  var CATEGORY_LABELS = {category_labels};
  var detail = document.getElementById('detail');
  var cards = document.querySelectorAll('.card');

  cards.forEach(function (card) {{
    card.addEventListener('click', function () {{
      cards.forEach(function (c) {{ c.classList.remove('active'); }});
      card.classList.add('active');
      loadPlace(card.getAttribute('data-id'));
    }});
  }});

  function loadPlace(id) {{
    var url = '/api/places/' + id + '/';
    detail.innerHTML = '<p class="hint">불러오는 중…</p>';
    fetch(url)
      .then(function (res) {{
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      }})
      .then(function (data) {{ render(data, url); }})
      .catch(function (err) {{
        detail.innerHTML = '<p class="warn">불러오기 실패: ' + err.message + '</p>';
      }});
  }}

  function render(data, url) {{
    var html = '<h2>' + esc(data.name) + '</h2>';
    html += '<div class="addr">' + esc(data.address || '(주소 없음)') + '</div>';

    var works = data.works || [];
    if (works.length === 0) {{
      html += '<p class="warn">연결된 작품이 없습니다 (works: []).</p>';
    }} else {{
      html += '<div><b>등장 작품 ' + works.length + '편</b></div>';
      works.forEach(function (pw) {{
        var w = pw.work || {{}};
        var label = CATEGORY_LABELS[w.category] || w.category || '';
        html += '<div class="work">';
        html += '<span class="title">' + esc(w.title || '(제목 없음)') + '</span>';
        html += '<span class="cat">' + esc(label) + '</span>';
        if (pw.scene_description) {{
          html += '<div class="scene">' + esc(pw.scene_description) + '</div>';
        }}
        html += '</div>';
      }});
    }}
    html += '<div class="api">GET ' + url + '</div>';
    detail.innerHTML = html;
  }}

  function esc(s) {{
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }}
</script>
</body>
</html>
"""
