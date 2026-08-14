"""
예상경비 모델 - 학습 + 예측 함수
 
사용법:
    from estimate_expense import estimate_expense
    estimate_expense(period=4, destination='제주', num_of_people=2, theme=3, age=2)
"""
 
import pandas as pd
import numpy as np
import requests
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb
 
 
# ══════════════════════════════════════
# 0. 로드
# ══════════════════════════════════════
tourist = pd.read_excel("data/2025년 외래관광객조사_DATA.xlsx")
codebook_map = pd.read_excel("data/2025년_외래관광객조사_코드북.xlsx", sheet_name="코드")
codebook_map['변수명'] = codebook_map['변수명'].ffill()
codebook_map['코드값 설명'] = codebook_map['코드값 설명'].astype(str).str.replace(r'\s+', '', regex=True)
 
y_raw_cols = ['숙박비1인대체', '음식점1인대체', '식음료1인대체',
              '한국철도1인대체', '한국도로1인대체', '대여서1인대체', '유류비1인대체',
              '쇼핑비1인대체', '오락및1인대체', '문화서1인대체',
              '데이터1인대체', '치료및1인대체', '미용서1인대체', '기타비1인대체']
 
tourist = tourist[[
    'pnid', 'Q1', 'TYP', 'M일HAP', 'RQ7_1', 'D_AGE', 'D_NAT', 'weight'
] + y_raw_cols
+ [f'Q9_2a{str(i).zfill(2)}' for i in range(1, 18)]
+ [f'Q8a{str(i).zfill(2)}' for i in range(1, 21)]]
 
 
# ══════════════════════════════════════
# 1. 필터링
# ══════════════════════════════════════
tourist = tourist[tourist['Q1'] == 1]
tourist = tourist[tourist['TYP'] == 1]
 
 
# ══════════════════════════════════════
# 2. 지역 멀티핫 (UI팀 destination 값 그대로 쓸 수 있게 시/도 이름 컬럼명 유지)
# ══════════════════════════════════════
region_cols = [f'Q9_2a{str(i).zfill(2)}' for i in range(1, 18)]
region_names = ['서울', '경기', '인천', '강원', '대전', '충북', '충남', '세종',
                 '경북', '경남', '대구', '울산', '부산', '광주', '전북', '전남', '제주']
for col, name in zip(region_cols, region_names):
    tourist[f'방문_{name}'] = tourist[col].notna().astype(int)
 
 
# ══════════════════════════════════════
# 3. 테마 멀티핫 — UI팀 코드(1~17)에 맞춰 컬럼명을 'theme_1' ~ 'theme_17'로 통일
# ══════════════════════════════════════
ui_theme_to_q8a = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
                   11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 20}
 
for ui_code, q8a_num in ui_theme_to_q8a.items():
    col = f'Q8a{str(q8a_num).zfill(2)}'
    tourist[f'theme_{ui_code}'] = tourist[col].notna().astype(int)
 
theme_flag_cols = [f'theme_{i}' for i in range(1, 18)]
 
 
# ══════════════════════════════════════
# 4. 국적 → 대륙권 (UI엔 국적 입력이 없으므로 학습에만 쓰고, 예측 시엔 기본값 처리)
# ══════════════════════════════════════
nat_map = codebook_map[codebook_map['변수명'] == 'D_NAT'].set_index('코드')['코드값 설명'].to_dict()
tourist['국적_라벨'] = tourist['D_NAT'].map(nat_map)
 
continent_map = {
    '중국': '동아시아', '일본': '동아시아', '대만': '동아시아', '홍콩': '동아시아', '몽골': '동아시아',
    '태국': '동남아', '베트남': '동남아', '말레이시아': '동남아', '싱가포르': '동남아',
    '필리핀': '동남아', '인도네시아': '동남아',
    '미국': '북미', '캐나다': '북미',
    '영국': '유럽', '독일': '유럽', '프랑스': '유럽', '러시아': '유럽',
    '호주': '오세아니아', '인도': '남아시아', '중동': '중동', '기타': '기타'
}
tourist['대륙'] = tourist['국적_라벨'].map(continent_map)
continent_onehot = pd.get_dummies(tourist['대륙'], prefix='대륙')
tourist = pd.concat([tourist, continent_onehot], axis=1)
 
 
# ══════════════════════════════════════
# 5. y, weight
# ══════════════════════════════════════
y_data = tourist[y_raw_cols].sum(axis=1)
w_data = tourist['weight']
 
 
# ══════════════════════════════════════
# 6. X_data 최종 정리
# ══════════════════════════════════════
drop_cols = (
    ['pnid', 'Q1', 'TYP', 'D_NAT', '국적_라벨', '대륙', 'weight']
    + y_raw_cols
    + [f'Q9_2a{str(i).zfill(2)}' for i in range(1, 18)]
    + [f'Q8a{str(i).zfill(2)}' for i in range(1, 21)]
)
X_data = tourist.drop(columns=drop_cols)
 
