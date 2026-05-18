"""
Streamlit 메인 앱 - 기사 스크랩 페이지
- 중요도 배지 (키워드 규칙 기반 자동 추정)
- 업무 관련성 필터 (법령·정책 / 인사·노무 / 사업영향 / ESG·인증)
- 중복 기사 묶기 (제목 유사도 기반)
- 검색 강화 (언론사, 제외 키워드)
- UI 보완 (카드 압축, 마지막 업데이트 시각, 중요도순 정렬)
"""
import re
import html
import difflib
from datetime import datetime, timezone, timedelta

import streamlit as st

from config import (
    CATEGORIES, CATEGORY_GROUPS,
    IMPORTANCE_RULES, RELEVANCE_RULES,
)
from database import (
    init_db, fetch_articles, get_article_count_by_category,
    get_latest_pub_date, get_all_sources, get_last_scraped_time,
)

KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST)


def today_kst():
    return now_kst().date()


# ================================
# 분류 헬퍼 (키워드 규칙 기반)
# ================================
def estimate_importance(title, summary):
    """중요도 자동 추정: HIGH > MID > LOW"""
    text = f"{title} {summary}"
    for kw in IMPORTANCE_RULES.get("HIGH", []):
        if kw in text:
            return "HIGH"
    for kw in IMPORTANCE_RULES.get("MID", []):
        if kw in text:
            return "MID"
    return "LOW"


IMPORTANCE_META = {
    "HIGH": {"label": "상", "color": "#E74C3C", "bg": "#FDEDEC", "tip": "즉시 확인"},
    "MID": {"label": "중", "color": "#E67E22", "bg": "#FEF5E7", "tip": "주간 검토"},
    "LOW": {"label": "하", "color": "#95A5A6", "bg": "#F4F6F6", "tip": "단순 참고"},
}


def estimate_relevance(title, summary):
    """업무 관련성 태그 추정 (복수 가능, 없으면 일반)"""
    text = f"{title} {summary}"
    tags = []
    for tag, kws in RELEVANCE_RULES.items():
        if any(kw in text for kw in kws):
            tags.append(tag)
    return tags if tags else ["일반"]


def normalize_title(t):
    """제목 정규화 (중복 판정용)"""
    t = re.sub(r"\[.*?\]|\(.*?\)", "", t or "")
    t = re.sub(r"[^가-힣a-zA-Z0-9]", "", t)
    return t.lower()


def group_duplicates(articles, threshold=0.72):
    """제목 유사도 기반 중복 묶기 → [{rep, dups}, ...]"""
    groups = []
    used = [False] * len(articles)
    norm = [normalize_title(a["title"]) for a in articles]

    for i in range(len(articles)):
        if used[i]:
            continue
        rep = articles[i]
        dups = []
        used[i] = True
        for j in range(i + 1, len(articles)):
            if used[j] or not norm[i] or not norm[j]:
                continue
            ratio = difflib.SequenceMatcher(None, norm[i], norm[j]).ratio()
            contained = norm[i] in norm[j] or norm[j] in norm[i]
            if ratio >= threshold or contained:
                dups.append(articles[j])
                used[j] = True
        groups.append({"rep": rep, "dups": dups})
    return groups


IMPORTANCE_ORDER = {"HIGH": 0, "MID": 1, "LOW": 2}


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

