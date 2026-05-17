"""
Streamlit 메인 앱 - 기사 스크랩 페이지
- 분야 그룹 메뉴 (산업 / 인사·노무)
- UI 전면 리뉴얼 (깔끔한 디자인)
- KST 기준 시각 처리
"""
import streamlit as st
from datetime import datetime, timezone, timedelta
import html

from config import CATEGORIES, CATEGORY_GROUPS
from database import (
    init_db, fetch_articles, get_article_count_by_category,
    get_latest_pub_date
)
from visitor_counter import track_visit, display_visitor_stats

KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST)


def today_kst():
    return now_kst().date()


# ================================
# 페이지 설정
# ================================
st.set_page_config(
    page_title="기사 스크랩",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()
track_visit()

# ================================
# 커스텀 CSS - 깔끔한 디자인
# ================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Noto+Sans+KR:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    .block-container {
        padding-top: 2.5rem;
        padding-bottom: 6rem;
        max-width: 1400px;
    }

    /* ===== 헤더 ===== */
    .app-header {
        background: linear-gradient(120deg, #1e3a5f 0%, #2c5282 100%);
        border-radius: 16px;
        padding: 28px 36px;
        margin-bottom: 24px;
        color: #fff;
        box-shadow: 0 8px 24px rgba(30, 58, 95, 0.18);
    }
    .app-header h1 {
        font-size: 28px;
        font-weight: 700;
        margin: 0 0 6px 0;
        color: #fff;
        letter-spacing: -0.5px;
    }
    .app-header .subtitle {
        font-size: 13.5px;
        color: #cbd9ec;
        font-weight: 400;
    }
    .header-clock {
        text-align: right;
        font-size: 13px;
        color: #e2e8f0;
    }
    .header-clock .time-big {
        font-size: 18px;
        font-weight: 700;
        color: #fff;
        display: block;
        margin-bottom: 2px;
    }
    .header-clock .latest {
        font-size: 11.5px;
        color: #a8c0dd;
        margin-top: 4px;
    }

    /* ===== 컨트롤 바 ===== */
    .control-bar {
        background: #fff;
        border: 1px solid #e8edf3;
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 20px;
    }

    /* ===== 기사 카드 ===== */
    .article-card {
        background: #ffffff;
        border: 1px solid #eaeef3;
        border-left: 4px solid #ccc;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 16px;
        transition: all 0.18s ease;
        height: 100%;
        min-height: 190px;
        display: flex;
        flex-direction: column;
    }
    .article-card:hover {
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        transform: translateY(-2px);
        border-color: #d4dce6;
    }
    .article-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        color: #fff;
        letter-spacing: 0.3px;
    }
    .article-date {
        color: #95a5a6;
        font-size: 11.5px;
        font-weight: 500;
        margin-left: 8px;
    }
    .article-title {
        font-size: 16px;
        font-weight: 700;
        color: #1a2733;
        margin: 12px 0 8px 0;
        line-height: 1.45;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .article-summary {
        font-size: 13px;
        color: #5a6b7b;
        line-height: 1.6;
        margin: 4px 0;
        flex-grow: 1;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .article-footer {
        margin-top: 14px;
        padding-top: 12px;
        border-top: 1px solid #f0f3f6;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .article-source {
        font-size: 11.5px;
        color: #95a5a6;
        font-weight: 500;
    }
    .article-link {
        color: #2c5282;
        text-decoration: none;
        font-weight: 600;
        font-size: 12.5px;
    }
    .article-link:hover {
        color: #1e3a5f;
        text-decoration: underline;
    }

    /* ===== 사이드바 ===== */
    [data-testid="stSidebar"] {
        background: #f8fafc;
    }
    .sidebar-group-title {
        font-size: 13px;
        font-weight: 700;
        color: #2c5282;
        margin: 16px 0 8px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #e2e8f0;
    }

    /* ===== 결과 카운트 ===== */
    .result-count {
        font-size: 14px;
        color: #5a6b7b;
        margin: 8px 0 16px 0;
    }
    .result-count b {
        color: #2c5282;
        font-size: 17px;
    }

    /* ===== 방문자 카운터 ===== */
    .visitor-box {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: rgba(30, 58, 95, 0.92);
        color: #fff;
        padding: 11px 18px;
        border-radius: 24px;
        font-size: 12.5px;
        z-index: 999;
        box-shadow: 0 4px 16px rgba(30, 58, 95, 0.3);
    }
    .visitor-box .num {
        color: #7dd3c8;
        font-weight: 700;
    }

    /* ===== 푸터 ===== */
    .footer-section {
        margin-top: 36px;
        padding: 26px 28px 80px 28px;
        border-radius: 14px;
        background: #f4f7fa;
        border: 1px solid #e8edf3;
    }
    .footer-title {
        font-size: 13.5px;
        font-weight: 700;
        color: #2c5282;
        margin-bottom: 10px;
    }
    .footer-text {
        font-size: 12px;
        color: #6b7a89;
        line-height: 1.75;
        margin-bottom: 5px;
    }
    .footer-author {
        font-size: 13px;
        color: #2c5282;
        font-weight: 700;
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px dashed #cdd8e3;
    }
    .footer-author .heart { color: #e84393; }

    hr.fdiv { margin: 14px 0; border: none; border-top: 1px dashed #d5dee7; }

    /* Streamlit 기본 요소 숨김 */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ================================
# 카드 렌더링
# ================================
def get_card_html(art, show_tag=True):
    cat = art["category"]
    info = CATEGORIES.get(cat, {"color": "#999", "icon": "📰"})
    color = info["color"]

    title_safe = html.escape(art["title"] or "")
    summary_safe = html.escape(art["summary"] or "")
    source_safe = html.escape(art["source"] or "")
    url = art["url"]

    tag_html = (f'<span class="article-tag" style="background:{color};">'
                f'{info["icon"]} {cat}</span>') if show_tag else ""

    return f"""
    <div class="article-card" style="border-left-color:{color};">
        <div>
            {tag_html}
            <span class="article-date">📅 {art['pub_date']}</span>
        </div>
        <div class="article-title">{title_safe}</div>
        <div class="article-summary">{summary_safe}</div>
        <div class="article-footer">
            <span class="article-source">📰 {source_safe}</span>
            <a href="{url}" target="_blank" class="article-link">원문 보기 →</a>
        </div>
    </div>
    """


def render_grid(articles, show_tag=True, columns=2):
    for i in range(0, len(articles), columns):
        cols = st.columns(columns, gap="medium")
        for j, art in enumerate(articles[i:i + columns]):
            with cols[j]:
                st.markdown(get_card_html(art, show_tag), unsafe_allow_html=True)


# ================================
# 헤더
# ================================
current = now_kst()
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][current.weekday()]
latest_date = get_latest_pub_date()

hcol1, hcol2 = st.columns([3, 1.3])
with hcol1:
    st.markdown("""
    <div class="app-header" style="margin-bottom:0;">
        <h1>📰 기사 스크랩</h1>
        <div class="subtitle">산업 · 인사노무 분야별 최신 뉴스 모음</div>
    </div>
    """, unsafe_allow_html=True)
with hcol2:
    st.markdown(f"""
    <div class="app-header" style="margin-bottom:0; background:linear-gradient(120deg,#2c5282 0%,#3a6aa5 100%);">
        <div class="header-clock">
            <span class="time-big">{current.strftime("%H:%M")}</span>
            {current.strftime("%Y-%m-%d")} ({weekday_kr})
            <div class="latest">최신 기사: {latest_date if latest_date else '없음'} · KST</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ================================
# 사이드바 - 그룹 메뉴
# ================================
with st.sidebar:
    st.markdown("### 🔍 조회 조건")
    st.write("")

    counts = get_article_count_by_category()
    selected_categories = []

    # 그룹별로 분야 표시
    for group_name, cats in CATEGORY_GROUPS.items():
        st.markdown(f'<div class="sidebar-group-title">{group_name}</div>',
                    unsafe_allow_html=True)
        for cat in cats:
            if cat not in CATEGORIES:
                continue
            info = CATEGORIES[cat]
            cnt = counts.get(cat, 0)
            if st.checkbox(f"{info['icon']} {cat} ({cnt})",
                           value=True, key=f"cb_{cat}"):
                selected_categories.append(cat)

    st.divider()

    # 기간
    st.markdown("**📅 기간**")
    date_option = st.radio(
        "기간선택",
        ["오늘", "최근 3일", "최근 7일", "직접 선택"],
        index=0,
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
        dr = st.date_input("기간", value=(today - timedelta(days=7), today),
                           max_value=today)
        if isinstance(dr, tuple) and len(dr) == 2:
            start_date, end_date = dr
        else:
            start_date, end_date = today - timedelta(days=7), today

    st.divider()

    # 검색
    st.markdown("**🔎 검색**")
    keyword = st.text_input("검색", placeholder="키워드 입력",
                            label_visibility="collapsed")

    st.divider()

    # 레이아웃
    st.markdown("**🎨 레이아웃**")
    column_count = st.radio("열", [1, 2, 3], index=1,
                            horizontal=True, label_visibility="collapsed")

    st.divider()
    st.caption(f"📊 전체 기사 {sum(counts.values()):,}건")


# ================================
# 메인 - 컨트롤 바
# ================================
cc1, cc2, cc3 = st.columns([2, 2, 2])
with cc1:
    st.markdown("#### 📄 검색 결과")
with cc2:
    sort_label = st.radio("정렬", ["🔽 최신순", "🔼 오래된순"],
                          index=0, horizontal=True,
                          label_visibility="collapsed")
    sort_order = "desc" if "최신순" in sort_label else "asc"
with cc3:
    st.markdown(
        f"<div style='text-align:right;padding-top:6px;font-size:13px;color:#6b7a89;'>"
        f"📆 <b>{start_date}</b> ~ <b>{end_date}</b></div>",
        unsafe_allow_html=True
    )

articles = fetch_articles(
    categories=selected_categories if selected_categories else None,
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat(),
    keyword=keyword if keyword else None,
    sort_order=sort_order,
    limit=300
)

st.markdown(
    f'<div class="result-count"><b>{len(articles)}</b>건의 기사가 검색되었습니다.</div>',
    unsafe_allow_html=True
)

if not articles:
    st.info("🔍 조건에 맞는 기사가 없습니다. 필터를 조정해보세요.")
else:
    view_mode = st.radio("보기", ["전체 통합", "분야별 그룹"],
                         horizontal=True, label_visibility="collapsed")

    if view_mode == "분야별 그룹":
        for cat in selected_categories:
            cat_articles = [a for a in articles if a["category"] == cat]
            if not cat_articles:
                continue
            info = CATEGORIES[cat]
            st.markdown(f"### {info['icon']} {cat} "
                        f"<span style='font-size:14px;color:#95a5a6;'>"
                        f"({len(cat_articles)}건)</span>",
                        unsafe_allow_html=True)
            render_grid(cat_articles, show_tag=False, columns=column_count)
            st.write("")
    else:
        render_grid(articles, show_tag=True, columns=column_count)


# ================================
# 푸터
# ================================
st.markdown(f"""
<div class="footer-section">
    <div class="footer-title">📌 안내사항</div>
    <div class="footer-text">• 본 페이지는 공개된 RSS 피드를 통해 수집된 뉴스를 안내하는 비영리 정보 제공 서비스입니다.</div>
    <div class="footer-text">• <b>모든 기사의 저작권은 해당 언론사 및 기자에게 있습니다.</b> 본 페이지는 제목·요약·출처 링크만 제공하며, 원문은 각 언론사 사이트에서 확인하실 수 있습니다.</div>
    <div class="footer-text">• 수집 출처: 연합뉴스, 매일경제, 전자신문, 구글뉴스 등 공개 RSS</div>
    <hr class="fdiv">
    <div class="footer-author"><span class="heart">♥</span> Made by <b>정원호</b> · {current.year}</div>
</div>
""", unsafe_allow_html=True)

stats = display_visitor_stats()
st.markdown(f"""
<div class="visitor-box">
    👥 누적 <span class="num">{stats['total']:,}</span> · 오늘 <span class="num">{stats['today']:,}</span>
</div>
""", unsafe_allow_html=True)
