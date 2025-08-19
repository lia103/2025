import time
import datetime as dt
import uuid
import sqlite3
import hashlib
import hmac  # ← 안전 비교용
import os
from contextlib import closing

import pandas as pd
import streamlit as st

# ===============================
# 기본 설정
# ===============================
st.set_page_config(page_title="수능 러닝 메이트+", page_icon="EMOJI_0", layout="wide")

APP_DB = "study_mate_subjectless.db"
TODAY = dt.date.today().isoformat()

# ===============================
# 보안 유틸: 비밀번호 해시/검증
# ===============================
def hash_password(password: str, salt: bytes = None) -> tuple[str, bytes]:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex(), salt

def verify_password(password: str, hashed_hex: str, salt: bytes) -> bool:
    # sqlite가 memoryview로 반환하는 경우를 대비
    if isinstance(salt, memoryview):
        salt = salt.tobytes()
    dk_check, _ = hash_password(password, salt)
    return hmac.compare_digest(dk_check, hashed_hex)

# ===============================
# rerun 호환 유틸
# ===============================
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ===============================
# DB 초기화
# ===============================
def init_db():
    with closing(sqlite3.connect(APP_DB)) as conn:
        c = conn.cursor()
        # 사용자 계정
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            pw_hash TEXT,
            pw_salt BLOB,
            created_at TEXT
        );
        """)
        # 하루 상태(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS daily(
            date TEXT,
            user_id TEXT,
            goal_min INTEGER,
            coins INTEGER,
            streak INTEGER,
            theme TEXT,
            sound TEXT,
            mascot TEXT,
            PRIMARY KEY(date, user_id)
        );
        """)
        # 공부 세션 로그(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            subject TEXT,
            duration_min INTEGER,
            distractions INTEGER,
            mood TEXT,
            energy INTEGER,
            difficulty INTEGER
        );
        """)
        # 보유 아이템(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS inventory(
            item_id TEXT PRIMARY KEY,
            user_id TEXT,
            item_type TEXT,
            name TEXT
        );
        """)
        # 보상/구매 로그(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS rewards(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            type TEXT,
            name TEXT,
            coins_change INTEGER
        );
        """)
        # 길드(샘플) + 내 길드(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS guild(
            id TEXT PRIMARY KEY,
            name TEXT
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS my_guild(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT
        );
        """)
        # 사용자 정의 과목(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS subjects(
            name TEXT,
            user_id TEXT,
            PRIMARY KEY (name, user_id)
        );
        """)
        # 투두리스트(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS todos(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            subject TEXT,
            due_date TEXT,
            estimated_min INTEGER,
            priority INTEGER,
            is_done INTEGER,
            done_at TEXT,
            reward_coins INTEGER
        );
        """)
        conn.commit()

def get_conn():
    return sqlite3.connect(APP_DB)

init_db()

# ===============================
# 세션 상태
# ===============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "### 안내
사용자님, 앞서 발생한 AttributeError의 원인(verify_password에서 hashlib.compare_digest 사용)을 반영해 hmac.compare_digest로 수정했고, 위젯 중복 오류 방지를 위한 고유 key도 전면 적용했습니다. 회원가입/로그인 + 상단 내비 + 투두리스트(완료 시 코인 지급) + 타이머 + 상점(이미 구매함 배지)까지 모두 포함한 “붙여넣기용 완성본”입니다. 그대로 교체해 실행하시면 됩니다.