# ================================
# CSS
# ================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }

    .block-container { padding-top: 2.2rem; padding-bottom: 5rem; max-width: 1400px; }

    .app-header {
        background: linear-gradient(120deg, #1e3a5f 0%, #2c5282 100%);
        border-radius: 16px; padding: 24px 32px; color: #fff;
        box-shadow: 0 8px 24px rgba(30,58,95,0.18);
    }
    .app-header h1 { font-size: 26px; font-weight: 700; margin: 0 0 4px 0; color:#fff; }
    .app-header .subtitle { font-size: 13px; color: #cbd9ec; }
    .header-clock { text-align:right; font-size:12.5px; color:#e2e8f0; }
    .header-clock .time-big { font-size:18px; font-weight:700; color:#fff; display:block; }
    .header-clock .latest { font-size:11px; color:#a8c0dd; margin-top:4px; }

    .article-card {
        background:#fff; border:1px solid #eaeef3; border-left:4px solid #ccc;
        border-radius:12px; padding:16px 18px; margin-bottom:14px;
        transition:all .16s ease; height:100%; display:flex; flex-direction:column;
    }
    .article-card.compact { padding:11px 14px; margin-bottom:9px; }
    .article-card:hover { box-shadow:0 6px 18px rgba(0,0,0,.08); transform:translateY(-2px); }

    .imp-badge { padding:3px 10px; border-radius:6px; font-size:10.5px; font-weight:700; }
    .cat-tag {
        display:inline-block; padding:3px 10px; border-radius:20px;
        font-size:10.5px; font-weight:700; color:#fff; margin-right:5px;
    }
    .rel-tag {
        display:inline-block; padding:2px 8px; border-radius:5px;
        font-size:10px; font-weight:600; color:#34495e;
        background:#ecf0f1; margin-right:4px;
    }
    .article-date { color:#95a5a6; font-size:11px; font-weight:500; }
    .article-title {
        font-size:15.5px; font-weight:700; color:#1a2733; margin:10px 0 7px 0;
        line-height:1.45; display:-webkit-box; -webkit-line-clamp:2;
        -webkit-box-orient:vertical; overflow:hidden;
    }
    .article-card.compact .article-title { font-size:14px; margin:7px 0 5px 0; }
    .article-summary {
        font-size:12.5px; color:#5a6b7b; line-height:1.6; flex-grow:1;
        display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden;
    }
    .article-card.compact .article-summary { -webkit-line-clamp:2; font-size:11.5px; }
    .article-footer {
        margin-top:12px; padding-top:10px; border-top:1px solid #f0f3f6;
        display:flex; justify-content:space-between; align-items:center;
    }
    .article-source { font-size:11px; color:#95a5a6; font-weight:500; }
    .article-link { color:#2c5282; text-decoration:none; font-weight:600; font-size:12px; }
    .article-link:hover { text-decoration:underline; }
    .dup-note {
        font-size:11px; color:#7f8c8d; margin-top:8px;
        background:#f8fafc; border-radius:6px; padding:6px 10px;
    }

    [data-testid="stSidebar"] { background:#f8fafc; }
    .sidebar-group-title {
        font-size:12.5px; font-weight:700; color:#2c5282;
        margin:14px 0 6px 0; padding-bottom:5px; border-bottom:2px solid #e2e8f0;
    }
    .result-count { font-size:13.5px; color:#5a6b7b; margin:6px 0 14px 0; }
    .result-count b { color:#2c5282; font-size:16px; }

    .footer-section {
        margin-top:32px; padding:22px 26px 60px 26px; border-radius:14px;
        background:#f4f7fa; border:1px solid #e8edf3;
    }
    .footer-title { font-size:13px; font-weight:700; color:#2c5282; margin-bottom:8px; }
    .footer-text { font-size:11.5px; color:#6b7a89; line-height:1.7; margin-bottom:4px; }
    .footer-author {
        font-size:12.5px; color:#2c5282; font-weight:700;
        margin-top:12px; padding-top:12px; border-top:1px dashed #cdd8e3;
    }
    .footer-author .heart { color:#e84393; }
    hr.fdiv { margin:12px 0; border:none; border-top:1px dashed #d5dee7; }
    #MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)


# ================================
# 카드 렌더링
# ================================
def get_card_html(art, show_tag=True, compact=False, dup_count=0):
    cat = art["category"]
    info = CATEGORIES.get(cat, {"color": "#999", "icon": "📰"})
    color = info["color"]

    title_safe = html.escape(art["title"] or "")
    summary_safe = html.escape(art["summary"] or "")
    source_safe = html.escape(art["source"] or "")
    url = art["url"]

    imp = estimate_importance(art["title"], art["summary"])
    im = IMPORTANCE_META[imp]
    rel_tags = estimate_relevance(art["title"], art["summary"])

    imp_html = (f'<span class="imp-badge" style="background:{im["bg"]};'
                f'color:{im["color"]};">● {im["label"]} · {im["tip"]}</span>')
    cat_html = (f'<span class="cat-tag" style="background:{color};">'
                f'{info["icon"]} {cat}</span>') if show_tag else ""
    rel_html = "".join(
        f'<span class="rel-tag">{html.escape(t)}</span>' for t in rel_tags
    )
    summary_block = "" if compact else \
        f'<div class="article-summary">{summary_safe}</div>'

    dup_block = ""
    if dup_count > 0:
        dup_block = (f'<div class="dup-note">🔗 같은 이슈 관련 기사 '
                     f'{dup_count}건 더 있음 (대표 기사 표시 중)</div>')

    cls = "article-card compact" if compact else "article-card"

    return (
        f'<div class="{cls}" style="border-left-color:{color};">'
        f'<div>{imp_html} {cat_html}'
        f'<span class="article-date">📅 {art["pub_date"]}</span></div>'
        f'<div style="margin-top:6px;">{rel_html}</div>'
        f'<div class="article-title">{title_safe}</div>'
        f'{summary_block}{dup_block}'
        f'<div class="article-footer">'
        f'<span class="article-source">📰 {source_safe}</span>'
        f'<a href="{url}" target="_blank" class="article-link">원문 보기 →</a>'
        f'</div></div>'
    )


def render_groups(groups, show_tag=True, compact=False, columns=2):
    for i in range(0, len(groups), columns):
        cols = st.columns(columns, gap="medium")
        for j, g in enumerate(groups[i:i + columns]):
            with cols[j]:
                st.markdown(
                    get_card_html(g["rep"], show_tag, compact, len(g["dups"])),
                    unsafe_allow_html=True
                )


# ================================
# 헤더
# ================================
current = now_kst()
weekday_kr = ["월", "화", "수", "목", "금", "토", "일"][current.weekday()]
last_scraped = get_last_scraped_time()

hcol1, hcol2 = st.columns([3, 1.3])
with hcol1:
    st.markdown(
        '<div class="app-header">'
        '<h1>📰 기사 스크랩</h1>'
        '<div class="subtitle">산업 · 인사노무 분야 업무용 뉴스 모니터링</div>'
        '</div>',
        unsafe_allow_html=True
    )
with hcol2:
    upd = last_scraped[:16].replace("T", " ") if last_scraped else "없음"
    st.markdown(
        '<div class="app-header" style="background:linear-gradient(120deg,#2c5282 0%,#3a6aa5 100%);">'
        '<div class="header-clock">'
        f'<span class="time-big">{current.strftime("%H:%M")}</span>'
        f'{current.strftime("%Y-%m-%d")} ({weekday_kr})'
        f'<div class="latest">🔄 마지막 업데이트: {upd}</div>'
        '</div></div>',
        unsafe_allow_html=True
    )

st.write("")

# ================================
# 사이드바
# ================================
with st.sidebar:
    st.markdown("### 🔍 조회 조건")

    counts = get_article_count_by_category()
    selected_categories = []
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

    st.markdown("**🏷️ 업무 관련성**")
    rel_options = ["전체"] + list(RELEVANCE_RULES.keys()) + ["일반"]
    rel_filter = st.selectbox("업무관련성", rel_options,
                              label_visibility="collapsed")

    st.divider()

    st.markdown("**⭐ 중요도**")
    imp_filter = st.multiselect(
        "중요도",
        ["상 (즉시 확인)", "중 (주간 검토)", "하 (단순 참고)"],
        default=["상 (즉시 확인)", "중 (주간 검토)", "하 (단순 참고)"],
        label_visibility="collapsed"
    )
    imp_selected = set()
    if "상 (즉시 확인)" in imp_filter: imp_selected.add("HIGH")
    if "중 (주간 검토)" in imp_filter: imp_selected.add("MID")
    if "하 (단순 참고)" in imp_filter: imp_selected.add("LOW")

    st.divider()

    st.markdown("**📅 기간**")
    date_option = st.radio("기간선택",
                           ["오늘", "최근 3일", "최근 7일", "직접 선택"],
                           index=0, label_visibility="collapsed")
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

    st.markdown("**🔎 검색**")
    keyword = st.text_input("검색어", placeholder="제목/내용 키워드",
                            label_visibility="collapsed")
    all_sources = ["전체"] + get_all_sources()
    source_filter = st.selectbox("언론사", all_sources)
    exclude_kw = st.text_input("제외 키워드",
                               placeholder="예: 주가, 연예 (쉼표 구분)")

    st.divider()

    st.markdown("**🎨 보기 옵션**")
    column_count = st.radio("열", [1, 2, 3], index=1,
                            horizontal=True, label_visibility="collapsed")
    compact_mode = st.toggle("압축 보기", value=False)
    merge_dup = st.toggle("중복 기사 묶기", value=True)

    st.divider()
    st.caption(f"📊 전체 기사 {sum(counts.values()):,}건")


# ================================
# 메인 - 컨트롤
# ================================
cc1, cc2, cc3 = st.columns([2, 2.4, 1.8])
with cc1:
    st.markdown("#### 📄 검색 결과")
with cc2:
    sort_label = st.radio("정렬",
                          ["🔽 최신순", "🔼 오래된순", "⭐ 중요도순"],
                          index=0, horizontal=True,
                          label_visibility="collapsed")
with cc3:
    st.markdown(
        f"<div style='text-align:right;padding-top:6px;font-size:12.5px;color:#6b7a89;'>"
        f"📆 <b>{start_date}</b> ~ <b>{end_date}</b></div>",
        unsafe_allow_html=True
    )

db_sort = "asc" if "오래된순" in sort_label else "desc"
articles = fetch_articles(
    categories=selected_categories if selected_categories else None,
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat(),
    keyword=keyword if keyword else None,
    sort_order=db_sort,
    limit=400
)

if source_filter != "전체":
    articles = [a for a in articles if a["source"] == source_filter]

if exclude_kw.strip():
    ex_list = [w.strip() for w in exclude_kw.split(",") if w.strip()]
    if ex_list:
        articles = [
            a for a in articles
            if not any(w in f"{a['title']} {a['summary']}" for w in ex_list)
        ]

if rel_filter != "전체":
    articles = [
        a for a in articles
        if rel_filter in estimate_relevance(a["title"], a["summary"])
    ]

if imp_selected and len(imp_selected) < 3:
    articles = [
        a for a in articles
        if estimate_importance(a["title"], a["summary"]) in imp_selected
    ]

if "중요도순" in sort_label:
    articles.sort(
        key=lambda a: (
            IMPORTANCE_ORDER[estimate_importance(a["title"], a["summary"])],
            a["pub_date"]
        )
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
            cat_arts = [a for a in articles if a["category"] == cat]
            if not cat_arts:
                continue
            info = CATEGORIES[cat]
            grps = group_duplicates(cat_arts) if merge_dup else \
                [{"rep": a, "dups": []} for a in cat_arts]
            st.markdown(
                f"### {info['icon']} {cat} "
                f"<span style='font-size:13px;color:#95a5a6;'>"
                f"({len(cat_arts)}건)</span>",
                unsafe_allow_html=True
            )
            render_groups(grps, show_tag=False,
                          compact=compact_mode, columns=column_count)
            st.write("")
    else:
        grps = group_duplicates(articles) if merge_dup else \
            [{"rep": a, "dups": []} for a in articles]
        render_groups(grps, show_tag=True,
                      compact=compact_mode, columns=column_count)


# ================================
# 푸터
# ================================
st.markdown(
    '<div class="footer-section">'
    '<div class="footer-title">📌 안내사항</div>'
    '<div class="footer-text">• 본 페이지는 공개된 RSS 피드를 통해 수집된 뉴스를 안내하는 비영리 정보 제공 서비스입니다.</div>'
    '<div class="footer-text">• <b>모든 기사의 저작권은 해당 언론사 및 기자에게 있습니다.</b> 제목·요약·출처 링크만 제공하며 원문은 각 언론사 사이트에서 확인하실 수 있습니다.</div>'
    '<div class="footer-text">• 중요도·업무 관련성 태그는 키워드 규칙 기반 <b>자동 추정값</b>으로, 실제 업무 판단과 다를 수 있습니다.</div>'
    '<div class="footer-text">• 수집 출처: 연합뉴스, 매일경제, 전자신문, 구글뉴스 등 공개 RSS</div>'
    '<hr class="fdiv">'
    f'<div class="footer-author"><span class="heart">♥</span> Made by <b>정원호</b> · {current.year}</div>'
    '</div>',
    unsafe_allow_html=True
)
