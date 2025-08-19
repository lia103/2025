import time
import datetime as dt
import uuid
import sqlite3
from contextlib import closing

import pandas as pd
import streamlit as st

# ---------------------------
# 기본 설정 및 테마(라임색 제외)
# ---------------------------
st.set_page_config(page_title="수능 러닝 메이트+", page_icon="🌟", layout="wide")

PRIMARY = "#F5A6C6"   # 파스텔 핑크
SECONDARY = "#B7A8F5" # 라일락
ACCENT = "#8DB7F5"    # 하늘색
DARK = "#1E2A44"      # 네이비

CSS = f"""
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
st.markdown(CSS, unsafe_allow_html=True)

# ---------------------------
# DB 초기화(SQLite)
# ---------------------------
def init_db():
    with closing(sqlite3.connect("study_mate_clean.db")) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            nickname TEXT,
            created_at TEXT
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            subject TEXT,
            duration_min INTEGER,
            distractions INTEGER,
            mood TEXT,
            energy INTEGER,
            difficulty INTEGER
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS daily(
            user_id TEXT,
            date TEXT,
            goal_min INTEGER,
            coins INTEGER,
            streak INTEGER,
            PRIMARY KEY(user_id, date)
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS rewards(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            type TEXT,
            name TEXT,
            coins_change INTEGER
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS guilds(
            id TEXT PRIMARY KEY,
            name TEXT
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS guild_members(
            guild_id TEXT,
            user_id TEXT,
            joined_at TEXT,
            PRIMARY KEY(guild_id, user_id)
        );""")
        conn.commit()

def get_conn():
    return sqlite3.connect("study_mate_clean.db")

init_db()

# ---------------------------
# 유틸/데이터 접근
# ---------------------------
def get_or_create_user(nickname: str):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE nickname=?", (nickname,))
        row = c.fetchone()
        if row:
            return row[0]
        uid = str(uuid.uuid4())
        c.execute("INSERT INTO users(id, nickname, created_at) VALUES(?,?,?)",
                  (uid, nickname, dt.datetime.utcnow().isoformat()))
        conn.commit()
        return uid

def get_daily_row(user_id: str, for_date: str):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT date, goal_min, coins, streak FROM daily WHERE user_id=? AND date=?",
                  (user_id, for_date))
        row = c.fetchone()
        if not row:
            y = (dt.date.fromisoformat(for_date) - dt.timedelta(days=1)).isoformat()
            c.execute("SELECT streak FROM daily WHERE user_id=? AND date=?", (user_id, y))
            prev = c.fetchone()
            streak = (prev[0] + 1) if prev else 1
            c.execute("INSERT INTO daily(user_id, date, goal_min, coins, streak) VALUES(?,?,?,?,?)",
                      (user_id, for_date, 120, 0, streak))
            conn.commit()
            return (for_date, 120, 0, streak)
        return row

def update_daily(user_id: str, for_date: str, goal=None, coins_delta=0, overwrite_streak=None):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        date, goal_min, coins, streak = get_daily_row(user_id, for_date)
        goal_min = goal if goal is not None else goal_min
        if overwrite_streak is not None:
            streak = overwrite_streak
        coins = coins + coins_delta
        c.execute("""REPLACE INTO daily(user_id, date, goal_min, coins, streak)
                     VALUES(?,?,?,?,?)""", (user_id, for_date, goal_min, coins, streak))
        conn.commit()

