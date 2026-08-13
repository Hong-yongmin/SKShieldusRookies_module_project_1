import pandas as pd
import json
import numpy as np

import os
import joblib

from sklearn.ensemble import ExtraTreesRegressor

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)

tour_df = pd.read_pickle('data/tour_df.pkl') # 데이터셋 로드

final_model = ExtraTreesRegressor( # 모델 생성
            random_state=42,
            n_estimators=50,
            max_depth=5,
            min_samples_leaf=2,
            n_jobs=-1
        )

categorical_features = [ # 인코딩할 column
    'signguCode',
    'daywkDivCd'
]

numeric_features = [ # 따로 처리하지 않을 column
    'year',
    'month',
    'day',
    'day_of_year',
    'isDayOff',
    'isLongHoliday',
    'previous_year_touNum'
]

preprocessor = ColumnTransformer(
    transformers=[
        (
            'cat',
            OneHotEncoder(
                handle_unknown='ignore',
                sparse_output=False
            ),
            categorical_features
        ),
        (
            'num',
            'passthrough',
            numeric_features
        )
    ]
)

X = tour_df.drop(columns=['touNum'])
y = tour_df['touNum']

# 날짜는 연, 월, 일, 1년의 n번째 날(day of year)로 분리
X['year'] = X['baseYmd'].dt.year
X['month'] = X['baseYmd'].dt.month
X['day'] = X['baseYmd'].dt.day
X['day_of_year'] = X['baseYmd'].dt.dayofyear

# Train: 2024-01-01 ~ 2025-03-31
# Validation: 2025-04-01 ~ 2025-06-30
# Test: 2025-07-01 ~ 2025-12-31

train_mask = X['baseYmd'] < '2025-04-01'

val_mask = (
    (X['baseYmd'] >= '2025-04-01') &
    (X['baseYmd'] < '2025-07-01')
)

test_mask = X['baseYmd'] >= '2025-07-01'

X_train = X.loc[train_mask].copy()
y_train = y.loc[train_mask].copy()

X_val = X.loc[val_mask].copy()
y_val = y.loc[val_mask].copy()

X_test = X.loc[test_mask].copy()
y_test = y.loc[test_mask].copy()

# 학습에 사용되지 않을 column 분리
X_train = X_train.drop(columns=['baseYmd'])
X_val = X_val.drop(columns=['baseYmd'])
X_test = X_test.drop(columns=['baseYmd'])

X_train.drop(columns=['signguNm'], inplace=True)
X_val.drop(columns=['signguNm'], inplace=True)
X_test.drop(columns=['signguNm'], inplace=True)

preprocessor.fit(X_train) # 학습 데이터에 맞춰 전처리기 fit

final_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('model', final_model)
])

X_train_val = pd.concat([X_train, X_val], axis=0)
y_train_val = pd.concat([y_train, y_val], axis=0)

final_pipeline.fit(X_train_val, y_train_val) # 학습 데이터에 맞게 모델 fit

y_pred_test = final_pipeline.predict(X_test)

test_mae = mean_absolute_error(
    y_test,
    y_pred_test
)

test_rmse = np.sqrt(
    mean_squared_error(y_test, y_pred_test)
)

test_r2 = r2_score(
    y_test,
    y_pred_test
)

print('=' * 50)
print('최종 Test 성능')
print('=' * 50)
print(f'MAE  : {test_mae:,.2f}')
print(f'RMSE : {test_rmse:,.2f}')
print(f'R2   : {test_r2:.5f}')

# 최종 모델 저장
joblib.dump(
    final_pipeline,
    f'data/is_peak_model.pkl'
)

print('저장 완료!')
print(f'모델: data/is_peak_model.pkl')