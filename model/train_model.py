"""
예상경비 모델 - 학습 전용 스크립트

이 파일은 딱 한 번(또는 데이터/모델 바뀔 때만) 실행합니다.
실행하면 model/model_final.pkl, model/x_columns.pkl 이 생성됩니다.
UI팀은 estimate_expense.py만 있으면 됩니다.

실행 방법 (프로젝트 루트에서):
    python model/train_model.py
"""

import pandas as pd
import numpy as np
import pickle
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
# 2. 지역 멀티핫
# ══════════════════════════════════════
region_cols = [f'Q9_2a{str(i).zfill(2)}' for i in range(1, 18)]
region_names = ['서울', '경기', '인천', '강원', '대전', '충북', '충남', '세종',
                 '경북', '경남', '대구', '울산', '부산', '광주', '전북', '전남', '제주']
for col, name in zip(region_cols, region_names):
    tourist[f'방문_{name}'] = tourist[col].notna().astype(int)


# ══════════════════════════════════════
# 3. 테마 멀티핫
# ══════════════════════════════════════
ui_theme_to_q8a = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10,
                   11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 20}

for ui_code, q8a_num in ui_theme_to_q8a.items():
    col = f'Q8a{str(q8a_num).zfill(2)}'
    tourist[f'theme_{ui_code}'] = tourist[col].notna().astype(int)

theme_flag_cols = [f'theme_{i}' for i in range(1, 18)]


# ══════════════════════════════════════
# 4. 국적 → 대륙권
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
# 10. 모델과 컬럼 정보를 pickle로 저장
# ══════════════════════════════════════
with open('model/model_final.pkl', 'wb') as f:
    pickle.dump(model_final, f)

with open('model/x_columns.pkl', 'wb') as f:
    pickle.dump(X_data.columns.tolist(), f)

print("\n저장 완료: model/model_final.pkl, model/x_columns.pkl")