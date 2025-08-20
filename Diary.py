import streamlit as st
import sqlite3
import os
import uuid
from datetime import date, datetime
from PIL import Image
import pandas as pd
import altair as alt

# ===== 비밀번호 해시 라이브러리 선택 =====
# 기본: passlib.bcrypt 사용
from passlib.hash import bcrypt
# 만약 passlib/bcrypt 설치가 어려우면, 아래 주석 해제하고 위 import를 주석 처리하세요.
# import hashlib, hmac
# def hash_pw(pw: str, salt: bytes | None = None):
#     import os as _os
#     salt = salt or _os.urandom(16)
#     dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000)
#     return salt.hex() + ":" + dk.hex()
# def verify_pw(pw: str, stored: str):
#     salt_hex, dk_hex = stored.split(":")
#     salt = bytes.fromhex(salt_hex)
#     new_dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 100_000).hex()
#     return hmac.compare_digest(new_dk, dk_hex)

# ===== 경로/상수 =====
DB_PATH = "diary.db"
MEDIA_DIR = "media"
IMG_DIR = os.path.join(MEDIA_DIR, "images")
AUD_DIR = os.path.join(MEDIA_DIR, "audio")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(AUD_DIR, exist_ok=True)

APP_TITLE = "EMOJI_0 나의 일기장"
PALETTE = {
    "primary": "#FF7A9E",   # 코랄핑크
    "accent":  "#B39DDB",   # 라일락
    "mint":    "#6EC6C1",   # 청록
    "bg_soft": "#FFF0F4",   # 연핑크 배경
    "text":    "#2B2B2B",
}

