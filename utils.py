import sqlite3
import pandas as pd
import os

# 컬럼명 매핑 사전 (한글화용)
COLUMN_MAPPING = {
    'title': '매물명',
    'deposit': '보증금(만원)',
    'monthlyRent': '월세(만원)',
    'premium': '권리금(만원)',
    'maintenanceFee': '관리비(만원)',
    'size': '전용면적(㎡)',
    'floor': '층수',
    'businessLargeCodeName': '업종 대분류',
    'businessMiddleCodeName': '업종 중분류',
    'nearSubwayStation': '인근 지하철역',
    'viewCount': '조회수',
    'favoriteCount': '찜수',
    'createdDateUtc': '등록일',
    'rent_per_size': '평당 월세'
}

def load_data(db_path):
    """
    SQLite 데이터베이스에서 Nemo 상가 데이터를 로드하여 DataFrame으로 반환합니다.
    Streamlit dashbaord에서 캐싱을 적용하기 위해 래퍼 함수를 사용합니다.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM stores", conn)
    conn.close()
    
    # 데이터 전처리
    import json
    
    # JSON 문자열(리스트 형태)로 저장된 사진 URL 컬럼 처리
    photo_cols = ['smallPhotoUrls', 'originPhotoUrls']
    for col in photo_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) and x.startswith('[') else (x if isinstance(x, list) else []))

    # 수치형 컬럼 변환
    numeric_cols = ['deposit', 'monthlyRent', 'maintenanceFee', 'premium', 'size', 'floor', 'groundFloor']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # 지역 정보 추출 (nearSubwayStation 또는 title에서 '동' 정보 추출 시도)
    # 간단히 nearSubwayStation에서 역 이름만 추출하거나, title에서 추출
    df['district'] = df['title'].str.extract(r'([가-힣\d]+동)')
    # nan인 경우 '기타'로 표시
    df['district'] = df['district'].fillna('기타')
            
    # 평당 가격 등 추가 필드
    if 'size' in df.columns and 'monthlyRent' in df.columns:
        df['rent_per_size'] = df.apply(lambda x: x['monthlyRent'] / (x['size'] / 3.3057) if x['size'] > 0 else 0, axis=1)
        
    return df

def get_benchmarks(df, item):
    """
    특정 매물의 동일 업종/지역 대비 상대적 가치를 계산합니다.
    """
    # 동일 업종(대분류) 평균
    cat_avg = df[df['businessLargeCodeName'] == item['businessLargeCodeName']]
    cat_rent_avg = cat_avg['monthlyRent'].mean()
    cat_prem_avg = cat_avg['premium'].mean()
    
    # 동일 지역(동) 평균
    dist_avg = df[df['district'] == item['district']]
    dist_rent_avg = dist_avg['monthlyRent'].mean()
    dist_prem_avg = dist_avg['premium'].mean()
    
    benchmarks = {
        'cat_rent_diff': ((item['monthlyRent'] - cat_rent_avg) / cat_rent_avg * 100) if cat_rent_avg > 0 else 0,
        'cat_prem_diff': ((item['premium'] - cat_prem_avg) / cat_prem_avg * 100) if cat_prem_avg > 0 else 0,
        'dist_rent_diff': ((item['monthlyRent'] - dist_rent_avg) / dist_rent_avg * 100) if dist_rent_avg > 0 else 0,
        'dist_prem_diff': ((item['premium'] - dist_prem_avg) / dist_prem_avg * 100) if dist_prem_avg > 0 else 0,
        'avg_rent': cat_rent_avg,
        'avg_premium': cat_prem_avg
    }
    return benchmarks
