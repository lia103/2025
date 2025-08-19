import time
import datetime as dt
import uuid
import sqlite3
from contextlib import closing

import pandas as pd
import streamlit as st

# ---------------------------
# 기본 설정 및 테마(라임색 배제)
# ---------------------------
st.set_page_config(page_title="수능 러닝 메이트", page_icon="📚", layout="centered")

PRIMARY = "#F5A6C6"   # 파스텔 핑크
SECONDARY = "#B7A8F5" # 라일락
ACCENT = "#8DB7F5"    # 하늘색
DARK = "#1E2A44"      # 네이비 톤

CUSTOM_CSS = f"""
<style>
:root {{
  --primary: {PRIMARY};
  --secondary: {SECONDARY};
  --accent: {ACCENT};
  --dark: {DARK};
}}
/* 카드형 느낌 */
.block-container {{
  padding-top: 1.2rem;
}}
h1, h2, h3 {{
  color: var(--dark);
}}
.stProgress > div > div > div > div {{
  background-color: var(--primary);
}}
.stButton>button {{
  border-radius: 12px;
  border: 2px solid {ACCENT}20;
  background: linear-gradient(135deg, {PRIMARY}33, {SECONDARY}33);
  color: var(--dark);
  padding: 0.5rem 1rem;
}}
.badge {{
  display: inline-block;
  padding: 4px 10px;
  border-radius: 999px;
  background: {ACCENT}22;
  color: var(--dark);
  border: 1px solid {ACCENT}55;
  margin-right: 6px;
  font-size: 0.85rem;
}}
.card {{
  border-radius: 16px;
  border: 1px solid {ACCENT}33;
  padding: 14px;
  background: white;
  box-shadow: 0 6px 18px rgba(0,0,0,0.04);
  margin-bottom: 10px;
}}
.small {{
  color: #6b7280;
  font-size: 0.85rem;
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------
# 간단 DB 초기화(SQLite)
# ---------------------------
def init_db():
    with closing(sqlite3.connect("study_mate.db")) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS sessions(
            id TEXT PRIMARY KEY,
            date TEXT,
            subject TEXT,
            duration_min INTEGER,
            distractions INTEGER,
            mood TEXT,
            energy INTEGER,
            difficulty INTEGER
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS daily(
            date TEXT PRIMARY KEY,
            goal_min INTEGER,
            coins INTEGER,
            streak INTEGER
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS rewards(
            id TEXT PRIMARY KEY,
            date TEXT,
            type TEXT,
            name TEXT,
            coins_change INTEGER
        );""")
        c.execute("""CREATE TABLE IF NOT EXISTS meta(
            key TEXT PRIMARY KEY,
            value TEXT
        );""")
        conn.commit()

def get_conn():
    return sqlite3.connect("study_mate.db")

init_db()

# ---------------------------
# 유틸
# ---------------------------
TODAY = dt.date.today().isoformat()

def get_daily_row():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT date, goal_min, coins, streak FROM daily WHERE date=?", (TODAY,))
        row = c.fetchone()
        if not row:
            # 전날 스트릭 이어받기
            y = (dt.date.today() - dt.timedelta(days=1)).isoformat()
            c.execute("SELECT streak FROM daily WHERE date=?", (y,))
            prev = c.fetchone()
            streak = prev[0] + 1 if prev else 1
            c.execute("INSERT INTO daily(date, goal_min, coins, streak) VALUES(?,?,?,?)",
                      (TODAY, 120, 0, streak))
            conn.commit()
            return (TODAY, 120, 0, streak)
        return row

def update_daily(goal=None, coins_delta=0, overwrite_streak=None):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        date, goal_min, coins, streak = get_daily_row()
        goal_min = goal if goal is not None else goal_min
        if overwrite_streak is not None:
            streak = overwrite_streak
        coins = coins + coins_delta
        c.execute("REPLACE INTO daily(date, goal_min, coins, streak) VALUES(?,?,?,?)",
                  (TODAY, goal_min, coins, streak))
        conn.commit()

