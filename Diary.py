import streamlit as st
import sqlite3
import os
import uuid
from datetime import date, datetime
from PIL import Image
import pandas as pd
import altair as alt
from passlib.hash import bcrypt

# ================== 공통 상수/경로 ==================
DB_PATH = "diary.db"
MEDIA_DIR = "media"
IMG_DIR = os.path.join(MEDIA_DIR, "images")
AUD_DIR = os.path.join(MEDIA_DIR, "audio")
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(AUD_DIR, exist_ok=True)

APP_TITLE = "EMOJI_0 나의 일기장"

# 기본 팔레트(라임색 제외)
BASE_PALETTE = {
    "primary": "#FF7A9E",   # 코랄핑크
    "accent":  "#B39DDB",   # 라일락
    "mint":    "#6EC6C1",   # 청록
    "bg_soft": "#FFF0F4",   # 연핑크 배경(라이트)
    "bg_dark": "#0F1115",   # 다크 배경
    "card_dark":"#161A22",
    "text":    "#2B2B2B",
    "text_dark":"#E9E9E9"
}

# 감정 라벨(라벨은 이모지 포함, 저장은 key로)
EMOTIONS = [
    {"key": "happy",   "label": "EMOJI_1 행복"},
    {"key": "calm",    "label": "EMOJI_2 평온"},
    {"key": "neutral", "label": "EMOJI_3 보통"},
    {"key": "sad",     "label": "EMOJI_4 우울"},
    {"key": "anxious", "label": "EMOJI_5 불안"},
    {"key": "drive",   "label": "EMOJI_6 의욕"},
]
EMO_KEY_TO_LABEL = {e["key"]: e["label"] for e in EMOTIONS}
EMO_LABELS = [e["label"] for e in EMOTIONS]
EMO_KEYS = [e["key"] for e in EMOTIONS]