def add_session(user_id, date, subject, duration_min, distractions, mood, energy, difficulty):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        sid = str(uuid.uuid4())
        c.execute("""INSERT INTO sessions(id, user_id, date, subject, duration_min, distractions, mood, energy, difficulty)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (sid, user_id, date, subject, duration_min, distractions, mood, energy, difficulty))
        conn.commit()

def add_reward(user_id, date, rtype, name, coins_change):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        rid = str(uuid.uuid4())
        c.execute("""INSERT INTO rewards(id, user_id, date, type, name, coins_change)
                     VALUES (?,?,?,?,?,?)""",
                  (rid, user_id, date, rtype, name, coins_change))
        conn.commit()

def get_today_summary(user_id, for_date):
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT * FROM sessions WHERE user_id=? AND date=?",
                               conn, params=(user_id, for_date))
        total = int(df["duration_min"].sum()) if not df.empty else 0
        return total, df

def get_weekly(user_id):
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("""
            SELECT date, SUM(duration_min) AS total_min
            FROM sessions
            WHERE user_id=?
            GROUP BY date
            ORDER BY date ASC
        """, conn, params=(user_id,))
        if not df.empty:
            df = df.tail(7)
        return df

def grant_coins(user_id, for_date, base=10, bonus=0, reason="세션 완료"):
    update_daily(user_id, for_date, coins_delta=(base+bonus))
    add_reward(user_id, for_date, "coin", reason, base+bonus)

# 길드
def ensure_default_guilds():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM guilds")
        count = c.fetchone()[0]
        if count == 0:
            for gid, name in [("focus-fox", "포커스 폭스"), ("steady-bear", "스테디 베어"), ("owl-night", "올빼미 나잇")]:
                c.execute("INSERT INTO guilds(id, name) VALUES(?,?)", (gid, name))
            conn.commit()

def join_guild(user_id, gid):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("DELETE FROM guild_members WHERE user_id=?", (user_id,))
        c.execute("INSERT OR REPLACE INTO guild_members(guild_id, user_id, joined_at) VALUES(?,?,?)",
                  (gid, user_id, dt.datetime.utcnow().isoformat()))
        conn.commit()

def get_user_guild(user_id):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("""SELECT gm.guild_id, g.name FROM guild_members gm
                     JOIN guilds g ON g.id=gm.guild_id
                     WHERE gm.user_id=?""", (user_id,))
        row = c.fetchone()
        if row: return row[0], row[1]
        return None, None

def get_guild_rankings(gid):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        if gid:
            c.execute("SELECT user_id FROM guild_members WHERE guild_id=?", (gid,))
        else:
            c.execute("SELECT user_id FROM guild_members")
        users = [r[0] for r in c.fetchall()]
        rows = []
        for uid in users:
            df = pd.read_sql_query("""SELECT SUM(duration_min) AS total_min
                                      FROM sessions
                                      WHERE user_id=? AND date >= ?""",
                                   conn, params=(uid, (dt.date.today()-dt.timedelta(days=6)).isoformat()))
            total = int(df["total_min"].iloc[0]) if not df.empty and df["total_min"].iloc[0] else 0
            nickname = pd.read_sql_query("SELECT nickname FROM users WHERE id=?", conn, params=(uid,)).iloc[0,0]
            rows.append((nickname, total))
        rows.sort(key=lambda x: x[1], reverse=True)
        return rows[:10]

# ---------------------------
# 상태/세션 초기화
# ---------------------------
TODAY = dt.date.today().isoformat()
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
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ---------------------------
# 상단: 로그인/닉네임
# ---------------------------
st.sidebar.title("수능 러닝 메이트+")
nickname = st.sidebar.text_input("닉네임", value="사용자")
if st.sidebar.button("시작/로그인"):
    st.session_state.user_id = get_or_create_user(nickname)
    st.toast(f"{nickname}님, 환영해요!")

if not st.session_state.user_id:
    st.session_state.user_id = get_or_create_user(nickname)

user_id = st.session_state.user_id
ensure_default_guilds()

date, goal_min, coins, streak = get_daily_row(user_id, TODAY)
with st.sidebar:
    st.markdown("#### 오늘의 목표")
    new_goal = st.slider("분 단위 목표", 30, 600, value=goal_min, step=10)
    if new_goal != goal_min:
        update_daily(user_id, TODAY, goal=new_goal)
        st.toast("오늘의 목표를 업데이트했어요!")
        date, goal_min, coins, streak = get_daily_row(user_id, TODAY)
    st.markdown("---")
    st.markdown(f"보유 코인: {coins} • 스트릭: {streak}일")

# ---------------------------
# 멀티 탭 네비게이션
# ---------------------------
tab_home, tab_timer, tab_stats, tab_guild, tab_shop = st.tabs(["홈", "타이머", "통계", "길드", "상점"])

# 홈 탭
with tab_home:
    st.title("오늘의 공부, 충분히 멋져요! ✨")
    total_min, df_today = get_today_summary(user_id, TODAY)
    progress = min(total_min / max(1, goal_min), 1.0)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"<div class='card'><b>오늘 누적</b><br><h3>{total_min}분</h3></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='card'><b>목표</b><br><h3>{goal_min}분</h3></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='card'><b>코인</b><br><h3>{coins}</h3></div>", unsafe_allow_html=True)
    with c4:
        st.markdown(f"<div class='card'><b>스트릭</b><br><h3>{streak}일</h3></div>", unsafe_allow_html=True)

    st.progress(progress)
    if progress >= 1.0:
        st.success("오늘 목표 달성! +30코인 보너스 지급!")
        grant_coins(user_id, TODAY, base=0, bonus=30, reason="데일리 목표 달성")

    badges = []
    if total_min >= 100: badges.append("첫 100분 달성")
    if total_min >= 200: badges.append("200분 돌파")
    if dt.datetime.now().hour <= 8 and total_min > 0: badges.append("아침 출발 배지")
    if badges:
        st.markdown("획득 배지")
        st.write(" ".join([f"<span class='badge'>🏅 {b}</span>" for b in badges]), unsafe_allow_html=True)

    st.subheader("오늘의 기록")
    if df_today is not None and not df_today.empty:
        st.dataframe(df_today[["subject", "duration_min", "distractions", "mood", "energy", "difficulty"]]
            .rename(columns={"subject":"과목","duration_min":"분","distractions":"방해","mood":"기분","energy":"에너지","difficulty":"난이도"}),
            use_container_width=True)
    else:
        st.info("아직 기록이 없어요. 타이머 탭에서 한 세션 시작해 볼까요?")

    st.markdown("<div class='card kudos'>오늘의 한 줄 칭찬: 짧게라도 꾸준히가 정답이에요. 지금의 한 번이 내일을 바꿔요! 💪</div>", unsafe_allow_html=True)

# 타이머 탭
with tab_timer:
    st.header("포모도로 타이머")
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
            timer_placeholder.markdown(
                f"<div class='card'><h3>남은 시간: {mm:02d}:{ss:02d}</h3><div class='small'>집중! 휴대폰은 잠시 멀리 📵</div></div>",
                unsafe_allow_html=True
            )
            time.sleep(1)
            st.experimental_rerun()

    def reflection_form(duration_min):
        with st.form("reflection"):
            st.write(f"이번 세션: {st.session_state.subject} • {duration_min}분 • 방해 {st.session_state.distractions}회")
            mood = st.radio("기분", ["🙂 좋음","😐 보통","😣 낮음"], horizontal=True)
            energy = st.slider("에너지", 1, 5, 3)
            difficulty = st.slider("난이도", 1, 5, 3)
            submitted = st.form_submit_button("저장하고 코인 받기")
            if submitted:
                add_session(user_id, TODAY, st.session_state.subject, duration_min,
                            st.session_state.distractions, mood, energy, difficulty)
                bonus = 10 if st.session_state.distractions <= 1 else 0
                grant_coins(user_id, TODAY, base=10, bonus=bonus, reason="세션 완료")
                st.success(f"기록 완료! +{10+bonus}코인 지급")
                st.balloons()
                st.experimental_rerun()

    if not st.session_state.timer_running and st.session_state.end_time and (st.session_state.end_time - time.time()) <= 0:
        reflection_form(st.session_state.preset)

# 통계 탭
with tab_stats:
    st.header("주간 통계")
    weekly = get_weekly(user_id)
    if weekly is not None and not weekly.empty:
        chart_df = weekly.set_index("date")
        st.bar_chart(chart_df)
    else:
        st.info("이번 주 데이터가 곧 채워질 거예요.")

# 길드 탭
with tab_guild:
    st.header("길드")
    guild_map = {"포커스 폭스":"focus-fox","스테디 베어":"steady-bear","올빼미 나잇":"owl-night"}
    gname = st.selectbox("길드 선택", list(guild_map.keys()))
    if st.button("길드 참여/변경"):
        join_guild(user_id, guild_map[gname])
        st.success(f"{gname}에 참여했어요! 함께 꾸준히 가봐요.")
    my_gid, my_gname = get_user_guild(user_id)
    cga, cgb = st.columns(2)
    with cga:
        st.markdown(f"<div class='card'><b>현재 길드</b><br>{my_gname if my_gname else '길드 미참여'}</div>", unsafe_allow_html=True)
    with cgb:
        scope = "내 길드" if my_gid else "전체"
        st.markdown(f"<div class='card'><b>랭킹 범위</b><br>{scope}</div>", unsafe_allow_html=True)

    rank_rows = get_guild_rankings(my_gid if my_gid else None)
    if rank_rows:
        rank_df = pd.DataFrame(rank_rows, columns=["닉네임", "최근 7일(분)"])
        st.table(rank_df)
    else:
        st.info("랭킹 데이터를 불러오는 중이에요. 길드에 참여하면 랭킹이 표시돼요!")

# 상점 탭(독립 페이지)
with tab_shop:
    st.header("상점")
    st.caption("코인으로 테마와 타이머 사운드를 해금하세요. 라임색은 제외하고 밝고 귀여운 톤으로 준비했어요.")
    _, cshop_main, _ = st.columns([1,2,1])
    with cshop_main:
        st.markdown(f"<div class='card'><b>보유 코인</b><br><h3>{coins}</h3></div>", unsafe_allow_html=True)
        st.subheader("아이템")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("핑크 테마 • 50코인"):
                if coins >= 50:
                    update_daily(user_id, TODAY, coins_delta=-50)
                    add_reward(user_id, TODAY, "shop", "핑크 테마", -50)
                    st.success("핑크 테마 해금 완료!")
                else:
                    st.warning("코인이 부족해요.")
        with col2:
            if st.button("라일락 테마 • 50코인"):
                if coins >= 50:
                    update_daily(user_id, TODAY, coins_delta=-50)
                    add_reward(user_id, TODAY, "shop", "라일락 테마", -50)
                    st.success("라일락 테마 해금 완료!")
                else:
                    st.warning("코인이 부족해요.")
        with col3:
            if st.button("타이머 사운드 • 30코인"):
                if coins >= 30:
                    update_daily(user_id, TODAY, coins_delta=-30)
                    add_reward(user_id, TODAY, "shop", "타이머 사운드", -30)
                    st.success("타이머 사운드 해금 완료!")
                else:
                    st.warning("코인이 부족해요.")

        st.subheader("구매/보상 내역")
        with closing(get_conn()) as conn:
            df_r = pd.read_sql_query("SELECT date, type, name, coins_change FROM rewards WHERE user_id=? ORDER BY date DESC",
                                     conn, params=(user_id,))
        if df_r.empty:
            st.info("아직 구매나 보상 내역이 없어요. 세션을 완료해 코인을 모아보세요!")
        else:
            st.dataframe(df_r.rename(columns={"date":"날짜","type":"구분","name":"아이템/사유","coins_change":"코인 변화"}), use_container_width=True)