def add_session(subject, duration_min, distractions, mood, energy, difficulty):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        sid = str(uuid.uuid4())
        c.execute("""INSERT INTO sessions(id, date, subject, duration_min, distractions, mood, energy, difficulty)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (sid, TODAY, subject, duration_min, distractions, mood, energy, difficulty))
        conn.commit()

def add_reward(rtype, name, coins_change):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        rid = str(uuid.uuid4())
        c.execute("""INSERT INTO rewards(id, date, type, name, coins_change)
                     VALUES (?,?,?,?,?)""",
                  (rid, TODAY, rtype, name, coins_change))
        conn.commit()

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
            ORDER BY date DESC
            LIMIT 7
        """, conn)
        return df.sort_values("date")

def get_coins_streak_goal():
    date, goal_min, coins, streak = get_daily_row()
    return coins, streak, goal_min

def grant_coins(base=10, bonus=0, reason="세션 완료"):
    update_daily(coins_delta=base+bonus)
    add_reward("coin", reason, base+bonus)

# ---------------------------
# 사이드바: 데일리 목표, 테마, 상점
# ---------------------------
st.sidebar.title("수능 러닝 메이트")
coins, streak, goal_min = get_coins_streak_goal()

with st.sidebar:
    st.markdown("#### 오늘의 목표")
    new_goal = st.slider("분 단위 목표", min_value=30, max_value=600, step=10, value=goal_min)
    if new_goal != goal_min:
        update_daily(goal=new_goal)
        st.toast("오늘의 목표가 업데이트되었어요!")

    st.markdown("---")
    st.markdown(f"보유 코인: {coins} • 스트릭: {streak}일 연속")
    st.markdown("---")
    st.markdown("#### 상점")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("테마 핑크 • 50코인"):
            if coins >= 50:
                update_daily(coins_delta=-50)
                add_reward("shop", "핑크 테마", -50)
                st.success("핑크 테마 해금! 곧 테마 선택에서 커스텀 가능해요.")
            else:
                st.warning("코인이 부족해요.")
    with col2:
        if st.button("타이머 벨소리 • 30코인"):
            if coins >= 30:
                update_daily(coins_delta=-30)
                add_reward("shop", "타이머 사운드", -30)
                st.success("타이머 사운드 해금!")
            else:
                st.warning("코인이 부족해요.")

# ---------------------------
# 메인: 대시보드
# ---------------------------
st.title("오늘의 공부, 충분히 멋져요! ✨")

total_min, df_today = get_today_summary()
progress = min(total_min / max(1, get_coins_streak_goal()[2]), 1.0)
st.markdown(f"현재까지 누적 집중: {total_min}분 / 목표: {get_coins_streak_goal()[2]}분")
st.progress(progress)

if progress >= 1.0:
    st.success("목표 달성! +30코인 보너스 지급!")
    grant_coins(base=0, bonus=30, reason="데일리 목표 달성 보너스")

# 배지(간단 규칙)
badges = []
if total_min >= 100:
    badges.append("첫 100분 달성")
if total_min >= 200:
    badges.append("집중 200분 클리어")
if df_today is not None and not df_today.empty:
    morning_sessions = any([(dt.datetime.now().hour <= 8)])
    if morning_sessions:
        badges.append("아침 출발 배지")

if badges:
    st.markdown("획득 배지")
    st.write(" ".join([f"<span class='badge'>🏅 {b}</span>" for b in badges]), unsafe_allow_html=True)

# ---------------------------
# 타이머 카드
# ---------------------------
st.subheader("포모도로 타이머")

# 상태 초기화
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "end_time" not in st.session_state:
    st.session_state.end_time = None
if "subject" not in st.session_state:
    st.session_state.subject = "국어"
if "distractions" not in st.session_state:
    st.session_state.distractions = 0
if "preset" not in st.session_state:
    st.session_state.preset = 25

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

