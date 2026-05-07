"""
웹 크롤링 모듈 - 검증된 국내 언론사 RSS + 구글 뉴스 RSS 조합
- 모든 시각을 KST(한국 시간) 기준으로 처리
- 6개 분야 지원 (원자력, 전력, 방산, 반도체, 물류, 해운)
"""
import time
import requests
import urllib3
from bs4 import BeautifulSoup
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

from config import CATEGORIES, CRAWL_CONFIG
from database import insert_article, init_db

# SSL 인증서 검증 우회 (사내망 대응)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 한국 표준시
KST = timezone(timedelta(hours=9))


def now_kst():
    return datetime.now(KST)


# 검증 완료된 RSS 피드
RSS_FEEDS = [
    {"name": "연합뉴스 산업", "url": "https://www.yna.co.kr/rss/industry.xml"},
    {"name": "연합뉴스 경제", "url": "https://www.yna.co.kr/rss/economy.xml"},
    {"name": "매일경제 기업", "url": "https://www.mk.co.kr/rss/50300009/"},
    {"name": "매일경제 경제", "url": "https://www.mk.co.kr/rss/30100041/"},
    {"name": "한국경제 IT", "url": "https://www.hankyung.com/feed/it"},
    {"name": "한국경제 경제", "url": "https://www.hankyung.com/feed/economy"},
    {"name": "전자신문", "url": "https://rss.etnews.com/Section901.xml"},
]

# 분야별 구글뉴스 검색용 대표 키워드 (보강 검색용)
# 분야 키워드 중 너무 일반적이지 않으면서도 잘 매칭되는 것들 선정
SEARCH_KEYWORDS = {
    "원자력": ["원자력", "원전", "SMR"],
    "전력": ["전력망", "한전", "신재생에너지"],
    "방산": ["방산수출", "K-방산", "방위산업"],
    "반도체": ["반도체", "HBM", "파운드리"],
    "물류": ["물류", "택배", "물류센터"],
    "해운": ["해운", "HMM", "해상운임"],
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
    """RSS 발행일을 KST 기준 YYYY-MM-DD로 변환"""
    if not date_str:
        return now_kst().strftime("%Y-%m-%d")
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_kst = dt.astimezone(KST)
        return dt_kst.strftime("%Y-%m-%d")
    except Exception:
        try:
            return date_str[:10]
        except Exception:
            return now_kst().strftime("%Y-%m-%d")


def parse_rss(content, source_name):
    """RSS XML을 파싱"""
    articles = []
    try:
        soup = BeautifulSoup(content, "xml")
        items = soup.find_all("item")

        for item in items:
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
                    desc_html = desc_tag.get_text()
                    desc_soup = BeautifulSoup(desc_html, "html.parser")
                    summary = desc_soup.get_text(" ", strip=True)
                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                pub_date = parse_pub_date(
                    pubdate_tag.get_text(strip=True) if pubdate_tag else None
                )

                articles.append({
                    "title": title,
                    "url": article_url,
                    "summary": summary,
                    "source": source_name,
                    "pub_date": pub_date,
                })
            except Exception:
                continue
    except Exception as e:
        print(f"  ! 파싱 실패: {e}")
    return articles


def fetch_rss(url, source_name):
    try:
        resp = requests.get(
            url, headers=get_headers(),
            timeout=CRAWL_CONFIG["request_timeout"], verify=False
        )
        resp.raise_for_status()
        return parse_rss(resp.content, source_name)
    except requests.RequestException as e:
        print(f"  ! 요청 실패 ({source_name}): {str(e)[:80]}")
        return []


def fetch_google_news(keyword, max_count=20):
    encoded = quote(keyword)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        resp = requests.get(
            url, headers=get_headers(),
            timeout=CRAWL_CONFIG["request_timeout"], verify=False
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "xml")
        items = soup.find_all("item")[:max_count]

        articles = []
        for item in items:
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
                    desc_soup = BeautifulSoup(desc_tag.get_text(), "html.parser")
                    summary = desc_soup.get_text(" ", strip=True)
                    if len(summary) > 200:
                        summary = summary[:200] + "..."

                pub_date = parse_pub_date(
                    pubdate_tag.get_text(strip=True) if pubdate_tag else None
                )

                articles.append({
                    "title": title,
                    "url": article_url,
                    "summary": summary,
                    "source": source,
                    "pub_date": pub_date,
                })
            except Exception:
                continue
        return articles
    except requests.RequestException as e:
        print(f"  ! 구글뉴스 요청 실패 ({keyword}): {str(e)[:80]}")
        return []


def categorize_article(title, summary):
    """기사를 보고 어느 분야에 속하는지 판단"""
    text = f"{title} {summary}"
    for category, info in CATEGORIES.items():
        for kw in info["keywords"]:
            if kw in text:
                return category
    return None


def is_in_category(title, summary, target_category):
    """특정 분야에 속하는지 확인"""
    text = f"{title} {summary}"
    keywords = CATEGORIES[target_category]["keywords"]
    return any(kw in text for kw in keywords)


def run_scraping():
    """전체 크롤링 실행"""
    print(f"\n{'='*60}")
    print(f"  크롤링 시작: {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'='*60}")

    init_db()
    total_new = 0

    # 1단계: 국내 언론사 RSS
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

            inserted = insert_article(
                title=art["title"],
                category=category,
                summary=art["summary"],
                url=art["url"],
                source=art["source"],
                pub_date=art["pub_date"],
            )
            if inserted:
                category_counts[category] += 1
                total_new += 1

        time.sleep(CRAWL_CONFIG["delay_between_requests"])

    print(f"\n  → 1단계 분야별 신규 저장:")
    for cat, cnt in category_counts.items():
        info = CATEGORIES[cat]
        print(f"     {info['icon']} {cat}: {cnt}건")

    # 2단계: 구글 뉴스 보강
    print(f"\n[2단계] 구글 뉴스 분야별 보강 검색")
    google_counts = {cat: 0 for cat in CATEGORIES}

    for category, info in CATEGORIES.items():
        print(f"\n  {info['icon']} {category}")
        # 분야별 정해진 검색 키워드 사용
        search_kws = SEARCH_KEYWORDS.get(category, info["keywords"][:2])

        for kw in search_kws:
            print(f"    검색어: '{kw}'")
            articles = fetch_google_news(kw, max_count=15)

            for art in articles:
                if not is_in_category(art["title"], art["summary"], category):
                    continue

                inserted = insert_article(
                    title=art["title"],
                    category=category,
                    summary=art["summary"],
                    url=art["url"],
                    source=art["source"],
                    pub_date=art["pub_date"],
                )
                if inserted:
                    google_counts[category] += 1
                    total_new += 1

            time.sleep(CRAWL_CONFIG["delay_between_requests"])

        print(f"    → 신규 {google_counts[category]}건")

    # 결과 요약
    print(f"\n{'='*60}")
    print(f"  ✅ 완료: 총 {total_new}건 신규 저장")
    print(f"  종료 시각: {now_kst().strftime('%Y-%m-%d %H:%M:%S KST')}")
    print(f"{'='*60}")
    print(f"  분야별 합계:")
    for cat in CATEGORIES:
        info = CATEGORIES[cat]
        total = category_counts[cat] + google_counts[cat]
        print(f"    {info['icon']} {cat}: {total}건")
    print(f"{'='*60}\n")
    return total_new


if __name__ == "__main__":
    run_scraping()
