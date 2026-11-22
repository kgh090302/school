"""Supabase 데이터 계층.

기존 앱이 complaints.csv 를 읽고 쓰던 부분만 이 파일로 옮겼습니다.
앱 코드에서는 예전과 똑같이 한글 컬럼명(ID, 날짜, 상태, ...)을 가진 DataFrame 을 그대로 씁니다.
"""
import os
import streamlit as st
import pandas as pd
from supabase import create_client

TABLE = "complaints"
COLUMNS = ["ID", "날짜", "상태", "공감수", "비밀글", "담당 부서", "요약 내용", "원본 내용"]

# 앱의 한글 컬럼명 <-> Supabase 테이블 컬럼명
_DB_COLUMNS = {
    "ID": "id",
    "날짜": "submitted_at",
    "상태": "status",
    "공감수": "likes",
    "비밀글": "is_secret",
    "담당 부서": "department",
    "요약 내용": "summary",
    "원본 내용": "original_text",
}
_TO_KR = {v: k for k, v in _DB_COLUMNS.items()}


def get_secret(name):
    """Streamlit secrets 우선, 없으면 환경변수에서 값을 가져옵니다."""
    try:
        value = st.secrets[name]
    except Exception:
        value = None
    return value or os.environ.get(name)


@st.cache_resource(show_spinner=False)
def _make_client(url, key):
    return create_client(url, key)


def get_client(admin=False):
    """학생용: SUPABASE_KEY(공개용 키) / 관리자용: SUPABASE_SERVICE_KEY(서비스 키)."""
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_SERVICE_KEY" if admin else "SUPABASE_KEY")
    if not url or not key:
        needed = "SUPABASE_URL, SUPABASE_SERVICE_KEY" if admin else "SUPABASE_URL, SUPABASE_KEY"
        raise RuntimeError(f"Supabase 설정이 없습니다. secrets 에 {needed} 를 넣어 주세요. (README 참고)")
    return _make_client(url, key)


def _to_df(rows):
    if not rows:
        return pd.DataFrame(columns=COLUMNS)
    return pd.DataFrame(rows).rename(columns=_TO_KR)[COLUMNS]


def load_df(admin=False):
    """예전의 pd.read_csv(DATA_FILE) 대신 쓰는 함수. 오래된 글 -> 최신 글 순서입니다.

    학생용(admin=False)은 DB 보안 규칙(RLS) 때문에 비밀글이 애초에 포함되지 않습니다.
    """
    client = get_client(admin)
    rows, start, step = [], 0, 1000
    while True:
        res = (
            client.table(TABLE)
            .select("*")
            .order("submitted_at")
            .order("id")
            .range(start, start + step - 1)
            .execute()
        )
        rows.extend(res.data)
        if len(res.data) < step:
            break
        start += step
    return _to_df(rows)


def add_complaints(new_data):
    """예전의 'concat 후 to_csv' 대신, 새 민원 행들을 DB에 추가합니다."""
    client = get_client()
    for _, r in new_data.iterrows():
        client.rpc(
            "submit_complaint",
            {
                "p_id": str(r["ID"]),
                "p_submitted_at": str(r["날짜"]),
                "p_is_secret": bool(r["비밀글"]),
                "p_department": str(r["담당 부서"]),
                "p_summary": str(r["요약 내용"]),
                "p_original": str(r["원본 내용"]),
            },
        ).execute()


def add_like(complaint_id):
    """공감 +1 (DB 안에서 원자적으로 증가)."""
    get_client().rpc("add_like", {"p_id": str(complaint_id)}).execute()


def save_df(edited_df):
    """관리자용: 편집된 표에서 달라진 행만 DB에 반영합니다. (상태 / 담당 부서 / 비밀 여부)"""
    client = get_client(admin=True)
    current = load_df(admin=True).set_index("ID")
    changed = 0
    for _, row in edited_df.iterrows():
        cid = row["ID"]
        if cid not in current.index:
            continue
        dept = row["담당 부서"]
        if pd.isna(dept) or not str(dept).strip():
            dept = "기타"
        new_values = {
            "status": str(row["상태"]),
            "department": str(dept),
            "is_secret": bool(row["비밀글"]),
        }
        old = current.loc[cid]
        old_values = {
            "status": old["상태"],
            "department": old["담당 부서"],
            "is_secret": bool(old["비밀글"]),
        }
        if new_values != old_values:
            client.table(TABLE).update(new_values).eq("id", cid).execute()
            changed += 1
    return changed