# ===== DB =====
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            d TEXT,
            mood TEXT,
            mood_score INTEGER,
            tags TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER,
            kind TEXT,
            path TEXT,
            original_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(entry_id) REFERENCES entries(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    return conn

# ===== 사용자 =====
def create_user(conn, email, name, password_plain):
    c = conn.cursor()
    # passlib 사용
    pw_hash = bcrypt.hash(password_plain)
    # PBKDF2 대체 사용 시:
    # pw_hash = hash_pw(password_plain)
    c.execute("INSERT INTO users(email, name, password_hash) VALUES(?, ?, ?)",
              (email, name, pw_hash))
    conn.commit()
    return c.lastrowid

def get_user_by_email(conn, email):
    c = conn.cursor()
    c.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", (email,))
    return c.fetchone()

# ===== 일기 =====
def insert_entry(conn, user_id, d, mood, mood_score, tags, content):
    c = conn.cursor()
    c.execute("""
        INSERT INTO entries(user_id, d, mood, mood_score, tags, content, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, d, mood, mood_score, tags, content, datetime.utcnow().isoformat()))
    conn.commit()
    return c.lastrowid

def update_entry(conn, entry_id, user_id, d, mood, mood_score, tags, content):
    c = conn.cursor()
    c.execute("""
        UPDATE entries
        SET d=?, mood=?, mood_score=?, tags=?, content=?, updated_at=?
        WHERE id=? AND user_id=?
    """, (d, mood, mood_score, tags, content, datetime.utcnow().isoformat(), entry_id, user_id))
    conn.commit()

def delete_entry(conn, entry_id, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE id=? AND user_id=?", (entry_id, user_id))
    conn.commit()

def get_entries(conn, user_id, q=None, mood=None, tag=None):
    c = conn.cursor()
    base = "SELECT id, d, mood, mood_score, tags, content, created_at FROM entries WHERE user_id=?"
    params = [user_id]
    if q:
        base += " AND (content LIKE ? OR tags LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if mood:
        base += " AND mood = ?"
        params.append(mood)
    if tag:
        base += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    base += " ORDER BY d DESC, id DESC"
    c.execute(base, params)
    return c.fetchall()

# ===== 파일 =====
def insert_file(conn, entry_id, kind, path, original_name):
    c = conn.cursor()
    c.execute("INSERT INTO files(entry_id, kind, path, original_name) VALUES (?, ?, ?, ?)",
              (entry_id, kind, path, original_name))
    conn.commit()

def get_files(conn, entry_id, user_id):
    c = conn.cursor()
    c.execute("""
        SELECT f.kind, f.path, f.original_name
        FROM files f
        JOIN entries e ON e.id = f.entry_id
        WHERE f.entry_id=? AND e.user_id=?
        ORDER BY f.id ASC
    """, (entry_id, user_id))
    return c.fetchall()

def delete_files_of_entry(conn, entry_id, user_id):
    files = get_files(conn, entry_id, user_id)
    for _, path, _ in files:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    c = conn.cursor()
    c.execute("""
        DELETE FROM files
        WHERE entry_id IN (SELECT id FROM entries WHERE id=? AND user_id=?)
    """, (entry_id, user_id))
    conn.commit()

def save_uploaded_images(files):
    saved = []
    for f in files:
        ext = os.path.splitext(f.name)[1].lower() or ".jpg"
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = os.path.join(IMG_DIR, fname)
        image = Image.open(f).convert("RGB")
        image.save(fpath, quality=90)
        saved.append((fpath, f.name))
    return saved

def save_uploaded_audios(files):
    saved = []
    for f in files:
        ext = os.path.splitext(f.name)[1].lower() or ".mp3"
        fname = f"{uuid.uuid4().hex}{ext}"
        fpath = os.path.join(AUD_DIR, fname)
        with open(fpath, "wb") as out:
            out.write(f.read())
        saved.append((fpath, f.name))
    return saved

def get_entries_with_files(conn, user_id, mood=None, q=None, tag=None):
    rows = get_entries(conn, user_id, q=q, mood=mood, tag=tag)
    data = []
    c = conn.cursor()
    for r in rows:
        eid = r[0]
        c.execute("SELECT kind, path, original_name FROM files WHERE entry_id=? ORDER BY id ASC", (eid,))
        fs = c.fetchall()
        data.append((r, fs))
    return data

# ===== 스타일 =====
st.set_page_config(page_title=APP_TITLE, page_icon="EMOJI_1", layout="centered")
st.markdown(f"""
<style>
:root {{
  --primary: {PALETTE["primary"]};
  --accent:  {PALETTE["accent"]};
  --mint:    {PALETTE["mint"]};
  --bgsoft:  {PALETTE["bg_soft"]};
  --text:    {PALETTE["text"]};
}}
.stApp {{
  background: linear-gradient(180deg, #FFFFFF 0%, var(--bgsoft) 100%);
  color: var(--text);
}}
.stButton>button[kind="primary"] {{
  background-color: var(--primary);
  color: white;
  border: 0; border-radius: 10px;
}}
.emotion-badge {{
  display:inline-block; padding:4px 10px; border-radius:999px;
  background: var(--accent); color:#fff; font-weight:600; margin-right:6px;
}}
.chip {{
  display:inline-block; padding:2px 8px; border-radius:999px;
  background:#FFD1E0; margin-right:6px; color:#5A3C45;
}}
.card {{
  border-radius:14px; padding:12px; background:#FFFFFF;
  box-shadow:0 6px 20px rgba(0,0,0,0.06); margin-bottom:12px;
}}
</style>
""", unsafe_allow_html=True)

st.title(APP_TITLE)

# ===== 세션 =====
if "user" not in st.session_state:
    st.session_state.user = None
if "authed" not in st.session_state:
    st.session_state.authed = False
conn = init_db()

# ===== 인증 뷰 =====
def auth_view():
    tabs = st.tabs(["로그인", "회원가입"])

    with tabs[0]:
        st.subheader("로그인")
        email = st.text_input("이메일")
        password = st.text_input("비밀번호", type="password")
        col1, col2 = st.columns(2)
        if col1.button("로그인", type="primary", use_container_width=True):
            user = get_user_by_email(conn, email)
            ok = False
            if user:
                # passlib 사용
                try:
                    ok = bcrypt.verify(password, user[3])
                except Exception:
                    ok = False
                # PBKDF2 대체 사용 시:
                # ok = verify_pw(password, user[3])
            if ok:
                st.session_state.user = {"id": user[0], "email": user[1], "name": user[2]}
                st.session_state.authed = True
                st.success("환영합니다!")
                st.rerun()
            else:
                st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
        if col2.button("초기화", use_container_width=True):
            st.rerun()

    with tabs[1]:
        st.subheader("회원가입")
        with st.form("signup_form", clear_on_submit=False):
            email_s = st.text_input("이메일")
            name_s = st.text_input("이름(선택)")
            pw1 = st.text_input("비밀번호", type="password")
            pw2 = st.text_input("비밀번호 확인", type="password")
            ok_btn = st.form_submit_button("회원가입", type="primary")
            if ok_btn:
                if not email_s or not pw1:
                    st.warning("이메일과 비밀번호를 입력해 주세요.")
                elif pw1 != pw2:
                    st.warning("비밀번호가 서로 다릅니다.")
                else:
                    try:
                        create_user(conn, email_s, name_s, pw1)
                        st.success("회원가입이 완료되었습니다. 로그인해 주세요.")
                    except sqlite3.IntegrityError:
                        st.error("이미 존재하는 이메일입니다.")

# ===== 메인 뷰 =====
def main_view():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"안녕하세요, {user.get('name') or user['email']}님!")
        if st.button("로그아웃"):
            st.session_state.user = None
            st.session_state.authed = False
            st.rerun()
        st.markdown("---")
        st.caption("코랄/라일락/청록 톤으로 꾸몄어요. 라임색은 사용하지 않았습니다.")

    tab_write, tab_list, tab_stats, tab_backup = st.tabs(["작성하기", "목록/검색", "통계", "백업"])

    # 작성하기
    with tab_write:
        st.subheader("오늘의 일기 작성")
        c1, c2 = st.columns(2)
        d = c1.date_input("날짜", value=date.today())
        mood = c2.selectbox("감정", ["EMOJI_2 행복", "EMOJI_3 평온", "EMOJI_4 보통", "EMOJI_5 우울", "EMOJI_6 불안", "EMOJI_7 의욕"])
        mood_score = st.slider("감정 강도(선택)", 1, 5, 3)
        tags = st.text_input("태그 (쉼표로 구분)", placeholder="공부, 개발, 일상")
        content = st.text_area("내용", height=200, placeholder="오늘 있었던 일들을 적어보세요...")

        st.markdown("첨부 파일")
        img_files = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg","webp"], accept_multiple_files=True)
        aud_files = st.file_uploader("음성 업로드", type=["mp3","wav","m4a","ogg"], accept_multiple_files=True)

        if st.button("저장", type="primary", use_container_width=True):
            if content.strip() or img_files or aud_files:
                eid = insert_entry(conn, user["id"], d.isoformat(), mood, mood_score, tags, content)
                if img_files:
                    for fpath, oname in save_uploaded_images(img_files):
                        insert_file(conn, eid, "image", fpath, oname)
                if aud_files:
                    for fpath, oname in save_uploaded_audios(aud_files):
                        insert_file(conn, eid, "audio", fpath, oname)
                st.success("일기가 저장되었습니다!")
                st.rerun()
            else:
                st.warning("내용 또는 첨부 파일을 추가해 주세요.")

    # 목록/검색
    with tab_list:
        st.subheader("목록/검색")
        with st.expander("검색/필터", expanded=True):
            q = st.text_input("키워드 검색", placeholder="내용 또는 태그")
            c1, c2 = st.columns(2)
            mood_f = c1.selectbox("감정 필터", ["(전체)","EMOJI_8 행복","EMOJI_9 평온","EMOJI_10 보통","EMOJI_11 우울","EMOJI_12 불안","EMOJI_13 의욕"])
            tag_f = c2.text_input("태그 포함", placeholder="예: 개발")
            mood_val = None if mood_f == "(전체)" else mood_f

        items = get_entries_with_files(conn, user["id"], mood=mood_val, q=q, tag=tag_f if tag_f else None)

        if not items:
            st.info("일기가 없거나 조건에 맞는 결과가 없어요.")
        else:
            for (id_, d_, mood_, score_, tags_, content_, created_), files_ in items:
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write(f"{d_} · <span class='emotion-badge'>{mood_}</span> · 강도 {score_}/5", unsafe_allow_html=True)
                if tags_:
                    for t in [t.strip() for t in tags_.split(",") if t.strip()]:
                        st.markdown(f"<span class='chip'>#{t}</span>", unsafe_allow_html=True)
                if content_:
                    st.write(content_)

                img_cols = st.columns(3)
                img_i = 0
                for kind, path, oname in files_:
                    if kind == "image":
                        if img_i < 3:
                            with img_cols[img_i % 3]:
                                st.image(path, use_column_width=True)
                            img_i += 1
                    elif kind == "audio":
                        st.audio(path)

                e1, e2 = st.columns([1,1])
                if e1.button("수정", key=f"edit_{id_}"):
                    st.session_state[f"editing_{id_}"] = True
                if e2.button("삭제", key=f"del_{id_}"):
                    delete_files_of_entry(conn, id_, user["id"])
                    delete_entry(conn, id_, user["id"])
                    st.success("삭제되었습니다.")
                    st.rerun()

                if st.session_state.get(f"editing_{id_}", False):
                    st.info("아래에서 내용을 수정하세요.")
                    ed_d = st.date_input("날짜", value=date.fromisoformat(d_), key=f"ed_d_{id_}")
                    ed_m = st.selectbox("감정", ["EMOJI_14 행복","EMOJI_15 평온","EMOJI_16 보통","EMOJI_17 우울","EMOJI_18 불안","EMOJI_19 의욕"], index=0, key=f"ed_m_{id_}")
                    ed_s = st.slider("감정 강도", 1, 5, score_, key=f"ed_s_{id_}")
                    ed_t = st.text_input("태그", value=tags_ or "", key=f"ed_t_{id_}")
                    ed_c = st.text_area("내용", value=content_ or "", key=f"ed_c_{id_}")
                    s1, s2 = st.columns(2)
                    if s1.button("저장", key=f"save_{id_}"):
                        update_entry(conn, id_, user["id"], ed_d.isoformat(), ed_m, ed_s, ed_t, ed_c)
                        st.session_state[f"editing_{id_}"] = False
                        st.success("수정되었습니다.")
                        st.rerun()
                    if s2.button("취소", key=f"cancel_{id_}"):
                        st.session_state[f"editing_{id_}"] = False
                        st.info("취소했습니다.")
                st.markdown('</div>', unsafe_allow_html=True)

    # 통계
    with tab_stats:
        st.subheader("감정 통계")
        df = pd.read_sql_query("SELECT d, mood, mood_score FROM entries WHERE user_id=?", conn, params=(user["id"],))
        if df.empty:
            st.info("통계를 보여줄 데이터가 아직 없어요.")
        else:
            mood_counts = df["mood"].value_counts().reset_index()
            mood_counts.columns = ["감정", "횟수"]
            chart = alt.Chart(mood_counts).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("감정:N", sort="-y", title="감정"),
                y=alt.Y("횟수:Q", title="작성 수"),
                color=alt.Color("감정:N", scale=alt.Scale(range=[PALETTE["primary"], PALETTE["accent"], PALETTE["mint"], "#FF9EBB", "#C6B6F3", "#88D5D1"]))
            )
            st.altair_chart(chart, use_container_width=True)

            df["d"] = pd.to_datetime(df["d"])
            by_month = df.groupby(df["d"].dt.to_period("M")).size().reset_index(name="count")
            by_month["월"] = by_month["d"].astype(str)
            line = alt.Chart(by_month).mark_line(point=True, strokeWidth=3, color=PALETTE["primary"]).encode(
                x=alt.X("월:N", title="월"),
                y=alt.Y("count:Q", title="작성 수")
            )
            st.altair_chart(line, use_container_width=True)

    # 백업
    with tab_backup:
        st.subheader("백업")
        st.caption("데이터베이스 파일은 로컬에 저장됩니다. 아래 버튼으로 DB를 내려받을 수 있어요.")
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                st.download_button("DB 백업 다운로드(diary_backup.db)", data=f, file_name="diary_backup.db", mime="application/octet-stream")
        else:
            st.info("DB 파일이 아직 생성되지 않았습니다. 먼저 일기를 한 번 저장해 보세요.")

# ===== 라우팅 =====
if not st.session_state.authed or not st.session_state.user:
    auth_view()
else:
    main_view()
