import time
import joblib
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, hamming_loss
from sklearn.multioutput import MultiOutputClassifier


# 현재 프로젝트 폴더 위치
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
REPORT_DIR = BASE_DIR / 'reports'
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
DATA_PATH = DATA_DIR / 'region_recommend_data.csv'

if not DATA_PATH.exists():
    raise FileNotFoundError('Data_preprocessing.py를 먼저 실행해 주세요.')

df = pd.read_csv(DATA_PATH, low_memory=False)

# 모델이 예측할 17개 지역 방문 여부 열 이름 자동 생성
TARGET_COLUMNS = [f'REGION_{i:02d}' for i in range(1, 18)]

# REGION_01~REGION_17과 순서대로 대응하는 실제 지역 이름
DESTINATIONS = [
    '서울특별시', '경기도', '인천광역시', '강원도', '대전광역시', '충청북도', '충청남도',
    '세종특별자치시', '경상북도', '경상남도', '대구광역시', '울산광역시', '부산광역시',
    '광주광역시', '전라북도', '전라남도', '제주특별자치도'
]

# 모델 학습 전, 반드시 존재해야 하는 입력 열과 정답 열
required_columns = ['year', 'D_SEX', 'D_AGE', 'RQ7_1', 'Q3_1a1'] + TARGET_COLUMNS

# 필요한 열 중 실제 데이터에 존재하지 않는 열 확인
missing_columns = [column for column in required_columns if column not in df]

# 필요한 열이 하나라도 없으면 어떤 열이 없는지 출력하고 실행 중단
if missing_columns:
    raise ValueError(f'전처리 데이터에 필요한 열이 없습니다: {missing_columns}')

# 필수 입력값과 지역 방문 여부에 처리되지 않은 결측치가 있는지 확인
# 하나라도 NaN이 존재하면 모델 학습을 중단
if df[required_columns].isna().any().any():
    raise ValueError('학습 데이터에 처리되지 않은 결측치가 있습니다.')

# 17개 지역 방문 여부가 0 또는 1로만 구성되어 있는지 확인
# 0은 미방문, 1은 방문을 의미
if not df[TARGET_COLUMNS].isin([0, 1]).all().all():
    raise ValueError('지역 방문 정답값은 0 또는 1이어야 합니다.')


# 범주형 입력값 원핫 인코딩

# 사용자 UI와 동일하게 성별, 연령대, 인원수, 테마 1개만 사용
# 각 항목에 사용할 원본 열과 정상 코드 범위를 설정
code_columns = {
    # D_SEX의 1~2번 코드를 SEX_1, SEX_2로 변환
    'SEX': ('D_SEX', range(1, 3)),

    # D_AGE의 1~6번 코드를 AGE_1~AGE_6으로 변환
    'AGE': ('D_AGE', range(1, 7)),

    # RQ7_1의 1~3번 코드를 GROUP_1~GROUP_3으로 변환
    'GROUP': ('RQ7_1', range(1, 4)),

    # Q3_1a1의 1~17번 코드를 THEME_1~THEME_17로 변환
    'THEME': ('Q3_1a1', range(1, 18))
}

# 모델 학습에 사용할 원핫 인코딩 열 이름을 저장할 리스트
feature_columns = []

# 성별, 연령대, 인원수, 테마를 차례대로 반복
for name, (source_column, codes) in code_columns.items():

    # 각 항목에서 사용할 코드 번호 반복
    for code in codes:

        # 새로 만들 원핫 인코딩 열 이름
        # 예: SEX_1, AGE_3, GROUP_2, THEME_14
        feature = f'{name}_{code}'

        # 원본값과 현재 코드가 같으면 1, 다르면 0으로 변환
        df[feature] = (df[source_column] == code).astype(int)

        # 나중에 모델 입력값으로 사용할 수 있도록 열 이름 저장
        feature_columns.append(feature)


# 연도 기준 학습·검증 데이터 분리

# 과거 2023~2024년으로 학습하고 새로운 2025년 자료로 검증

# 2023년과 2024년 데이터를 모델 학습에 사용
train_df = df[df['year'] < 2025].reset_index(drop=True)

# 2025년 데이터를 학습된 모델의 성능 검증에 사용
test_df = df[df['year'] == 2025].reset_index(drop=True)

# 학습 또는 검증 데이터가 비어 있으면 모델을 정상적으로 평가할 수 없음
if train_df.empty or test_df.empty:
    raise ValueError('학습용 2023~2024년 또는 검증용 2025년 데이터가 없습니다.')

# X는 모델에 입력하는 사용자 조건
# 성별, 연령대, 인원수, 테마를 원핫 인코딩한 데이터
X_train = train_df[feature_columns]

