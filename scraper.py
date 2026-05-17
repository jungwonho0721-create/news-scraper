"""
웹 크롤링 모듈
- 8개 분야 지원 (산업 6 + 인사노무 2)
- 한국경제 RSS 제거 (프리미엄 구독 필요)
- 연예/스포츠/가십성 기사 자동 필터링
- KST(한국 시간) 기준
"""
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from config import CATEGORIES, CRAWL_CONFIG, EXCLUDE_KEYWORDS, BLOCKED_SOURCES
from database import insert_article, init_db

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST)


# RSS 피드 (한국경제 제거됨)
RSS_FEEDS = [
    {"name": "연합뉴스 산업", "url": "https://www.yna.co.kr/rss/industry.xml"},
    {"name": "연합뉴스 경제", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"name": "매일경제 기업", "url": "https://www.mk.co.kr/rss/50300009/"},
    {"name": "매일경제 경제", "url": "https://www.mk.co.kr/rss/30100041/"},
    {"name": "전자신문", "url": "https://rss.etnews.com/Section901.xml"},
]

# 분야별 구글뉴스 검색 키워드
SEARCH_KEYWORDS = {
    "원자력": ["원자력", "원전", "SMR"],
    "전력": ["전력망", "한전", "신재생에너지"],
    "방산": ["방산수출", "K-방산", "방위산업"],
    "반도체": ["반도체", "HBM", "파운드리"],
    "물류": ["물류", "택배", "물류센터"],
    "해운": ["해운", "HMM", "해상운임"],
    "인사·노무": ["최저임금", "노동조합", "고용노동부"],
    "출산·육아": ["저출산", "육아휴직", "출산지원"],
}


def get_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }


def parse_pub_date(date_str):
    if not date_str:
        return now_kst().strftime("%Y-%m-%d")
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%Y-%m-%d")
    except Exception:
        try:
            return date_str[:10]
        except Exception:
            return now_kst().strftime("%Y-%m-%d")


def is_blocked_source(source_name):
    if not source_name:
        return False
    s = source_name.lower()
    return any(b.lower() in s for b in BLOCKED_SOURCES)


def is_excluded_article(title, summary):
    text = f"{title} {summary}"
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def parse_rss(content, source_name):
    articles = []
    try:
        soup = BeautifulSoup(content, "xml")
        for item in soup.find_all("item"):
            try:
                title_tag = item.find("title")
                link_tag = item.find("link")
                pubdate_tag = item.find("pubDate") or item.find("dc:date")
                desc_tag = item.find("description")

                if not (title_tag and link_tag):
                    continue

                title = title_tag.get_text(strip=True)
                article_url = link_tag.get_text(strip=True)

                summary = ""
                if desc_tag:
                    ds = BeautifulSoup(desc_tag.get_text(), "html.parser")
                    summary = ds.get_text(" ", strip=True)
                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                pub_date = parse_pub_date(
                    pubdate_tag.get_text(strip=True) if pubdate_tag else None
                )

                articles.append({
                    "title": title, "url": article_url,
                    "summary": summary, "source": source_name,
                    "pub_date": pub_date,
                })
            except Exception:
                continue
    except Exception as e:
        print(f"  ! 파싱 실패: {e}")
    return articles


def fetch_rss(url, source_name):
    try:
        resp = requests.get(url, headers=get_headers(),
                            timeout=CRAWL_CONFIG["request_timeout"], verify=False)
        resp.raise_for_status()
        return parse_rss(resp.content, source_name)
    except requests.RequestException as e:
        print(f"  ! 요청 실패 ({source_name}): {str(e)[:80]}")
        return []


