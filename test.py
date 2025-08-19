import time
import datetime as dt
import uuid
import sqlite3
from contextlib import closing

import pandas as pd
import streamlit as st

# ===============================
# 기본 설정: 단일 사용자/로그인 없음
# ===============================
st.set_page_config(page_title="수능 러닝 메이트+", page_icon="🌟", layout="wide")

APP_DB = "study_mate_final.db"
TODAY = dt.date.today().isoformat()

# ===============================
# DB 초기화
# ===============================
def init_db():
    with closing(sqlite3.connect(APP_DB)) as conn:
        c = conn.cursor()
        # 하루 상태(목표/코인/스트릭/현재 장착 아이템)
        c.execute("""
        CREATE TABLE IF NOT EXISTS daily(
            date TEXT PRIMARY KEY,
            goal_min INTEGER,
            coins INTEGER,
            streak INTEGER,
            theme TEXT,
            sound TEXT,
            mascot TEXT
        );
        """)
        # 공부 세션 로그
        c.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY,
            date TEXT,
            subject TEXT,
            duration_min INTEGER,
            distractions INTEGER,
            mood TEXT,
            energy INTEGER,
            difficulty INTEGER
        );
        """)
        # 보유 아이템
        c.execute("""
        CREATE TABLE IF NOT EXISTS inventory(
            item_id TEXT PRIMARY KEY,
            item_type TEXT,
            name TEXT
        );
        """)
        # 보상/구매 로그
        c.execute("""
        CREATE TABLE IF NOT EXISTS rewards(
            id TEXT PRIMARY KEY,
            date TEXT,
            type TEXT,
            name TEXT,
            coins_change INTEGER
        );
        """)
        # 길드(로컬 모의 데이터)
        c.execute("""
        CREATE TABLE IF NOT EXISTS guild(
            id TEXT PRIMARY KEY,
            name TEXT
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS my_guild(
            id TEXT PRIMARY KEY,
            name TEXT
        );
        """)
        conn.commit()

def get_conn():
    return sqlite3.connect(APP_DB)

init_db()

# ===============================
# 초기 상태 보장
# ===============================
def ensure_today():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT date FROM daily WHERE date=?", (TODAY,))
        row = c.fetchone()
        if not row:
            # 스트릭(전날 기록 있으면 +1)
            y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
            c.execute("SELECT streak FROM daily WHERE date=?", (y,))
            prev = c.fetchone()
            streak = (prev[0] + 1) if prev else 1
            # 기본값(라임 배제, 밝고 귀엽고 화려한 팔레트)
            c.execute("""INSERT INTO daily(date, goal_min, coins, streak, theme, sound, mascot)
                         VALUES(?,?,?,?,?,?,?)""",
                      (TODAY, 120, 0, streak, "핑크", "벨", "여우"))
            conn.commit()

def get_daily():
    ensure_today()
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM daily WHERE date=?", conn, params=(TODAY,))
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
        c.execute("""REPLACE INTO daily(date, goal_min, coins, streak, theme, sound, mascot)
                     VALUES(?,?,?,?,?,?,?)""",
                  (TODAY, goal_min, coins, streak, theme, sound, mascot))
        conn.commit()

def add_session(subject, duration_min, distractions, mood, energy, difficulty):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO sessions(id, date, subject, duration_min, distractions, mood, energy, difficulty)
                     VALUES(?,?,?,?,?,?,?,?)""",
                  (str(uuid.uuid4()), TODAY, subject, duration_min, distractions, mood, energy, difficulty))
        conn.commit()

