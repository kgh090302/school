import os
import uuid
import json
import streamlit as st
import pandas as pd
from datetime import datetime
from openai import OpenAI

from db import COLUMNS, load_df, add_complaints, add_like as db_add_like, get_client, get_secret
from ui import apply_style, hero

# 1. 웹 사이트 기본 설정 (학생용)
st.set_page_config(page_title="학교 대신 전해드립니다 (학생용)", page_icon="🏫", layout="wide")
apply_style()
hero("🏫 학교 대신 전해드립니다", "학생회가 여러분의 목소리를 듣고 있어요. 건의사항을 남기면 AI가 알맞은 부서를 찾아 전달해 드려요.")

# 2. 데이터베이스 연결 확인 (예전: complaints.csv 파일 초기화 -> 지금: Supabase 연결)
try:
    get_client()
except RuntimeError as e:
    st.error(str(e))
    st.stop()

# 공감 버튼 클릭 함수
def add_like(complaint_id):
    db_add_like(complaint_id)

def get_status_badge(status):
    if status == "접수 완료": return "🟢 접수 완료"
    elif status == "검토 중": return "🟡 검토 중"
    elif status == "처리 완료": return "🔵 처리 완료"
    return status

# 3. 사이드바 메뉴 설정 (관리자 메뉴 없음!)
with st.sidebar:
    st.header("⚙️ 기본 설정")
    api_key = st.text_input("OpenAI API Key를 입력하세요", type="password")
    api_key = api_key or get_secret("OPENAI_API_KEY")  # 서버 secrets 에 키를 넣어두면 학생이 입력하지 않아도 됩니다
    st.divider()
    
    st.header("📂 메뉴 이동")
    menu = st.radio("접속 페이지 선택:", ["📝 새 민원 작성", "📢 공개 민원 게시판"])

if api_key:
    os.environ["OPENAI_API_KEY"] = api_key
    client = OpenAI(api_key=api_key)

    # ==========================================
    # 메뉴 1: 새 민원 작성 (AI 부서 배정 & 비밀글)
    # ==========================================
    if menu == "📝 새 민원 작성":
        st.title("📝 새로운 의견을 들려주세요")
        
        if 'step' not in st.session_state: st.session_state.step = 1
        
        student_message = st.text_area("건의사항 작성", height=150, placeholder="학교에 바라는 점을 자유롭게 적어주세요.")
        is_secret = st.checkbox("☑️ 이 건의사항을 비밀글로 설정합니다 (학생회만 확인 가능)")
        
        if st.button("🔍 AI 검토 및 부서 배정받기"):
            if student_message.strip():
                with st.spinner("AI가 내용을 분석 중입니다..."):
                    df = load_df()
                    existing_summaries = df[df['비밀글'] == False]['요약 내용'].tail(5).tolist() 
                    
                    instructions = """
                    당신은 학교 학생회 비서입니다. 민원을 분석하여 JSON 형식으로 출력하세요.
                    1. "department": [시설관리부, 급식부, 학생생활부, 교무학사부, 행사복지부, 기타] 중 1개 선택.
                    2. "summary": 욕설을 순화하고 3문장 이내 핵심 요약.
                    3. "similarity": 제공된 기존 민원과 유사하면 안내, 없으면 "없음" 출력.
                    """
                    prompt = f"[건의사항] {student_message}\n[기존 민원] {existing_summaries}"
                    
                    try:
                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            response_format={"type": "json_object"},
                            messages=[
                                {"role": "system", "content": instructions},
                                {"role": "user", "content": prompt}
                            ],
                            temperature=0.3
                        )
                        ai_result = json.loads(response.choices[0].message.content)
                        st.session_state.dept = ai_result.get("department", "기타")
                        st.session_state.summary = ai_result.get("summary", "요약 오류")
                        st.session_state.similarity = ai_result.get("similarity", "")
                        st.session_state.step = 2
                    except Exception as e:
                        st.error(f"오류: {e}")
            else:
                st.warning("내용을 입력해 주세요!")
                
        # [제출 단계] 데이터를 생성하여 DB에 추가(Append)만 수행
        if st.session_state.step == 2:
            with st.container(border=True):
                st.success("✅ AI 분석 완료!")
                st.markdown(f"**🏷️ 배정 부서:** `{st.session_state.dept}`\n\n**📝 요약:** {st.session_state.summary}")
                
                if st.button("🚀 최종 제출하기"):
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_data = pd.DataFrame([{
                        "ID": str(uuid.uuid4())[:8], "날짜": now, "상태": "접수 완료", 
                        "공감수": 0, "비밀글": is_secret, "담당 부서": st.session_state.dept,
                        "요약 내용": st.session_state.summary, "원본 내용": student_message
                    }])
                    add_complaints(new_data)
                    st.success("✅ 제출 완료!")
                    st.session_state.step = 1 

    # ==========================================
    # 메뉴 2: 공개 민원 게시판 (비밀글 원천 차단)
    # ==========================================
    elif menu == "📢 공개 민원 게시판":
        st.title("📢 접수된 학생들의 목소리")
        df = load_df()
        df_public = df[df['비밀글'] == False] # 💡 보안: 비밀글은 이 화면에 절대 데이터를 넘기지 않음
        
        if df_public.empty:
            st.info("공개된 민원이 없습니다.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("공개 민원", f"{len(df_public)}건")
            m2.metric("검토 중", f"{int((df_public['상태'] == '검토 중').sum())}건")
            m3.metric("처리 완료", f"{int((df_public['상태'] == '처리 완료').sum())}건")
            st.write("")

            df_public = df_public.sort_values(by="날짜", ascending=False)
            for _, row in df_public.iterrows():
                with st.container(border=True):
                    st.markdown(f"### {get_status_badge(row['상태'])} | 🏷️ {row['담당 부서']}")
                    st.markdown(f"**요약 내용:** {row['요약 내용']}")
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.button(f"👍 공감 ({row['공감수']})", key=row['ID'], on_click=add_like, args=(row['ID'],))
                    with col2:
                        with st.expander("원본 내용 보기"):
                            st.write(row['원본 내용'])
else:
    st.info("👈 API 키를 입력해 주세요.")