```python
import time
import datetime as dt
import uuid
import sqlite3
import hashlib
import hmac  # 중요: 안전 비교는 hmac.compare_digest 사용
import os
from contextlib import closing

import pandas as pd
import streamlit as st

# ===============================
# 기본 설정
# ===============================
st.set_page_config(page_title="수능 러닝 메이트+", page_icon="EMOJI_0", layout="wide")

APP_DB = "study_mate_subjectless.db"
TODAY = dt.date.today().isoformat()

# ===============================
# 비밀번호 해시/검증 유틸
# ===============================
def hash_password(password: str, salt: bytes = None) -> tuple[str, bytes]:
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return dk.hex(), salt

def verify_password(password: str, hashed_hex: str, salt: bytes) -> bool:
    # sqlite에서 BLOB 꺼낼 때 memoryview로 나올 수 있어 방어적으로 bytes 캐스팅
    if isinstance(salt, memoryview):
        salt = salt.tobytes()
    dk_check, _ = hash_password(password, salt)
    return hmac.compare_digest(dk_check, hashed_hex)

# ===============================
# rerun 유틸
# ===============================
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ===============================
# DB 초기화
# ===============================
def init_db():
    with closing(sqlite3.connect(APP_DB)) as conn:
        c = conn.cursor()
        # 사용자 계정
        c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            pw_hash TEXT,
            pw_salt BLOB,
            created_at TEXT
        );
        """)
        # 하루 상태(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS daily(
            date TEXT,
            user_id TEXT,
            goal_min INTEGER,
            coins INTEGER,
            streak INTEGER,
            theme TEXT,
            sound TEXT,
            mascot TEXT,
            PRIMARY KEY(date, user_id)
        );
        """)
        # 공부 세션 로그(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            subject TEXT,
            duration_min INTEGER,
            distractions INTEGER,
            mood TEXT,
            energy INTEGER,
            difficulty INTEGER
        );
        """)
        # 보유 아이템(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS inventory(
            item_id TEXT PRIMARY KEY,
            user_id TEXT,
            item_type TEXT,
            name TEXT
        );
        """)
        # 보상/구매 로그(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS rewards(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            type TEXT,
            name TEXT,
            coins_change INTEGER
        );
        """)
        # 길드(샘플) + 내 길드(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS guild(
            id TEXT PRIMARY KEY,
            name TEXT
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS my_guild(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT
        );
        """)
        # 사용자 정의 과목(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS subjects(
            name TEXT,
            user_id TEXT,
            PRIMARY KEY (name, user_id)
        );
        """)
        # 투두리스트(유저별)
        c.execute("""
        CREATE TABLE IF NOT EXISTS todos(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            subject TEXT,
            due_date TEXT,
            estimated_min INTEGER,
            priority INTEGER,
            is_done INTEGER,
            done_at TEXT,
            reward_coins INTEGER
        );
        """)
        conn.commit()

def get_conn():
    return sqlite3.connect(APP_DB)

init_db()

# ===============================
# 세션 상태
# ===============================
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "end_time" not in st.session_state:
    st.session_state.end_time = None
if "preset" not in st.session_state:
    st.session_state.preset = 25
if "subject" not in st.session_state:
    st.session_state.subject = None
if "distractions" not in st.session_state:
    st.session_state.distractions = 0

TAB_AUTH = "로그인"
TAB_HOME = "홈"
TAB_TODO = "투두리스트"
TAB_TIMER = "타이머"
TAB_STATS = "통계"
TAB_GUILD = "길드"
TAB_SHOP = "상점"

if "active_tab" not in st.session_state:
    st.session_state.active_tab = TAB_AUTH

# ===============================
# 인증/계정
# ===============================
def create_user(email: str, username: str, password: str) -> tuple[bool, str]:
    email = (email or "").strip().lower()
    username = (username or "").strip()
    if not email or not username or not password:
        return False, "이메일, 사용자명, 비밀번호를 모두 입력해 주세요."
    pw_hex, salt = hash_password(password)
    uid = str(uuid.uuid4())
    try:
        with closing(get_conn()) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO users(id, email, username, pw_hash, pw_salt, created_at) VALUES(?,?,?,?,?,?)",
                      (uid, email, username, pw_hex, salt, dt.datetime.now().isoformat()))
            conn.commit()
        return True, uid
    except sqlite3.IntegrityError:
        return False, "이미 사용 중인 이메일 또는 사용자명입니다."

def authenticate(login_id: str, password: str) -> tuple[bool, tuple[str, str] | None, str]:
    q = "SELECT id, email, username, pw_hash, pw_salt FROM users WHERE email=? OR username=?"
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute(q, (login_id.strip().lower(), login_id.strip()))
        row = c.fetchone()
        if not row:
            return False, None, "계정을 찾을 수 없습니다."
        uid, email, username, pw_hex, salt = row
        if verify_password(password, pw_hex, salt):
            return True, (uid, username), ""
        else:
            return False, None, "비밀번호가 일치하지 않습니다."

def require_login():
    if not st.session_state.user_id:
        st.warning("이 기능은 로그인 후 이용하실 수 있어요.")
        st.session_state.active_tab = TAB_AUTH
        st.stop()

# ===============================
# Daily(유저별)
# ===============================
def ensure_today():
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT date FROM daily WHERE date=? AND user_id=?", (TODAY, uid))
        row = c.fetchone()
        if not row:
            y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
            c.execute("SELECT streak FROM daily WHERE date=? AND user_id=?", (y, uid))
            prev = c.fetchone()
            streak = (prev[0] + 1) if prev else 1
            c.execute("""INSERT INTO daily(date, user_id, goal_min, coins, streak, theme, sound, mascot)
                         VALUES(?,?,?,?,?,?,?,?)""",
                      (TODAY, uid, 120, 0, streak, "핑크", "벨", "여우"))
            conn.commit()

def get_daily():
    ensure_today()
    uid = st.session_state.user_id
    if not uid:
        return dict(date=TODAY, goal_min=120, coins=0, streak=0, theme="핑크", sound="벨", mascot="여우")
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM daily WHERE date=? AND user_id=?", conn, params=(TODAY, uid))
    if df.empty:
        return dict(date=TODAY, goal_min=120, coins=0, streak=0, theme="핑크", sound="벨", mascot="여우")
    r = df.iloc[0]
    return dict(
        date=r["date"],
        goal_min=int(r["goal_min"]),
        coins=int(r["coins"]),
        streak=int(r["streak"]),
        theme=r["theme"],
        sound=r["sound"],
        mascot=r["mascot"]
    )

def update_daily(goal=None, coins_delta=0, theme=None, sound=None, mascot=None, overwrite_streak=None):
    uid = st.session_state.user_id
    if not uid:
        return
    ensure_today()
    d = get_daily()
    goal_min = goal if goal is not None else d["goal_min"]
    coins = d["coins"] + coins_delta
    streak = overwrite_streak if overwrite_streak is not None else d["streak"]
    theme = theme if theme is not None else d["theme"]
    sound = sound if sound is not None else d["sound"]
    mascot = mascot if mascot is not None else d["mascot"]
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""REPLACE INTO daily(date, user_id, goal_min, coins, streak, theme, sound, mascot)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (TODAY, uid, goal_min, coins, streak, theme, sound, mascot))
        conn.commit()

# ===============================
# 세션/보상(유저별)
# ===============================
def add_session(subject, duration_min, distractions, mood, energy, difficulty):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO sessions(id, user_id, date, subject, duration_min, distractions, mood, energy, difficulty)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (str(uuid.uuid4()), uid, TODAY, subject, duration_min, distractions, mood, energy, difficulty))
        conn.commit()

def add_reward(rtype, name, coins_change):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO rewards(id, user_id, date, type, name, coins_change)
                     VALUES(?,?,?,?,?,?)""",
                  (str(uuid.uuid4()), uid, TODAY, rtype, name, coins_change))
        conn.commit()

def grant_coins(base=10, bonus=0, reason="세션 완료"):
    update_daily(coins_delta=(base+bonus))
    add_reward("coin", reason, base+bonus)

def get_today_summary():
    uid = st.session_state.user_id
    if not uid:
        return 0, pd.DataFrame()
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM sessions WHERE date=? AND user_id=?", conn, params=(TODAY, uid))
    total = int(df["duration_min"].sum()) if not df.empty else 0
    return total, df

def get_weekly():
    uid = st.session_state.user_id
    if not uid:
        return pd.DataFrame()
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("""
            SELECT date, SUM(duration_min) AS total_min
            FROM sessions
            WHERE user_id=?
            GROUP BY date
            ORDER BY date ASC
        """, conn, params=(uid,))
    return df.tail(7) if not df.empty else df

# ===============================
# 과목(유저별)
# ===============================
def get_subjects() -> list:
    uid = st.session_state.user_id
    if not uid:
        return []
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT name FROM subjects WHERE user_id=? ORDER BY name ASC", conn, params=(uid,))
    return df["name"].tolist() if not df.empty else []

def add_subject(name: str) -> bool:
    uid = st.session_state.user_id
    if not uid:
        return False
    name = (name or "").strip()
    if not name:
        return False
    with closing(get_conn()) as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO subjects(name, user_id) VALUES(?,?)", (name, uid))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def remove_subject(name: str) -> bool:
    uid = st.session_state.user_id
    if not uid:
        return False
    name = (name or "").strip()
    if not name:
        return False
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM subjects WHERE name=? AND user_id=?", (name, uid))
        conn.commit()
    return True

# ===============================
# 상점/테마
# ===============================
THEMES = {
    "핑크":   {"PRIMARY":"#F5A6C6", "SECONDARY":"#B7A8F5", "ACCENT":"#8DB7F5", "DARK":"#1E2A44"},
    "라일락": {"PRIMARY":"#C8B6FF", "SECONDARY":"#E7C6FF", "ACCENT":"#B8C0FF", "DARK":"#1E2A44"},
    "하늘":   {"PRIMARY":"#9CCCFB", "SECONDARY":"#CFE8FF", "ACCENT":"#86B6F2", "DARK":"#18324B"},
    "네이비": {"PRIMARY":"#203A74", "SECONDARY":"#2F4A8A", "ACCENT":"#7AA2FF", "DARK":"#101A2E"},
    "코랄":   {"PRIMARY":"#FF8A80", "SECONDARY":"#FFD3C9", "ACCENT":"#FFA8A0", "DARK":"#2B1E1E"},
}
SHOP_ITEMS = [
    {"type":"theme", "name":"핑크", "price":50},
    {"type":"theme", "name":"라일락", "price":50},
    {"type":"theme", "name":"하늘", "price":50},
    {"type":"theme", "name":"네이비", "price":50},
    {"type":"theme", "name":"코랄", "price":50},
    {"type":"sound", "name":"벨", "price":30},
    {"type":"sound", "name":"우드블럭", "price":30},
    {"type":"sound", "name":"빗소리", "price":30},
    {"type":"mascot", "name":"여우", "price":40},
    {"type":"mascot", "name":"곰", "price":40},
    {"type":"mascot", "name":"올빼미", "price":40},
]

def has_item(item_type, name):
    uid = st.session_state.user_id
    if not uid:
        return False
    with closing(get_conn()) as conn:
        df = pd.read_sql_query(
            "SELECT 1 FROM inventory WHERE user_id=? AND item_type=? AND name=?",
            conn, params=(uid, item_type, name)
        )
    return not df.empty

def add_item(item_type, name):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR IGNORE INTO inventory(item_id, user_id, item_type, name)
                     VALUES(?,?,?,?)""", (str(uuid.uuid4()), uid, item_type, name))
        conn.commit()

def get_inventory(item_type=None):
    uid = st.session_state.user_id
    if not uid:
        return pd.DataFrame()
    with closing(get_conn()) as conn:
        if item_type:
            df = pd.read_sql_query(
                "SELECT item_type, name FROM inventory WHERE user_id=? AND item_type=?",
                conn, params=(uid, item_type)
            )
        else:
            df = pd.read_sql_query(
                "SELECT item_type, name FROM inventory WHERE user_id=?",
                conn, params=(uid,)
            )
    return df

# ===============================
# 테마 CSS
# ===============================
def apply_theme(theme_name):
    palette = THEMES.get(theme_name, THEMES["핑크"])
    PRIMARY = palette["PRIMARY"]
    SECONDARY = palette["SECONDARY"]
    ACCENT = palette["ACCENT"]
    DARK = palette["DARK"]
    css = f"""
    <style>
    :root {{
      --primary: {PRIMARY};
      --secondary: {SECONDARY};
      --accent: {ACCENT};
      --dark: {DARK};
    }}
    .block-container {{ padding-top: 0.8rem; }}
    h1, h2, h3, h4 {{ color: var(--dark); }}
    .stProgress > div > div > div > div {{ background-color: var(--primary); }}
    .stButton>button {{
      border-radius: 12px; border: 2px solid {ACCENT}20;
      background: linear-gradient(135deg, {PRIMARY}33, {SECONDARY}33);
      color: var(--dark); padding: 0.5rem 1rem;
    }}
    .topbar .stButton>button {{
      border-radius: 999px; border: 1px solid {ACCENT}55;
      background: linear-gradient(135deg, {PRIMARY}22, {SECONDARY}22);
      padding: 0.35rem 0.9rem; font-weight: 600;
    }}
    .card {{
      border-radius: 16px; border: 1px solid {ACCENT}33; padding: 14px; background: white;
      box-shadow: 0 6px 18px rgba(0,0,0,0.06); margin-bottom: 10px;
    }}
    .badge {{
      display: inline-block; padding: 4px 10px; border-radius: 999px;
      background: {ACCENT}22; color: var(--dark); border: 1px solid {ACCENT}55;
      margin-right: 6px; font-size: 0.85rem;
    }}
    .small {{ color: #6b7280; font-size: 0.85rem; }}
    .badge-owned {{
      display:inline-block; padding:6px 12px; border-radius:10px;
      background: {PRIMARY}22; color: var(--dark);
      border: 1px solid {ACCENT}55; font-weight:600;
    }}
    .disabled-box {{ opacity: 0.7; pointer-events: none; }}
    .kudos {{ color: {DARK}; font-weight: 600; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

apply_theme(get_daily()["theme"])

# ===============================
# 사이드바
# ===============================
st.sidebar.title("수능 러닝 메이트+")
if st.session_state.user_id:
    st.sidebar.success(f"안녕하세요, 사용자님!")
else:
    st.sidebar.info("로그인하지 않으셨습니다.")

d_side = get_daily()
if st.session_state.user_id:
    new_goal = st.sidebar.slider("오늘 목표(분)", min_value=30, max_value=600, step=10, value=d_side["goal_min"], key="sb_goal_slider")
    if new_goal != d_side["goal_min"]:
        update_daily(goal=new_goal)
        st.toast("오늘의 목표가 업데이트되었어요!")

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"보유 코인: {get_daily()['coins']} • 스트릭: {get_daily()['streak']}일")
    st.sidebar.caption(f"현재 테마: {get_daily()['theme']} • 사운드: {get_daily()['sound']} • 마스코트: {get_daily()['mascot']}")

nav_items = [TAB_AUTH] if not st.session_state.user_id else [TAB_HOME, TAB_TODO, TAB_TIMER, TAB_STATS, TAB_GUILD, TAB_SHOP]
nav_choice = st.sidebar.radio("빠른 이동", nav_items,
                              index=0 if st.session_state.active_tab not in nav_items else nav_items.index(st.session_state.active_tab),
                              key="sb_nav_radio")
if nav_choice != st.session_state.active_tab:
    st.session_state.active_tab = nav_choice
    safe_rerun()

# ===============================
# 상단바
# ===============================
st.markdown("<div class='topbar'>", unsafe_allow_html=True)
if st.session_state.user_id:
    c_nav1, c_nav2, c_nav3, c_nav4, c_nav5, c_nav6, c_sp = st.columns([1,1,1,1,1,1,4])
    with c_nav1:
        if st.button("🏠 홈", key="top_home"):
            st.session_state.active_tab = TAB_HOME; safe_rerun()
    with c_nav2:
        if st.button("📝 투두", key="top_todo"):
            st.session_state.active_tab = TAB_TODO; safe_rerun()
    with c_nav3:
        if st.button("⏱ 타이머", key="top_timer"):
            st.session_state.active_tab = TAB_TIMER; safe_rerun()
    with c_nav4:
        if st.button("📊 통계", key="top_stats"):
            st.session_state.active_tab = TAB_STATS; safe_rerun()
    with c_nav5:
        if st.button("🛒 상점", key="top_shop"):
            st.session_state.active_tab = TAB_SHOP; safe_rerun()
    with c_nav6:
        if st.button("로그아웃", key="top_logout"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.active_tab = TAB_AUTH
            st.toast("로그아웃 되었습니다.")
            safe_rerun()
else:
    c_nav1, c_sp = st.columns([1,9])
    with c_nav1:
        if st.button("로그인", key="top_login"):
            st.session_state.active_tab = TAB_AUTH; safe_rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ===============================
# 화면 컴포넌트
# ===============================
def render_auth():
    st.header("로그인 / 회원가입")
    tab_login, tab_signup = st.tabs(["로그인", "회원가입"])

    with tab_login:
        login_id = st.text_input("이메일 또는 사용자명", key="auth_login_id")
        pw = st.text_input("비밀번호", type="password", key="auth_login_pw")
        if st.button("로그인", key="auth_login_btn"):
            ok, data, msg = authenticate(login_id, pw)
            if ok:
                uid, username = data
                st.session_state.user_id = uid
                st.session_state.username = username
                st.session_state.active_tab = TAB_HOME
                st.success("환영합니다! 로그인에 성공했어요.")
                safe_rerun()
            else:
                st.error(msg)

    with tab_signup:
        email = st.text_input("이메일", key="auth_signup_email")
        username = st.text_input("사용자명", key="auth_signup_username")
        pw1 = st.text_input("비밀번호", type="password", key="auth_signup_pw1")
        pw2 = st.text_input("비밀번호 확인", type="password", key="auth_signup_pw2")
        if st.button("회원가입", key="auth_signup_btn"):
            if pw1 != pw2:
                st.error("비밀번호 확인이 일치하지 않습니다.")
            else:
                ok, res = create_user(email, username, pw1)
                if ok:
                    st.success("회원가입이 완료되었습니다. 이제 로그인해 주세요.")
                else:
                    st.error(res)

def render_home():
    require_login()
    st.title("오늘의 공부, 충분히 멋져요! ✨")
    total_min, df_today = get_today_summary()
    d = get_daily()
    progress = min(total_min / max(1, d["goal_min"]), 1.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='card'><b>오늘 누적</b><br><h3>{total_min}분</h3></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='card'><b>목표</b><br><h3>{d['goal_min']}분</h3></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='card'><b>코인</b><br><h3>{d['coins']}</h3></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='card'><b>스트릭</b><br><h3>{d['streak']}일</h3></div>", unsafe_allow_html=True)

    st.progress(progress)
    if progress >= 1.0:
        st.success("오늘 목표 달성! +30코인 보너스 지급!")
        grant_coins(base=0, bonus=30, reason="데일리 목표 달성 보너스")

    st.subheader("오늘의 기록")
    if df_today is not None and not df_today.empty:
        st.dataframe(
            df_today[["subject", "duration_min", "distractions", "mood", "energy", "difficulty"]]
            .rename(columns={"subject":"과목","duration_min":"분","distractions":"방해","mood":"기분","energy":"에너지","difficulty":"난이도"}),
            use_container_width=True
        )
    else:
        st.info("아직 기록이 없어요. 타이머 화면에서 한 세션 시작해 볼까요?")

    st.markdown("<div class='card kudos'>오늘의 한 줄 칭찬: 짧게라도 꾸준히가 정답이에요. 지금의 한 번이 내일을 바꿔요! EMOJI_1</div>", unsafe_allow_html=True)

def render_stats():
    require_login()
    st.header("주간 통계")
    weekly = get_weekly()
    if weekly is not None and not weekly.empty:
        chart_df = weekly.set_index("date")
        st.bar_chart(chart_df)
    else:
        st.info("이번 주 데이터가 곧 채워질 거예요.")

def render_guild():
    require_login()
    st.header("길드")
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM guild")
        if c.fetchone()[0] == 0:
            for gid, name in [("focus-fox","포커스 폭스"), ("steady-bear","스테디 베어"), ("owl-night","올빼미 나잇")]:
                c.execute("INSERT INTO guild(id,name) VALUES(?,?)", (gid,name))
            conn.commit()

    with closing(get_conn()) as conn:
        df_guilds = pd.read_sql_query("SELECT id, name FROM guild", conn)
        df_mine = pd.read_sql_query("SELECT id, name FROM my_guild WHERE user_id=?", conn, params=(st.session_state.user_id,))

    current_name = df_mine["name"].iloc[0] if not df_mine.empty else "길드 미참여"
    st.caption(f"현재 길드: {current_name}")

    gname = st.selectbox("길드 선택", df_guilds["name"].tolist(), key="guild_select")
    if st.button("길드 참여/변경", key="guild_join_btn"):
        with closing(get_conn()) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM my_guild WHERE user_id=?", (st.session_state.user_id,))
            gid = df_guilds.loc[df_guilds["name"]==gname, "id"].iloc[0]
            c.execute("INSERT INTO my_guild(id,user_id,name) VALUES(?,?,?)", (str(uuid.uuid4()), st.session_state.user_id, gname))
            conn.commit()
        st.success(f"{gname}에 참여했어요! 함께 꾸준히 가봐요.")

    st.subheader("길드 랭킹(최근 7일)")
    st.info("현재는 로컬 단일 사용자 모드예요. 온라인 동기화 후 실제 멤버 랭킹이 제공됩니다.")

def render_timer():
    require_login()
    st.header("포모도로 타이머")

    # 과목 관리
    st.subheader("과목 관리")
    col_add, col_del = st.columns([2,2])
    with col_add:
        new_subj = st.text_input("새 과목 추가", placeholder="예: 수학 II", key="subj_add_input")
        if st.button("과목 추가", key="subj_add_btn"):
            if add_subject(new_subj):
                st.success(f"'{new_subj}' 과목이 추가되었어요.")
                safe_rerun()
            else:
                st.warning("과목명이 비었거나 이미 존재합니다.")
    with col_del:
        existing = get_subjects()
        del_choice = st.selectbox("삭제할 과목 선택", ["(선택)"] + existing, index=0, key="subj_del_select")
        if st.button("과목 삭제", key="subj_del_btn"):
            if del_choice != "(선택)" and remove_subject(del_choice):
                st.success(f"'{del_choice}' 과목을 삭제했어요.")
                if st.session_state.subject == del_choice:
                    st.session_state.subject = None
                safe_rerun()
            else:
                st.warning("삭제할 과목을 선택해 주세요.")

    st.markdown("---")

    # 과목 선택
    subjects = get_subjects()
    if not subjects:
        st.info("등록된 과목이 없습니다. 위에서 과목을 먼저 추가해 주세요.")
    else:
        if st.session_state.subject not in subjects:
            st.session_state.subject = subjects[0]
        st.session_state.subject = st.selectbox("과목", subjects, index=subjects.index(st.session_state.subject), key="timer_subject_select")

    # 프리셋
    colA, colB, colC, colD = st.columns(4)
    with colA:
        if st.button("25분", key="preset_25"): st.session_state.preset = 25
    with colB:
        if st.button("40분", key="preset_40"): st.session_state.preset = 40
    with colC:
        if st.button("50분", key="preset_50"): st.session_state.preset = 50
    with colD:
        st.session_state.preset = st.number_input("커스텀(분)", min_value=10, max_value=120, value=st.session_state.preset, step=5, key="preset_custom")

    t1, t2, t3 = st.columns(3)
    with t1:
        if (not st.session_state.timer_running) and subjects and st.button("시작 ▶", key="timer_start"):
            st.session_state.timer_running = True
            st.session_state.end_time = time.time() + st.session_state.preset * 60
            st.session_state.distractions = 0
            st.toast("타이머 시작! 종료 시 회고를 기록해 코인을 받아요.")
    with t2:
        if st.session_state.timer_running and st.button("일시정지 ⏸", key="timer_pause"):
            st.session_state.timer_running = False
    with t3:
        if st.session_state.timer_running and st.button("방해 +1", key="timer_disturb"):
            st.session_state.distractions += 1

    # 카운트다운
    timer_placeholder = st.empty()
    if st.session_state.timer_running and (st.session_state.end_time is not None):
        remaining = int(st.session_state.end_time - time.time())
        if remaining <= 0:
            st.session_state.timer_running = False
            st.success("세션 완료! 아래에서 회고를 기록해 코인을 받아요.")
        else:
            mm, ss = divmod(remaining, 60)
            timer_placeholder.markdown(
                f"<div class='card'><h3>남은 시간: {mm:02d}:{ss:02d}</h3>"
                f"<div class='small'>집중! 휴대폰은 잠시 멀리 EMOJI_2</div></div>",
                unsafe_allow_html=True
            )
            time.sleep(1)
            safe_rerun()

    # 회고 폼
    def reflection_form(duration_min):
        with st.form("reflection_form"):
            st.write(f"이번 세션: {st.session_state.subject if st.session_state.subject else '(과목 미선택)'} • {duration_min}분 • 방해 {st.session_state.distractions}회")
            mood = st.radio("기분", ["EMOJI_3 좋음","EMOJI_4 보통","EMOJI_5 낮음"], horizontal=True, key="reflect_mood")
            energy = st.slider("에너지", 1, 5, 3, key="reflect_energy")
            difficulty = st.slider("난이도", 1, 5, 3, key="reflect_difficulty")
            submitted = st.form_submit_button("저장하고 코인 받기", key="reflect_submit")
            if submitted:
                subject_to_save = st.session_state.subject if st.session_state.subject else "(미지정)"
                add_session(subject_to_save, duration_min, st.session_state.distractions, mood, energy, difficulty)
                bonus = 10 if st.session_state.distractions <= 1 else 0
                grant_coins(base=10, bonus=bonus, reason="세션 완료")
                st.session_state.timer_running = False
                st.success(f"기록 완료! +{10+bonus}코인 지급")
                st.balloons()
                safe_rerun()

    end_time = st.session_state.end_time
    if (st.session_state.timer_running is False) and (end_time is not None) and ((end_time - time.time()) <= 0):
        reflection_form(st.session_state.preset)

# 투두
def get_todos(show_all=False, only_today=False):
    uid = st.session_state.user_id
    if not uid:
        return pd.DataFrame()
    query = "SELECT * FROM todos WHERE user_id=?"
    params = [uid]
    conds = []
    if only_today:
        conds.append("due_date=?")
        params.append(TODAY)
    if not show_all and not only_today:
        conds.append("is_done=0")
    if conds:
        query += " AND " + " AND ".join(conds)
    query += " ORDER BY is_done ASC, priority DESC, due_date ASC"
    with closing(get_conn()) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df

def add_todo(title, subject, due_date, estimated_min, priority, reward_coins):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO todos(id, user_id, title, subject, due_date, estimated_min, priority, is_done, done_at, reward_coins)
                     VALUES(?,?,?,?,?,?,?,?,?,?)""",
                  (str(uuid.uuid4()), uid, title, subject, due_date, estimated_min, priority, 0, None, reward_coins))
        conn.commit()

def update_todo_done(todo_id, done=True):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT is_done, reward_coins FROM todos WHERE id=? AND user_id=?", (todo_id, uid))
        row = c.fetchone()
        if not row:
            return
        is_done_now, reward = row
        if done and is_done_now == 0:
            c.execute("UPDATE todos SET is_done=1, done_at=? WHERE id=?", (dt.datetime.now().isoformat(), todo_id))
            conn.commit()
            if reward and reward > 0:
                update_daily(coins_delta=reward)
                add_reward("todo", "계획 완료", reward)
        elif (not done) and is_done_now == 1:
            c.execute("UPDATE todos SET is_done=0, done_at=NULL WHERE id=?", (todo_id,))
            conn.commit()

def edit_todo(todo_id, title, subject, due_date, estimated_min, priority, reward_coins):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""UPDATE todos
                     SET title=?, subject=?, due_date=?, estimated_min=?, priority=?, reward_coins=?
                     WHERE id=? AND user_id=?""",
                  (title, subject, due_date, estimated_min, priority, reward_coins, todo_id, uid))
        conn.commit()

def delete_todo(todo_id):
    uid = st.session_state.user_id
    if not uid:
        return
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM todos WHERE id=? AND user_id=?", (todo_id, uid))
        conn.commit()

def render_todo():
    require_login()
    st.header("투두리스트 · 공부 계획")
    st.caption("계획을 완료하면 설정한 코인이 자동 지급돼요!")

    # 필터
    box1, box2, box3 = st.columns(3)
    with box1:
        if st.button("오늘 할 일 보기", key="todo_filter_today"):
            st.session_state.todo_filter = "today"; safe_rerun()
    with box2:
        if st.button("미완료 보기", key="todo_filter_pending"):
            st.session_state.todo_filter = "pending"; safe_rerun()
    with box3:
        if st.button("전체 보기", key="todo_filter_all"):
            st.session_state.todo_filter = "all"; safe_rerun()

    if "todo_filter" not in st.session_state:
        st.session_state.todo_filter = "pending"

    only_today = st.session_state.todo_filter == "today"
    show_all = st.session_state.todo_filter == "all"

    # 추가 폼
    st.subheader("새 계획 추가")
    subjects = get_subjects()
    col_a, col_b = st.columns([3,2])
    with col_a:
        title = st.text_input("계획 제목", placeholder="예: 수학 II 3개년 기출 2세트", key="todo_add_title")
    with col_b:
        subject = st.selectbox("과목(선택)", ["(미지정)"] + subjects, key="todo_add_subject")
    col_c, col_d, col_e = st.columns([1,1,1])
    with col_c:
        due_date = st.date_input("마감일", value=dt.date.today(), key="todo_add_due").isoformat()
    with col_d:
        estimated = st.number_input("예상 소요(분)", min_value=10, max_value=600, value=60, step=10, key="todo_add_est")
    with col_e:
        priority = st.selectbox("우선순위", [1,2,3,4,5], index=2, key="todo_add_pri")
    col_f, col_g = st.columns([1,3])
    with col_f:
        reward = st.number_input("보상 코인", min_value=0, max_value=100, value=10, step=5, key="todo_add_reward")
    with col_g:
        if st.button("계획 추가", key="todo_add_btn"):
            if (title or "").strip():
                add_todo(
                    title=title.strip(),
                    subject=None if subject=="(미지정)" else subject,
                    due_date=due_date,
                    estimated_min=int(estimated),
                    priority=int(priority),
                    reward_coins=int(reward)
                )
                st.success("계획이 추가되었어요!")
                safe_rerun()
            else:
                st.warning("계획 제목을 입력해 주세요.")

    st.markdown("---")

    # 목록
    df = get_todos(show_all=show_all, only_today=only_today)
    if df is None or df.empty:
        st.info("표시할 계획이 없어요. 새로운 계획을 추가해 보세요!")
        return

    st.subheader("계획 목록")
    for _, row in df.iterrows():
        with st.container():
            col1, col2, col3, col4, col5, col6, col7 = st.columns([4,2,2,1,1,1,1])
            title_disp = row["title"]
            subj_disp = row["subject"] if row["subject"] else "(미지정)"
            due_disp = row["due_date"]
            est_disp = f"{int(row['estimated_min'])}분"
            prio_disp = int(row["priority"])
            reward_disp = int(row["reward_coins"]) if row["reward_coins"] else 0
            done = bool(row["is_done"])

            with col1:
                st.markdown(f"<div class='card'><b>{title_disp}</b><br><span class='small'>{subj_disp} • {due_disp} • 예상 {est_disp}</span></div>", unsafe_allow_html=True)
            with col2:
                st.write(f"우선순위: {prio_disp}")
            with col3:
                st.write(f"보상: {reward_disp}코인")
            with col4:
                if st.button("완료" if not done else "완료 취소", key=f"todo_done_{row['id']}"):
                    update_todo_done(row["id"], done=not done)
                    if not done and reward_disp > 0:
                        st.toast(f"+{reward_disp} 코인 지급!")
                    safe_rerun()
            with col5:
                if st.button("편집", key=f"todo_edit_{row['id']}"):
                    st.session_state.edit_id = row["id"]
                    st.session_state.edit_payload = row.to_dict()
                    safe_rerun()
            with col6:
                if st.button("삭제", key=f"todo_del_{row['id']}"):
                    delete_todo(row["id"])
                    st.toast("삭제되었습니다.")
                    safe_rerun()
            with col7:
                st.write("✅" if done else "🕒")

    # 편집 섹션
    if "edit_id" in st.session_state and st.session_state.edit_id:
        st.markdown("---")
        st.subheader("계획 편집")
        data = st.session_state.edit_payload
        e_title = st.text_input("계획 제목", value=data["title"], key="todo_edit_title")
        subj_list = ["(미지정)"] + get_subjects()
        default_index = subj_list.index(data["subject"]) if data["subject"] in subj_list else 0
        e_subject = st.selectbox("과목(선택)", subj_list, index=default_index, key="todo_edit_subject")
        e_due = st.date_input("마감일", value=dt.date.fromisoformat(data["due_date"]), key="todo_edit_due").isoformat()
        e_est = st.number_input("예상 소요(분)", min_value=10, max_value=600, value=int(data["estimated_min"]), step=10, key="todo_edit_est")
        e_pri = st.selectbox("우선순위", [1,2,3,4,5], index=[1,2,3,4,5].index(int(data["priority"])), key="todo_edit_pri")
        e_reward = st.number_input("보상 코인", min_value=0, max_value=100, value=int(data["reward_coins"] or 0), step=5, key="todo_edit_reward")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("저장", key="todo_edit_save"):
                edit_todo(
                    todo_id=st.session_state.edit_id,
                    title=e_title.strip(),
                    subject=None if e_subject=="(미지정)" else e_subject,
                    due_date=e_due,
                    estimated_min=int(e_est),
                    priority=int(e_pri),
                    reward_coins=int(e_reward)
                )
                st.success("수정되었어요!")
                st.session_state.edit_id = None
                st.session_state.edit_payload = None
                safe_rerun()
        with c2:
            if st.button("취소", key="todo_edit_cancel"):
                st.session_state.edit_id = None
                st.session_state.edit_payload = None
                safe_rerun()

# 상점
def render_shop():
    require_login()
    d = get_daily()
    st.header("상점")
    st.caption("해금한 테마/사운드/마스코트를 실제 UI에 적용할 수 있어요. 라임색은 제외했습니다.")
    st.markdown(f"<div class='card'><b>보유 코인</b><br><h3>{d['coins']}</h3></div>", unsafe_allow_html=True)

    st.subheader("아이템 구매")
    for item in SHOP_ITEMS:
        owned = has_item(item["type"], item["name"])
        card_class = "disabled-box" if owned else ""
        col1, col2, col3 = st.columns([4,1,2])
        with col1:
            st.markdown(
                f"<div class='card {card_class}'><b>{item['name']}</b> <span class='small'>• {item['type']}</span></div>",
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(f"<div class='{card_class}'>{item['price']}코인</div>", unsafe_allow_html=True)
        with col3:
            if owned:
                st.markdown("<div class='badge-owned'>이미 구매함</div>", unsafe_allow_html=True)
            else:
                if st.button("구매", key=f"buy_{item['type']}_{item['name']}"):
                    d_now = get_daily()
                    if d_now["coins"] < item["price"]:
                        st.warning("코인이 부족해요.")
                    else:
                        add_item(item["type"], item["name"])
                        update_daily(coins_delta=-item["price"])
                        add_reward("shop", item["name"], -item["price"])
                        st.success(f"{item['name']} 해금 완료!")
                        safe_rerun()

    st.subheader("장착/적용")
    inv_theme = get_inventory("theme")
    if not inv_theme.empty:
        current_theme = get_daily()["theme"]
        theme_list = inv_theme["name"].tolist()
        idx = theme_list.index(current_theme) if current_theme in theme_list else 0
        theme_to_apply = st.selectbox("적용할 테마", theme_list, index=idx, key="apply_theme_select")
        if st.button("테마 적용", key="apply_theme_btn"):
            update_daily(theme=theme_to_apply)
            apply_theme(theme_to_apply)
            st.success(f"테마 '{theme_to_apply}'가 적용되었어요!")
            safe_rerun()
    else:
        st.caption("테마를 하나 구매하면 여기서 적용할 수 있어요.")

    inv_sound = get_inventory("sound")
    if not inv_sound.empty:
        current_sound = get_daily()["sound"]
        sound_list = inv_sound["name"].tolist()
        idx = sound_list.index(current_sound) if current_sound in sound_list else 0
        sound_to_apply = st.selectbox("적용할 타이머 사운드", sound_list, index=idx, key="apply_sound_select")
        if st.button("사운드 적용", key="apply_sound_btn"):
            update_daily(sound=sound_to_apply)
            st.success(f"종료 사운드 '{sound_to_apply}'로 설정되었어요! (미리보기 문구)")
    else:
        st.caption("사운드를 하나 구매하면 종료 알림 문구로 안내해 드려요.")

    inv_masc = get_inventory("mascot")
    if not inv_masc.empty:
        current_masc = get_daily()["mascot"]
        masc_list = inv_masc["name"].tolist()
        idx = masc_list.index(current_masc) if current_masc in masc_list else 0
        mascot_to_apply = st.selectbox("적용할 마스코트", masc_list, index=idx, key="apply_masc_select")
        if st.button("마스코트 적용", key="apply_masc_btn"):
            update_daily(mascot=mascot_to_apply)
            st.success(f"마스코트 '{mascot_to_apply}'로 설정되었어요! 타이머 화면에 표시됩니다.")
    else:
        st.caption("마스코트를 하나 구매하면 타이머 화면에 귀여운 이모지가 표시돼요.")

# ===============================
# 라우팅
# ===============================
if st.session_state.active_tab == TAB_AUTH:
    render_auth()
elif st.session_state.active_tab == TAB_HOME:
    render_home()
elif st.session_state.active_tab == TAB_TODO:
    render_todo()
elif st.session_state.active_tab == TAB_TIMER:
    render_timer()
elif st.session_state.active_tab == TAB_STATS:
    render_stats()
elif st.session_state.active_tab == TAB_GUILD:
    render_guild()
elif st.session_state.active_tab == TAB_SHOP:
    render_shop()
