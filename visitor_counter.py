"""
방문자 카운터 모듈
- 세션 단위로 1회만 카운트
- IP 해시 기반 일일 유니크 집계
"""
import hashlib
import streamlit as st
from database import record_visitor, get_visitor_stats


def get_visitor_id():
    """
    방문자 식별자 생성 (개인정보 보호를 위해 해시 처리)
    Streamlit은 클라이언트 IP 직접 접근이 제한적이므로
    세션 + 헤더 정보를 조합하여 해시화
    """
    try:
        # Streamlit 1.30+ 에서 클라이언트 IP 접근
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        from streamlit.runtime import get_instance

        ctx = get_script_run_ctx()
        if ctx is None:
            return None
        session_info = get_instance().get_client(ctx.session_id)
        if session_info is None:
            return None

        # 클라이언트 IP + User-Agent 조합
        ip = getattr(session_info.request, "remote_ip", "unknown")
        ua = session_info.request.headers.get("User-Agent", "")
        raw = f"{ip}_{ua}"
    except Exception:
        # 환경에 따라 접근 불가 시 세션 ID 사용
        raw = st.session_state.get("_visitor_raw", "fallback_session")

    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def track_visit():
    """
    페이지 진입 시 1회만 호출되도록 세션 상태로 제어
    """
    if not st.session_state.get("visit_recorded", False):
        visitor_id = get_visitor_id()
        if visitor_id:
            record_visitor(visitor_id)
        st.session_state["visit_recorded"] = True


def display_visitor_stats():
    """방문자 통계 표시 (우측 하단용 HTML 반환)"""
    stats = get_visitor_stats()
    return stats