region_flag_cols = [f'방문_{n}' for n in region_names]
X_data['방문지역_개수'] = X_data[region_flag_cols].sum(axis=1)
X_data['참여테마_개수'] = X_data[theme_flag_cols].sum(axis=1)
 
 
# ══════════════════════════════════════
# 7. 이상치 제거
# ══════════════════════════════════════
valid_idx = y_data[(y_data > 0) & (y_data <= y_data.quantile(0.99))].index
X_data = X_data.loc[valid_idx]
y_data = y_data.loc[valid_idx]
w_data = w_data.loc[valid_idx]
 
print("최종 표본 수:", len(y_data))
 
 
# ══════════════════════════════════════
# 8. split + 학습
# ══════════════════════════════════════
y_log = np.log1p(y_data)
X_train, X_test, y_train_log, y_test_log, w_train, w_test = train_test_split(
    X_data, y_log, w_data, test_size=0.2, random_state=42
)
 
monotone = tuple(1 if c == 'M일HAP' else 0 for c in X_data.columns)
 
model_final = xgb.XGBRegressor(
    n_estimators=300, max_depth=4, learning_rate=0.05, random_state=42,
    objective='reg:quantileerror', quantile_alpha=0.5, n_jobs=-1,
    monotone_constraints=monotone
)
model_final.fit(X_train, y_train_log, sample_weight=w_train)
 
 
# ══════════════════════════════════════
# 9. 검증
# ══════════════════════════════════════
y_pred_log = model_final.predict(X_test)
y_pred_real = np.expm1(y_pred_log)
y_test_real = np.expm1(y_test_log)
 
mae = mean_absolute_error(y_test_real, y_pred_real, sample_weight=w_test)
r2 = r2_score(y_test_real, y_pred_real, sample_weight=w_test)
print(f"MAE: {mae:.1f}, R²: {r2:.4f}")
 
 
# ══════════════════════════════════════
# 10. 환율 조회 함수
# ══════════════════════════════════════
def get_usd_to_krw(default=1450):
    try:
        res = requests.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"base": "USD", "symbols": "KRW"},
            timeout=15
        )
        res.raise_for_status()
        return res.json()["rates"]["KRW"]
    except Exception as e:
        print(f"환율 API 실패, 기본값 사용: {e}")
        return default
 
 
EXCHANGE_RATE = get_usd_to_krw()
print("적용된 환율:", EXCHANGE_RATE)
 
 
# ══════════════════════════════════════
# 11. 지역명 매핑표 (정식 행정구역명 → 짧은 이름)
# ══════════════════════════════════════
region_full_to_short = {
    '서울특별시': '서울', '경기도': '경기', '인천광역시': '인천', '강원특별자치도': '강원',
    '대전광역시': '대전', '충청북도': '충북', '충청남도': '충남', '세종특별자치시': '세종',
    '경상북도': '경북', '경상남도': '경남', '대구광역시': '대구', '울산광역시': '울산',
    '부산광역시': '부산', '광주광역시': '광주', '전북특별자치도': '전북',
    '전라남도': '전남', '제주특별자치도': '제주'
}
 
 
# ══════════════════════════════════════
# 12. 최종 예측 함수
# ══════════════════════════════════════
def estimate_expense(period, destination, num_of_people, theme, age):
    """
    입력:
        period          : int   (여행 일수)
        destination     : str   (시/도 이름, 예: '제주', '서울특별시' 등)
        num_of_people   : int   (1=1명, 2=2명, 3=3명이상)
        theme           : int   (1~17, UI팀 테마 코드)
        age             : int   (1~6)
    출력:
        int (1인당 예상 총경비, 원화)
    """
    input_dict = {col: 0 for col in X_data.columns}
    input_dict['M일HAP'] = period
    input_dict['RQ7_1'] = num_of_people
    input_dict['D_AGE'] = age
 
    destination_short = region_full_to_short.get(destination, destination)
    region_col = f'방문_{destination_short}'
    if region_col in input_dict:
        input_dict[region_col] = 1
        input_dict['방문지역_개수'] = 1
    else:
        print(f"지역 매칭 실패: {destination} -> 기본값(서울)으로 대체")
        input_dict['방문_서울'] = 1
        input_dict['방문지역_개수'] = 1
 
    theme_col = f'theme_{theme}'
    if theme_col in input_dict:
        input_dict[theme_col] = 1
    input_dict['참여테마_개수'] = 1
 
    input_df = pd.DataFrame([input_dict])[X_data.columns]
    pred_log = model_final.predict(input_df)[0]
    pred_total_usd = np.expm1(pred_log)
    pred_total_krw = pred_total_usd * EXCHANGE_RATE
 
    return int(round(pred_total_krw, -3))