def add_reward(rtype, name, coins_change):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT INTO rewards(id, date, type, name, coins_change)
                     VALUES(?,?,?,?,?)""",
                  (str(uuid.uuid4()), TODAY, rtype, name, coins_change))
        conn.commit()

def grant_coins(base=10, bonus=0, reason="세션 완료"):
    update_daily(coins_delta=(base+bonus))
    add_reward("coin", reason, base+bonus)

def get_today_summary():
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM sessions WHERE date=?", conn, params=(TODAY,))
    total = int(df["duration_min"].sum()) if not df.empty else 0
    return total, df

def get_weekly():
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("""
            SELECT date, SUM(duration_min) AS total_min
            FROM sessions
            GROUP BY date
            ORDER BY date ASC
        """, conn)
    return df.tail(7) if not df.empty else df

# ===============================
# 상점/인벤토리
# ===============================
THEMES = {
    "핑크":   {"PRIMARY":"#F5A6C6", "SECONDARY":"#B7A8F5", "ACCENT":"#8DB7F5", "DARK":"#1E2A44"},
    "라일락": {"PRIMARY":"#C8B6FF", "SECONDARY":"#E7C6FF", "ACCENT":"#B8C0FF", "DARK":"#1E2A44"},
    "하늘":   {"PRIMARY":"#9CCCFB", "SECONDARY":"#CFE8FF", "ACCENT":"#86B6F2", "DARK":"#18324B"},
    "네이비": {"PRIMARY":"#203A74", "SECONDARY":"#2F4A8A", "ACCENT":"#7AA2FF", "DARK":"#101A2E"},
    "코랄":   {"PRIMARY":"#FF8A80", "SECONDARY":"#FFD3C9", "ACCENT":"#FFA8A0", "DARK":"#2B1E1E"},
}
# 라임색은 의도적으로 제외

SHOP_ITEMS = [
    # 테마 5종
    {"type":"theme", "name":"핑크", "price":50},
    {"type":"theme", "name":"라일락", "price":50},
    {"type":"theme", "name":"하늘", "price":50},
    {"type":"theme", "name":"네이비", "price":50},
    {"type":"theme", "name":"코랄", "price":50},
    # 사운드 3종(미리보기 문구)
    {"type":"sound", "name":"벨", "price":30},
    {"type":"sound", "name":"우드블럭", "price":30},
    {"type":"sound", "name":"빗소리", "price":30},
    # 마스코트 3종(타이머 이모지)
    {"type":"mascot", "name":"여우", "price":40},
    {"type":"mascot", "name":"곰", "price":40},
    {"type":"mascot", "name":"올빼미", "price":40},
]

def has_item(item_type, name):
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT 1 FROM inventory WHERE item_type=? AND name=?",
                               conn, params=(item_type, name))
    return not df.empty

def add_item(item_type, name):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""INSERT OR IGNORE INTO inventory(item_id, item_type, name)
                     VALUES(?,?,?)""", (str(uuid.uuid4()), item_type, name))
        conn.commit()

def get_inventory(item_type=None):
    with closing(get_conn()) as conn:
        if item_type:
            df = pd.read_sql_query("SELECT item_type, name FROM inventory WHERE item_type=?",
                                   conn, params=(item_type,))
        else:
            df = pd.read_sql_query("SELECT item_type, name FROM inventory", conn)
    return df

