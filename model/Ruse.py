import joblib
import pandas as pd

from pathlib import Path
from code_book import AREA_OPTIONS


# 현재 프로젝트 폴더 위치
BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / 'data' / 'region_recommender.pkl'
if not MODEL_PATH.exists():
    raise FileNotFoundError('study_model.py를 먼저 실행해 주세요.')
model_data = joblib.load(MODEL_PATH)

# 학습된 최종 모델 (Random Forest)
model = model_data['model']

# 모델이 학습할 때 사용한 원핫 인코딩 열 이름과 순서
# 예: SEX_1, AGE_2, GROUP_3, THEME_14
feature_columns = model_data['features']

# REGION_01~REGION_17에 대응하는 실제 지역 이름
destination_names = model_data['destination_names']


# 목적지별 방문 가능성 계산

def get_destination_probabilities(user_data):
    """17개 분류기에서 방문 값 1의 확률만 가져온다."""

    # 저장된 MultiOutputClassifier에 사용자 조건을 전달
    # 17개 지역마다 미방문 0과 방문 1의 확률을 반환
    probability_list = model.predict_proba(user_data)

    # 각 지역의 방문 확률만 저장할 리스트
    probabilities = []

    # 서울부터 제주까지 17개 지역의 예측 결과를 하나씩 확인
    for index, probability in enumerate(probability_list):

        # 현재 지역 분류기가 학습한 정답 종류 확인
        # 일반적으로 [0, 1]로 구성됨
        classes = list(model.estimators_[index].classes_)

        # 방문을 뜻하는 숫자 1이 학습된 경우
        if 1 in classes:

            # 현재 지역의 방문값 1에 해당하는 확률만 가져오기
            probabilities.append(
                float(probability[0, classes.index(1)])
            )

        # 학습 데이터에 현재 지역 방문자가 한 명도 없었던 특수한 경우
        else:

            # 해당 지역의 방문 가능성을 0으로 설정
            probabilities.append(0.0)

    # 17개 지역의 방문 가능성 목록 반환
    return probabilities


# 사용자 입력값 검사

def check_inputs(gender, age, num_of_people, theme, preferred_area, top_n):
    """UI 또는 OpenAI 도구에서 전달된 코드의 허용 범위를 확인한다."""

    # 성별은 코드북 기준으로 1 또는 2만 허용
    if gender not in [1, 2]:
        raise ValueError('성별 코드는 1 또는 2여야 합니다.')

    # 연령대는 코드북 기준으로 1~6만 허용
    if age not in range(1, 7):
        raise ValueError('연령대 코드는 1~6이어야 합니다.')

    # 여행 인원수는 코드북 기준으로 1~3만 허용
    if num_of_people not in range(1, 4):
        raise ValueError('여행 인원수 코드는 1~3이어야 합니다.')

    # 여행 테마는 코드북 기준으로 1~17만 허용
    if theme not in range(1, 18):
        raise ValueError('여행 테마 코드는 1~17이어야 합니다.')

    # 희망 권역이 code_book.py의 허용 목록에 있는지 확인
    if preferred_area not in AREA_OPTIONS:
        raise ValueError('희망 권역은 전체, 수도권, 지방 중 하나여야 합니다.')

    # 최소 1개 이상의 목적지를 추천하도록 검사
    if top_n < 1:
        raise ValueError('추천 개수는 1개 이상이어야 합니다.')

# 여행 목적지 추천