# y는 모델이 예측할 실제 지역 방문 여부
# REGION_01~REGION_17의 0과 1
y_train = train_df[TARGET_COLUMNS]

# 2025년 검증 데이터의 사용자 입력 조건
X_test = test_df[feature_columns]

# 2025년 관광객이 실제로 방문한 지역
y_test = test_df[TARGET_COLUMNS]


# 목적지별 방문확률 계산

def get_probabilities(model, input_data):
    """17개 분류기에서 방문 값 1의 확률만 가져온다."""

    # MultiOutputClassifier가 반환한 17개 지역의 확률 목록
    # 각 지역마다 미방문 0과 방문 1의 확률이 포함됨
    probability_list = model.predict_proba(input_data)

    # 지역별 방문 확률만 저장할 리스트
    positive_probabilities = []

    # 17개 지역의 확률 결과를 차례대로 확인
    for index, probabilities in enumerate(probability_list):

        # 현재 지역 분류기가 학습한 정답 종류 확인
        # 일반적으로 [0, 1]이지만 특수한 경우 [0]만 있을 수 있음
        classes = list(model.estimators_[index].classes_)

        # 방문을 의미하는 값 1이 학습된 경우
        if 1 in classes:

            # 미방문 확률은 제외하고 방문값 1의 확률만 저장
            positive_probabilities.append(probabilities[:, classes.index(1)])

        # 학습 데이터에 해당 지역 방문자가 전혀 없는 특수한 경우
        else:

            # 방문 가능성을 전부 0으로 설정
            positive_probabilities.append(np.zeros(len(input_data)))

    # 지역별로 분리된 결과를 하나의 2차원 배열로 합침
    # 결과 형태: 관광객 수 × 17개 지역
    return np.column_stack(positive_probabilities)


# 추천 TOP 3 성공 비율 계산

def calculate_hit_rate(probabilities, actual, top_n=3):
    """추천 TOP N에 실제 방문 지역이 하나라도 있던 응답자 비율이다."""

    # 각 관광객에게 예측확률이 높은 지역의 위치를 찾음
    # top_n=3이면 확률이 가장 높은 지역 3개의 인덱스를 가져옴
    top_indexes = np.argsort(probabilities, axis=1)[:, -top_n:]

    # 추천이 성공한 관광객 수
    hit_count = 0

    # 관광객 한 명씩 추천 지역과 실제 방문 지역 비교
    for row_index, predicted_indexes in enumerate(top_indexes):

        # 현재 관광객의 실제 방문값이 1인 지역 위치 찾기
        actual_indexes = np.where(actual.iloc[row_index].to_numpy() == 1)[0]

        # 추천 지역과 실제 방문 지역에 하나라도 같은 지역이 있는지 확인
        if set(predicted_indexes) & set(actual_indexes):

            # 하나라도 일치하면 추천 성공 횟수 증가
            hit_count += 1

    # 추천 성공 관광객 수를 전체 관광객 수로 나누어 성공 비율 계산
    return hit_count / len(actual)


# 모델 성능 평가

def evaluate_model(model_name, model, training_time):
    """전체 성능과 지역별 F1 점수를 계산한다."""

    # 2025년 사용자 조건으로 지역별 방문 여부 0 또는 1 예측
    predicted = model.predict(X_test)

    # 2025년 사용자 조건으로 지역별 방문 확률 계산
    probabilities = get_probabilities(model, X_test)

    # 모델별 전체 평가 결과를 딕셔너리로 저장
    result = {
        # 평가 중인 모델 이름
        'model_name': model_name,

        # 전체 지역의 0/1 예측 결과를 합쳐 계산한 F1 점수
        # 방문 건수가 많은 지역의 영향을 상대적으로 많이 받음
        'micro_f1': f1_score(y_test, predicted, average='micro', zero_division=0),

        # 17개 지역의 F1 점수를 각각 구한 다음 동일한 비중으로 평균
        # 방문자가 적은 지역의 성능도 함께 확인할 수 있음
        'macro_f1': f1_score(y_test, predicted, average='macro', zero_division=0),

        # 전체 0/1 예측 중 실제값과 다르게 예측한 비율
        # 값이 낮을수록 좋음
        'hamming_loss': hamming_loss(y_test, predicted),

        # 추천 TOP 3 중 실제 방문 지역이 하나 이상 포함된 관광객의 비율
        'hit_rate_at_3': calculate_hit_rate(probabilities, y_test),

        # 모델 학습에 걸린 시간
        'training_time_seconds': training_time
    }

    # 지역별 성능 결과를 저장할 리스트
    region_results = []

    # 서울부터 제주까지 지역별로 F1 점수 계산
    for index, destination in enumerate(DESTINATIONS):

        region_results.append({
            # 어떤 모델의 결과인지 표시
            'model_name': model_name,

            # 현재 평가한 지역 이름
            'destination': destination,

            # 2025년에 현재 지역을 실제 방문한 관광객 수
            'visit_count': int(y_test.iloc[:, index].sum()),

            # 현재 지역의 실제 방문 여부와 예측 방문 여부를 비교한 F1 점수
            'f1_score': f1_score(
                y_test.iloc[:, index],
                predicted[:, index],
                zero_division=0
            )
        })

    # 모델별 주요 성능을 터미널에 출력
    print('\n모델:', model_name)
    print('Micro F1:', round(result['micro_f1'], 4))
    print('Macro F1:', round(result['macro_f1'], 4))
    print('Hamming Loss:', round(result['hamming_loss'], 4))
    print('추천 TOP 3 성공 비율:', round(result['hit_rate_at_3'] * 100, 2), '%')
    print('학습 시간:', round(training_time, 2), '초')

    # 전체 성능 결과와 지역별 성능 결과를 함께 반환
    return result, region_results