def fetch_google_news(keyword, max_count=20):
    encoded = quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        resp = requests.get(url, headers=get_headers(),
                            timeout=CRAWL_CONFIG["request_timeout"], verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        articles = []
        for item in soup.find_all("item")[:max_count]:
            try:
                title_tag = item.find("title")
                link_tag = item.find("link")
                pubdate_tag = item.find("pubDate")
                desc_tag = item.find("description")

                if not (title_tag and link_tag):
                    continue

                title = title_tag.get_text(strip=True)
                article_url = link_tag.get_text(strip=True)

                source = "구글뉴스"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0].strip()
                    source = parts[1].strip()

                summary = ""
                if desc_tag:
                    ds = BeautifulSoup(desc_tag.get_text(), "html.parser")
                    summary = ds.get_text(" ", strip=True)
                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                pub_date = parse_pub_date(
                    pubdate_tag.get_text(strip=True) if pubdate_tag else None
                )

                articles.append({
                    "title": title, "url": article_url,
                    "summary": summary, "source": source,
                    "pub_date": pub_date,
                })
            except Exception:
                continue
        return articles
    except requests.RequestException as e:
        print(f"  ! 구글뉴스 요청 실패 ({keyword}): {str(e)[:80]}")
        return []


def categorize_article(title, summary):
    text = f"{title} {summary}"
    for category, info in CATEGORIES.items():
        for kw in info["keywords"]:
            if kw in text:
                return category
    return None


def is_in_category(title, summary, target_category):
    text = f"{title} {summary}"
    return any(kw in text for kw in CATEGORIES[target_category]["keywords"])


def should_save(article, target_category=None):
    if is_blocked_source(article["source"]):
        return False, "차단된 출처"
    if is_excluded_article(article["title"], article["summary"]):
        return False, "블랙리스트"
    if target_category:
        if not is_in_category(article["title"], article["summary"], target_category):
            return False, "분야 불일치"
    return True, "OK"


def run_scraping():
    print(f"\n{'='*60}")
    print(f"  크롤링 시작: {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'='*60}")

    init_db()
    total_new = 0
    total_filtered = 0

    print(f"\n[1단계] 국내 언론사 RSS 수집")
    category_counts = {cat: 0 for cat in CATEGORIES}

    for feed in RSS_FEEDS:
        print(f"\n  📰 {feed['name']}")
        articles = fetch_rss(feed["url"], feed["name"])
        print(f"     수집: {len(articles)}건")

        for art in articles:
            category = categorize_article(art["title"], art["summary"])
            if not category:
                continue
            should, reason = should_save(art)
            if not should:
                total_filtered += 1
                continue
            if insert_article(
                title=art["title"], category=category,
                summary=art["summary"], url=art["url"],
                source=art["source"], pub_date=art["pub_date"],
            ):
                category_counts[category] += 1
                total_new += 1

        time.sleep(CRAWL_CONFIG["delay_between_requests"])

    print(f"\n  → 1단계 분야별 신규 저장:")
    for cat, cnt in category_counts.items():
        info = CATEGORIES[cat]
        print(f"     {info['icon']} {cat}: {cnt}건")

    print(f"\n[2단계] 구글 뉴스 분야별 보강 검색")
    google_counts = {cat: 0 for cat in CATEGORIES}

    for category, info in CATEGORIES.items():
        print(f"\n  {info['icon']} {category}")
        search_kws = SEARCH_KEYWORDS.get(category, info["keywords"][:2])

        for kw in search_kws:
            print(f"    검색어: '{kw}'")
            articles = fetch_google_news(kw, max_count=15)

            for art in articles:
                should, reason = should_save(art, target_category=category)
                if not should:
                    if reason != "분야 불일치":
                        total_filtered += 1
                    continue
                if insert_article(
                    title=art["title"], category=category,
                    summary=art["summary"], url=art["url"],
                    source=art["source"], pub_date=art["pub_date"],
                ):
                    google_counts[category] += 1
                    total_new += 1

            time.sleep(CRAWL_CONFIG["delay_between_requests"])

        print(f"    → 신규 {google_counts[category]}건")

    print(f"\n{'='*60}")
    print(f"  ✅ 완료: 총 {total_new}건 신규 저장")
    print(f"  🚫 필터링됨: {total_filtered}건")
    print(f"  종료 시각: {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'='*60}")
    print(f"  분야별 합계:")
    for cat in CATEGORIES:
        info = CATEGORIES[cat]
        print(f"    {info['icon']} {cat}: {category_counts[cat] + google_counts[cat]}건")
    print(f"{'='*60}\n")
    return total_new


if __name__ == "__main__":
    run_scraping()
