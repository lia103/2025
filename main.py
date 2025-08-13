# ... 기존 파이썬 로직은 동일, CSS만 교체/추가 ...

st.markdown("""
<style>
:root{
  --theme-main: #FF66B3; /* 런타임에 MBTI별 주입됨 */
  --theme-sub: #66E0FF;  /* 런타임에 MBTI별 주입됨 */
  --text:#222;
  --bg:#FFFFFF;
  --muted:#7a7a7a;
  --card:#FFFFFF;          /* 카드 배경 단색 */
  --badge:#FAFAFB;         /* 배지 단색 */
  --tag:#FFF2F7;           /* 태그 기본 단색(핑크 톤), 타입별로 살짝 바뀜 */
  --border: rgba(0,0,0,0.06);
}

html, body, [class*="main"] {
  font-family: "Pretendard","NanumSquareRound","Nunito","Apple SD Gothic Neo",sans-serif;
  color: var(--text);
  background: var(--bg);
}

/* 대제목은 포인트용 그라디언트 유지(텍스트만) */
.big-title {
  background: linear-gradient(90deg, var(--theme-main), var(--theme-sub));
  -webkit-background-clip: text; background-clip: text; color: transparent;
  font-weight: 900; font-size: 40px; letter-spacing: 0.2px;
}

/* 배지: 단색 배경 + 얇은 테두리 */
.mbti-badge {
  display:inline-flex; align-items:center; gap:8px;
  padding:10px 14px; border-radius:14px;
  background: var(--badge);
  border:1px solid var(--border);
  font-weight:800; color:var(--text);
}

/* 카드: 완전 단색 + 미세 그림자 */
.gradient-card {
  padding:18px 20px; border-radius:18px;
  background: var(--card);
  border:1px solid var(--border);
  box-shadow: 0 6px 14px rgba(0,0,0,0.06);
}

/* 섹션 타이틀: 단색 텍스트, 보조색 밑줄 */
.section-title {
  font-size: 20px; font-weight: 900; color:var(--text); margin: 4px 0 8px;
  border-bottom: 3px solid color-mix(in srgb, var(--theme-main) 35%, white);
  display:inline-block; padding-bottom: 4px;
}

/* 태그: 단색 + 대비 확보(유형별 색 주입 시 배경만 바뀜) */
.tag {
  display:inline-block; padding:6px 10px; border-radius:999px;
  background: var(--tag);
  font-weight: 700; color:var(--text);
  margin-right:8px; margin-bottom:8px;
  border: 1px solid var(--border);
}

/* 버튼: 단색(hover 시 테두리 강조) */
.cute-button button {
  background: color-mix(in srgb, var(--theme-main) 25%, white) !important;
  color: var(--text) !important; border: 1px solid var(--border) !important; 
  font-weight: 800 !important; box-shadow: none !important; border-radius: 12px !important;
}
.cute-button button:hover {
  background: color-mix(in srgb, var(--theme-main) 35%, white) !important;
  border-color: color-mix(in srgb, var(--theme-main) 60%, #000) !important;
}

/* 본문 가독성 보완 */
p, li, .stMarkdown { font-size: 16px; line-height: 1.6; }
.small-note { color: var(--muted); font-size: 13px; }

/* 구분선: 아주 얕은 단색 */
hr { border: none; height:1px; background: rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)
