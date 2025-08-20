import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="공부 타이머", page_icon="⏱️", layout="centered")

# 초기 상태
if "subjects" not in st.session_state:
    st.session_state.subjects = ["국어", "수학", "영어"]
if "sessions" not in st.session_state:
    st.session_state.sessions = []  # list of dict
if "running" not in st.session_state:
    st.session_state.running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "elapsed_sec" not in st.session_state:
    st.session_state.elapsed_sec = 0
if "selected_subject" not in st.session_state:
    st.session_state.selected_subject = st.session_state.subjects[0]

st.title("공부 타이머 ⏱️")
st.caption("공부 시작하고 시간을 기록하세요. 목표를 채우면 보상 코인도!")

# 상단: 오늘 통계
def get_df():
    if not st.session_state.sessions:
        return pd.DataFrame(columns=["subject","start","end","duration_min","note","coins"])
    return pd.DataFrame(st.session_state.sessions)

df = get_df()
today = pd.Timestamp.now().normalize()
today_df = df[(pd.to_datetime(df["start"]) >= today)]
today_minutes = int(today_df["duration_min"].sum()) if not today_df.empty else 0
st.metric("오늘 학습 시간", f"{today_minutes}분")

# 과목 선택
st.session_state.selected_subject = st.selectbox("과목을 선택하세요", options=st.session_state.subjects)

# 메모
note = st.text_input("세션 메모(선택)")

# 타이머 표시
def format_time(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

timer_placeholder = st.empty()

col1, col2, col3 = st.columns(3)
start_btn = col1.button("시작 ▶")
pause_btn = col2.button("일시정지 ⏸️")
stop_btn  = col3.button("종료 ⏹️")

# 타이머 로직
if start_btn and not st.session_state.running:
    st.session_state.running = True
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time() - st.session_state.elapsed_sec

if pause_btn and st.session_state.running:
    st.session_state.running = False
    st.session_state.elapsed_sec = int(time.time() - st.session_state.start_time)

if stop_btn:
    if st.session_state.start_time is not None:
        end_time = time.time() if st.session_state.running else (st.session_state.start_time + st.session_state.elapsed_sec)
        duration_sec = int(end_time - st.session_state.start_time)
        duration_min = max(1, duration_sec // 60)  # 1분 미만 올림 처리
        coins = duration_min  # 1분=1코인
        st.session_state.sessions.append({
            "subject": st.session_state.selected_subject,
            "start": datetime.fromtimestamp(st.session_state.start_time).isoformat(timespec="seconds"),
            "end": datetime.fromtimestamp(end_time).isoformat(timespec="seconds"),
            "duration_min": duration_min,
            "note": note,
            "coins": coins
        })
    # 리셋
    st.session_state.running = False
    st.session_state.start_time = None
    st.session_state.elapsed_sec = 0

# 표시/갱신
if st.session_state.running:
    st.toast("집중 중이에요! 힘내세요! EMOJI_0", icon="✅")
    # 1초 주기로 갱신
    with st.spinner("타이머 작동 중..."):
        time.sleep(1)
    elapsed = int(time.time() - st.session_state.start_time)
else:
    elapsed = st.session_state.elapsed_sec

timer_placeholder.markdown(f"### ⌛ {format_time(elapsed)}")

# 기록/통계
st.subheader("최근 기록")
df = get_df()
if df.empty:
    st.info("아직 기록이 없어요. 타이머를 시작해보세요!")
else:
    st.dataframe(df.sort_values("start", ascending=False), use_container_width=True)
    weekly = df[pd.to_datetime(df["start"]) >= (pd.Timestamp.now() - pd.Timedelta(days=7))]
    st.write(f"최근 7일 합계: {int(weekly['duration_min'].sum())}분, 코인: {int(weekly['coins'].sum())}")
