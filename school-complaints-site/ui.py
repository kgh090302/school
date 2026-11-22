"""두 앱이 함께 쓰는 화면 스타일(CSS)과 상단 배너."""
import streamlit as st

_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

html, body, .stMarkdown, button, input, textarea, label {
    font-family: 'Pretendard', -apple-system, 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
.block-container { padding-top: 2.2rem; max-width: 1080px; }

/* 상단 배너 */
.hero {
    padding: 1.7rem 2rem; border-radius: 20px; margin-bottom: 1.6rem; color: #fff;
    box-shadow: 0 10px 28px rgba(79, 70, 229, .22);
}
.hero-student { background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); }
.hero-admin   { background: linear-gradient(135deg, #1f2937 0%, #4338ca 100%); box-shadow: 0 10px 28px rgba(31, 41, 55, .25); }
.hero h1 { margin: 0; padding: 0; font-size: 1.9rem; font-weight: 800; color: #fff !important; letter-spacing: -0.02em; }
.hero p  { margin: .5rem 0 0; font-size: 1.02rem; opacity: .92; color: #fff; }

/* 페이지 제목 / 소제목 */
h1, h2, h3 { letter-spacing: -0.02em; }
h3 { font-size: 1.15rem !important; }

/* 카드(테두리 있는 컨테이너) */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; }

/* 통계 카드 */
[data-testid="stMetric"] {
    background: #f4f4fb; border-radius: 14px; padding: .9rem 1.1rem;
    border: 1px solid #e6e6f5;
}
[data-testid="stMetricLabel"] { font-weight: 600; }

/* 버튼 */
.stButton > button {
    border-radius: 12px; font-weight: 700; padding: .55rem 1.1rem;
    border: 1px solid #d9d9ee; transition: all .15s ease;
}
.stButton > button:hover { border-color: #4f46e5; color: #4f46e5; transform: translateY(-1px); }

/* 입력창 */
.stTextArea textarea, .stTextInput input { border-radius: 12px; }

/* 사이드바 */
section[data-testid="stSidebar"] { background: #f4f4fb; border-right: 1px solid #e6e6f5; }

/* 펼침 메뉴 */
[data-testid="stExpander"] { border-radius: 12px; }

hr { margin: .8rem 0; }
</style>
"""


def apply_style():
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(title, subtitle, variant="student"):
    st.markdown(
        f'<div class="hero hero-{variant}"><h1>{title}</h1><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
