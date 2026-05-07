"""
분야별 키워드 및 뉴스 소스 설정
"""

# 분야별 키워드 (제목/본문에서 매칭)
CATEGORIES = {
    "원자력": {
        "keywords": ["원자력", "원전", "SMR", "한수원", "방사성", "핵연료", "탈원전", "원자로"],
        "color": "#FF6B6B",
        "icon": "⚛️"
    },
    "전력": {
        "keywords": ["전력", "한전", "전기요금", "송전", "변전", "전력망", "발전소", "전력수급", "ESS"],
        "color": "#4ECDC4",
        "icon": "⚡"
    },
    "방산": {
        "keywords": ["방산", "방위산업", "K-방산", "무기수출", "한화에어로", "KAI", "LIG넥스원", 
                    "현대로템", "K2전차", "K9자주포", "FA-50", "천궁"],
        "color": "#95A5A6",
        "icon": "🛡️"
    },
    "반도체": {
        "keywords": ["반도체", "HBM", "파운드리", "삼성전자", "SK하이닉스", "D램", "낸드", 
                    "TSMC", "엔비디아", "팹리스", "EUV", "후공정"],
        "color": "#3498DB",
        "icon": "💾"
    }
}

# 크롤링 대상 뉴스 소스 (네이버 뉴스 검색 기반 - 안정적)
NEWS_SOURCES = [
    {
        "name": "네이버뉴스",
        "type": "naver_search",
        "base_url": "https://search.naver.com/search.naver",
    }
]

# 크롤링 설정
CRAWL_CONFIG = {
    "max_articles_per_category": 30,    # 분야별 최대 수집 개수
    "request_timeout": 10,               # 요청 타임아웃(초)
    "delay_between_requests": 1.5,       # 요청 간격(초) - 차단 방지
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# DB 경로
DB_PATH = "data/articles.db"
