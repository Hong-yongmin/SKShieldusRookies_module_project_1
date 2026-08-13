import os
from dotenv import load_dotenv
import requests
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import pandas as pd
import numpy as np

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline

from sklearn.ensemble import ExtraTreesRegressor

import joblib

class EstimatePeak:
    """
    입력받은 날짜에 여행지가 성수기인지 예측하기 위한 클래스입니다.
    """

    def __init__(self):
        """
        load_dotenv()를 한번 실행한 이후 선언해주세요.\n
        내부적으로 load_dotenv()를 실행하지 않고 환경변수를 받아옵니다.
        """
        # 가까운 날짜에 대해 방문자수 집중률을 알려주는 api
        self.predict_url='https://apis.data.go.kr/B551011/TatsCnctrRateService/tatsCnctrRatedList'
        self.predict_url += '?serviceKey=' + str(os.getenv('VISITOR_DENSITY_KEY')) # 키 추가
        self.predict_url += '&MobileApp=TestApp'   # 필수 파라미터
        self.predict_url += '&MobileOS=ETC'        # 필수 파라미터
        self.predict_url += '&_type=json'          # json 형식으로 응답
        self.predict_url += '&areaCd={areaCd}'     # 지역 코드
        self.predict_url += '&signguCd={signguCd}' # 시군구코드

        # 특정 연, 월의 공휴일을 알려주는 api
        self.holiday_url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
        self.holiday_url += '?ServiceKey=' + str(os.getenv('HOLIDAY_KEY'))
        self.holiday_url += '&solYear={year}'        # 연도 지정
        self.holiday_url += '&solMonth={month:02d}'  # 월 지정
        self.holiday_url += '&_type=json'            # json으로 응답

        self.signgu_code_info = pd.read_excel('data/한국관광공사_OpenAPI_관광지_시군구_코드정보_v1.0.xlsx')
        self.peak_threshold = pd.read_pickle('data/peak_threshold.pkl') # 지역별 월 평균 방문자수
        self.tounum_per_day = pd.read_pickle('data/tounum_per_day.pkl') # 전년도 방문자수 추가용 데이터셋
        self.model = joblib.load('data/is_peak_model.pkl')
        # 날짜, 지역에 따른 방문자수 예측 모델
        # signguCode, daywkDivCd, previous_year_touNum, isDayOff, isLongHoliday, year, month, day, day_of_year

        self.tounum_per_day['baseYmd'] = pd.to_datetime(self.tounum_per_day['baseYmd'])

    def get_area_signgu_code(self, destination):
        """
        여행지의 지역 및 시군구코드를 찾아 반환합니다.\n
        반환 형식은 (areaCd, signguCd) 형식의 tuple입니다.\n
        destination : ['서울특별시', '구로구']
        """
        # 지역과 시군구 이름이 일치하는 열 추출
        row = self.signgu_code_info[(self.signgu_code_info['areaNm'] == destination[0]) 
                                    & (self.signgu_code_info['sigunguNm'] == destination[1])]

        if row.empty:
            return -1, -1  # 일치하는 시군구를 찾지 못하면 -1 반환
        else:
            return (row['areaCd'].values[0], row['sigunguCd'].values[0]) # 일치하는 시군구를 찾으면 코드 반환

    def is_peak_season(self, trip_date, destination):
        """
        여행 날짜, 여행지를 입력받아 성수기일지 예측합니다.\n
        성수기라면 True, 비수기라면 False를 반환합니다.\n
        destination에 해당하는 시군구를 찾지 못했을 때는 None을 반환합니다.\n
        trip_date : ['출발날짜', '마지막날짜']\n
        destination : ['서울특별시', '구로구']
        """
        area_cd, sigungu_cd = self.get_area_signgu_code(destination)
        if area_cd == -1:
            return None # destination에 해당하는 시군구를 찾지 못했을 경우 None 반환
        area_cd = str(area_cd)
        sigungu_cd = str(sigungu_cd)
        
        response = requests.get(self.predict_url.format(areaCd=area_cd, signguCd=sigungu_cd)) # 집중률 예측 API 호출
        json_data = json.loads(response.text) 
        df = pd.DataFrame(json_data['response']['body']['items']['item']) # 응답 본문을 Dataframe 객체로 변환

        base_ymd = pd.to_datetime(df['baseYmd'])

        start_date = pd.to_datetime(trip_date[0])
        end_date = pd.to_datetime(trip_date[1])

        period = pd.date_range(start=start_date, end=end_date)

        result = df[base_ymd.isin(period)] # 기간에 해당하는 행만 추출

        if not result.empty: # 여행 기간에 해당하는 정보가 있다면
            cnctr_rate = result['cnctrRate'].astype(float).mean() # 기간에 해당하는 동안의 집중률 평균

            if cnctr_rate >= 70 :
                return True # 집중률이 70 이상이라면 성수기로 판단
            else:
                return False

        else: # 여행기간에 해당하는 정보가 없다면
            return self.predict_tounum(period, sigungu_cd)

    def predict_tounum(self, period, signgu_cd):
        """
        여행지의 시군구코드와 여행 기간을 입력받아 방문자 수를 예측합니다.\n
        여행 기간 동안의 방문자 수 평균을 threshold와 비교하여 성수기 여부를 판별합니다.\n
        반환 형식은 True | False 입니다.\n
        period : [datetime, datetime, ...]
        """
        sum = 0
        for date in period:
            is_dayoff, long_holiday = self.is_dayoff(date)
            if date.year >= 2027: # 2026년에 대한 방문자수 정보가 없으므로
                temp_str = f'2026-{date.month:02d}-{date.day:02d}' # 2025년 정보를 사용하기 위해 date.year를 2026으로 설정
                date = pd.to_datetime(temp_str)
            result = self.tounum_per_day[(self.tounum_per_day['signguCode'] == signgu_cd) &
                                                (self.tounum_per_day['baseYmd'] == str(date - relativedelta(years=1)))
                                                ]['touNum']
            if len(result) > 0:
                pre_year_tounum = result.iloc[0]
            else:
                print('조건에 맞는 행을 찾을 수 없습니다')
                return None
            X = pd.DataFrame({
                'signguCode' : [signgu_cd],
                'daywkDivCd' : [date.dayofweek],
                'previous_year_touNum' : [pre_year_tounum],
                'isDayOff' : [is_dayoff],
                'isLongHoliday' : [long_holiday],
                'year':[date.year], 'month':[date.month], 'day':[date.day], 'day_of_year':[date.day_of_year]
                })
            sum += self.model.predict(X)
        mean_tounum = sum / len(period)
        if mean_tounum >= self.peak_threshold[(self.peak_threshold['signguCode'] == signgu_cd)]['threshold'].values[0]:
            return True
        else:
            return False

    def get_holiday(self, date):
        """
        날짜를 입력받아 해당 달의 공휴일 리스트를 반환합니다.\n
        date : datetime
        """
        response = requests.get(self.holiday_url.format(year=date.year, month=date.month)) # 공휴일 정보 api 호출
        temp = json.loads(response.text)
        temp = temp['response']['body']['items']

        holiday = []
        if temp: # 공휴일이 있는 달인 경우
            temp = temp['item']
            if isinstance(temp, list): # 공휴일이 2개 이상인 경우 list 형식
                for item in temp:      # 각각의 공휴일 날짜를 holiday list에 추가
                    holiday.append(pd.to_datetime(item['locdate']))
            else:
                holiday.append(pd.to_datetime(temp['locdate']))

        return holiday

    def is_dayoff(self, date):
        """
        날짜를 입력받아 휴일인지, 연휴인지 확인합니다.\n
        반환 형식은 (휴일여부, 연휴여부) 이며, 각각 맞으면 1, 아니면 0의 값을 가집니다.\n
        연휴의 기준은 주말을 포함하여 3일 이상 휴일인 경우 입니다.\n
        date : datetime
        """
        dayoff = 0          # 휴일 여부
        long_holiday = 0    # 연휴 여부
        holiday = self.get_holiday(date) # 공휴일 리스트

        is_holiday = date in holiday # 공휴일인지 여부
        day_of_wk = date.dayofweek
        if day_of_wk == 0 or day_of_wk == 6 or is_holiday:
            # 일요일 or 토요일인 경우, 공유일 list에 포함되는 경우 휴일
            dayoff = 1
        yesterday = date - timedelta(days=1)
        tomorrow = date + timedelta(days=1)
        long_holiday = self.is_long_holiday([yesterday, date, tomorrow], holiday)

        return dayoff, long_holiday

    def is_long_holiday(self, three_days, holiday):
        """
        연속된 3일을 입력받아 각각이 휴일인지 확인합니다.\n
        모두 휴일이라면 1, 아니라면 0을 반환합니다.\n
        three_days : [datetime, datetime, datetime]\n
        holiday : [가운데 날짜가 포함된 월의 공휴일 리스트]
        """
        # 첫 번째날, 세 번째 날이 기준일과 다른 달이라면 해당 달의 공휴일 리스트도 추가
        if three_days[0].month != three_days[1].month:
            holiday.append(self.get_holiday(three_days[0]))
        elif three_days[1].month != three_days[2].month:
            holiday.append(self.get_holiday(three_days[2]))
    
        streak = 0 # 각 날짜가 휴일일 때 1씩 추가
        for date in three_days:
            is_holiday = date in holiday # 공휴일인지 여부
            day_of_wk = date.dayofweek
            if day_of_wk == 0 or day_of_wk == 6 or is_holiday:
                # 일요일 or 토요일인 경우, 공유일 list에 포함되는 경우 휴일
                streak +=  1

        if streak == 3:
            return 1 # 3일 연속 휴일이라면 연휴
        else:
            return 0 # 하루라도 아니라면 0

if __name__=='__main__':
    trip_date = ['20270715', '20270716']
    destination = ['서울특별시', '중구']
    load_dotenv()

    estimate_peak = EstimatePeak()

    print(estimate_peak.is_peak_season(trip_date, destination))