st.session_state.subject = st.selectbox("과목 선택", ["국어", "수학", "영어", "탐구-사탐", "탐구-과탐", "한국사", "기타"], index=0)

c1, c2, c3 = st.columns(3)
with c1:
    if not st.session_state.timer_running and st.button("시작 ▶"):
        st.session_state.timer_running = True
        st.session_state.end_time = time.time() + st.session_state.preset * 60
        st.session_state.distractions = 0
with c2:
    if st.session_state.timer_running and st.button("일시정지 ⏸"):
        st.session_state.end_time = st.session_state.end_time + 999999  # 간단 중지(실전에서는 별도 상태로)
        st.session_state.timer_running = False
with c3:
    if st.session_state.timer_running and st.button("방해 요소 +1"):
        st.session_state.distractions += 1

timer_placeholder = st.empty()

if st.session_state.timer_running and st.session_state.end_time:
    remaining = int(st.session_state.end_time - time.time())
    if remaining <= 0:
        # 세션 종료 → 회고 폼
        st.session_state.timer_running = False
        st.success("세션 완료! 회고를 기록해 볼까요?")
    else:
        mm, ss = divmod(remaining, 60)
        timer_placeholder.markdown(f"<div class='card'><h3>남은 시간: {mm:02d}:{ss:02d}</h3><div class='small'>집중! 휴대폰은 잠시 멀리 📵</div></div>", unsafe_allow_html=True)
        time.sleep(1)
        st.experimental_rerun()

# ---------------------------
# 회고 폼(세션 종료 후)
# ---------------------------
def reflection_form(duration_min):
    with st.form("reflection"):
        st.write(f"이번 세션: {st.session_state.subject} • {duration_min}분 • 방해 {st.session_state.distractions}회")
        mood = st.radio("기분", ["🙂 좋음", "😐 보통", "😣 낮음"], horizontal=True)
        energy = st.slider("에너지", 1, 5, 3)
        difficulty = st.slider("난이도", 1, 5, 3)
        submitted = st.form_submit_button("저장하고 코인 받기")
        if submitted:
            add_session(st.session_state.subject, duration_min, st.session_state.distractions, mood, energy, difficulty)
            bonus = 10 if st.session_state.distractions <= 1 else 0  # 방해 적었을 때 보너스
            grant_coins(base=10, bonus=bonus, reason="세션 완료")
            st.success(f"기록 완료! +{10+bonus}코인 지급")
            st.balloons()
            st.experimental_rerun()

# 세션이 막 끝난 경우(간단 감지: 타이머가 꺼져 있고 end_time가 과거)
if not st.session_state.timer_running and st.session_state.end_time and (st.session_state.end_time - time.time()) <= 0:
    duration = st.session_state.preset
    reflection_form(duration)

# ---------------------------
# 오늘의 기록
# ---------------------------
st.subheader("오늘의 기록")
if df_today is not None and not df_today.empty:
    st.dataframe(df_today[["subject", "duration_min", "distractions", "mood", "energy", "difficulty"]]
                 .rename(columns={
                     "subject": "과목", "duration_min": "분", "distractions":"방해",
                     "mood":"기분", "energy":"에너지", "difficulty":"난이도"
                 }), use_container_width=True)
else:
    st.info("아직 기록이 없어요. 짧게라도 한 세션을 시작해 볼까요?")

# ---------------------------
# 주간 통계(간단)
# ---------------------------
st.subheader("주간 통계")
weekly = get_weekly()
if weekly is not None and not weekly.empty:
    chart_df = weekly.set_index("date")
    st.bar_chart(chart_df)
else:
    st.write("이번 주 데이터가 곧 채워질 거예요.")

# 작은 응원 문구
st.markdown("<div class='card'>오늘의 한 줄 칭찬: 짧게라도 꾸준히가 정답이에요. 지금의 한 번이 내일을 바꿔요! 💪</div>", unsafe_allow_html=True)
