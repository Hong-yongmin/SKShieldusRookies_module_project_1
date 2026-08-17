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
        # 특정 연, 월의 공휴일을 알려주는 api
        self.holiday_url = 'http://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo'
        self.holiday_url += '?ServiceKey=' + str(os.getenv('HOLIDAY_KEY'))
        self.holiday_url += '&solYear={year}'        # 연도 지정
        self.holiday_url += '&solMonth={month:02d}'  # 월 지정
        self.holiday_url += '&_type=json'            # json으로 응답

        self.signgu_code_info = pd.read_excel('data/한국관광공사_OpenAPI_관광지_시군구_코드정보_v1.0.xlsx') # 각 시군구별 지역코드 및 시군구코드

        # 주소에서 시군구를 추출하기 위한 리스트
        # 길이가 긴 시군구 먼저 매칭되도록 내림차순 정렬
        self.sigungu_list = sorted(self.signgu_code_info['sigunguNm'].drop_duplicates().tolist(), key=len, reverse=True)

        self.minmax_per_signgu = pd.read_pickle('data/min_max_per_signgu.pkl') # 지역별 월 평균 방문자수 최저, 최고치
        self.tounum_per_day = pd.read_pickle('data/tounum_per_day.pkl') # 전년도 방문자수 추가용 데이터셋
        self.model = joblib.load('data/is_peak_model.pkl')
        # 날짜, 지역에 따른 방문자수 예측 모델
        # signguCode, daywkDivCd, previous_year_touNum, isDayOff, isLongHoliday, year, month, day, day_of_year

        self.tounum_per_day['baseYmd'] = pd.to_datetime(self.tounum_per_day['baseYmd'])

        self.metropolitan = ['서울특별시', '부산광역시', '대구광역시', '인천광역시',
                             '광주광역시', '대전광역시', '울산광역시', '제주특별자치도' ] # 광역시는 별도 처리 필요
        
    def extract_sigungu(self, destination):
        """
        주소 문자열에서 sigunguNm 목록 중 일치하는 항목을 추출합니다.\n
        지역과 함께 시군구를 반환합니다.\n
        destination : '부산광역시 해운대구 달맞이길'\n
        반환 : ('부산광역시', '해운대구')
        """
        for sigungu in self.sigungu_list:
            if sigungu in destination:
                return destination.split()[0], sigungu
                
        return None, None

    def get_area_signgu_code(self, destination):
        """
        여행지의 시군구코드를 찾아 반환합니다.\n
        signgu : '해운대구'
        """
        area, signgu = self.extract_sigungu(destination)

        if not area:
            return -1
        # 주소가 '부산', '서울' 로 되어있는 경우라도 '부산광역시', '서울특별시'와 매칭되도록 contatins 사용
        signgu_cd = self.signgu_code_info[(self.signgu_code_info['areaNm'].str.contains(area))
                                          &(self.signgu_code_info['sigunguNm'] == signgu)]['sigunguCd'].values
        if len(signgu_cd) == 0:
            return -1
        return signgu_cd[0]

    def is_peak_season(self, trip_date, trip_period, destination):
        """
        여행 날짜, 여행지를 입력받아 성수기일지 예측합니다.\n
        해당 기간동안의 방문객 비율의 평균을 반환합니다.\n
        destination에 해당하는 시군구를 찾지 못했을 때는 None을 반환합니다.\n
        trip_date : datetime\n
        trip_period : 여행 기간\n
        destination : '부산광역시 해운대구 달맞이길'
        """
        sigungu_cd = self.get_area_signgu_code(destination)
        if sigungu_cd == -1:
            return None

        sigungu_cd = str(sigungu_cd)

        start_date = pd.to_datetime(trip_date)
        end_date = pd.to_datetime(trip_date) + timedelta(days=(trip_period-1)) # 여행기간은 출발날짜를 포함하므로 -1
        period = pd.date_range(start=start_date, end=end_date) # 여행하는 날짜들

        return self.predict_tounum(period, sigungu_cd)

    def predict_tounum(self, period, signgu_cd):
        """
        여행지의 시군구코드와 여행 기간을 입력받아 방문자 수를 예측합니다.\n
        여행 기간 동안의 방문자 수 평균을 평균 최저치, 최대치와 비교합니다.\n
        최저를 0, 최대를 100으로 할 때 예측된 방문자 수의 비율을 계산해 반환합니다.\n
        period : [datetime, datetime, ...]
        """
        sum = 0
        for date in period:
            is_dayoff, long_holiday = self.is_dayoff(date)
            if date.year >= 2027: # 2026년에 대한 방문자수 정보가 없으므로
                temp_str = f'2026-{date.month:02d}-{date.day:02d}' # 2025년 정보를 사용하기 위해 date.year를 2026으로 설정
                date = pd.to_datetime(temp_str)
            pre_year_tounum = self.tounum_per_day[(self.tounum_per_day['signguCode'] == signgu_cd) &
                                                (self.tounum_per_day['baseYmd'] == str(date - relativedelta(years=1)))
                                                ]['touNum'].values[0]
            X = pd.DataFrame({
                'signguCode' : [signgu_cd],
                'daywkDivCd' : [date.dayofweek],
                'previous_year_touNum' : [pre_year_tounum],
                'isDayOff' : [is_dayoff],
                'isLongHoliday' : [long_holiday],
                'year':[date.year], 'month':[date.month], 'day':[date.day], 'day_of_year':[date.day_of_year]
                })
            sum += self.model.predict(X)[0]
        mean_tounum = sum / len(period)
        minmax = self.minmax_per_signgu[self.minmax_per_signgu['signguCode'] == signgu_cd]['month_touNum_mean'].values
        min_mean, max_mean = minmax[0], minmax[1]

        return (mean_tounum - min_mean) / (max_mean - min_mean)

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
        if day_of_wk == 5 or day_of_wk == 6 or is_holiday:
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
            if day_of_wk == 5 or day_of_wk == 6 or is_holiday:
                # 일요일 or 토요일인 경우, 공유일 list에 포함되는 경우 휴일
                streak +=  1

        if streak == 3:
            return 1 # 3일 연속 휴일이라면 연휴
        else:
            return 0 # 하루라도 아니라면 0

if __name__=='__main__':
    trip_date = '20260819'
    destination = '서울 중구 사직로 161'
    load_dotenv()
    estimate_peak = EstimatePeak()

    print(estimate_peak.is_peak_season(trip_date, 3, destination))