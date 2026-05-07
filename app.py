"""
Streamlit 메인 앱 - 산업 기사 스크랩 페이지
- KST(한국 시간) 기준으로 모든 시간 처리
- 페이지 상단에 현재 시각 표시
- 기본 조회 기간: 오늘
"""
import streamlit as st
from datetime import datetime, timezone, timedelta
import html

from config import CATEGORIES
from database import (
    init_db, fetch_articles, get_article_count_by_category,
    get_latest_pub_date
)
from visitor_counter import track_visit, display_visitor_stats

# 한국 표준시
KST = timezone(timedelta(hours=9))


def now_kst():
    """현재 KST 시각"""
    return datetime.now(KST)


def today_kst():
    """오늘 날짜 (KST)"""
    return now_kst().date()


# ================================
# 페이지 설정
# ================================
st.set_page_config(
    page_title="산업 기사 스크랩",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# DB 초기화 + 방문자 기록
init_db()
track_visit()

# ================================
# 커스텀 CSS
# ================================
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
    }
    
    /* 현재 시각 박스 */
    .current-time {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 8px;
        display: inline-block;
        font-size: 14px;
        color: #2c3e50;
        font-weight: 500;
    }
    .current-time .label {
        color: #7f8c8d;
        font-size: 12px;
        margin-right: 8px;
    }
    .current-time .time {
        color: #2c3e50;
        font-weight: 700;
    }
    
    .article-card {
        background: #ffffff;
        border-left: 5px solid #ccc;
        border-radius: 8px;
        padding: 16px 18px;
        margin-bottom: 14px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
        transition: all 0.2s ease;
        height: 100%;
        min-height: 180px;
        display: flex;
        flex-direction: column;
    }
    .article-card:hover {
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
        transform: translateY(-1px);
    }
    .article-tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11.5px;
        font-weight: 600;
        color: #fff;
        margin-right: 8px;
    }
    .article-title {
        font-size: 15.5px;
        font-weight: 700;
        color: #1a1a1a;
        margin: 8px 0;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .article-summary {
        font-size: 12.5px;
        color: #555;
        line-height: 1.5;
        margin: 6px 0;
        flex-grow: 1;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .article-meta {
        font-size: 12px;
        color: #888;
        margin-top: 10px;
    }
    .article-link {
        color: #2980b9;
        text-decoration: none;
        font-weight: 500;
        font-size: 12.5px;
    }
    .article-link:hover {
        text-decoration: underline;
    }
    .meta-date {
        color: #888;
        font-size: 11.5px;
    }
    
    .visitor-box {
        position: fixed;
        bottom: 18px;
        right: 18px;
        background: rgba(30, 30, 30, 0.85);
        color: #fff;
        padding: 10px 16px;
        border-radius: 8px;
        font-size: 12.5px;
        z-index: 999;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .visitor-box .num {
        color: #4ECDC4;
        font-weight: 700;
    }
</style>
""", unsafe_allow_html=True)


# ================================
# 카드 렌더링 함수
# ================================
def get_card_html(art, show_category_tag=True):
    """기사 카드 HTML 문자열 반환"""
    cat = art["category"]
    info = CATEGORIES.get(cat, {"color": "#999", "icon": "📰"})
    color = info["color"]

    title_safe = html.escape(art["title"] or "")
    summary_safe = html.escape(art["summary"] or "")
    source_safe = html.escape(art["source"] or "")
    url = art["url"]

    tag_html = (f'<span class="article-tag" style="background: {color};">'
                f'{info["icon"]} {cat}</span>') if show_category_tag else ""

    return f"""
    <div class="article-card" style="border-left-color: {color};">
        <div>
            {tag_html}
            <span class="meta-date">📅 {art['pub_date']} · {source_safe}</span>
        </div>
        <div class="article-title">{title_safe}</div>
        <div class="article-summary">{summary_safe}</div>
        <div class="article-meta">
            <a href="{url}" target="_blank" class="article-link">🔗 원문 보기 →</a>
        </div>
    </div>
    """


def render_grid(articles, show_category_tag=True, columns=2):
    """기사들을 N열 그리드로 렌더링"""
    for i in range(0, len(articles), columns):
        cols = st.columns(columns, gap="small")
        row_articles = articles[i:i + columns]
        for j, art in enumerate(row_articles):
            with cols[j]:
                st.markdown(
                    get_card_html(art, show_category_tag=show_category_tag),
                    unsafe_allow_html=True
                )


# ================================
# 헤더 + 현재 시각
# ================================
header_col1, header_col2 = st.columns([3, 2])

with header_col1:
    st.title("📰 산업 기사 스크랩")
    st.caption("원자력 · 전력 · 방산 · 반도체 · 물류 · 해운 분야 최신 뉴스")

with header_col2:
    current = now_kst()
    weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][current.weekday()]
    
    latest_date = get_latest_pub_date()
    
    st.markdown(f"""
    <div style="text-align: right; padding-top: 10px;">
        <div class="current-time">
            <span class="label">🕐 현재 시각</span>
            <span class="time">{current.strftime("%Y-%m-%d")} ({weekday_kr}) {current.strftime("%H:%M")}</span>
        </div>
        <div style="font-size: 11.5px; color: #888; margin-top: 4px;">
            최신 기사: {latest_date if latest_date else '없음'} · KST
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ================================
# 사이드바 (필터 메뉴)
# ================================
with st.sidebar:
    st.header("🔍 조회 조건")

    # 분야 선택
    st.subheader("📂 분야")
    counts = get_article_count_by_category()
    selected_categories = []
    for cat, info in CATEGORIES.items():
        cnt = counts.get(cat, 0)
        if st.checkbox(f"{info['icon']} {cat} ({cnt})", value=True, key=f"cb_{cat}"):
            selected_categories.append(cat)

    st.divider()

    # 날짜 범위 (KST 기준) - 기본값 "오늘"로 변경
    st.subheader("📅 기간")
    date_option = st.radio(
        "선택",
        ["오늘", "최근 3일", "최근 7일", "직접 선택"],
        index=0,  # ★ 기본값 "오늘"로 변경 (이전: 2 → 0)
        label_visibility="collapsed"
    )

    today = today_kst()
    
    if date_option == "오늘":
        start_date, end_date = today, today
    elif date_option == "최근 3일":
        start_date, end_date = today - timedelta(days=2), today
    elif date_option == "최근 7일":
        start_date, end_date = today - timedelta(days=6), today
    else:
        date_range = st.date_input(
            "기간 선택",
            value=(today - timedelta(days=7), today),
            max_value=today,
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = today - timedelta(days=7), today

    st.divider()

    # 검색어
    st.subheader("🔎 검색")
    keyword = st.text_input("제목/내용 검색", placeholder="키워드 입력")

    st.divider()

    # 레이아웃 선택
    st.subheader("🎨 레이아웃")
    column_count = st.radio(
        "열 개수",
        [1, 2, 3],
        index=1,
        horizontal=True,
        label_visibility="collapsed"
    )

    st.divider()
    st.caption(f"📊 전체 기사: {sum(counts.values())}건")


# ================================
# 메인 영역 - 기사 목록
# ================================
col1, col2, col3 = st.columns([2, 2, 2])

with col1:
    st.subheader(f"📄 검색 결과")

with col2:
    sort_label = st.radio(
        "정렬",
        ["🔽 최신순", "🔼 오래된순"],
        index=0,
        horizontal=True,
        label_visibility="collapsed"
    )
    sort_order = "desc" if "최신순" in sort_label else "asc"

with col3:
    st.markdown(
        f"<div style='text-align: right; padding-top: 8px; font-size: 13px; color: #666;'>"
        f"📆 조회 기간: <b>{start_date} ~ {end_date}</b>"
        f"</div>",
        unsafe_allow_html=True
    )

# 기사 조회
articles = fetch_articles(
    categories=selected_categories if selected_categories else None,
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat(),
    keyword=keyword if keyword else None,
    sort_order=sort_order,
    limit=300
)

st.markdown(f"**{len(articles)}건**의 기사가 검색되었습니다.")

if not articles:
    st.info("🔍 조건에 맞는 기사가 없습니다. 필터를 조정해보세요.")
else:
    view_mode = st.radio(
        "보기 방식",
        ["전체 통합", "분야별 그룹"],
        horizontal=True,
        label_visibility="collapsed"
    )

    if view_mode == "분야별 그룹":
        for cat in selected_categories:
            cat_articles = [a for a in articles if a["category"] == cat]
            if not cat_articles:
                continue
            info = CATEGORIES[cat]
            st.markdown(f"### {info['icon']} {cat} ({len(cat_articles)}건)")
            render_grid(cat_articles, show_category_tag=False, columns=column_count)
            st.markdown("---")
    else:
        render_grid(articles, show_category_tag=True, columns=column_count)


# ================================
# 우측 하단 방문자 카운터
# ================================
stats = display_visitor_stats()
st.markdown(f"""
<div class="visitor-box">
    👥 누적 <span class="num">{stats['total']:,}</span> · 
    오늘 <span class="num">{stats['today']:,}</span>
</div>
""", unsafe_allow_html=True)
