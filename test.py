import streamlit as st
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date

# =========================
# 기본 설정
# =========================
st.set_page_config(page_title="공부 관리 사이트", page_icon="⏱️", layout="wide")

# 밝고 귀엽고 화려한 커스텀 테마(CSS 주입) - 라임색 배제
THEME_COLORS = {
    "primary": "#FF6FA9",   # 딸기 핑크
    "accent": "#A78BFA",    # 라일락
    "mint": "#5DE2C2",      # 민트(라임 아님)
    "sky": "#BDE0FE",       # 라이트 스카이
    "cream": "#FFF8E7",     # 크림
    "bg_light": "#FFF0F6",  # 핑크 톤 배경
    "text": "#333333"
}

def inject_theme(theme=None):
    t = THEME_COLORS if theme is None else theme
    st.markdown(f"""
    <style>
    :root {{
        --primary: {t['primary']};
        --accent: {t['accent']};
        --mint: {t['mint']};
        --sky: {t['sky']};
        --cream: {t['cream']};
        --bg-light: {t['bg_light']};
        --text: {t['text']};
    }}
    .main {{
        background: linear-gradient(180deg, var(--bg-light) 0%, #FFFFFF 40%);
    }}
    .stButton>button {{
        background-color: var(--primary);
        color: white;
        border-radius: 12px;
        border: 0;
        padding: 0.5rem 1rem;
        box-shadow: 0 6px 18px rgba(255,111,169,0.35);
    }}
    .stButton>button:hover {{
        filter: brightness(0.95);
        transform: translateY(-1px);
    }}
    .metric-card {{
        background: var(--cream);
        border-radius: 16px;
        padding: 14px;
        border: 2px solid #FFE7F1;
    }}
    .chip {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        background: #F5F3FF;
        border: 1px solid var(--accent);
        color: #4B3FAE;
        font-size: 12px;
        margin-right: 6px;
    }}
    .store-card {{
        background: #FFFFFF;
        border: 2px solid #FFE7F1;
        border-radius: 16px;
        padding: 12px;
        box-shadow: 0 8px 24px rgba(167,139,250,0.12);
    }}
    .calendar-cell {{
        height: 64px;
        border-radius: 10px;
        display: flex;
        align-items: center; justify-content: center;
        font-weight: 600;
    }}
    .rank-highlight {{
        background: #FFF4FE;
        border: 2px solid #FFD5EF;
        border-radius: 12px;
        padding: 8px 12px;
    }}
    </style>
    """, unsafe_allow_html=True)

inject_theme()

# =========================
# 세션 상태 초기화
# =========================
def init_state():
    if "subjects" not in st.session_state:
        st.session_state.subjects = ["국어", "수학", "영어"]
    if "sessions" not in st.session_state:
        st.session_state.sessions = []  # {subject, start, end, duration_min, note, coins}
    if "running" not in st.session_state:
        st.session_state.running = False
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "elapsed_sec" not in st.session_state:
        st.session_state.elapsed_sec = 0
    if "selected_subject" not in st.session_state:
        st.session_state.selected_subject = st.session_state.subjects[0]
    if "daily_goal_min" not in st.session_state:
        st.session_state.daily_goal_min = 180  # 기본 목표: 180분
    if "coins" not in st.session_state:
        st.session_state.coins = 0
    if "shop_items" not in st.session_state:
        st.session_state.shop_items = [
            {"id":"theme_pink","type":"theme","name":"딸기우유 핑크","price":120,"payload":{"primary":"#FF6FA9","bg":"#FFF0F6"}},
            {"id":"theme_lilac","type":"theme","name":"라벤더 밤하늘","price":150,"payload":{"primary":"#A78BFA","bg":"#F5F3FF"}},
            {"id":"theme_mint","type":"theme","name":"민트 버블","price":150,"payload":{"primary":"#5DE2C2","bg":"#EEFFFA"}},
            {"id":"badge_morning","type":"badge","name":"아침형 영웅","price":80,"payload":{"icon":"🌅"}},
            {"id":"badge_weekend","type":"badge","name":"주말 챌린저","price":90,"payload":{"icon":"🛡️"}},
            {"id":"sound_bell","type":"sound","name":"포커스 벨","price":60,"payload":{"file":"bell.mp3"}},
            {"id":"emoji_pack_study","type":"emoji","name":"스터디 이모지 팩","price":70,"payload":{"icons":["📘","📐","🧪","🎨"]}}
        ]
    if "inventory" not in st.session_state:
        st.session_state.inventory = set()
    if "equipped" not in st.session_state:
        st.session_state.equipped = {"theme":None, "sound":None, "badge":None, "emoji":None}
    if "nickname" not in st.session_state:
        st.session_state.nickname = "사용자"
    if "pomo_mode" not in st.session_state:
        st.session_state.pomo_mode = False
    if "pomo_focus" not in st.session_state:
        st.session_state.pomo_focus = 25  # 분
    if "pomo_break" not in st.session_state:
        st.session_state.pomo_break = 5
    if "pomo_is_break" not in st.session_state:
        st.session_state.pomo_is_break = False
    if "pomo_remaining" not in st.session_state:
        st.session_state.pomo_remaining = st.session_state.pomo_focus * 60
    if "leaderboard_dummy" not in st.session_state:
        # 로컬 더미 사용자들
        st.session_state.leaderboard_dummy = [
            {"user":"토끼","total_min":720,"subject":"수학","streak":4},
            {"user":"별빛","total_min":640,"subject":"영어","streak":6},
            {"user":"파도","total_min":510,"subject":"국어","streak":2},
        ]