# 인기 지역 TOP 3 고정 추천과 비교

# 모델이 단순히 인기 지역만 추천하는 것보다 나은지 확인하는 기준이다.

# 2023~2024년 학습 데이터에서 지역별 평균 방문률 계산
# 방문률이 가장 높은 지역 열 3개 선택
popular_columns = y_train.mean().nlargest(3).index.tolist()

# REGION_01과 같은 열 이름을 0~16 위치 번호로 변환
popular_indexes = [
    TARGET_COLUMNS.index(column)
    for column in popular_columns
]

# 인기 지역 고정 추천이 성공한 관광객 수
popular_hit_count = 0

# 2025년 관광객을 한 명씩 반복
for row_index in range(len(y_test)):

    # 현재 관광객이 실제로 방문한 지역 위치 찾기
    actual_indexes = np.where(
        y_test.iloc[row_index].to_numpy() == 1
    )[0]

    # 인기 지역 TOP 3와 실제 방문 지역이 하나라도 겹치면 성공
    if set(popular_indexes) & set(actual_indexes):
        popular_hit_count += 1

# 인기 지역 고정 추천 성공 비율
popular_hit_rate = popular_hit_count / len(y_test)

# 인기 지역의 인덱스를 실제 지역 이름으로 변환
popular_destinations = [
    DESTINATIONS[index]
    for index in popular_indexes
]

# 비교 기준이 되는 인기 지역과 성공 비율 출력
print('인기 지역 TOP 3:', popular_destinations)
print('인기 지역 TOP 3 성공 비율:', round(popular_hit_rate * 100, 2), '%')


# Logistic Regression과 Random Forest 모델 비교

# 같은 학습 데이터로 비교할 두 모델 설정
models = {
    # 지역별 방문 여부를 선형적인 관계로 학습하는 모델
    'Logistic Regression': MultiOutputClassifier(
        LogisticRegression(
            # 학습 반복 횟수의 최대값
            max_iter=1000,

            # 비교적 작은 범주형 데이터에 사용할 최적화 방식
            solver='liblinear',

            # 실행할 때마다 같은 학습 결과를 만들기 위한 고정값
            random_state=42
        ),

        # 17개 지역 분류기를 여러 CPU 코어에서 병렬 실행
        n_jobs=-1
    ),

    # 여러 결정트리의 결과를 합쳐 예측하는 모델
    'Random Forest': MultiOutputClassifier(
        RandomForestClassifier(
            # 사용할 결정트리 개수
            n_estimators=200,

            # 트리가 지나치게 깊어져 과적합되는 것을 방지
            max_depth=15,

            # 최종 잎에 최소 5개의 학습 데이터가 있도록 제한
            min_samples_leaf=5,

            # 실행할 때마다 같은 결과를 만들기 위한 고정값
            random_state=42,

            # 바깥쪽 MultiOutputClassifier가 병렬 처리하므로 내부는 1
            n_jobs=1
        ),

        # 17개 지역 분류기를 여러 CPU 코어에서 병렬 실행
        n_jobs=-1
    )
}

# 두 모델의 전체 평가 결과를 저장할 리스트
model_results = []

# 두 모델의 지역별 F1 결과를 저장할 리스트
region_results = []

# Logistic Regression과 Random Forest를 하나씩 학습
for model_name, model in models.items():

    print('\n', model_name, '학습 시작')

    # 학습 시작 시간 저장
    start_time = time.time()

    # 2023~2024년 입력값과 실제 방문 지역을 이용해 모델 학습
    model.fit(X_train, y_train)

    # 현재 시간에서 시작 시간을 빼서 학습 시간 계산
    training_time = time.time() - start_time

    # 학습된 모델의 2025년 검증 성능 계산
    result, region_result = evaluate_model(
        model_name,
        model,
        training_time
    )

    # 모델 전체 평가 결과 추가
    model_results.append(result)

    # 17개 지역별 평가 결과 추가
    region_results.extend(region_result)


