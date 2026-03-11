import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import load_data, COLUMN_MAPPING, get_benchmarks
import os
import json

# --- 스타일 및 페이지 설정 ---
st.set_page_config(page_title="Nemo Premium Analytics", layout="wide")

st.markdown("""
<style>
    .main { background-color: #fcfcfc; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #eee; }
    .card { border: 1px solid #ddd; border-radius: 12px; padding: 15px; background: white; margin-bottom: 20px; transition: 0.3s; }
    .card:hover { box-shadow: 0 8px 16px rgba(0,0,0,0.1); border-color: #3b82f6; }
    .badge { background: #eff6ff; color: #1e40af; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
    .price-tag { color: #2563eb; font-weight: bold; font-size: 1.2em; }
    .stButton>button { width: 100%; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# --- 세션 상태 초기화 ---
if 'selected_article_id' not in st.session_state:
    st.session_state.selected_article_id = None
if 'basket' not in st.session_state:
    st.session_state.basket = []
if 'filter_presets' not in st.session_state:
    st.session_state.filter_presets = {}

# --- 데이터 로드 (캐싱) ---
@st.cache_data
def get_data():
    DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "nemo.db"))
    return load_data(DB_PATH)

df = get_data()

# --- 사이드바: 고도화 필터 ---
with st.sidebar:
    st.title("🏙️ Nemo Premium")
    
    # [개선 8] 필터 프리셋
    with st.expander("⭐ 필터 프리셋", expanded=False):
        preset_name = st.text_input("프리셋 이름", key="ps_name")
        if st.button("현재 필터 저장"):
            # 실제 필터 값들이 정의된 후 아래에서 저장 로직 수행 (아래에서 구현 가능하게 나중에 처리)
            pass
        if st.session_state.filter_presets:
            p_choice = st.selectbox("저장된 필터 불러오기", list(st.session_state.filter_presets.keys()))
    
    st.divider()
    search_query = st.text_input("🔍 키워드 검색 (매물명)", "")
    
    # 필터 범위 설정
    dep_range = st.slider("보증금(만)", int(df['deposit'].min()), int(df['deposit'].max()), (int(df['deposit'].min()), int(df['deposit'].max())))
    rent_range = st.slider("월세(만)", int(df['monthlyRent'].min()), int(df['monthlyRent'].max()), (int(df['monthlyRent'].min()), int(df['monthlyRent'].max())))
    prem_range = st.slider("권리금(만)", int(df['premium'].min()), int(df['premium'].max()), (int(df['premium'].min()), int(df['premium'].max())))
    size_range = st.slider("면적(㎡)", float(df['size'].min()), float(df['size'].max()), (float(df['size'].min()), float(df['size'].max())))
    
    large_cats = ["전체"] + sorted(df['businessLargeCodeName'].dropna().unique().tolist())
    sel_cat = st.selectbox("업종 대분류", large_cats)

    # [개선 9] 데이터 내보내기
    st.divider()
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 필터 데이터 다운로드 (CSV)", data=csv_data, file_name='nemo_filtered.csv', mime='text/csv')

# --- 필터링 로직 ---
f_df = df[
    (df['deposit'].between(dep_range[0], dep_range[1])) &
    (df['monthlyRent'].between(rent_range[0], rent_range[1])) &
    (df['premium'].between(prem_range[0], prem_range[1])) &
    (df['size'].between(size_range[0], size_range[1]))
]
if sel_cat != "전체": f_df = f_df[f_df['businessLargeCodeName'] == sel_cat]
if search_query: f_df = f_df[f_df['title'].str.contains(search_query, case=False, na=False)]

# --- 메인 로직 ---

def reset_view():
    st.session_state.selected_article_id = None
    st.rerun()

if st.session_state.selected_article_id:
    # --- [상세 페이지] ---
    item = df[df['id'] == st.session_state.selected_article_id].iloc[0]
    st.button("⬅️ 목록으로 돌아가기", on_click=reset_view)
    
    st.title(f"{item['title']}")
    
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        photos = item.get('originPhotoUrls', [])
        if photos:
            for p in photos: st.image(p, use_container_width=True)
        else:
            st.warning("사진 정보가 없습니다.")
            
    with c2:
        # [개선 2] 벤치마킹 분석
        st.subheader("📊 매물 가치 평가 (Benchmarking)")
        bench = get_benchmarks(df, item)
        
        # 메트릭 디자인
        bc1, bc2 = st.columns(2)
        bc1.metric("업종 평균 대비 월세", f"{bench['cat_rent_diff']:.1f}%", delta=f"{bench['cat_rent_diff']:.1f}%", delta_color="inverse")
        bc2.metric("지역 평균 대비 월세", f"{bench['dist_rent_diff']:.1f}%", delta=f"{bench['dist_rent_diff']:.1f}%", delta_color="inverse")
        
        st.info(f"💡 해당 매물은 `{item['district']}` 지역 `{item['businessLargeCodeName']}` 업종 평균 가격 대비 분석된 결과입니다.")
        
        st.divider()
        # [개선 5] 한글화 상세 정보
        st.subheader("📝 상세 매물 정보")
        for eng, kor in COLUMN_MAPPING.items():
            if eng in item:
                val = item[eng]
                if eng == 'createdDateUtc' and isinstance(val, str): val = val.split('T')[0]
                st.write(f"**{kor}**: {val}")
        
        st.divider()
        # [개선 7] 유사 매물 추천
        st.subheader("🏠 추천 매물")
        # 같은 동네 + 비슷한 월세 (+/- 20%)
        sim_df = df[(df['district'] == item['district']) & (df['id'] != item['id']) & 
                    (df['monthlyRent'].between(item['monthlyRent']*0.8, item['monthlyRent']*1.2))].head(3)
        if not sim_df.empty:
            for _, s in sim_df.iterrows():
                with st.container(border=True):
                    st.write(f"**{s['title'][:20]}...**")
                    st.write(f"💰 {s['deposit']}/{s['monthlyRent']}")
                    if st.button("보기", key=f"sim_btn_{s['id']}"):
                        st.session_state.selected_article_id = s['id']
                        st.rerun()
        else: st.write("추천할 유사 매물이 없습니다.")

else:
    # --- [목록 페이지] ---
    st.title("🏙️ Nemo Premium Dashboard")
    
    tabs = st.tabs(["🖼️ 갤러리/필터", "📊 시장 분석(통계)", "🗺️ 지역 분석(밀집도)", "⚖️ 매물 비교"])
    
    with tabs[0]:
        # 상단 KPI
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("검색 결과", f"{len(f_df)} 건")
        k2.metric("평균 보증금", f"{f_df['deposit'].mean():.0f} 만")
        k3.metric("평균 월세", f"{f_df['monthlyRent'].mean():.0f} 만")
        k4.metric("평균 권리금", f"{f_df['premium'].mean():.0f} 만")
        
        st.divider()
        
        if not f_df.empty:
            # [개선 10] 갤러리 레이아웃
            for i in range(0, len(f_df), 3):
                cols = st.columns(3)
                for j in range(3):
                    idx = i + j
                    if idx < len(f_df):
                        row = f_df.iloc[idx]
                        with cols[j]:
                            st.markdown(f"""
                            <div class="card">
                                <img src="{row['smallPhotoUrls'][0] if row['smallPhotoUrls'] else 'https://via.placeholder.com/300'}" style="width:100%; border-radius:8px; height:180px; object-fit:cover; margin-bottom:10px;">
                                <div class="badge">{row['district']} | {row['businessLargeCodeName']}</div>
                                <h4 style="margin:10px 0;">{row['title'][:25]}...</h4>
                                <div class="price-tag">💰 {row['deposit']}/{row['monthlyRent']} 만</div>
                                <p style="font-size:0.9em; color:#666;">전용 {row['size']}㎡ | {row['floor']}층</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            c_btn1, c_btn2 = st.columns(2)
                            if c_btn1.button("상세보기", key=f"v_{row['id']}"):
                                st.session_state.selected_article_id = row['id']
                                st.rerun()
                            
                            is_in = row['id'] in st.session_state.basket
                            if c_btn2.button("비교 담기" if not is_in else "담기 취소", key=f"b_{row['id']}"):
                                if is_in: st.session_state.basket.remove(row['id'])
                                else: 
                                    if len(st.session_state.basket) < 3: st.session_state.basket.append(row['id'])
                                    else: st.error("최대 3개")
                                st.rerun()
        else: st.warning("결과가 없습니다.")

    with tabs[1]:
        st.subheader("📊 지역 및 업종 통계")
        r1, r2 = st.columns(2)
        with r1:
            # [개선 4] 층별 임대료 분석
            floor_data = f_df.groupby('floor')['monthlyRent'].mean().sort_index().reset_index()
            fig = px.bar(floor_data, x='floor', y='monthlyRent', title="층별 평균 월세 현황", labels={'floor':'층수', 'monthlyRent':'평균 월세(만)'}, color='monthlyRent')
            st.plotly_chart(fig, use_container_width=True)
        with r2:
            fig_size = px.scatter(f_df, x='size', y='monthlyRent', color='businessLargeCodeName', size='premium', hover_name='title', title="면적 vs 월세 (원형 크기=권리금)")
            st.plotly_chart(fig_size, use_container_width=True)
        
        # [개선 5] 한글 컬럼 상세 테이블
        st.subheader("📋 상세 데이터 리스트")
        st.dataframe(f_df.rename(columns=COLUMN_MAPPING)[[v for v in COLUMN_MAPPING.values() if v in f_df.rename(columns=COLUMN_MAPPING).columns]], use_container_width=True)

    with tabs[2]:
        # [개선 1] 지도 시각화 (동네 밀집도)
        st.subheader("🗺️ 지역별 매물 밀집도 차트")
        dist_df = f_df['district'].value_counts().reset_index()
        fig_dist = px.pie(dist_df, names='district', values='count', hole=0.4, title="행정구역(동)별 매물 분포")
        st.plotly_chart(fig_dist, use_container_width=True)
        st.info("💡 현재 좌표 데이터가 부재하여 동별 분포 비중으로 대체 표기합니다.")

    with tabs[3]:
        # [개선 6] 매물 비교 바구니
        st.subheader("⚖️ 매물 비교 (최대 3개)")
        if not st.session_state.basket: st.info("매물을 담아주세요.")
        else:
            comp_df = df[df['id'].isin(st.session_state.basket)].rename(columns=COLUMN_MAPPING)
            items = ['매물명', '보증금(만원)', '월세(만원)', '권리금(만원)', '전용면적(㎡)', '층수', '업종 대분류', '인근 지하철역']
            st.table(comp_df[items].T)
            if st.button("바구니 비우기"):
                st.session_state.basket = []
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Nemo Premium Dashboard v2.5")