init_state()

# =========================
# 유틸 함수
# =========================
def get_sessions_df():
    if not st.session_state.sessions:
        return pd.DataFrame(columns=["subject","start","end","duration_min","note","coins"])
    return pd.DataFrame(st.session_state.sessions)

def format_hms(sec):
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def build_daily_stats(df_sessions, daily_goal_min=None):
    if daily_goal_min is None:
        daily_goal_min = st.session_state.daily_goal_min
    if df_sessions.empty:
        return pd.DataFrame(columns=["date","total_min","goal_met"])
    df = df_sessions.copy()
    df["date"] = pd.to_datetime(df["start"]).dt.date
    grp = df.groupby("date")["duration_min"].sum().reset_index()
    grp.rename(columns={"duration_min":"total_min"}, inplace=True)
    grp["goal_met"] = grp["total_min"] >= daily_goal_min
    return grp

def calc_streak(daily_df):
    if daily_df.empty:
        return 0
    # 날짜 연속성 기반 스트릭 계산(최근부터 역순)
    d = daily_df.copy().sort_values("date", ascending=False)
    today = date.today()
    streak = 0
    expected = today
    date_set = {row for row in d["date"].tolist()}
    while expected in date_set:
        row = d[d["date"] == expected]
        if not row.empty and bool(row["goal_met"].iloc[0]):
            streak += 1
            expected = expected - timedelta(days=1)
        else:
            break
    return streak

def color_bucket(mins):
    bins = [0, 30, 60, 120, 180, 240, 99999]
    idx = np.digitize([mins], bins)[0]  # 1~6
    palette = {
        1: "#F8E7F1",  # 매우 옅은 핑크
        2: "#FBD1E6",
        3: "#F8A8CF",
        4: "#F17CB4",
        5: "#E85A9B",
        6: "#D63D83"
    }
    return palette.get(idx, "#F8E7F1")

def ensure_coin_reward(duration_min):
    # 1분 = 1코인 + 목표 달성 보너스(세션 종료 시점에 일일 합계 기준)
    st.session_state.coins += duration_min

def update_theme_by_equipped():
    eq = st.session_state.equipped.get("theme")
    if not eq:
        return
    item = next((i for i in st.session_state.shop_items if i["id"] == eq), None)
    if item and item["type"] == "theme":
        primary = item["payload"].get("primary", THEME_COLORS["primary"])
        bg = item["payload"].get("bg", THEME_COLORS["bg_light"])
        custom = dict(THEME_COLORS)
        custom["primary"] = primary
        custom["bg_light"] = bg
        inject_theme(custom)

def buy_item(item_id):
    item = next(i for i in st.session_state.shop_items if i["id"] == item_id)
    if item_id in st.session_state.inventory:
        st.warning("이미 보유 중이에요.")
        return
    if st.session_state.coins < item["price"]:
        st.error("코인이 부족해요.")
        return
    st.session_state.coins -= item["price"]
    st.session_state.inventory.add(item_id)
    st.success(f"{item['name']}을(를) 구매했어요! ✨")