# 최적 모델 선택과 평가 결과 저장

# 지역 편향을 함께 보기 위해 Macro F1을 가장 먼저 비교

# 두 모델의 평가 결과를 표 형태의 DataFrame으로 변환
result_df = pd.DataFrame(model_results)

# 단순 인기 지역 TOP 3의 성공 비율을 두 모델 결과에 추가
result_df['popular_hit_rate_at_3'] = popular_hit_rate

# 각 모델이 인기 지역 고정 추천보다 얼마나 개선됐는지 계산
result_df['improvement_over_popular'] = (
    result_df['hit_rate_at_3'] - popular_hit_rate
)

# 아래 평가 기준 순서대로 가장 좋은 모델이 위로 오도록 정렬
result_df = result_df.sort_values(
    [
        'hit_rate_at_3',  # TOP 3 추천 성공률: 높을수록 좋음
        'macro_f1',       # 지역별 성능 평균: 높을수록 좋음
        'micro_f1',       # 전체 예측 성능: 높을수록 좋음
        'hamming_loss'    # 틀린 예측 비율: 낮을수록 좋음
    ],
    ascending=[
        False,
        False,
        False,
        True
    ]
).reset_index(drop=True)

# 정렬 결과의 첫 번째 행에 있는 모델을 최종 모델로 선택
best_model_name = result_df.loc[0, 'model_name']

# 모델 비교 결과와 최종 선택 모델 출력
print('\n모델 비교 결과')
print(result_df.round(4))
print('\n최종 선택 모델:', best_model_name)

# 두 모델의 전체 성능 비교 결과를 CSV로 저장
result_df.to_csv(
    REPORT_DIR / 'model_comparison_results.csv',
    index=False,
    encoding='utf-8-sig'
)

# 두 모델의 17개 지역별 F1 점수를 CSV로 저장
pd.DataFrame(region_results).to_csv(
    REPORT_DIR / 'destination_f1_results.csv',
    index=False,
    encoding='utf-8-sig'
)


# 전체 데이터로 최종 모델 학습

# 선택된 최적 모델의 설정을 복사해 새로운 모델 생성
# 기존 검증 모델에 전체 데이터를 다시 학습시키지 않고 새 모델을 만드는 과정
final_model = clone(models[best_model_name])

# 2023~2025년 전체 데이터로 서비스에서 사용할 최종 모델 학습
final_model.fit(
    df[feature_columns],
    df[TARGET_COLUMNS]
)


# 입력 변수 중요도 저장

# 최종 모델이 Random Forest인 경우
if best_model_name == 'Random Forest':

    # 17개 지역별 Random Forest가 계산한 변수 중요도의 평균
    importance = np.mean(
        [
            estimator.feature_importances_
            for estimator in final_model.estimators_
        ],
        axis=0
    )

# 최종 모델이 Logistic Regression인 경우
else:

    # 17개 지역별 회귀계수 절댓값의 평균을 변수 영향력으로 사용
    importance = np.mean(
        [
            np.abs(estimator.coef_[0])
            for estimator in final_model.estimators_
        ],
        axis=0
    )

# 입력 변수 이름과 중요도를 표 형태로 만들고 큰 순서대로 정렬
pd.DataFrame({
    'feature': feature_columns,
    'importance': importance
}).sort_values(
    'importance',
    ascending=False
).to_csv(
    # 발표 및 분석에 사용할 변수 중요도 보고서
    REPORT_DIR / 'region_feature_importance.csv',
    index=False,
    encoding='utf-8-sig'
)


# 최종 모델과 호출에 필요한 정보 저장

# Ruse_checked.py에서 모델과 입력·출력 정보를 함께 불러올 수 있도록 구성
model_data = {
    # 학습이 완료된 최종 모델
    'model': final_model,

    # 최종 선택된 모델 이름
    'model_name': best_model_name,

    # 사용자 입력을 변환할 때 사용할 원핫 인코딩 열 순서
    'features': feature_columns,

    # 모델이 예측하는 17개 지역 정답 열 순서
    'targets': TARGET_COLUMNS,

    # REGION_01~17에 대응하는 지역 이름 순서
    'destination_names': DESTINATIONS
}

# 모델과 관련 정보를 하나의 pkl 파일로 압축(3) 저장
joblib.dump(
    model_data,
    DATA_DIR / 'region_recommender.pkl',
    compress=3
)

# 최종 저장 완료 메시지와 선택 모델 이름 출력
print('\n최종 모델 저장 완료:', best_model_name)
