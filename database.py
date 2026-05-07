"""
SQLite 데이터베이스 관리 모듈
"""
import sqlite3
import os
from datetime import datetime, date
from contextlib import contextmanager
from config import DB_PATH


@contextmanager
def get_connection():
    """DB 커넥션 컨텍스트 매니저"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db():
    """DB 테이블 초기화"""
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                summary TEXT,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                pub_date TEXT,
                scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_date TEXT NOT NULL,
                visitor_hash TEXT NOT NULL,
                visit_time TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(visit_date, visitor_hash)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON articles(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pub_date ON articles(pub_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_visit_date ON visitors(visit_date)")


def insert_article(title, category, summary, url, source, pub_date):
    """기사 저장 (URL 중복 시 무시)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO articles (title, category, summary, url, source, pub_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, category, summary, url, source, pub_date))
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False


def fetch_articles(categories=None, start_date=None, end_date=None, keyword=None,
                   sort_order="desc", limit=300):
    """
    조건에 따라 기사 조회
    - categories: 분야 리스트
    - start_date, end_date: 날짜 범위 (YYYY-MM-DD)
    - keyword: 제목 검색어
    - sort_order: 'desc' (최신순) or 'asc' (오래된순)
    """
    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if categories:
        placeholders = ",".join("?" * len(categories))
        query += f" AND category IN ({placeholders})"
        params.extend(categories)

    if start_date:
        query += " AND date(pub_date) >= date(?)"
        params.append(start_date)

    if end_date:
        query += " AND date(pub_date) <= date(?)"
        params.append(end_date)

    if keyword:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    # 정렬: 최신순(desc) / 오래된순(asc)
    order = "DESC" if sort_order == "desc" else "ASC"
    query += f" ORDER BY pub_date {order}, scraped_at {order} LIMIT ?"
    params.append(limit)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_article_count_by_category():
    """분야별 기사 개수"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT category, COUNT(*) as cnt 
            FROM articles 
            GROUP BY category
        """)
        return {row["category"]: row["cnt"] for row in cursor.fetchall()}


def record_visitor(visitor_hash):
    """방문자 기록 (일일 유니크)"""
    today = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO visitors (visit_date, visitor_hash)
                VALUES (?, ?)
            """, (today, visitor_hash))
            return cursor.rowcount > 0
        except sqlite3.Error:
            return False


def get_visitor_stats():
    """누적/일일 방문자 수 조회"""
    today = date.today().isoformat()
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM visitors")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as today FROM visitors WHERE visit_date = ?", (today,))
        today_count = cursor.fetchone()["today"]

        return {"total": total, "today": today_count}
