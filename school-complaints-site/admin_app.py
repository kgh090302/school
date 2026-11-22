import os
import streamlit as st
import pandas as pd
from openai import OpenAI

from db import load_df, save_df, get_secret
from ui import apply_style, hero

# 1. 웹 사이트 기본 설정 (관리자용)
st.set_page_config(page_title="학생회 관리자 대시보드", page_icon="🔒", layout="wide")
apply_style()
hero("🔒 학생회 관리자 대시보드", "비밀 민원 확인, 처리 상태 관리, 월간 성과 보고서를 한 곳에서 관리하세요.", variant="admin")

# 접속 비밀번호: secrets 에 ADMIN_PASSWORD 를 넣으면 그 값을 쓰고, 없으면 기본값 1234 를 씁니다.
ADMIN_PW = get_secret("ADMIN_PASSWORD") or "1234"

def get_status_badge(status):
    if status == "접수 완료": return "🟢 접수 완료"
    elif status == "검토 중": return "🟡 검토 중"
    elif status == "처리 완료": return "🔵 처리 완료"
    return status

# 2. 사이드바 설정
with st.sidebar:
    st.header("⚙️ 관리자 설정")
    api_key = st.text_input("OpenAI API Key (보고서용)", type="password")
    api_key = api_key or get_secret("OPENAI_API_KEY")  # secrets 에 넣어두면 매번 입력하지 않아도 됩니다
    
    st.divider()
    st.header("📂 메뉴 이동")
    menu = st.radio("관리 메뉴:", [
        "🤫 비밀 민원 집중 관리", 
        "🚦 전체 민원 상태 관리", 
        "📊 AI 성과 보고서 생성"
    ])

# 💡 관리자 페이지 자체에 강력한 비밀번호(접근 제어) 설정
admin_pw = st.sidebar.text_input("학생회 접속 비밀번호", type="password")

if admin_pw == ADMIN_PW:
    # 데이터 불러오기 (Supabase)
    try:
        df = load_df(admin=True)
    except Exception as e:
        st.error(f"Supabase 연결에 실패했습니다. secrets 설정(SUPABASE_URL, SUPABASE_SERVICE_KEY)을 확인해 주세요.\n\n{e}")
        st.stop()
        
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        client = OpenAI(api_key=api_key)

    # 상단 요약 카드
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("전체 민원", f"{len(df)}건")
    s2.metric("접수 완료", f"{int((df['상태'] == '접수 완료').sum())}건")
    s3.metric("검토 중", f"{int((df['상태'] == '검토 중').sum())}건")
    s4.metric("처리 완료", f"{int((df['상태'] == '처리 완료').sum())}건")
    s5.metric("비밀 민원", f"{int((df['비밀글'] == True).sum())}건")
    st.write("")

    # ==========================================
    # 메뉴 1: 비밀 민원 확인 (관리자만 볼 수 있음)
    # ==========================================
    if menu == "🤫 비밀 민원 집중 관리":
        st.title("🤫 비밀 민원 관리함")
        st.warning("학생들이 비밀로 남긴 민감한 건의사항입니다. 외부 유출에 엄격히 주의해 주세요.")
        
        df_secret = df[df['비밀글'] == True]
        
        if df_secret.empty:
            st.info("현재 접수된 비밀 민원이 없습니다.")
        else:
            df_secret = df_secret.sort_values(by="날짜", ascending=False)
            for _, row in df_secret.iterrows():
                with st.container(border=True):
                    st.markdown(f"### 🔒 {get_status_badge(row['상태'])} | 🏷️ {row['담당 부서']}")
                    st.markdown(f"**접수 날짜:** {row['날짜']}")
                    st.markdown(f"**요약 내용:** {row['요약 내용']}")
                    with st.expander("원본 내용 꼼꼼히 읽기"):
                        st.write(row['원본 내용'])

    # ==========================================
    # 메뉴 2: 전체 상태 관리 (DB 수정 권한)
    # ==========================================
    elif menu == "🚦 전체 민원 상태 관리":
        st.title("🚦 통합 데이터베이스 관리")
        st.markdown("모든 민원을 확인하고 '처리 상태'나 '담당 부서'를 변경할 수 있습니다.")
        
        # 관리자 전용 데이터 편집기
        edited_df = st.data_editor(
            df,
            column_config={
                "상태": st.column_config.SelectboxColumn("처리 상태", options=["접수 완료", "검토 중", "처리 완료"]),
                "비밀글": st.column_config.CheckboxColumn("비밀 여부"),
                "담당 부서": st.column_config.TextColumn("담당 부서")
            },
            disabled=["ID", "날짜", "공감수", "요약 내용", "원본 내용"], # 내용 조작 방지
            use_container_width=True,
            hide_index=True
        )
        
        if st.button("💾 변경된 상태 서버에 저장"):
            save_df(edited_df)
            st.success("데이터베이스 업데이트 완료!")

    # ==========================================
    # 메뉴 3: AI 월간 보고서 (OpenAI API 필요)
    # ==========================================
    elif menu == "📊 AI 성과 보고서 생성":
        if not api_key:
            st.error("이 기능을 사용하려면 좌측에 OpenAI API 키를 입력해야 합니다.")
        else:
            st.title("📊 학생회 월간 성과 자동 보고서")
            completed_df = df[df['상태'] == '처리 완료']
            
            if st.button("✨ 이번 달 보고서 작성하기"):
                if completed_df.empty:
                    st.warning("'처리 완료'된 민원이 없습니다.")
                else:
                    with st.spinner("처리된 민원들을 모아 보고서를 작성 중입니다..."):
                        completed_texts = "\n".join([f"- [{r['담당 부서']}] {r['요약 내용']}" for _, r in completed_df.iterrows()])
                        prompt = f"""
                        이번 달 학생회 해결 민원:
                        {completed_texts}
                        위 내용을 바탕으로 인스타그램에 올릴 학생회 성과 보고서를 마크다운으로 친절하게 작성해줘.
                        """
                        try:
                            response = client.chat.completions.create(
                                model="gpt-4o-mini",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.4
                            )
                            st.success("보고서 생성 완료!")
                            st.info(response.choices[0].message.content)
                        except Exception as e:
                            st.error(f"오류: {e}")

elif admin_pw:
    st.error("비밀번호가 틀렸습니다." + ("" if get_secret("ADMIN_PASSWORD") else " (기본값: 1234)"))
else:
    st.info("👈 학생회 관리자 비밀번호를 입력해 주세요.")
