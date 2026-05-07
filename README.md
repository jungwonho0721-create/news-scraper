# 📰 산업 기사 스크랩

원자력 · 전력 · 방산 · 반도체 분야의 최신 뉴스를 자동 수집하여 보여주는 Streamlit 웹앱.

## 🚀 빠른 시작

### 로컬 실행
```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 최초 데이터 수집
python scraper.py

# 3. 앱 실행
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 로 접속.

## 📂 프로젝트 구조

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit UI |
| `scraper.py` | 네이버 뉴스 크롤러 |
| `database.py` | SQLite CRUD |
| `visitor_counter.py` | 방문자 카운터 |
| `config.py` | 분야/키워드 설정 |
| `.github/workflows/scrape.yml` | 일 4회 자동 수집 |

## 🌐 Streamlit Cloud 배포

1. 본 폴더를 GitHub 저장소에 푸시
2. https://share.streamlit.io/ 접속 → 저장소 연결
3. Main file: `app.py` 지정 후 Deploy
4. 발급된 URL을 배포

## ⏰ 자동 스크래핑

GitHub Actions가 매일 KST 기준 **07:00 / 09:00 / 12:00 / 15:00** 에 자동으로
기사를 수집하여 DB를 업데이트하고 커밋합니다.

## ⚠️ 참고사항

- **저작권**: 본 앱은 기사 제목/요약/링크만 표시하며 원문은 언론사 페이지로 연결됩니다.
- **크롤링 차단 방지**: 요청 간 1.5초 딜레이를 두고 있습니다. 만약 차단 발생 시
  `config.py`의 `delay_between_requests`를 늘려주세요.
- **방문자 카운터**: IP를 SHA-256 해시 처리하여 개인정보를 보호합니다.

## 🔧 분야/키워드 수정

`config.py`의 `CATEGORIES` 딕셔너리에서 자유롭게 추가/수정 가능합니다.