def equip_item(item_id):
    item = next(i for i in st.session_state.shop_items if i["id"] == item_id)
    st.session_state.equipped[item["type"]] = item_id
    st.success(f"{item['name']} 적용 완료! 🎉")
    if item["type"] == "theme":
        update_theme_by_equipped()

def current_week_range():
    today = datetime.now().date()
    start = today - timedelta(days=today.weekday())  # 월요일 시작
    end = start + timedelta(days=6)
    return start, end

def filter_week(df, start, end):
    if df.empty:
        return df
    df2 = df.copy()
    df2["d"] = pd.to_datetime(df2["start"]).dt.date
    return df2[(df2["d"] >= start) & (df2["d"] <= end)]

# =========================
# 상단 헤더
# =========================
left, right = st.columns([1, 2])
with left:
    st.markdown(f"## ⏱️ 공부 관리 사이트")
    st.caption("밝고 귀엽고 화려한 공부 타이머, 캘린더, 랭킹, 코인 상점")
with right:
    with st.container():
        df_all = get_sessions_df()
        today_total = 0
        if not df_all.empty:
            tdf = df_all[pd.to_datetime(df_all["start"]).dt.date == date.today()]
            today_total = int(tdf["duration_min"].sum())
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("오늘 학습", f"{today_total}분")
        c2.metric("일일 목표", f"{st.session_state.daily_goal_min}분")
        st.metric(label="보유 코인", value=f"{st.session_state.coins}💰")
        # 스트릭
        daily_df = build_daily_stats(df_all)
        streak_val = calc_streak(daily_df)
        c4.metric("연속 달성", f"{streak_val}일 🔥")
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# =========================
# 탭: 타이머 | 캘린더 | 랭킹 | 상점 | 설정
# =========================
tab_timer, tab_calendar, tab_rank, tab_shop, tab_settings = st.tabs(["타이머", "캘린더", "랭킹", "상점", "설정"])

