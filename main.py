import streamlit as st

st.set_page_config(page_title="MBTI 인사이트: 큐티 컬러 에디션", page_icon="🌈", layout="wide")

# 이모지 매핑
MBTI_EMOJI = {
    "INTJ":"🧠✨","INTP":"🧩🔍","ENTJ":"🧭🚀","ENTP":"💡🌀",
    "INFJ":"🌙🕊️","INFP":"🎨🌿","ENFJ":"🌟🤝","ENFP":"🎉🌈",
    "ISTJ":"📘✅","ISFJ":"🫶🌸","ESTJ":"📊🏗️","ESFJ":"😊🎀",
    "ISTP":"🛠️⚡","ISFP":"🖌️🍃","ESTP":"🏁🔥","ESFP":"🎤✨"
}

MBTIS = list(MBTI_EMOJI.keys())

# 데모 데이터(핵심만 샘플, 기존 데이터에 연결 가능)
DATA = {
    "ENFP": {
        "요약": "활동가형. 상상력과 사람 중심 에너지로 변화를 이끕니다.",
        "특징": ["새로움/자율성 선호", "다양한 아이디어 연결", "팀 분위기 메이커"],
        "추천직업": ["브랜딩/마케팅", "콘텐츠 기획", "교육/코칭", "창업"],
        "관계팁": ["약속을 줄이고 핵심 3개에 집중", "아이디어는 실행 파트너와 매칭"],
        "공부팁": ["테마 주간 운영", "보상·챌린지로 동기 유지", "공개 약속으로 마감 관리"]
    },
    "INTJ": {
        "요약": "전략가형. 장기 목표를 체계적으로 달성합니다.",
        "특징": ["분석·계획에 강점", "비효율 싫어함", "깊은 몰입 선호"],
        "추천직업": ["전략/기획", "데이터/연구", "제품 매니징", "정책 분석"],
        "관계팁": ["직설 피드백 시 감정 고려", "맥락/목적을 먼저 공유"],
        "공부팁": ["역산 로드맵", "심화 원리 중심", "포모도로로 과몰입 관리"]
    },
    # 필요 유형 추가...
}
# 미정 데이터는 기본 템플릿
DEFAULT = {
    "요약": "해당 유형의 자세한 데이터는 곧 추가됩니다!",
    "특징": ["호기심이 많고 성장 지향적", "상황에 따른 유연성 발휘"],
    "추천직업": ["관심 분야 기반 탐색 추천", "강점-가치 일치 직무 우선"],
    "관계팁": ["명확한 의사소통", "경계 존중과 피드백 교환"],
    "공부팁": ["작은 승리 루프", "주간 리뷰로 개선 주기"]
}

# 커스텀 CSS
st.markdown("""
<style>
:root{
  --pink:#FF66B3; --lime:#A4FF4F; --sky:#66E0FF; --lilac:#B39DFF; --lemon:#FFD166;
}
html, body, [class*="main"] {
  font-family: "Pretendard","NanumSquareRound","Nunito","Apple SD Gothic Neo",sans-serif;
}
h1,h2,h3 { letter-spacing: 0.2px; }
.big-title {
  background: linear-gradient(90deg, var(--pink), var(--sky), var(--lilac));
  -webkit-background-clip: text; background-clip: text; color: transparent;
  font-weight: 900; font-size: 44px; text-shadow: 0 0 18px rgba(255,102,179,0.25);
}
.sub-note {
  color:#7a7a7a; font-size:14px; margin-top:-10px;
}
.gradient-card {
  padding:18px 20px; border-radius:18px;
  background: linear-gradient(135deg, rgba(255,102,179,0.15), rgba(102,224,255,0.15));
  border:1px solid rgba(255,255,255,0.5);
  box-shadow: 0 10px 24px rgba(179,157,255,0.25);
  backdrop-filter: blur(6px);
}
.tag {
  display:inline-block; padding:6px 10px; border-radius:999px;
  background: linear-gradient(90deg, var(--lemon), var(--lime));
  font-weight: 700; color:#222; margin-right:8px; margin-bottom:8px;
}
.mbti-badge {
  display:inline-flex; align-items:center; gap:8px;
  padding:10px 14px; border-radius:14px;
  background: linear-gradient(90deg, rgba(180,255,120,0.6), rgba(255,209,102,0.6));
  border:1px solid rgba(0,0,0,0.05);
  font-weight:800; color:#222;
  box-shadow: 0 6px 14px rgba(164,255,79,0.35);
}
.cute-button button {
  background: linear-gradient(90deg, var(--pink), var(--lemon)) !important;
  color: #222 !important; border: none !important; font-weight: 800 !important;
  box-shadow: 0 8px 18px rgba(255,102,179,0.45) !important;
}
.cute-button button:hover {
  filter: brightness(1.05);
  transform: translateY(-1px);
}
.section-title {
  font-size: 22px; font-weight: 900; color:#222;
  text-shadow: 0 2px 8px rgba(255,209,102,0.4);
  margin-top: 8px; margin-bottom: 8px;
}
hr { border: none; height:1px; background: linear-gradient(90deg, transparent, #ffd166, transparent); }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown('<div class="big-title">🌈 MBTI 인사이트 · 큐티 컬러 에디션 ✨</div>', unsafe_allow_html=True)
st.caption("밝고 귀엽고 화려하게! 이모지와 컬러로 직관적인 유형 가이드를 만나보세요.")

# 입력 영역
col1, col2, col3 = st.columns([2,1,1])
with col1:
    mbti = st.selectbox("MBTI를 선택하세요", MBTIS, index=MBTIS.index("ENFP"))
with col2:
    reveal = st.toggle("모든 항목 펼치기", value=True)
with col3:
    if st.button("🎈 컬러 풍선!"):
        st.balloons()

emoji = MBTI_EMOJI.get(mbti, "✨")
st.markdown(f'<div class="mbti-badge">{emoji} {mbti} 타입</div>', unsafe_allow_html=True)

# 데이터 로딩
info = DATA.get(mbti, DEFAULT)

# 요약 카드
st.markdown('<div class="section-title">요약</div>', unsafe_allow_html=True)
st.markdown(f'<div class="gradient-card">{info["요약"]}</div>', unsafe_allow_html=True)

# 3열 카드: 특징 / 추천 직업 / 인간관계 팁
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
    st.caption("참고: 진로는 개인의 역량·경험·가치에 따라 달라집니다.")
    st.markdown('</div>', unsafe_allow_html=True)

with c3:
    st.markdown('<div class="section-title">인간관계 팁</div>', unsafe_allow_html=True)
    st.markdown('<div class="gradient-card">', unsafe_allow_html=True)
    for tip in info["관계팁"]:
        st.markdown(f'<span class="tag">🤝 {tip}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 공부 팁 섹션
st.markdown('<hr/>', unsafe_allow_html=True)
st.markdown('<div class="section-title">공부/시간관리</div>', unsafe_allow_html=True)
st.markdown('<div class="gradient-card">', unsafe_allow_html=True)
for tip in info["공부팁"]:
    st.markdown(f'<span class="tag">📚 {tip}</span>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# 하단 액션
st.markdown('<hr/>', unsafe_allow_html=True)
colA, colB = st.columns([1,2])
with colA:
    st.markdown('<div class="section-title">테마 액션</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="cute-button">', unsafe_allow_html=True)
        st.button("🌟 반짝 모드")
        st.markdown('</div>', unsafe_allow_html=True)
with colB:
    st.caption("팁: 컬러와 이모지는 집중을 방해하지 않도록 섹션별 대비를 유지하세요.")