# ===============================
# 테마 적용(CSS 주입)
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
    .kudos {{ color: {DARK}; font-weight: 600; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ===============================
# 세션 상태(타이머)
# ===============================
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "end_time" not in st.session_state:
    st.session_state.end_time = None
if "preset" not in st.session_state:
    st.session_state.preset = 25
if "subject" not in st.session_state:
    st.session_state.subject = "국어"
if "distractions" not in st.session_state:
    st.session_state.distractions = 0

# 현재 테마 적용
apply_theme(get_daily()["theme"])

# ===============================
# 사이드바(오늘 목표/코인/현재 장착)
# ===============================
st.sidebar.title("수능 러닝 메이트+")
d_side = get_daily()
new_goal = st.sidebar.slider("오늘 목표(분)", min_value=30, max_value=600, step=10, value=d_side["goal_min"])
if new_goal != d_side["goal_min"]:
    update_daily(goal=new_goal)
    st.toast("오늘의 목표가 업데이트되었어요!")

st.sidebar.markdown("---")
st.sidebar.markdown(f"보유 코인: {get_daily()['coins']} • 스트릭: {get_daily()['streak']}일")
st.sidebar.caption(f"현재 테마: {get_daily()['theme']} • 사운드: {get_daily()['sound']} • 마스코트: {get_daily()['mascot']}")

# ===============================
# 상단 고정 보조 네비게이션 버튼
# ===============================
st.markdown(
    "<div style='position:sticky; top:0; background:white; padding:8px 0; z-index:999; border-bottom:1px solid #e5e7eb;'>"
    "<span style='margin-right:8px; font-weight:600;'>빠른 이동:</span>"
    "</div>", unsafe_allow_html=True
)
nav_c1, nav_c2, nav_c3 = st.columns([1,1,8])
with nav_c1:
    if st.button("타이머로 이동 ▶"):
        st.session_state.__go_timer = True
with nav_c2:
    if st.button("상점으로 이동 🛍️"):
        st.session_state.__go_shop = True

# ===============================
# 탭 구성: 홈, 타이머, 통계, 길드, 상점
# ===============================
tab_home, tab_timer, tab_stats, tab_guild, tab_shop = st.tabs(["홈", "타이머", "통계", "길드", "상점"])

# 홈 탭
with tab_home:
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

    # 간단 배지
    badges = []
    if total_min >= 100: badges.append("첫 100분 달성")
    if total_min >= 200: badges.append("200분 돌파")
    if dt.datetime.now().hour <= 8 and total_min > 0: badges.append("아침 출발 배지")
    if badges:
        st.markdown("획득 배지")
        st.write(" ".join([f"<span class='badge'>🏅 {b}</span>" for b in badges]), unsafe_allow_html=True)

    st.subheader("오늘의 기록")
    if df_today is not None and not df_today.empty:
        st.dataframe(
            df_today[["subject", "duration_min", "distractions", "mood", "energy", "difficulty"]]
            .rename(columns={"subject":"과목","duration_min":"분","distractions":"방해","mood":"기분","energy":"에너지","difficulty":"난이도"}),
            use_container_width=True
        )
    else:
        st.info("아직 기록이 없어요. 타이머 탭에서 한 세션 시작해 볼까요?")

    st.markdown("<div class='card kudos'>오늘의 한 줄 칭찬: 짧게라도 꾸준히가 정답이에요. 지금의 한 번이 내일을 바꿔요! 💪</div>", unsafe_allow_html=True)

# 타이머 탭
with tab_timer:
    st.markdown("<a name='timer_anchor'></a>", unsafe_allow_html=True)
    d = get_daily()
    st.header(f"포모도로 타이머 • 마스코트: {d['mascot']}")
    st.caption("마스코트는 상점에서 변경할 수 있어요.")

    colA, colB, colC, colD = st.columns(4)
    with colA:
        if st.button("25분"):
            st.session_state.preset = 25
    with colB:
        if st.button("40분"):
            st.session_state.preset = 40
    with colC:
        if st.button("50분"):
            st.session_state.preset = 50
    with colD:
        st.session_state.preset = st.number_input("커스텀(분)", min_value=10, max_value=120, value=st.session_state.preset, step=5)

    st.session_state.subject = st.selectbox("과목", ["국어","수학","영어","탐구-사탐","탐구-과탐","한국사","기타"], index=0)

    t1, t2, t3 = st.columns(3)
    with t1:
        if not st.session_state.timer_running and st.button("시작 ▶"):
            st.session_state.timer_running = True
            st.session_state.end_time = time.time() + st.session_state.preset * 60
            st.session_state.distractions = 0
            st.toast(f"타이머 시작! 종료 사운드: {d['sound']}")
    with t2:
        if st.session_state.timer_running and st.button("일시정지 ⏸"):
            st.session_state.timer_running = False
    with t3:
        if st.session_state.timer_running and st.button("방해 +1"):
            st.session_state.distractions += 1

    timer_placeholder = st.empty()
    if st.session_state.timer_running and st.session_state.end_time:
        remaining = int(st.session_state.end_time - time.time())
        if remaining <= 0:
            st.session_state.timer_running = False
            st.success("세션 완료! 회고를 기록해 볼까요?")
        else:
            mm, ss = divmod(remaining, 60)
            mascot_emoji = {"여우":"🦊","곰":"🐻","올빼미":"🦉"}.get(d["mascot"], "✨")
            timer_placeholder.markdown(
                f"<div class='card'><h3>{mascot_emoji} 남은 시간: {mm:02d}:{ss:02d}</h3><div class='small'>집중! 휴대폰은 잠시 멀리 📵</div></div>",
                unsafe_allow_html=True
            )
            time.sleep(1)
            st.experimental_rerun()

    # 회고 폼
    def reflection_form(duration_min):
        with st.form("reflection"):
            st.write(f"이번 세션: {st.session_state.subject} • {duration_min}분 • 방해 {st.session_state.distractions}회")
            mood = st.radio("기분", ["🙂 좋음","😐 보통","😣 낮음"], horizontal=True)
            energy = st.slider("에너지", 1, 5, 3)
            difficulty = st.slider("난이도", 1, 5, 3)
            submitted = st.form_submit_button("저장하고 코인 받기")
            if submitted:
                add_session(st.session_state.subject, duration_min, st.session_state.distractions, mood, energy, difficulty)
                bonus = 10 if st.session_state.distractions <= 1 else 0
                grant_coins(base=10, bonus=bonus, reason="세션 완료")
                st.success(f"기록 완료! +{10+bonus}코인 지급")
                st.balloons()
                st.experimental_rerun()

    if not st.session_state.timer_running and st.session_state.end_time and (st.session_state.end_time - time.time()) <= 0:
        reflection_form(st.session_state.preset)

# 통계 탭
with tab_stats:
    st.header("주간 통계")
    weekly = get_weekly()
    if weekly is not None and not weekly.empty:
        chart_df = weekly.set_index("date")
        st.bar_chart(chart_df)
    else:
        st.info("이번 주 데이터가 곧 채워질 거예요.")

# 길드 탭(로컬 모드)
with tab_guild:
    st.header("길드")
    # 길드 후보 초기 주입
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM guild")
        if c.fetchone()[0] == 0:
            for gid, name in [("focus-fox","포커스 폭스"), ("steady-bear","스테디 베어"), ("owl-night","올빼미 나잇")]:
                c.execute("INSERT INTO guild(id,name) VALUES(?,?)", (gid,name))
            conn.commit()

    with closing(get_conn()) as conn:
        df_guilds = pd.read_sql_query("SELECT id, name FROM guild", conn)
        df_mine = pd.read_sql_query("SELECT id, name FROM my_guild", conn)

    current_name = df_mine["name"].iloc[0] if not df_mine.empty else "길드 미참여"
    st.caption(f"현재 길드: {current_name}")

    gname = st.selectbox("길드 선택", df_guilds["name"].tolist())
    if st.button("길드 참여/변경"):
        with closing(get_conn()) as conn:
            c = conn.cursor()
            c.execute("DELETE FROM my_guild")
            gid = df_guilds.loc[df_guilds["name"]==gname, "id"].iloc[0]
            c.execute("INSERT INTO my_guild(id,name) VALUES(?,?)", (gid, gname))
            conn.commit()
        st.success(f"{gname}에 참여했어요! 함께 꾸준히 가봐요.")

    st.subheader("길드 랭킹(최근 7일)")
    st.info("현재는 로컬 단일 사용자 모드예요. 온라인 동기화 후 실제 멤버 랭킹이 제공됩니다.")

# 상점 탭
with tab_shop:
    st.markdown("<a name='shop_anchor'></a>", unsafe_allow_html=True)
    d = get_daily()
    st.header("상점")
    st.caption("해금한 테마/사운드/마스코트를 실제 UI에 적용할 수 있어요. 라임색은 제외했습니다.")
    st.markdown(f"<div class='card'><b>보유 코인</b><br><h3>{d['coins']}</h3></div>", unsafe_allow_html=True)

    st.subheader("아이템 구매")
    for item in SHOP_ITEMS:
        col1, col2, col3, col4 = st.columns([3,1,1,2])
        with col1:
            st.write(f"- {item['type']} • {item['name']}")
        with col2:
            st.write(f"{item['price']}코인")
        with col3:
            owned = has_item(item["type"], item["name"])
            st.write("보유" if owned else "미보유")
        with col4:
            if st.button(f"구매: {item['name']}", key=f"buy_{item['type']}_{item['name']}"):
                d_now = get_daily()
                if has_item(item["type"], item["name"]):
                    st.warning("이미 보유 중이에요.")
                elif d_now["coins"] < item["price"]:
                    st.warning("코인이 부족해요.")
                else:
                    add_item(item["type"], item["name"])
                    update_daily(coins_delta=-item["price"])
                    add_reward("shop", item["name"], -item["price"])
                    st.success(f"{item['name']} 해금 완료!")
                    st.experimental_rerun()

    st.subheader("장착/적용")
    # 테마 적용
    inv_theme = get_inventory("theme")
    if not inv_theme.empty:
        current_theme = get_daily()["theme"]
        theme_list = inv_theme["name"].tolist()
        idx = theme_list.index(current_theme) if current_theme in theme_list else 0
        theme_to_apply = st.selectbox("적용할 테마", theme_list, index=idx)
        if st.button("테마 적용"):
            update_daily(theme=theme_to_apply)
            apply_theme(theme_to_apply)
            st.success(f"테마 '{theme_to_apply}'가 적용되었어요!")
            st.experimental_rerun()
    else:
        st.caption("테마를 하나 구매하면 여기서 적용할 수 있어요.")

    # 사운드 적용
    inv_sound = get_inventory("sound")
    if not inv_sound.empty:
        current_sound = get_daily()["sound"]
        sound_list = inv_sound["name"].tolist()
        idx = sound_list.index(current_sound) if current_sound in sound_list else 0
        sound_to_apply = st.selectbox("적용할 타이머 사운드", sound_list, index=idx)
        if st.button("사운드 적용"):
            update_daily(sound=sound_to_apply)
            st.success(f"종료 사운드 '{sound_to_apply}'로 설정되었어요! (미리보기 문구)")
    else:
        st.caption("사운드를 하나 구매하면 종료 알림 문구로 안내해 드려요.")

    # 마스코트 적용
    inv_masc = get_inventory("mascot")
    if not inv_masc.empty:
        current_masc = get_daily()["mascot"]
        masc_list = inv_masc["name"].tolist()
        idx = masc_list.index(current_masc) if current_masc in masc_list else 0
        mascot_to_apply = st.selectbox("적용할 마스코트", masc_list, index=idx)
        if st.button("마스코트 적용"):
            update_daily(mascot=mascot_to_apply)
            st.success(f"마스코트 '{mascot_to_apply}'로 설정되었어요! 타이머 화면에 표시됩니다.")
    else:
        st.caption("마스코트를 하나 구매하면 타이머 화면에 귀여운 이모지가 표시돼요.")

    st.subheader("구매/보상 내역")
    with closing(get_conn()) as conn:
        df_r = pd.read_sql_query("SELECT date, type, name, coins_change FROM rewards ORDER BY date DESC", conn)
    if df_r.empty:
        st.info("아직 구매나 보상 내역이 없어요. 세션을 완료해 코인을 모아보세요!")
    else:
        st.dataframe(
            df_r.rename(columns={"date":"날짜","type":"구분","name":"아이템/사유","coins_change":"코인 변화"}),
            use_container_width=True
        )

# ===============================
# 네비 버튼 클릭 시 안내(탭 전환 대안)
# ===============================
if st.session_state.get("__go_timer"):
    st.session_state.__go_timer = False
    st.info("상단의 '타이머' 탭을 눌러 이동해 주세요.")
if st.session_state.get("__go_shop"):
    st.session_state.__go_shop = False
    st.info("상단의 '상점' 탭을 눌러 이동해 주세요.")
tab_home, tab_timer, tab_stats, tab_guild, tab_shop = st.tabs(["홈", "타이머", "통계", "길드", "상점"])