# ================== DB ==================
def make_conn(db_path: str):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.text_factory = str
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = make_conn(DB_PATH)
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
    # 사용자 테마 설정 저장 테이블
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_settings(
            user_id INTEGER PRIMARY KEY,
            theme TEXT,               -- 'light' or 'dark'
            primary TEXT,             -- 포인트 컬러
            bg_style TEXT,            -- 'pastel' or 'matte'
            font_scale TEXT,          -- 'sm'/'md'/'lg'
            updated_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    return conn

# 사용자
def create_user(conn, email, name, password_plain):
    c = conn.cursor()
    pw_hash = bcrypt.hash(password_plain)
    c.execute("INSERT INTO users(email, name, password_hash) VALUES(?, ?, ?)",
              (email, name, pw_hash))
    conn.commit()
    # 기본 테마 설정도 같이 생성
    upsert_user_settings(conn, c.lastrowid, theme="light", primary=BASE_PALETTE["primary"],
                         bg_style="pastel", font_scale="md")
    return c.lastrowid

def get_user_by_email(conn, email):
    c = conn.cursor()
    c.execute("SELECT id, email, name, password_hash FROM users WHERE email = ?", (email,))
    return c.fetchone()

# 일기
def insert_entry(conn, user_id, d, mood_key, mood_score, tags, content):
    c = conn.cursor()
    c.execute("""
        INSERT INTO entries(user_id, d, mood, mood_score, tags, content, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, d, mood_key, mood_score, tags, content, datetime.utcnow().isoformat()))
    conn.commit()
    return c.lastrowid

def update_entry(conn, entry_id, user_id, d, mood_key, mood_score, tags, content):
    c = conn.cursor()
    c.execute("""
        UPDATE entries
        SET d=?, mood=?, mood_score=?, tags=?, content=?, updated_at=?
        WHERE id=? AND user_id=?
    """, (d, mood_key, mood_score, tags, content, datetime.utcnow().isoformat(), entry_id, user_id))
    conn.commit()

def delete_entry(conn, entry_id, user_id):
    c = conn.cursor()
    c.execute("DELETE FROM entries WHERE id=? AND user_id=?", (entry_id, user_id))
    conn.commit()

def get_entries(conn, user_id, q=None, mood_key=None, tag=None):
    c = conn.cursor()
    base = "SELECT id, d, mood, mood_score, tags, content, created_at FROM entries WHERE user_id=?"
    params = [user_id]
    if q:
        base += " AND (content LIKE ? OR tags LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if mood_key:
        base += " AND mood = ?"
        params.append(mood_key)
    if tag:
        base += " AND tags LIKE ?"
        params.append(f"%{tag}%")
    base += " ORDER BY d DESC, id DESC"
    c.execute(base, params)
    return c.fetchall()

# 파일
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

def get_entries_with_files(conn, user_id, mood_key=None, q=None, tag=None):
    rows = get_entries(conn, user_id, q=q, mood_key=mood_key, tag=tag)
    data = []
    c = conn.cursor()
    for r in rows:
        eid = r[0]
        c.execute("SELECT kind, path, original_name FROM files WHERE entry_id=? ORDER BY id ASC", (eid,))
        fs = c.fetchall()
        data.append((r, fs))
    return data

# ================== 사용자 설정(테마) ==================
def get_user_settings(conn, user_id):
    c = conn.cursor()
    c.execute("""
        SELECT theme, primary, bg_style, font_scale
        FROM user_settings WHERE user_id=?
    """, (user_id,))
    row = c.fetchone()
    if not row:
        return {"theme":"light", "primary":BASE_PALETTE["primary"], "bg_style":"pastel", "font_scale":"md"}
    return {"theme":row[0], "primary":row[1], "bg_style":row[2], "font_scale":row[3]}

def upsert_user_settings(conn, user_id, theme, primary, bg_style, font_scale):
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_settings(user_id, theme, primary, bg_style, font_scale, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            theme=excluded.theme,
            primary=excluded.primary,
            bg_style=excluded.bg_style,
            font_scale=excluded.font_scale,
            updated_at=excluded.updated_at
    """, (user_id, theme, primary, bg_style, font_scale, datetime.utcnow().isoformat()))
    conn.commit()

# ================== 유틸 ==================
def label_to_key(label: str) -> str:
    for e in EMOTIONS:
        if e["label"] == label:
            return e["key"]
    if label in EMO_KEYS:
        return label
    return "neutral"

def key_to_label(key: str) -> str:
    return EMO_KEY_TO_LABEL.get(key, "EMOJI_7 보통")

def build_css(theme: str, primary: str, bg_style: str, font_scale: str):
    # 글꼴 크기 스케일
    font_map = {"sm":"14px", "md":"16px", "lg":"18px"}
    base_font = font_map.get(font_scale, "16px")

    if theme == "dark":
        app_bg = BASE_PALETTE["bg_dark"]
        text_c = BASE_PALETTE["text_dark"]
        card_bg = BASE_PALETTE["card_dark"]
        chip_bg = "#2A2F3A"
        chip_fg = "#E9E2E6"
        badge_bg = primary
        gradient = f"linear-gradient(180deg, {app_bg} 0%, {app_bg} 100%)"
    else:
        app_bg = "#FFFFFF" if bg_style == "matte" else f"linear-gradient(180deg, #FFFFFF 0%, {BASE_PALETTE['bg_soft']} 100%)"
        text_c = BASE_PALETTE["text"]
        card_bg = "#FFFFFF"
        chip_bg = "#FFD1E0"          # 라임 배제, 파스텔 핑크
        chip_fg = "#5A3C45"
        badge_bg = BASE_PALETTE["accent"]
        gradient = app_bg

    css = f"""
    <style>
    html, body, .stApp {{
        color: {text_c};
        font-size: {base_font};
        background: {gradient};
    }}
    .stButton>button[kind="primary"] {{
        background-color: {primary};
        color: white;
        border: 0; border-radius: 10px;
    }}
    .emotion-badge {{
        display:inline-block; padding:4px 10px; border-radius:999px;
        background: {badge_bg}; color:#fff; font-weight:600; margin-right:6px;
    }}
    .chip {{
        display:inline-block; padding:2px 8px; border-radius:999px;
        background:{chip_bg}; margin-right:6px; color:{chip_fg};
    }}
    .card {{
        border-radius:14px; padding:12px; background:{card_bg};
        box-shadow:0 6px 20px rgba(0,0,0,0.06); margin-bottom:12px;
        border: { '1px solid #2A2F3A' if theme=='dark' else 'none' };
    }}
    </style>
    """
    return css

# ================== 앱 시작/세션 ==================
st.set_page_config(page_title=APP_TITLE, page_icon="EMOJI_8", layout="centered")
st.title(APP_TITLE)

if "user" not in st.session_state:
    st.session_state.user = None
if "authed" not in st.session_state:
    st.session_state.authed = False

conn = init_db()

# ================== 인증 뷰 ==================
def auth_view():
    tabs = st.tabs(["로그인", "회원가입"])

    with tabs[0]:
        st.subheader("로그인")
        email = st.text_input("이메일", key="login_email")
        password = st.text_input("비밀번호", type="password", key="login_pw")
        col1, col2 = st.columns(2)
        if col1.button("로그인", type="primary", use_container_width=True, key="login_btn"):
            user = get_user_by_email(conn, (email or "").strip())
            ok = False
            if user:
                try:
                    ok = bcrypt.verify(password, user[3])
                except Exception:
                    ok = False
            if ok:
                st.session_state.user = {"id": user[0], "email": user[1], "name": user[2]}
                st.session_state.authed = True
                st.success("환영합니다!")
                st.rerun()
            else:
                st.error("이메일 또는 비밀번호가 올바르지 않습니다.")
        if col2.button("초기화", use_container_width=True, key="login_reset"):
            st.rerun()

    with tabs[1]:
        st.subheader("회원가입")
        with st.container():
            with st.form(key="signup_form_v2", clear_on_submit=False):
                colA, colB = st.columns(2)
                email_s = colA.text_input("이메일", key="email_s")
                name_s  = colB.text_input("이름(선택)", key="name_s")
                pw1 = st.text_input("비밀번호", type="password", key="pw1")
                pw2 = st.text_input("비밀번호 확인", type="password", key="pw2")
                agreed = st.checkbox("이용 약관에 동의합니다", key="tos_agree")
                submit_signup = st.form_submit_button("회원가입", type="primary")
            if submit_signup:
                if not email_s or not pw1:
                    st.warning("이메일과 비밀번호를 입력해 주세요.")
                elif pw1 != pw2:
                    st.warning("비밀번호가 서로 다릅니다.")
                elif not agreed:
                    st.warning("약관에 동의해 주세요.")
                else:
                    try:
                        create_user(conn, email_s.strip(), (name_s or "").strip(), pw1)
                        st.success("회원가입이 완료되었습니다. 상단의 '로그인' 탭에서 로그인해 주세요.")
                        for k in ["email_s", "name_s", "pw1", "pw2", "tos_agree"]:
                            if k in st.session_state:
                                del st.session_state[k]
                    except sqlite3.IntegrityError:
                        st.error("이미 존재하는 이메일입니다.")

# ================== 테마 설정 사이드바 ==================
def theme_sidebar(user_id):
    settings = get_user_settings(conn, user_id)

    with st.sidebar:
        st.markdown("설정")
        # 테마 토글(라이트/다크)
        theme = st.radio("테마", options=["light", "dark"],
                         index=0 if settings["theme"]=="light" else 1, horizontal=True, key="theme_radio")

        # 포인트 색(라임 제외)
        color_options = {
            "코랄": "#FF7A9E",
            "라일락": "#B39DDB",
            "청록": "#6EC6C1",
            "살몬": "#FF9EBB",
            "라일락-라이트": "#C6B6F3",
            "민트-라이트": "#88D5D1"
        }
        default_idx = list(color_options.values()).index(settings["primary"]) if settings["primary"] in color_options.values() else 0
        color_label = st.selectbox("포인트 색상", list(color_options.keys()), index=default_idx, key="primary_color_sel")
        primary = color_options[color_label]

        # 배경 톤
        bg_style = st.radio("배경 톤", options=["pastel", "matte"],
                            index=0 if settings["bg_style"]=="pastel" else 1, horizontal=True, key="bg_style_radio")

        # 글꼴 크기
        font_names = {"작게":"sm", "보통":"md", "크게":"lg"}
        inv_font = {v:k for k,v in font_names.items()}
        font_sel = st.selectbox("글꼴 크기", list(font_names.keys()),
                                index=["sm","md","lg"].index(settings["font_scale"]) if settings["font_scale"] in ["sm","md","lg"] else 1,
                                key="font_scale_sel")

        colA, colB = st.columns(2)
        if colA.button("저장", type="primary", use_container_width=True, key="save_theme_btn"):
            upsert_user_settings(conn, user_id, theme=theme, primary=primary,
                                 bg_style=bg_style, font_scale=font_names[font_sel])
            st.success("테마가 저장되고 적용되었습니다.")
            st.rerun()
        if colB.button("리셋", use_container_width=True, key="reset_theme_btn"):
            upsert_user_settings(conn, user_id, theme="light", primary=BASE_PALETTE["primary"],
                                 bg_style="pastel", font_scale="md")
            st.info("기본 테마로 돌아갔습니다.")
            st.rerun()

        st.markdown("---")

# ================== 메인 뷰 ==================
def main_view():
    user = st.session_state.user

    # 사이드바: 로그아웃 + 테마 설정
    with st.sidebar:
        st.markdown(f"안녕하세요, {user.get('name') or user['email']}님!")
        if st.button("로그아웃", key="logout_btn"):
            st.session_state.user = None
            st.session_state.authed = False
            st.rerun()
        st.markdown("---")

    # 테마 설정 UI
    theme_sidebar(user["id"])

    # 현재 사용자 테마 로드 후 CSS 적용
    s = get_user_settings(conn, user["id"])
    st.markdown(build_css(theme=s["theme"], primary=s["primary"],
                          bg_style=s["bg_style"], font_scale=s["font_scale"]),
                unsafe_allow_html=True)

    tab_write, tab_list, tab_stats, tab_backup = st.tabs(["작성하기", "목록/검색", "통계", "백업"])

    # 작성하기
    with tab_write:
        st.subheader("오늘의 일기 작성")
        c1, c2 = st.columns(2)
        d = c1.date_input("날짜", value=date.today(), key="write_date")
        mood_label = c2.selectbox("감정", EMO_LABELS, key="write_mood_label")
        mood_key = label_to_key(mood_label)
        mood_score = st.slider("감정 강도(선택)", 1, 5, 3, key="write_score")
        tags = st.text_input("태그 (쉼표로 구분)", placeholder="공부, 개발, 일상", key="write_tags")
        content = st.text_area("내용", height=200, placeholder="오늘 있었던 일들을 적어보세요...", key="write_content")

        st.markdown("첨부 파일")
        img_files = st.file_uploader("이미지 업로드", type=["png","jpg","jpeg","webp"], accept_multiple_files=True, key="write_imgs")
        aud_files = st.file_uploader("음성 업로드", type=["mp3","wav","m4a","ogg"], accept_multiple_files=True, key="write_auds")

        if st.button("저장", type="primary", use_container_width=True, key="save_entry_btn"):
            if (content and content.strip()) or img_files or aud_files:
                eid = insert_entry(conn, user["id"], d.isoformat(), mood_key, mood_score, tags, content)
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
            q = st.text_input("키워드 검색", placeholder="내용 또는 태그", key="filter_q")
            c1, c2 = st.columns(2)
            mood_filter_label = c1.selectbox("감정 필터", ["(전체)"] + EMO_LABELS, key="filter_mood_label")
            tag_f = c2.text_input("태그 포함", placeholder="예: 개발", key="filter_tag")
            mood_val = None if mood_filter_label == "(전체)" else label_to_key(mood_filter_label)

        items = get_entries_with_files(conn, user["id"], mood_key=mood_val, q=q, tag=tag_f if tag_f else None)

        if not items:
            st.info("일기가 없거나 조건에 맞는 결과가 없어요.")
        else:
            for (id_, d_, mood_key_saved, score_, tags_, content_, created_), files_ in items:
                mood_label_saved = key_to_label(mood_key_saved)
                st.markdown('<div class="card">', unsafe_allow_html=True)
                st.write(f"{d_} · <span class='emotion-badge'>{mood_label_saved}</span> · 강도 {score_}/5", unsafe_allow_html=True)
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
                    ed_label = st.selectbox("감정", EMO_LABELS,
                        index=max(0, EMO_LABELS.index(mood_label_saved)) if mood_label_saved in EMO_LABELS else 2,
                        key=f"ed_m_{id_}")
                    ed_key = label_to_key(ed_label)
                    ed_s = st.slider("감정 강도", 1, 5, score_, key=f"ed_s_{id_}")
                    ed_t = st.text_input("태그", value=tags_ or "", key=f"ed_t_{id_}")
                    ed_c = st.text_area("내용", value=content_ or "", key=f"ed_c_{id_}")
                    s1, s2 = st.columns(2)
                    if s1.button("저장", key=f"save_{id_}"):
                        update_entry(conn, id_, user["id"], ed_d.isoformat(), ed_key, ed_s, ed_t, ed_c)
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
            df["mood_label"] = df["mood"].map(key_to_label)
            mood_counts = df["mood_label"].value_counts().reset_index()
            mood_counts.columns = ["감정", "횟수"]
            chart = alt.Chart(mood_counts).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("감정:N", sort="-y", title="감정"),
                y=alt.Y("횟수:Q", title="작성 수"),
                color=alt.Color("감정:N", scale=alt.Scale(range=[BASE_PALETTE["primary"], BASE_PALETTE["accent"], BASE_PALETTE["mint"], "#FF9EBB", "#C6B6F3", "#88D5D1"]))
            )
            st.altair_chart(chart, use_container_width=True)

            df["d"] = pd.to_datetime(df["d"])
            by_month = df.groupby(df["d"].dt.to_period("M")).size().reset_index(name="count")
            by_month["월"] = by_month["d"].astype(str)
            line = alt.Chart(by_month).mark_line(point=True, strokeWidth=3, color=s["primary"]).encode(
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
                st.download_button("DB 백업 다운로드(diary_backup.db)", data=f,
                                   file_name="diary_backup.db", mime="application/octet-stream")
        else:
            st.info("DB 파일이 아직 생성되지 않았습니다. 먼저 일기를 한 번 저장해 보세요.")

# ================== 라우팅 ==================
if not st.session_state.authed or not st.session_state.user:
    auth_view()
else:
    main_view()