def recommend_destination(
    gender,
    age,
    num_of_people,
    theme,
    preferred_area='전체',
    top_n=3
):
    """
    성별, 연령대, 인원수, 테마와 희망 권역을 입력받아
    모델 예측값이 높은 지역을 반환한다.
    score는 다른 기능에서 사용할 숫자 예측값이고,
    """

    # 모델을 실행하기 전에 모든 사용자 입력값 검사
    check_inputs(gender, age, num_of_people, theme, preferred_area, top_n)

    # 사용자 입력을 학습 모델과 동일한 원핫 인코딩 형태로 만든다.

    # 모든 입력값이 0인 한 행짜리 DataFrame 생성
    # 열의 종류와 순서는 모델 학습 당시 feature_columns와 동일함
    user_data = pd.DataFrame(0, index=[0], columns=feature_columns)

    # 사용자가 선택한 조건에 해당하는 원핫 인코딩 열 이름 생성
    selected_features = [
        f'SEX_{gender}',
        f'AGE_{age}',
        f'GROUP_{num_of_people}',
        f'THEME_{theme}'
    ]

    # 현재 선택한 입력 열이 저장된 모델의 입력 열에 있는지 확인
    missing_features = [
        feature
        for feature in selected_features
        if feature not in feature_columns
    ]

    # 코드와 모델 파일의 입력 구조가 다르면 재학습 안내
    # 예전 THEME1 모델 파일을 새 THEME 코드에서 사용하는 문제 등을 방지
    if missing_features:
        raise ValueError(
            '현재 코드와 저장된 모델의 입력 형식이 다릅니다. '
            'study_model_checked.py를 다시 실행해 주세요.'
        )

    # 사용자가 선택한 성별·연령대·인원수·테마 열만 1로 변경
    # 나머지 입력 열은 0으로 유지
    user_data.loc[0, selected_features] = 1

    # 숫자 예측값은 원본 모델 결과 그대로 보관한다.

    # 지역 이름과 모델이 예측한 방문 가능성을 표 형태로 생성
    result = pd.DataFrame({
        'destination': destination_names,
        'probability': get_destination_probabilities(user_data)
    })

    # 희망 권역은 모델 입력값이 아니라 추천 후보를 제한하는 필터이다.

    # 수도권으로 분류할 3개 지역
    capital = ['서울특별시', '경기도', '인천광역시']

    # 수도권을 선택한 경우 세 지역만 추천 후보로 유지
    if preferred_area == '수도권':
        result = result[result['destination'].isin(capital)].copy()

    # 지방을 선택한 경우 수도권 세 지역을 추천 후보에서 제외
    elif preferred_area == '지방':
        result = result[~result['destination'].isin(capital)].copy()

    # 전체를 선택한 경우에는 별도의 필터 없이 17개 지역 모두 유지

    # 권역 필터 결과가 비어 있으면 빈 목록 반환
    if result.empty:
        return []

    # 모델 예측값으로만 순위를 정하며 별도 가중치로 순서를 바꾸지 않는다.

    # 방문 가능성이 높은 지역부터 내림차순 정렬
    result = result.sort_values('probability', ascending=False)

    # 정렬 결과에서 사용자가 요청한 개수만큼 선택
    result = (result.head(top_n).reset_index(drop=True))

    # 최종 반환 결과를 저장할 목록
    recommendations = []

    # 상위 추천 지역을 한 개씩 딕셔너리 형태로 변환
    for index, row in result.iterrows():

        # 현재 지역의 모델 예측값
        probability = float(row['probability'])

        rank = index + 1

        recommendations.append({
            # 추천 순위는 1부터 시작
            'rank': rank,

            # 추천 지역 공식 명칭
            'destination': str(row['destination']),
            
            # 모델 원본 예측값을 100배 한 숫자
            # 내부 코드용
            'score': round(probability * 100, 1)
        })

    # 최종 추천 결과 반환
    return recommendations


# 단독 실행 테스트
# 이 파일을 직접 실행했을 때만 아래 테스트 코드가 실행됨.
# 다른 파일에서 import 시, 실행되지 않음
if __name__ == '__main__':
    sample_result = recommend_destination(
        gender=1,
        age=2,
        num_of_people=1,
        theme=1,
        preferred_area='지방',
        top_n=3
    )
    print('| 순위 | 추천 지역 |')

    for item in sample_result:
        print(
            f"| {item['rank']} "
            f"| {item['destination']} "
        )
