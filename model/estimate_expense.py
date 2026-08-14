"""
예상경비 모델 - 예측 함수 (UI팀이 import해서 쓰는 파일)

주의: 이 파일을 실행하기 전에 반드시 train_model.py를 먼저 한 번 실행해서
      model/model_final.pkl, model/x_columns.pkl 을 생성해둬야 합니다.

사용법:
    from model.estimate_expense import estimate_expense
    estimate_expense(period=4, destination='제주', num_of_people=2, theme=3, age=2)
"""

import pandas as pd
import numpy as np
import pickle
import requests


# ══════════════════════════════════════
# 학습된 모델 불러오기
# ══════════════════════════════════════
with open('model/model_final.pkl', 'rb') as f:
    model_final = pickle.load(f)

with open('model/x_columns.pkl', 'rb') as f:
    X_columns = pickle.load(f)


# ══════════════════════════════════════
# 환율 조회
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


# ══════════════════════════════════════
# 지역명 매핑표 (정식 행정구역명 → 짧은 이름)
# ══════════════════════════════════════
region_full_to_short = {
    '서울특별시': '서울', '경기도': '경기', '인천광역시': '인천', '강원특별자치도': '강원',
    '대전광역시': '대전', '충청북도': '충북', '충청남도': '충남', '세종특별자치시': '세종',
    '경상북도': '경북', '경상남도': '경남', '대구광역시': '대구', '울산광역시': '울산',
    '부산광역시': '부산', '광주광역시': '광주', '전북특별자치도': '전북',
    '전라남도': '전남', '제주특별자치도': '제주'
}


# ══════════════════════════════════════
# 예측 함수
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
    input_dict = {col: 0 for col in X_columns}
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

    input_df = pd.DataFrame([input_dict])[X_columns]
    pred_log = model_final.predict(input_df)[0]
    pred_total_usd = np.expm1(pred_log)
    pred_total_krw = pred_total_usd * EXCHANGE_RATE

    return int(round(pred_total_krw, -3))