# =========================
# 타이머 탭
# =========================
with tab_timer:
    st.markdown("### 타이머")
    colA, colB = st.columns([2, 1])

    with colA:
        st.session_state.selected_subject = st.selectbox("과목을 선택하세요", options=st.session_state.subjects, index=st.session_state.subjects.index(st.session_state.selected_subject) if st.session_state.selected_subject in st.session_state.subjects else 0)
        note = st.text_input("세션 메모(선택)")
        st.toggle("포모도로 모드", key="pomo_mode")
        if st.session_state.pomo_mode:
            col_pf, col_pb = st.columns(2)
            st.number_input("집중(분)", min_value=5, max_value=120, value=st.session_state.pomo_focus, step=5, key="pomo_focus")
            st.number_input("휴식(분)", min_value=3, max_value=60, value=st.session_state.pomo_break, step=1, key="pomo_break")
            if st.button("사이클 초기화"):
                st.session_state.pomo_is_break = False
                st.session_state.pomo_remaining = st.session_state.pomo_focus * 60
                st.success("포모도로 타이머가 초기화되었어요.")
        timer_placeholder = st.empty()

        c1, c2, c3 = st.columns(3)
        start_btn = c1.button("시작 ▶")
        pause_btn = c2.button("일시정지 ⏸️")
        stop_btn  = c3.button("종료 ⏹️")

        # 타이머 로직
        if start_btn and not st.session_state.running:
            st.session_state.running = True
            if st.session_state.start_time is None:
                st.session_state.start_time = time.time() - st.session_state.elapsed_sec
            st.toast("집중 시작! 힘내세요! 💪", icon="✅")

        if pause_btn and st.session_state.running:
            st.session_state.running = False
            st.session_state.elapsed_sec = int(time.time() - st.session_state.start_time)

        if stop_btn:
            if st.session_state.start_time is not None:
                end_time = time.time() if st.session_state.running else (st.session_state.start_time + st.session_state.elapsed_sec)
                duration_sec = int(end_time - st.session_state.start_time)
                duration_min = max(1, duration_sec // 60)
                coins = duration_min  # 기본 규칙
                # 세션 저장
                st.session_state.sessions.append({
                    "subject": st.session_state.selected_subject,
                    "start": datetime.fromtimestamp(st.session_state.start_time).isoformat(timespec="seconds"),
                    "end": datetime.fromtimestamp(end_time).isoformat(timespec="seconds"),
                    "duration_min": duration_min,
                    "note": note,
                    "coins": coins
                })
                ensure_coin_reward(duration_min)

                # 목표 달성 보너스(세션 저장 후 오늘 합계 검사)
                df_tmp = get_sessions_df()
                tdf = df_tmp[pd.to_datetime(df_tmp["start"]).dt.date == date.today()]
                if int(tdf["duration_min"].sum()) >= st.session_state.daily_goal_min:
                    # 하루 한번만 보너스 주도록 플래그
                    if "daily_bonus_date" not in st.session_state or st.session_state.daily_bonus_date != date.today():
                        st.session_state.coins += 50
                        st.session_state.daily_bonus_date = date.today()
                        st.balloons()
                        st.success("오늘 목표 달성! 보너스 50코인 지급 🎊")

            # 리셋
            st.session_state.running = False
            st.session_state.start_time = None
            st.session_state.elapsed_sec = 0

        # 표시/갱신
        if st.session_state.running:
            if st.session_state.pomo_mode:
                # 포모도로: 남은 시간 카운트다운
                elapsed_now = int(time.time() - st.session_state.start_time)
                # 일반 경과도 업데이트
                display_sec = elapsed_now
                # 남은 시간 처리
                if "last_tick" not in st.session_state:
                    st.session_state.last_tick = time.time()
                # 틱 처리
                now = time.time()
                delta = now - st.session_state.last_tick
                if delta >= 1:
                    dec = int(delta)
                    st.session_state.pomo_remaining = max(0, st.session_state.pomo_remaining - dec)
                    st.session_state.last_tick = now
                # 사이클 전환
                if st.session_state.pomo_remaining == 0:
                    st.session_state.pomo_is_break = not st.session_state.pomo_is_break
                    if st.session_state.pomo_is_break:
                        st.session_state.pomo_remaining = st.session_state.pomo_break * 60
                        st.toast("휴식 시간이에요. 눈과 몸을 풀어주세요. 🌿", icon="💤")
                    else:
                        st.session_state.pomo_remaining = st.session_state.pomo_focus * 60
                        st.toast("다시 집중 시작! 할 수 있어요! ✨", icon="💪")
                timer_text = f"{'휴식' if st.session_state.pomo_is_break else '집중'} {format_hms(st.session_state.pomo_remaining)}"
                timer_placeholder.markdown(f"#### ⌛ {timer_text}")
            else:
                with st.spinner("타이머 작동 중..."):
                    time.sleep(1)
                elapsed = int(time.time() - st.session_state.start_time)
                timer_placeholder.markdown(f"#### ⌛ {format_hms(elapsed)}")
        else:
            timer_placeholder.markdown(f"#### ⌛ {format_hms(st.session_state.elapsed_sec)}")

        # 기록/통계
        st.markdown("#### 최근 기록")
        df_view = get_sessions_df()
        if df_view.empty:
            st.info("아직 기록이 없어요. 타이머를 시작해보세요!")
        else:
            st.dataframe(df_view.sort_values("start", ascending=False), use_container_width=True, height=280)

    with colB:
        st.markdown("#### 빠른 정보")
        df_all = get_sessions_df()
        week_start, week_end = current_week_range()
        week_df = filter_week(df_all, week_start, week_end)
        week_min = int(week_df["duration_min"].sum()) if not week_df.empty else 0
        st.metric("이번 주 합계", f"{week_min}분")
        if not df_all.empty:
            by_subject = df_all.groupby("subject")["duration_min"].sum().sort_values(ascending=False)
            top_subject = by_subject.index[0]
            st.write(f"가장 많이 공부한 과목: {top_subject}")
        st.write("")
        st.markdown(f'<span class="chip">집중 모드</span> <span class="chip">목표 보너스</span> <span class="chip">코인 적립</span>', unsafe_allow_html=True)

# =========================
# 캘린더 탭
# =========================
with tab_calendar:
    st.markdown("### 캘린더(월별 열 지도)")
    df_all = get_sessions_df()
    daily_df = build_daily_stats(df_all)

    # 월 선택
    today = date.today()
    sel_month = st.date_input("월을 선택하세요", value=date(today.year, today.month, 1))
    month_start = date(sel_month.year, sel_month.month, 1)
    next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    # 해당 월 데이터
    days = []
    d = month_start
    while d <= month_end:
        days.append(d)
        d += timedelta(days=1)

    # 요일 헤더
    st.write("일  월  화  수  목  금  토")
    # 앞쪽 공백(해당 월 시작 요일만큼)
    first_wday = month_start.weekday()  # 월=0 ... 일=6
    # 우리 UI는 일요일부터라서 보정
    # Python weekday(월0) -> (일0)로 맞춤
    start_shift = (first_wday + 1) % 7

    # 그리드 출력
    grid = []
    week = [None]*start_shift
    for dt_ in days:
        if len(week) == 7:
            grid.append(week)
            week = []
        week.append(dt_)
    if week:
        while len(week) < 7:
            week.append(None)
        grid.append(week)

    # 렌더
    for wk in grid:
        c = st.columns(7)
        for i, d_ in enumerate(wk):
            with c[i]:
                if d_ is None:
                    st.write("")
                else:
                    row = daily_df[daily_df["date"] == d_]
                    total_min = int(row["total_min"].iloc[0]) if not row.empty else 0
                    goal_met = bool(row["goal_met"].iloc[0]) if not row.empty else False
                    color = color_bucket(total_min)
                    icon = "🎉" if goal_met else ""
                    st.markdown(
                        f'<div class="calendar-cell" style="background:{color}; border:1px solid #FFD5EF;">{d_.day}<br/>{total_min}분 {icon}</div>',
                        unsafe_allow_html=True
                    )
    st.markdown("---")

    # 날짜 상세
    sel_date = st.date_input("날짜 상세 보기", value=today)
    if not df_all.empty:
        day_df = df_all[pd.to_datetime(df_all["start"]).dt.date == sel_date]
        if day_df.empty:
            st.info("선택한 날짜에는 기록이 없어요.")
        else:
            st.markdown(f"#### {sel_date} 세션 목록")
            st.dataframe(day_df.sort_values("start"), use_container_width=True, height=240)
            pie = day_df.groupby("subject")["duration_min"].sum().reset_index()
            st.bar_chart(pie.set_index("subject"))

# =========================
# 랭킹 탭
# =========================
with tab_rank:
    st.markdown("### 랭킹(주간)")
    df_all = get_sessions_df()
    week_start, week_end = current_week_range()
    my_week_df = filter_week(df_all, week_start, week_end)
    my_total = int(my_week_df["duration_min"].sum()) if not my_week_df.empty else 0
    my_streak = calc_streak(build_daily_stats(df_all))

    # 더미와 합쳐 순위 구성
    lb = st.session_state.leaderboard_dummy.copy()
    lb.append({"user": st.session_state.nickname, "total_min": my_total, "subject":"종합", "streak": my_streak})
    ldf = pd.DataFrame(lb)
    ldf = ldf.sort_values(["total_min","streak"], ascending=[False, False]).reset_index(drop=True)
    ldf["rank"] = ldf.index + 1

    # 상단 내 정보
    me = ldf[ldf["user"] == st.session_state.nickname].iloc[0]
    st.markdown(f'<div class="rank-highlight">🏆 내 순위: {int(me["rank"])}위 | 이번 주: {int(me["total_min"])}분 | 스트릭: {int(me["streak"])}일</div>', unsafe_allow_html=True)

    # 전체 랭킹 표와 그래프
    st.markdown("#### 전체 순위")
    st.dataframe(ldf[["rank","user","total_min","streak"]], use_container_width=True, height=280)
    st.markdown("#### 시각화(분)")
    st.bar_chart(ldf.set_index("user")["total_min"])

    # 과목별(내 기록 기준)
    st.markdown("#### 과목별 내 주간 기록")
    if my_week_df.empty:
        st.info("이번 주 기록이 아직 없어요. 지금 바로 시작해볼까요?")
    else:
        sb = my_week_df.groupby("subject")["duration_min"].sum().sort_values(ascending=False)
        st.bar_chart(sb)

# =========================
# 상점 탭
# =========================
with tab_shop:
    st.markdown("### 코인 상점 ✨")
    top1, top2 = st.columns([1,1])
    with top1:
        st.metric("보유 코인", f"{st.session_state.coins}💰")
    with top2:
        eq = st.session_state.equipped
        eq_theme = eq.get("theme") or "-"
        eq_badge = eq.get("badge") or "-"
        eq_sound = eq.get("sound") or "-"
        eq_emoji = eq.get("emoji") or "-"
        st.write(f"적용 중 | 테마: {eq_theme}, 배지: {eq_badge}, 사운드: {eq_sound}, 이모지: {eq_emoji}")

    tabs_shop = st.tabs(["추천", "테마", "배지", "사운드", "이모지"])
    def render_items(filter_type=None):
        items = st.session_state.shop_items if filter_type is None else [i for i in st.session_state.shop_items if i["type"] == filter_type]
        cols = st.columns(3)
        for idx, it in enumerate(items):
            with cols[idx % 3]:
                st.markdown('<div class="store-card">', unsafe_allow_html=True)
                st.write(f"이름: {it['name']}")
                st.write(f"가격: {it['price']} 코인")
                owned = it["id"] in st.session_state.inventory
                if it["type"] == "theme":
                    preview_primary = it["payload"].get("primary", THEME_COLORS["primary"])
                    preview_bg = it["payload"].get("bg", THEME_COLORS["bg_light"])
                    st.markdown(f'<div style="height:40px; border-radius:8px; background: linear-gradient(90deg, {preview_bg}, {preview_primary}); border:1px solid #FFD5EF;"></div>', unsafe_allow_html=True)
                if owned:
                    st.success("보유 중")
                    if st.button(f"적용하기 - {it['id']}"):
                        equip_item(it["id"])
                else:
                    if st.button(f"구매하기 - {it['id']}"):
                        buy_item(it["id"])
                st.markdown('</div>', unsafe_allow_html=True)

    with tabs_shop[0]:
        render_items()
    with tabs_shop[1]:
        render_items("theme")
    with tabs_shop[2]:
        render_items("badge")
    with tabs_shop[3]:
        render_items("sound")
    with tabs_shop[4]:
        render_items("emoji")

# =========================
# 설정 탭
# =========================
with tab_settings:
    st.markdown("### 설정")
    st.text_input("닉네임", key="nickname")
    st.number_input("일일 목표(분)", min_value=30, max_value=600, step=10, key="daily_goal_min")
    st.write("과목 관리")
    col_add1, col_add2 = st.columns([3,1])
    with col_add1:
        new_subject = st.text_input("새 과목 이름", key="new_subject")
    with col_add2:
        if st.button("과목 추가"):
            ns = st.session_state.get("new_subject","").strip()
            if ns and ns not in st.session_state.subjects:
                st.session_state.subjects.append(ns)
                st.success(f"과목 '{ns}' 추가 완료!")
            else:
                st.warning("유효하지 않거나 이미 존재하는 과목입니다.")

    # 데이터 내보내기/불러오기
    st.markdown("---")
    st.markdown("#### 데이터 관리")
    col_exp, col_imp = st.columns(2)
    with col_exp:
        if st.button("세션 CSV로 내보내기"):
            df = get_sessions_df()
            if df.empty:
                st.info("내보낼 세션 데이터가 없어요.")
            else:
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("CSV 다운로드", data=csv, file_name="study_sessions.csv", mime="text/csv")
    with col_imp:
        up = st.file_uploader("세션 CSV 불러오기", type=["csv"])
        if up is not None:
            df_new = pd.read_csv(up)
            required_cols = {"subject","start","end","duration_min","note","coins"}
            if required_cols.issubset(set(df_new.columns)):
                # 기존 데이터 보존 + 합치기
                old = get_sessions_df()
                merged = pd.concat([old, df_new], ignore_index=True)
                # 메모리 상태 갱신
                st.session_state.sessions = merged.to_dict(orient="records")
                st.success("불러오기가 완료되었어요.")
            else:
                st.error("컬럼이 맞지 않아요. 템플릿을 사용해주세요.")

    st.markdown("---")
    st.caption("테마와 배지는 상점에서 구매/적용할 수 있어요. 라임색은 사용하지 않았습니다.")

# 적용된 테마 반영
update_theme_by_equipped()
