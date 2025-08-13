import streamlit as st

st.set_page_config(page_title="MBTI 인사이트: 컬러 테마", page_icon="🌈", layout="wide")

MBTI_EMOJI = {
    "INTJ":"🧠✨","INTP":"🧩🔍","ENTJ":"🧭🚀","ENTP":"💡🌀",
    "INFJ":"🌙🕊️","INFP":"🎨🌿","ENFJ":"🌟🤝","ENFP":"🎉🌈",
    "ISTJ":"📘✅","ISFJ":"🫶🌸","ESTJ":"📊🏗️","ESFJ":"😊🎀",
    "ISTP":"🛠️⚡","ISFP":"🖌️🍃","ESTP":"🏁🔥","ESFP":"🎤✨"
}
MBTIS = list(MBTI_EMOJI.keys())

# MBTI별 메인/보조 컬러(라임 제거)
MBTI_COLORS = {
    "INTJ": {"main":"#B39DFF", "sub":"#66E0FF"},
    "INTP": {"main":"#66E0FF", "sub":"#B39DFF"},
    "ENTJ": {"main":"#FF66B3", "sub":"#66E0FF"},
    "ENTP": {"main":"#FFD166", "sub":"#FF66B3"},
    "INFJ": {"main":"#8C9EFF", "sub":"#B39DFF"},
    "INFP": {"main":"#FFB3A7", "sub":"#66E0FF"},
    "ENFJ": {"main":"#FF7FA3", "sub":"#B39DFF"},
    "ENFP": {"main":"#FF66B3", "sub":"#66E0FF"},
    "ISTJ": {"main":"#6B7A90", "sub":"#B39DFF"},
    "ISFJ": {"main":"#FF9CCF", "sub":"#66E0FF"},
    "ESTJ": {"main":"#4FB3FF", "sub":"#FFB3A7"},
    "ESFJ": {"main":"#FFA7D1", "sub":"#66E0FF"},
    "ISTP": {"main":"#7AA7C7", "sub":"#B39DFF"},
    "ISFP": {"main":"#7EE7D5", "sub":"#FFB3A7"},
    "ESTP": {"main":"#FF9A66", "sub":"#66E0FF"},
    "ESFP": {"main":"#FF5CA8", "sub":"#FFD166"},
}

# 데모 데이터(필요 시 기존 DATA로 교체)
DATA = {
    "ENFP": {
        "요약": "활동가형. 상상력과 사람 중심 에너지로 변화를 이끕니다.",
        "특징": ["새로움/자율성 선호", "다양한 아이디어 연결", "팀 분위기 메이커"],
        "추천직업": ["브랜딩/마케팅", "콘텐츠 기획", "교육/코칭", "창업"],
        "관계팁": ["약속을 줄이고 핵심 3개에 집중", "아이디어는 실행 파트너와 매칭"],
        "공부팁": ["테마 주간 운영", "보상·챌린지로 동기 유지", "공개 약속으로 마감 관리"]
    }
}
DEFAULT = {
    "요약": "해당 유형의 자세한 데이터는 곧 추가됩니다!",
    "특징": ["호기심이 많고 성장 지향적", "상황에 따른 유연성 발휘"],
    "추천직업": ["관심 분야 기반 탐색 추천", "강점-가치 일치 직무 우선"],
    "관계팁": ["명확한 의사소통", "경계 존중과 피드백 교환"],
    "공부팁": ["작은 승리 루프", "주간 리뷰로 개선 주기"]
}

