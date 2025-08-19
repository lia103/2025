import time
import datetime as dt
import uuid
import sqlite3
from contextlib import closing
from typing import List, Optional, Dict

import pandas as pd
import streamlit as st

# --------------------------------
# 기본 설정 및 테마(라임 제외)
# --------------------------------
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
.divider {{ height: 1px; background: {ACCENT}33; margin: 10px 0; }}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --------------------------------
# DB 초기화(SQLite)
# --------------------------------
def init_db():
    with closing(sqlite3.connect("study_mate_plus.db")) as conn:
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
        c.execute("""CREATE TABLE IF NOT EXISTS mistakes(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            subject TEXT,
            question_type TEXT,  -- 객관식/주관식/서술형 등
            mistake_type TEXT,   -- 개념/계산/시간/부주의
            concept_tag TEXT,    -- 관련 개념 태그
            memo TEXT
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
    return sqlite3.connect("study_mate_plus.db")

init_db()

# --------------------------------
# 간단 계정(로컬 닉네임 기반)
# --------------------------------
def get_or_create_user(nickname: str):
    uid = None
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE nickname=?", (nickname,))
        row = c.fetchone()
        if row:
            uid = row[0]
        else:
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
            # 스트릭 계산(전날 기록 여부)
            y = (dt.date.fromisoformat(for_date) - dt.timedelta(days=1)).isoformat()
            c.execute("SELECT streak FROM daily WHERE user_id=? AND date=?", (user_id, y))
            prev = c.fetchone()
            # 전날 데이터가 없으면 스트릭 1로 시작
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

def add_mistake(user_id, date, subject, question_type, mistake_type, concept_tag, memo):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        mid = str(uuid.uuid4())
        c.execute("""INSERT INTO mistakes(id, user_id, date, subject, question_type, mistake_type, concept_tag, memo)
                     VALUES (?,?,?,?,?,?,?,?)""",
                  (mid, user_id, date, subject, question_type, mistake_type, concept_tag, memo))
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
        # 최근 7일만
        if not df.empty:
            df = df.tail(7)
        return df

def grant_coins(user_id, for_date, base=10, bonus=0, reason="세션 완료"):
    update_daily(user_id, for_date, coins_delta=(base+bonus))
    add_reward(user_id, for_date, "coin", reason, base+bonus)

# --------------------------------
# 길드/랭킹(로컬 모의)
# --------------------------------
def ensure_default_guilds():
    with closing(get_conn()) as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM guilds")
        count = c.fetchone()[0]
        if count == 0:
            gids = [("focus-fox", "포커스 폭스"), ("steady-bear", "스테디 베어"), ("owl-night", "올빼미 나잇")]
            for gid, name in gids:
                c.execute("INSERT INTO guilds(id, name) VALUES(?,?)", (gid, name))
            conn.commit()

def join_guild(user_id, gid):
    with closing(get_conn()) as conn:
        c = conn.cursor()
        # 한 유저 1길드 정책: 기존 제거
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

def get_guild_rankings(gid: Optional[str]):
    # 간단 랭킹: 최근 7일 누적 시간 합
    with closing(get_conn()) as conn:
        c = conn.cursor()
        if gid:
            c.execute("""SELECT gm.user_id FROM guild_members gm WHERE gm.guild_id=?""", (gid,))
        else:
            c.execute("""SELECT user_id FROM guild_members""")
        users = [r[0] for r in c.fetchall()]
        rows = []
        for uid in users:
            df = pd.read_sql_query("""SELECT SUM(duration_min) as total_min FROM sessions
                                      WHERE user_id=? AND date >= ?""",
                                   conn, params=(uid, (dt.date.today()-dt.timedelta(days=6)).isoformat()))
            total = int(df["total_min"].iloc[0]) if not df.empty and df["total_min"].iloc[0] else 0
            nickname = pd.read_sql_query("SELECT nickname FROM users WHERE id=?", conn, params=(uid,)).iloc[0,0]
            rows.append((nickname, total))
        rows.sort(key=lambda x: x[1], reverse=True)
        return rows[:10]

# --------------------------------
# 상태 초기화
# --------------------------------
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

# --------------------------------
# 사이드바: 로그인/목표/상점/길드
# --------------------------------
st.sidebar.title("수능 러닝 메이트+")
nickname = st.sidebar.text_input("닉네임", value="사용자")
if st.sidebar.button("시작/로그인"):
    st.session_state.user_id = get_or_create_user(nickname)
    st.toast(f"{nickname}님, 환영해요!")

# 사용자 식별이 없으면 게스트로 생성
if "user_id" not in st.session_state:
    st.session_state.user_id = get_or_create_user(nickname)

user_id = st.session_state.user_id

ensure_default_guilds()

date, goal_min, coins, streak = get_daily_row(user_id, TODAY)
with st.sidebar:
    st.markdown("#### 오늘의 목표")
    new_goal = st.slider("분 단위 목표", min_value=30, max_value=600, step=10, value=goal_min)
    if new_goal != goal_min:
        update_daily(user_id, TODAY, goal=new_goal)
        st.toast("오늘의 목표가 업데이트되었어요!")
        date, goal_min, coins, streak = get_daily_row(user_id, TODAY)

    st.markdown("---")
    st.markdown(f"보유 코인: {coins} • 스트릭: {streak}일")
    st.markdown("---")

    st.markdown("#### 길드 선택")
    guild_map = {"포커스 폭스": "focus-fox", "스테디 베어": "steady-bear", "올빼미 나잇": "owl-night"}
    gname = st.selectbox("나의 학습 무드에 맞는 길드", list(guild_map.keys()))
    if st.button("길드 참여/변경"):
        join_guild(user_id, guild_map[gname])
        st.success(f"{gname}에 참여했어요! 함께 꾸준히 가볼까요?")
    my_gid, my_gname = get_user_guild(user_id)
    if my_gid:
        st.caption(f"현재 길드: {my_gname}")

    st.markdown("---")
    st.markdown("#### 상점")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("핑크 테마 • 50"):
            if coins >= 50:
                update_daily(user_id, TODAY, coins_delta=-50)
                add_reward(user_id, TODAY, "shop", "핑크 테마", -50)
                st.success("핑크 테마 해금 완료!")
            else:
                st.warning("코인이 부족해요.")
    with col2:
        if st.button("라일락 테마 • 50"):
            if coins >= 50:
                update_daily(user_id, TODAY, coins_delta=-50)
                add_reward(user_id, TODAY, "shop", "라일락 테마", -50)
                st.success("라일락 테마 해금 완료!")
            else:
                st.warning("코인이 부족해요.")
    with col3:
        if st.button("타이머 사운드 • 30"):
            if coins >= 30:
                update_daily(user_id, TODAY, coins_delta=-30)
                add_reward(user_id, TODAY, "shop", "타이머 사운드", -30)
                st.success("타이머 사운드 해금 완료!")
            else:
                st.warning("코인이 부족해요.")

# --------------------------------
# 상단 대시보드
# --------------------------------
st.title("오늘의 공부, 충분히 멋져요! ✨")
total_min, df_today = get_today_summary(user_id, TODAY)
progress = min(total_min / max(1, goal_min), 1.0)

c_top1, c_top2, c_top3, c_top4 = st.columns(4)
with c_top1:
    st.markdown(f"<div class='card'><b>오늘 누적</b><br><h3>{total_min}분</h3></div>", unsafe_allow_html=True)
with c_top2:
    st.markdown(f"<div class='card'><b>목표</b><br><h3>{goal_min}분</h3></div>", unsafe_allow_html=True)
with c_top3:
    st.markdown(f"<div class='card'><b>코인</b><br><h3>{coins}</h3></div>", unsafe_allow_html=True)
with c_top4:
    st.markdown(f"<div class='card'><b>스트릭</b><br><h3>{streak}일</h3></div>", unsafe_allow_html=True)

st.progress(progress)
if progress >= 1.0:
    st.success("목표 달성! +30코인 보너스 지급!")
    grant_coins(user_id, TODAY, base=0, bonus=30, reason="데일리 목표 달성 보너스")

# 배지(간단)
badges = []
if total_min >= 100: badges.append("첫 100분 달성")
if total_min >= 200: badges.append("200분 돌파")
if dt.datetime.now().hour <= 8 and total_min > 0: badges.append("아침 출발 배지")
if badges:
    st.markdown("획득 배지")
    st.write(" ".join([f"<span class='badge'>🏅 {b}</span>" for b in badges]), unsafe_allow_html=True)

# --------------------------------
# 포모도로 타이머
# --------------------------------
st.subheader("포모도로 타이머")
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

st.session_state.subject = st.selectbox("과목", ["국어", "수학", "영어", "탐구-사탐", "탐구-과탐", "한국사", "기타"], index=0)

t1, t2, t3 = st.columns(3)
with t1:
    if not st.session_state.timer_running and st.button("시작 ▶"):
        st.session_state.timer_running = True
        st.session_state.end_time = time.time() + st.session_state.preset * 60
        st.session_state.distractions = 0
with t2:
    if st.session_state.timer_running and st.button("일시정지 ⏸"):
        # 간단 중지 로직(실서비스에선 별도 상태/남은시간 저장 권장)
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

# 회고 폼
def reflection_form(duration_min):
    with st.form("reflection"):
        st.write(f"이번 세션: {st.session_state.subject} • {duration_min}분 • 방해 {st.session_state.distractions}회")
        mood = st.radio("기분", ["🙂 좋음", "😐 보통", "😣 낮음"], horizontal=True)
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
    duration = st.session_state.preset
    reflection_form(duration)

# --------------------------------
# 오답노트(다음 단계)
# --------------------------------
st.subheader("오답노트 입력 및 10분 요약 카드")
with st.expander("오답 입력하기"):
    colm1, colm2, colm3 = st.columns(3)
    with colm1:
        m_subject = st.selectbox("과목", ["국어", "수학", "영어", "탐구-사탐", "탐구-과탐", "한국사", "기타"])
    with colm2:
        q_type = st.selectbox("문항 유형", ["객관식", "주관식", "서술형", "기타"])
    with colm3:
        m_type = st.selectbox("실수 유형", ["개념", "계산", "시간", "부주의"])
    concept = st.text_input("관련 개념 태그(예: 극한의 정의, 등비수열 합)")
    memo = st.text_area("간단 메모/틀린 이유")
    if st.button("오답 저장"):
        add_mistake(user_id, TODAY, m_subject, q_type, m_type, concept, memo)
        st.success("오답이 저장되었어요! 다음 시험 대비에 큰 도움이 될 거예요.")

with st.expander("오늘 입력된 오답 보기"):
    with closing(get_conn()) as conn:
        df_m = pd.read_sql_query("SELECT subject, question_type, mistake_type, concept_tag, memo FROM mistakes WHERE user_id=? AND date=?",
                                 conn, params=(user_id, TODAY))
    if df_m.empty:
        st.info("아직 오답이 없어요.")
    else:
        st.dataframe(df_m.rename(columns={
            "subject":"과목", "question_type":"문항", "mistake_type":"실수", "concept_tag":"개념", "memo":"메모"
        }), use_container_width=True)

def make_10min_summary(user_id, for_date):
    # 간단 요약: 오늘 오답의 개념 태그/실수 빈도 상위
    with closing(get_conn()) as conn:
        df = pd.read_sql_query("SELECT subject, mistake_type, concept_tag FROM mistakes WHERE user_id=? AND date=?",
                               conn, params=(user_id, for_date))
    if df.empty:
        return "오늘 등록된 오답이 없어요. 핵심 개념 노트를 3장만 훑어보세요."
    concept_top = df["concept_tag"].fillna("").value_counts().head(3)
    mistake_top = df["mistake_type"].value_counts().head(2)
    lines = []
    lines.append("시험 전 10분 집중 요약")
    lines.append("- 오늘 오답에서 가장 많이 등장한 개념:")
    for k, v in concept_top.items():
        if k.strip():
            lines.append(f"  • {k} × {v}")
    lines.append("- 실수 유형 상위:")
    for k, v in mistake_top.items():
        lines.append(f"  • {k} × {v}")
    lines.append("- 액션 플랜(10분): 개념 3줄 요약 → 유사 2문제만 확인 → 계산 실수 체크리스트 점검")
    return "\n".join(lines)

if st.button("시험 전 10분 요약 카드 생성"):
    card = make_10min_summary(user_id, TODAY)
    st.code(card, language="text")

# --------------------------------
# 길드 랭킹
# --------------------------------
st.subheader("길드 랭킹(최근 7일)")
my_gid, my_gname = get_user_guild(user_id)
colg1, colg2 = st.columns(2)
with colg1:
    st.markdown(f"<div class='card'><b>내 길드</b><br>{my_gname if my_gname else '길드 미참여'}</div>", unsafe_allow_html=True)
with colg2:
    target = "내 길드" if my_gid else "전체"
    st.markdown(f"<div class='card'><b>랭킹 범위</b><br>{target}</div>", unsafe_allow_html=True)

rank_rows = get_guild_rankings(my_gid if my_gid else None)
if rank_rows:
    rank_df = pd.DataFrame(rank_rows, columns=["닉네임", "최근 7일(분)"])
    st.table(rank_df)
else:
    st.info("랭킹 데이터를 불러오는 중이에요. 길드에 참여하면 랭킹이 표시돼요!")

# --------------------------------
# 오늘의 기록 & 주간 통계
# --------------------------------
colrec1, colrec2 = st.columns(2)
with colrec1:
    st.subheader("오늘의 기록")
    if df_today is not None and not df_today.empty:
        st.dataframe(df_today[["subject", "duration_min", "distractions", "mood", "energy", "difficulty"]]
            .rename(columns={
                "subject":"과목", "duration_min":"분", "distractions":"방해",
                "mood":"기분", "energy":"에너지", "difficulty":"난이도"
            }), use_container_width=True)
    else:
        st.info("아직 기록이 없어요. 짧게라도 한 세션을 시작해 볼까요?")

with colrec2:
    st.subheader("주간 통계")
    weekly = get_weekly(user_id)
    if weekly is not None and not weekly.empty:
        chart_df = weekly.set_index("date")
        st.bar_chart(chart_df)
    else:
        st.write("이번 주 데이터가 곧 채워질 거예요.")

# --------------------------------
# 주간 성과 리포트(이메일 미리보기)
# --------------------------------
st.subheader("주간 성과 리포트(이메일 미리보기)")
def build_weekly_email_preview(user_id):
    with closing(get_conn()) as conn:
        # 최근 7일 합계
        df = pd.read_sql_query("""SELECT date, SUM(duration_min) AS total_min
                                  FROM sessions WHERE user_id=?
                                  GROUP BY date ORDER BY date ASC""",
                               conn, params=(user_id,))
        df = df.tail(7) if not df.empty else df
        total7 = int(df["total_min"].sum()) if not df.empty else 0
        days = df["date"].tolist() if not df.empty else []
        # 감정-성과 간단 상관: 평균 에너지
        df_e = pd.read_sql_query("""SELECT AVG(energy) as avg_energy FROM sessions WHERE user_id=? 
                                    AND date >= ?""",
                                 conn, params=(user_id, (dt.date.today()-dt.timedelta(days=6)).isoformat()))
        avg_energy = round(float(df_e["avg_energy"].iloc[0]), 2) if not df_e.empty and df_e["avg_energy"].iloc[0] else None

    lines = []
    lines.append("[수능 러닝 메이트+] 주간 성과 리포트")
    lines.append(f"- 최근 7일 총 집중 시간: {total7}분")
    if days:
        lines.append(f"- 활동한 날짜: {', '.join(days)}")
    if avg_energy:
        lines.append(f"- 평균 에너지 지수: {avg_energy}/5")
    # 간단 피드백 문구
    if total7 >= 900:
        lines.append("- 피드백: 대단해요! 하루 평균 2시간 이상 탄탄했어요. 현재 루틴을 유지해볼까요?")
    elif total7 >= 420:
        lines.append("- 피드백: 중간 페이스 좋아요. 주 1회 50분 롱세션을 추가해 보세요.")
    else:
        lines.append("- 피드백: 시작이 반이에요. 25분 초집중 1세션부터 매일 쌓아가요!")
    lines.append("- 다음 주 추천 미션: 방해 요소 1회 이하 세션 3회 달성하기")
    return "\n".join(lines)

if st.button("리포트 미리보기 생성"):
    preview = build_weekly_email_preview(user_id)
    st.code(preview, language="text")

# 작은 응원
st.markdown("<div class='card kudos'>오늘의 한 줄 칭찬: 짧게라도 꾸준히가 정답이에요. 지금의 한 번이 내일을 바꿔요! 💪</div>", unsafe_allow_html=True)