# 공통 CSS(컬러 변수는 런타임에 주입)
BASE_CSS = """
<style>
:root{
  --pink:#FF66B3; --sky:#66E0FF; --lilac:#B39DFF; --lemon:#FFD166; --peach:#FFB3A7; --mint:#7EE7D5;
}
html, body, [class*="main"] {
  font-family: "Pretendard","NanumSquareRound","Nunito","Apple SD Gothic Neo",sans-serif;
}
.big-title {
  background: linear-gradient(90deg, var(--theme-main), var(--theme-sub));
  -webkit-background-clip: text; background-clip: text; color: transparent;
  font-weight: 900; font-size: 44px; text-shadow: 0 0 18px rgba(0,0,0,0.08);
}
.mbti-badge {
  display:inline-flex; align-items:center; gap:8px;
  padding:10px 14px; border-radius:14px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--theme-main) 70%, white), color-mix(in srgb, var(--theme-sub) 70%, white));
  border:1px solid rgba(0,0,0,0.06);
  font-weight:800; color:#222;
  box-shadow: 0 6px 14px rgba(0,0,0,0.08);
}
.section-title {
  font-size: 22px; font-weight: 900; color:#222;
  text-shadow: 0 2px 8px color-mix(in srgb, var(--theme-sub) 40%, transparent);
  margin-top: 8px; margin-bottom: 8px;
}
.gradient-card {
  padding:18px 20px; border-radius:18px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--theme-main) 18%, white), color-mix(in srgb, var(--theme-sub) 16%, white));
  border:1px solid rgba(0,0,0,0.05);
  box-shadow: 0 10px 24px rgba(0,0,0,0.10);
  backdrop-filter: blur(6px);
}
.tag {
  display:inline-block; padding:6px 10px; border-radius:999px;
  background: linear-gradient(90deg, color-mix(in srgb, var(--theme-sub) 60%, white), color-mix(in srgb, var(--theme-main) 60%, white));
  font-weight: 700; color:#222; margin-right:8px; margin-bottom:8px; border: 1px solid rgba(0,0,0,0.03);
}
.cute-button button {
  background: linear-gradient(90deg, var(--theme-main), var(--theme-sub)) !important;
  color: #222 !important; border: none !important; font-weight: 800 !important;
  box-shadow: 0 8px 18px rgba(0,0,0,0.12) !important;
}
.cute-button button:hover { filter: brightness(1.05); transform: translateY(-1px); }
hr { border: none; height:1px; background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--theme-main) 40%, white), transparent); }
</style>
"""

def inject_theme(main, sub):
    st.markdown(BASE_CSS.replace(":root{", f""":root{{ --theme-main:{main}; --theme-sub:{sub};"""), unsafe_allow_html=True)

def get_info(mbti):
    return DATA.get(mbti, DEFAULT)

def main():
    col1, col2, col3 = st.columns([2,1,1])
    with col1:
        mbti = st.selectbox("MBTI를 선택하세요", MBTIS, index=MBTIS.index("ENFP"))
    with col2:
        reveal = st.toggle("모든 항목 펼치기", value=True)
    with col3:
        if st.button("🎈 풍선"):
            st.balloons()

    theme = MBTI_COLORS[mbti]
    inject_theme(theme["main"], theme["sub"])

    st.markdown('<div class="big-title">MBTI 인사이트 · 컬러 테마</div>', unsafe_allow_html=True)
    emoji = MBTI_EMOJI.get(mbti, "✨")
    st.markdown(f'<div class="mbti-badge">{emoji} {mbti} 타입</div>', unsafe_allow_html=True)

    info = get_info(mbti)

    st.markdown('<div class="section-title">요약</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="gradient-card">{info["요약"]}</div>', unsafe_allow_html=True)

    st.markdown('<hr/>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="section-title">특징</div>', unsafe_allow_html=True)
        st.markdown('<div class="gradient-card">', unsafe_allow_html=True)
        if reveal:
            for t in info["특징"]:
                st.markdown(f'<span class="tag">✨ {t}</span>', unsafe_allow_html=True)
        else:
            st.write("• " + " / ".join(info["특징"][:3]))
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-title">추천 직업</div>', unsafe_allow_html=True)
        st.markdown('<div class="gradient-card">', unsafe_allow_html=True)
        for job in info["추천직업"]:
            st.markdown(f'<span class="tag">💼 {job}</span>', unsafe_allow_html=True)
        st.caption("참고: 진로는 개인차가 크니 본인 강점·가치와 맞춰 보세요.")
        st.markdown('</div>', unsafe_allow_html=True)

    with c3:
        st.markdown('<div class="section-title">인간관계 팁</div>', unsafe_allow_html=True)
        st.markdown('<div class="gradient-card">', unsafe_allow_html=True)
        for tip in info["관계팁"]:
            st.markdown(f'<span class="tag">🤝 {tip}</span>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr/>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">공부/시간관리</div>', unsafe_allow_html=True)
    st.markdown('<div class="gradient-card">', unsafe_allow_html=True)
    for tip in info["공부팁"]:
        st.markdown(f'<span class="tag">📚 {tip}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr/>', unsafe_allow_html=True)
    colA, colB = st.columns([1,2])
    with colA:
        st.markdown('<div class="section-title">테마 액션</div>', unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="cute-button">', unsafe_allow_html=True)
            st.button("🌟 반짝 모드")
            st.markdown('</div>', unsafe_allow_html=True)
    with colB:
        st.caption("현재 테마는 선택한 MBTI의 개별 색상에 맞춰 자동으로 바뀝니다.")

if __name__ == "__main__":
    main()
