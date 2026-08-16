import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys

# 현재 파일 기준 상위(최상위) 폴더 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# from pathlib import Path
# # 프로젝트 루트 경로 추가
# PROJECT_ROOT = Path(__file__).resolve().parent.parent

# if str(PROJECT_ROOT) not in sys.path:
#     sys.path.insert(0, str(PROJECT_ROOT))

# from modules.functions import recommend_destination
from model.Ruse import recommend_destination
from model.estimate_expense import estimate_expense
from model.estimate_peak import EstimatePeak

from main import recommend_places
from new import get_accommodations, get_weather

from model.estimate_peak import EstimatePeak

from transport.api import (
    get_train_city_codes,
    get_express_bus_city_codes,
    get_intercity_bus_city_codes,
    get_train_stations,
    get_express_bus_terminal_list,
    get_intercity_bus_terminal_list,
    get_airport_codes,
    get_domestic_airport_list
)

from transport.transport_service import get_transport_options

# ==========================================
# 입력값 코드
# ==========================================

# 성별
SEX_CODES = {
    1: '남성',
    2: '여성'
}

# 연령대
AGE_CODES = {
    1: '15~19세',
    2: '20대',
    3: '30대',
    4: '40대',
    5: '50대',
    6: '60대 이상'
}

# 본인 포함 여행 인원수
GROUP_CODES = {
    1: '1명',
    2: '2명',
    3: '3명 이상'
}

# 여행 테마
THEME_CODES = {
    1: '식도락(음식/미식) 관광',
    2: '쇼핑',
    3: '자연경관 감상',
    4: '휴양/휴식(웰니스)',
    5: '고궁/역사 유적지 방문',
    6: '전통문화 체험',
    7: '박물관·전시관 관람',
    8: 'K-POP·한류 콘텐츠 관광',
    9: '연극·뮤지컬·발레 등 공연 관람',
    10: '지역 축제 참여',
    11: '유흥·나이트라이프·카지노',
    12: '놀이공원·테마파크',
    13: '뷰티·미용 관광',
    14: '치료·건강검진',
    15: '스포츠·레포츠 관람',
    16: '스포츠·레포츠 참가',
    17: '기타'
}

# 희망 권역
AREA_OPTIONS = [
    '전체',
    '수도권',
    '지방'
]


# ==========================================
# 이동 정보 - 출발지, 추천 기준 범주
# ==========================================

DEPARTURE_OPTIONS = [
    "서울",
    "부산",
    "대구",
    "인천",
    "광주",
    "대전",
    "울산",
    "세종",
    "경기",
    "강원",
    "충북",
    "충남",
    "전북",
    "전남",
    "경북",
    "경남",
    "제주",
]

OPTION_OPTIONS = {
    "빠른 교통편": "fast",
    "저렴한 교통편": "cheap",
    "편한 교통편": "comfort",
    "환승 적은 교통편": "transfer",
    "원하는 시간대": "time",
}

AIRPORT_NAME_MAP = {
    '서울': '김포국제공항',
    '서울특별시': '김포국제공항',

    '부산': '김해국제공항',
    '부산광역시': '김해국제공항',

    '대구': '대구국제공항',
    '대구광역시': '대구국제공항',

    '인천': '인천국제공항',
    '인천광역시': '인천국제공항',

    '광주': '광주공항',
    '광주광역시': '광주공항',

    '울산': '울산공항',
    '울산광역시': '울산공항',

    '강원': '양양국제공항',
    '강원도': '양양국제공항',

    '충북': '청주국제공항',
    '충청북도': '청주국제공항',

    '전북': '군산공항',
    '전라북도': '군산공항',

    '전남': '무안국제공항',
    '전라남도': '무안국제공항',

    '경북': '포항경주공항',
    '경상북도': '포항경주공항',

    '경남': '김해국제공항',
    '경상남도': '김해국제공항',

    '제주': '제주국제공항',
    '제주도': '제주국제공항',
}


# ==========================================
# 함수
# ==========================================

# 코드 변환
def get_code(label, code_dict):
    return next(
        code
        for code, value in code_dict.items()
        if value == label
    )

# 소요 시간 포멧 변환 (분 -> 시간, 분)
def format_duration(minutes):
    if minutes is None:
        return None

    hours = minutes // 60
    mins = minutes % 60

    if hours > 0 and mins > 0:
        return f'{hours}시간 {mins}분'
    elif hours > 0:
        return f'{hours}시간'
    else:
        return f'{mins}분'


def _extract_items(data):
    """
    공공데이터 API 응답에서 item 목록만 추출합니다.
    """
    if not isinstance(data, dict):
        return []

    response = data.get('response', data)

    if not isinstance(response, dict):
        return []

    body = response.get('body', {})

    if not isinstance(body, dict):
        return []

    items = body.get('items', {})

    if isinstance(items, dict):
        items = items.get('item', [])

    if isinstance(items, dict):
        return [items]

    if isinstance(items, list):
        return items

    return []

def _find_city_code(
    city_name,
    city_code_data,
    name_key='cityname',
    code_key='citycode'
):
    """
    지역명 → 공공데이터 API city_code
    """

    items = _extract_items(city_code_data)

    aliases = {
        '서울': '서울특별시',
        '부산': '부산광역시',
        '대구': '대구광역시',
        '인천': '인천광역시',
        '광주': '광주광역시',
        '대전': '대전광역시',
        '울산': '울산광역시',
        '세종': '세종특별시',
        '경기': '경기도',
        '강원': '강원도',
        '충북': '충청북도',
        '충남': '충청남도',
        '전북': '전라북도',
        '전남': '전라남도',
        '경북': '경상북도',
        '경남': '경상남도',
        '제주': '제주도',
    }

    target_name = aliases.get(city_name, city_name)

    for item in items:
        if item.get(name_key) == target_name:
            return item.get(code_key)

    return None

def _find_first_station(city_code):
    """
    city_code에 해당하는 대표 기차역 1개를 반환합니다.
    """

    data = get_train_stations(city_code)
    stations = _extract_items(data)

    if not stations:
        return None

    return stations[0].get('nodeid')

def _normalize_bus_city_name(city_name):
    """
    앱에서 사용하는 지역명을
    고속/시외버스 터미널 API 검색용 지역명으로 변환합니다.
    """

    aliases = {
        '서울특별시': '서울',
        '부산광역시': '부산',
        '대구광역시': '대구',
        '인천광역시': '인천',
        '광주광역시': '광주',
        '대전광역시': '대전',
        '울산광역시': '울산',
        '세종특별자치시': '세종',
        '세종특별시': '세종',

        '경기도': '경기',
        '강원도': '강원',
        '충청북도': '충북',
        '충청남도': '충남',
        '전라북도': '전북',
        '전라남도': '전남',
        '경상북도': '경북',
        '경상남도': '경남',
        '제주특별자치도': '제주',
        '제주도': '제주',
    }

    return aliases.get(
        city_name,
        city_name
    )

# 여러 터미널이 존재하는 지역의 대표 고속버스터미널
EXPRESS_TERMINAL_PREFERENCE = {
    '서울': ['서울경부', '센트럴시티(서울)', '동서울'],
    '부산': ['부산', '부산시외', '부산사상'],
}

# 여러 터미널이 존재하는 지역의 대표 시외버스터미널
# 서울 → 부산 장거리 조회에서는 서울남부 → 부산서부(사상)을 우선 사용
INTERCITY_TERMINAL_PREFERENCE = {
    '서울': ['서울남부'],
    '부산': ['부산서부(사상)', '부산서부(사상)/심야', '부산동부'],
}


def _find_preferred_terminal(terminals, preferred_names):
    """검색된 터미널 중 대표 터미널을 우선 선택합니다."""

    if not terminals:
        return None

    for preferred_name in preferred_names:
        for terminal in terminals:
            if terminal.get('terminalNm') == preferred_name:
                return terminal.get('terminalId')

    # 대표 터미널이 없으면 검색 결과의 첫 번째 터미널을 사용
    return terminals[0].get('terminalId')


def _find_first_express_terminal(city_name):

    city_name = _normalize_bus_city_name(
        city_name
    )

    data = get_express_bus_terminal_list(
        terminal_nm=city_name,
        num_of_rows=100
    )

    terminals = _extract_items(data)

    if not terminals:
        return None

    preferred_names = EXPRESS_TERMINAL_PREFERENCE.get(
        city_name,
        []
    )

    return _find_preferred_terminal(
        terminals,
        preferred_names
    )


def _find_first_intercity_terminal(city_name):

    city_name = _normalize_bus_city_name(
        city_name
    )

    data = get_intercity_bus_terminal_list(
        terminal_nm=city_name,
        num_of_rows=100
    )

    terminals = _extract_items(data)

    if not terminals:
        return None

    preferred_names = INTERCITY_TERMINAL_PREFERENCE.get(
        city_name,
        []
    )

    return _find_preferred_terminal(
        terminals,
        preferred_names
    )

def _find_airport_id(city_name, airport_data):
    airport_name = AIRPORT_NAME_MAP.get(city_name)

    if not airport_name:
        return None

    for item in _extract_items(airport_data):
        if item.get('airportNm') == airport_name:
            return item.get('airportId')

    return None

# 교통수단 지역-ID 매핑
def _normalize_city_for_compare(city_name):
    aliases = {
        '서울': '서울특별시',
        '부산': '부산광역시',
        '대구': '대구광역시',
        '인천': '인천광역시',
        '광주': '광주광역시',
        '대전': '대전광역시',
        '울산': '울산광역시',
        '세종': '세종특별시',
        '경기': '경기도',
        '강원': '강원도',
        '충북': '충청북도',
        '충남': '충청남도',
        '전북': '전라북도',
        '전남': '전라남도',
        '경북': '경상북도',
        '경남': '경상남도',
        '제주': '제주도',
    }

    return aliases.get(city_name, city_name)


def get_transport_ids(departure, arrival):

    if not departure or not arrival:
        raise ValueError(
            '출발지 또는 도착지가 없습니다.'
        )

    # 동일 지역 여부는 get_transport_results()에서 처리합니다.
    # 여기서는 다른 지역의 교통수단 ID 매핑만 담당합니다.

    # ==========================================
    # 1. 기차 city code
    # ==========================================

    train_city_codes = get_train_city_codes()

    train_city_code_fallback = {
        '인천': '23',
    }

    dep_train_city_code = train_city_code_fallback.get(
        departure,
        _find_city_code(
            departure,
            train_city_codes,
            name_key='cityname',
            code_key='citycode'
        )
    )

    arr_train_city_code = train_city_code_fallback.get(
        arrival,
        _find_city_code(
            arrival,
            train_city_codes,
            name_key='cityname',
            code_key='citycode'
        )
    )

    dep_train_id = (
        _find_first_station(dep_train_city_code)
        if dep_train_city_code
        else None
    )

    arr_train_id = (
        _find_first_station(arr_train_city_code)
        if arr_train_city_code
        else None
    )

    # ==========================================
    # 2. 고속버스
    # ==========================================

    dep_express_id = _find_first_express_terminal(
        departure
    )

    arr_express_id = _find_first_express_terminal(
        arrival
    )

    # ==========================================
    # 3. 시외버스
    # ==========================================

    dep_intercity_id = _find_first_intercity_terminal(
        departure
    )

    arr_intercity_id = _find_first_intercity_terminal(
        arrival
    )

    # ==========================================
    # 4. 항공
    # ==========================================

    airport_data = get_domestic_airport_list(
        pageNo=1,
        numOfRows=100
    )

    dep_airport_id = _find_airport_id(
        departure,
        airport_data
    )

    arr_airport_id = _find_airport_id(
        arrival,
        airport_data
    )

    # ==========================================
    # 5. 결과
    # ==========================================

    return {
        'train': {
            'dep_place_id': dep_train_id,
            'arr_place_id': arr_train_id
        },

        'express_bus': {
            'dep_terminal_id': dep_express_id,
            'arr_terminal_id': arr_express_id
        },

        'intercity_bus': {
            'dep_terminal_id': dep_intercity_id,
            'arr_terminal_id': arr_intercity_id
        },

        'flight': {
            'depAirportId': dep_airport_id,
            'arrAirportId': arr_airport_id
        }
    }

def get_transport_results(
    departure,
    arrival,
    trip_date,
    option,
    time_after=None,
):

    # 동일 지역은 해당 여행지만 교통편 조회를 건너뜁니다.
    # 다른 추천 여행지의 교통편 조회에는 영향을 주지 않습니다.
    if (
        _normalize_city_for_compare(departure)
        == _normalize_city_for_compare(arrival)
    ):
        print(
            f'{departure} → {arrival} : 동일 지역이므로 '
            '교통편 조회를 건너뜁니다.'
        )

        empty_ids = {
            'train': {
                'dep_place_id': None,
                'arr_place_id': None
            },
            'express_bus': {
                'dep_terminal_id': None,
                'arr_terminal_id': None
            },
            'intercity_bus': {
                'dep_terminal_id': None,
                'arr_terminal_id': None
            },
            'flight': {
                'depAirportId': None,
                'arrAirportId': None
            }
        }

        return empty_ids, []

    transport_ids = get_transport_ids(
        departure,
        arrival
    )

    transport_types = []
    kwargs = {}

    if (
        transport_ids['train']['dep_place_id']
        and transport_ids['train']['arr_place_id']
    ):
        transport_types.append('train')
        kwargs['train'] = transport_ids['train']

    if (
        transport_ids['express_bus']['dep_terminal_id']
        and transport_ids['express_bus']['arr_terminal_id']
    ):
        transport_types.append('express_bus')
        kwargs['express_bus'] = transport_ids['express_bus']

    if (
        transport_ids['intercity_bus']['dep_terminal_id']
        and transport_ids['intercity_bus']['arr_terminal_id']
    ):
        transport_types.append('intercity_bus')
        kwargs['intercity_bus'] = transport_ids['intercity_bus']

    if (
        transport_ids['flight']['depAirportId']
        and transport_ids['flight']['arrAirportId']
    ):
        transport_types.append('flight')
        kwargs['flight'] = transport_ids['flight']

    if not transport_types:
        raise ValueError(
            f'{departure} → {arrival} 구간에서 조회 가능한 교통수단이 없습니다.'
        )
    
    results = get_transport_options(
        transport_types=transport_types,
        date=trip_date.strftime('%Y%m%d'),
        **kwargs,
    )

    # ==========================================
    # API 원본 결과 확인
    # ==========================================

    raw_result_count = len(results)

    print('====================================')
    print('교통 API 조회 테스트')
    print(f'출발지: {departure}')
    print(f'도착지: {arrival}')
    print(f'날짜: {trip_date.strftime("%Y%m%d")}')
    print(f'추천 기준: {option}')
    print(f'시간 조건: {time_after}')
    print(f'조회 교통수단: {transport_types}')
    print(f'교통수단 ID: {transport_ids}')
    print(f'API 원본 결과: {raw_result_count}건')

    if results:
        print('출발시간 목록:')
        print([
            item.get('departure_time')
            for item in results
        ])

    # ==========================================
    # 시간 필터
    # ==========================================

    if time_after:

        results = [
            item for item in results
            if item.get('departure_time')
            and item['departure_time'] >= time_after
        ]

        print(
            f'시간 필터 적용 후: {len(results)}건'
        )

    print('====================================')

    if option == 'fast':
        results.sort(key=lambda x: x.get('duration') if x.get('duration') is not None else 999999)
    elif option == 'cheap':
        results.sort(key=lambda x: x.get('price') if x.get('price') is not None else 999999999)
    elif option == 'comfort':
        results.sort(key=lambda x: (
            x.get('transfers', 999),
            x.get('duration') if x.get('duration') is not None else 999999
        ))
    elif option == 'transfer':
        results.sort(key=lambda x: x.get('transfers', 999))
    elif option == 'time':
        results.sort(key=lambda x: x.get('departure_time', '99:99'))

    return transport_ids, results

def _display_transport_item(item):
    st.info(item.get('name', item.get('transport_type', '교통편')))

    st.write(
        f"교통수단: {item.get('transport_type', '-')}"
    )

    st.write(
        f"{item.get('departure', '')} ➤ {item.get('arrival', '')}"
    )

    st.write(
        f"출발: {item.get('departure_time', '-')}"
    )

    st.write(
        f"도착: {item.get('arrival_time', '-')}"
    )

    if item.get('duration') is not None:
        st.write(
            f"소요 시간: {format_duration(item['duration'])}"
        )

    if item.get('price') is not None:
        st.write(
            f"가격: {item['price']:,}원"
        )

    if item.get('transfers') is not None:
        st.write(
            f"환승: {item['transfers']}회"
        )


# ==========================================
# API 환경 설정
# ==========================================

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# 키 없을 경우 예외처리
if not api_key:
    st.error('api key가 존재하지 않습니다.')
    st.stop()

client = OpenAI(api_key=api_key)

# ==========================================
# 객체 선언
# ==========================================
estimate_peak = EstimatePeak()


# ==========================================
# 페이지 레이아웃
# ==========================================

st.set_page_config(
    page_title='K-Guide',
    layout='wide'
)

st.title('K-Guide')
st.caption('AI 기반 여행 추천 서비스')


# ==========================================
# Session State
# ==========================================

# 화면 상태 저장
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = '여행 추천'

# 추천 여행지 결과 저장
if 'destinations' not in st.session_state:
    st.session_state.destinations = []

# 선택된 여행지 저장
if 'selected_recommendation' not in st.session_state:
    st.session_state.selected_recommendation = None

# 여행지별 정보 결과 저장
if 'recommendation_context' not in st.session_state:
    st.session_state.recommendation_context = []

# API 결과 저장
if 'api_context' not in st.session_state:
    st.session_state.api_context = []

# 여행 추천 실행 여부 저장
if 'trip_started' not in st.session_state:
    st.session_state.trip_started = False

# 챗봇 대화 기록 저장
if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------------------------------
# 항공 / 교통 추천 관련
# ------------------------------------------
# 이동 정보 설정 여부
if 'transport_enabled' not in st.session_state:
    st.session_state.transport_enabled = None

# 출발 지역
if 'departure' not in st.session_state:
    st.session_state.departure = None

# 교통편 추천 기준
if 'transport_option' not in st.session_state:
    st.session_state.transport_option = None

# 원하는 출발 시간
if 'time_after' not in st.session_state:
    st.session_state.time_after = None

# 항공/교통 API 요청 데이터 저장
if 'transport_requests' not in st.session_state:
    st.session_state.transport_requests = None


if 'transport_results' not in st.session_state:
    st.session_state.transport_results = {}

if 'transport_ids' not in st.session_state:
    st.session_state.transport_ids = None

# ==========================================
# 사용자 입력 영역
# ==========================================

# 사이드바
st.sidebar.title('사용자 입력 조건')

# 추천 내용 전체 초기화
if st.sidebar.button('추천 내용 초기화'):

    st.session_state.current_tab = '여행 추천'
    st.session_state.destinations = []
    st.session_state.selected_recommendation = None
    st.session_state.recommendation_context = []

    st.session_state.api_context = []
    st.session_state.trip_started = False
    st.session_state.messages = []

    st.session_state.transport_enabled = None
    st.session_state.departure = None
    st.session_state.transport_option = None
    st.session_state.time_after = None
    st.session_state.transport_requests = None
    st.session_state.transport_results = {}
    st.session_state.transport_ids = None

    st.toast('추천 내용이 초기화 되었습니다.')


# 성별
gender_label = st.sidebar.radio(
    '성별',
    list(SEX_CODES.values())
)

gender = get_code(gender_label, SEX_CODES)


# 나이
age_label = st.sidebar.selectbox(
    '연령대',
    list(AGE_CODES.values())
)

age = get_code(age_label, AGE_CODES)


# 여행 테마
theme_label = st.sidebar.selectbox(
    '여행 테마',
    list(THEME_CODES.values())
)

theme = get_code(theme_label, THEME_CODES)


# 인원수
num_of_people_label = st.sidebar.selectbox(
    '본인 포함 여행 인원수',
    list(GROUP_CODES.values())
)

num_of_people = get_code(num_of_people_label, GROUP_CODES)


# 희망 권역
area = st.sidebar.selectbox(
    '희망 권역',
    AREA_OPTIONS
)

# 여행 날짜
trip_date = st.sidebar.date_input(
    '출발 날짜'
)

# 여행 기간
period = st.sidebar.number_input(
    '여행 기간',
    min_value=1,
    value=3
)


# ==========================================
# 메뉴 선택 (여행 추천 / 챗봇)
# ==========================================

selected_tab = st.radio(
    '메뉴',
    ['여행 추천', 'K-Guide AI'],
    horizontal=True,
    label_visibility='collapsed',
    index=(
        0 if st.session_state.current_tab == '여행 추천'
        else 1
    )
)

# Radio에서 직접 선택한 화면을 Session State에 반영
if selected_tab != st.session_state.current_tab:
    st.session_state.current_tab = selected_tab
    st.rerun()


# ==========================================
# 더미 데이터
# 실제 모델 연결 전 UI 테스트를 위한 더미 데이터
# ==========================================

# 여행지 추천
# def recommend_destination(gender, age, theme, num_of_people):
# 	"""
# 	성별, 나이, 테마, 인원수를 입력받아 관광지별 선호도를 예측합니다.
# 	예측도가 가장 높은 상위 3개 여행지를 반환합니다.
# 	"""
# 	return [
#         {
#             'rank': 1,
#             'destination': '서울특별시',
#             'score': 91.7
#         },
#         {
#             'rank': 2,
#             'destination': '인천광역시',
#             'score': 82.9
#         },
#         {
#             'rank': 3,
#             'destination': '부산광역시',
#             'score': 77.1
#         }
#     ]

# 예상 경비
# def estimate_expense(period, destination, num_of_people, theme):
# 	"""
# 	여행 기간, 여행지, 인원수, 여행 테마를 입력받아
# 	1인당 1일 예상 경비를 예측해 반환합니다.
# 	"""
# 	return 300000

# API
def create_dummy_api_context(destinations):

    api_context = []

    for recommendation in destinations:

        destination = recommendation['destination']
        # 여행지별 더미 데이터
        data = {

            'destination': destination,

            'accommodations': [
                {
                    'name': f'{destination} K-Guide 호텔',
                    'address': f'{destination} 중심가 123',
                    'url': 'http://place.map.kakao.com/00000001'
                },
                {
                    'name': f'{destination} 시티 호텔',
                    'address': f'{destination} 중앙로 45',
                    'url': 'http://place.map.kakao.com/00000002'
                },
                {
                    'name': f'{destination} 관광호텔',
                    'address': f'{destination} 해안로 120',
                    'url': 'http://place.map.kakao.com/00000003'
                },
                {
                    'name': f'{destination} 스테이',
                    'address': f'{destination} 문화길 18',
                    'url': 'http://place.map.kakao.com/00000004'
                },
                {
                    'name': f'{destination} 비즈니스 호텔',
                    'address': f'{destination} 교통광장로 112',
                    'url': 'http://place.map.kakao.com/00000005'
                }
            ],

            'restaurants': [
                {
                    'name': f'{destination} 밤실마을',
                    'category': '한식',
                    'address': f'{destination} 북구 밤실로 163-9',
                    'opening_hours': '11:00~22:00',
                    'representative_menu': '국밥 / 김밥 / 국수 등',
                    'mapx': '126.9344',
                    'mapy': '35.1617',
                    'description': f'{destination} 지역의 한식 맛집입니다.',
                },
                {
                    'name': f'{destination} 모나리자531',
                    'category': '카페/전통찻집',
                    'address': f'{destination} 북구 삼소로 352',
                    'opening_hours': '평일 10:00~22:00 / 식사 10:30~19:30',
                    'representative_menu': '모과티 / 아메리카노 / 에이드 등',
                    'mapx': '126.8714',
                    'mapy': '35.1720',
                    'description': f'{destination}의 분위기 좋은 카페/전통찻집입니다.',
                },
                {
                    'name': f'{destination} 해피맛집',
                    'category': '일식',
                    'address': f'{destination} 서구 상무중앙로 16',
                    'opening_hours': '12:00~22:00',
                    'representative_menu': '연어 / 돈까스 / 하이볼 등',
                    'mapx': '126.8587',
                    'mapy': '35.1520',
                    'description': f'{destination}에서 다양한 메뉴를 즐길 수 있는 맛집입니다.',
                }
            ],

            'weather': {
                'max_temp': 32,
                'min_temp': 21,
                'weather': '맑음',
                'rain_probability': 20
            },

            'tourist_attractions': [
                {
                    'name': f'{destination} 전통문화관',
                    'category': '전시관',
                    'address': f'{destination} 동구 의재로 222',
                    'opening_hours': '09:00~18:00',
                    'mapx': '126.9524',
                    'mapy': '35.1617',
                    'description': f'{destination}의 전통과 문화를 체험할 수 있는 매력적인 전시관 공간입니다.'
                },
                {
                    'name': f'{destination} 중외공원',
                    'category': '공원',
                    'address': f'{destination} 북구 무등로 1550',
                    'opening_hours': '상시 개방',
                    'mapx': '126.9622',
                    'mapy': '35.2162',
                    'description': f'{destination}의 아름다운 풍경과 볼거리가 가득한 인기 공원입니다.'
                },
                {
                    'name': f'{destination} 운천저수지',
                    'category': '강',
                    'address': f'{destination} 서구 운천로 165',
                    'opening_hours': '상시 개방',
                    'mapx': '126.8582',
                    'mapy': '35.1472',
                    'description': f'{destination}에서 여행 중 잠깐 들러볼 만한 매력적인 장소입니다.'
                }
            ],

            # 'flights': [
            #     {
            #         'transport_type': 'flight',
            #         'name': '대한항공',
            #         'departure': '김포공항',
            #         'arrival': destination,
            #         'departure_time': '09:30',
            #         'arrival_time': '10:40',
            #         'duration': 70,
            #         'price': 85000,
            #         'price_type': 'api',
            #         'transfers': 0
            #     }
            # ],

            # 'transportation': [
            #     {
            #         'transport_type': 'train',
            #         'name': 'KTX',
            #         'departure': '서울역',
            #         'arrival': destination,
            #         'departure_time': '09:30',
            #         'arrival_time': '10:40',
            #         'duration': 120,
            #         'price': 50000,
            #         'price_type': 'api',
            #         'transfers': 0
            #     }
            # ]
        }

        api_context.append(data)

    return api_context

# ==========================================
# API 데이터
# 날씨, 관광지, 숙소, 맛집 정보
# ==========================================
def create_api_context(destinations):
    api_context = []

    for recommendation in destinations:
        destination = recommendation['destination']
        restaurant_attraction = recommend_places(destination, theme)
        data = {
            'destination' : destination,
            'accommodations' : get_accommodations(destination),
            'weather' : get_weather(destination),
            'restaurants': restaurant_attraction['restaurants'],
            'tourist_attractions' : restaurant_attraction['tourist_attractions']
        }
        api_context.append(data)
    
    return api_context

# ==========================================
# 여행 추천 결과
# ==========================================

if selected_tab == '여행 추천':
                
    # 추천 시작 버튼
    if st.sidebar.button('여행 추천 받기'):

        with st.status('맞춤 여행지를 분석합니다...', expanded=True) as status:

            # 여행지 추천
            try:
                st.write('여행지 추천 중...')

                st.session_state.destinations = recommend_destination(
                                    gender=gender,
                                    age=age,
                                    num_of_people=num_of_people,
                                    theme=theme,
                                    preferred_area=area,
                                    top_n=3
                                )

                # 추천 결과가 없는 경우
                if not st.session_state.destinations:
                    raise ValueError('추천 여행지가 없습니다.')
        
                # 성수기 비수기 / 경비 계산
                st.write('여행지별 정보 분석 중...')

                recommendation_context=[]

                for recommendation in st.session_state.destinations:
                    destination = recommendation['destination']
                    # 예상 경비
                    try:
                        expense = estimate_expense(
                            period,
                            destination,
                            num_of_people,
                            theme,
                            age
                        )
                    except Exception:
                        expense = None

                    recommendation_context.append({
                        'rank': recommendation['rank'],
                        'destination': destination,
                        'score': recommendation['score'],
                        #'peak_season': peak,
                        'expense': expense
                    })

                # 결과 저장
                st.session_state.recommendation_context = (
                    recommendation_context
                )

                # ==========================================
                # API 더미 데이터 생성
                # ------------------------------------------
                st.write('여행 정보 준비 중...')
                st.session_state.api_context = (
                    create_api_context(
                        st.session_state.destinations
                    )
                )
                # ==========================================

                st.session_state.trip_started = True

                st.write('추천 여행지 분석 완료')

                status.update(
                    label='여행지 추천 완료!',
                    state='complete',
                    expanded=False
                )
            except Exception as e:
                st.error(f'여행지 추천 중 오류가 발생했습니다. : {e}')    

    # ==========================================
    # 여행 추천 결과 출력
    # 여행지 후보 / 성수기/비수기 / 예상경비
    # ==========================================

    # ==========================================
    # 항공 / 교통 정보 설정
    # ==========================================

    if (
        st.session_state.trip_started
        and st.session_state.transport_enabled is None
    ):
        st.subheader('이동 정보 설정')

        st.write('항공편 및 교통편 정보를 함께 추천 받으시겠습니까?')
        st.info('추천된 여행지 3곳을 기준으로 이동 정보를 조회합니다.')

        departure = st.selectbox(
            '출발 지역',
            DEPARTURE_OPTIONS
        )

        transport_option_label = st.selectbox(
            '교통편 추천 기준',
            list(OPTION_OPTIONS.keys())
        )

        use_time_filter = st.checkbox(
            '원하는 출발 시간 설정'
        )

        if use_time_filter:
            time_after = st.time_input(
                '이 시간 이후 출발'
            )
        else:
            time_after = None

        col1, col2 = st.columns(2)

        with col1:
            submit_transport = st.button(
                '입력하고 추천받기',
                use_container_width=True
            )

        with col2:
            skip_transport = st.button(
                '건너뛰기',
                use_container_width=True
            )

        # ==========================================
        # 입력하고 추천받기
        # ==========================================

        if submit_transport:
            st.session_state.transport_enabled = True

            st.session_state.departure = departure

            st.session_state.transport_option = (
                OPTION_OPTIONS[transport_option_label]
            )

            st.session_state.time_after = (
                time_after.strftime('%H:%M')
                if time_after is not None
                else None
            )

            # 여행지별 API 요청 데이터 생성

            option = OPTION_OPTIONS[
                transport_option_label
            ]

            time_after_str = (
                time_after.strftime('%H:%M')
                if time_after is not None
                else None
            )

            try:

                with st.spinner(
                    '교통편 정보를 조회하고 있습니다...'
                ):

                    transport_results = {}

                    # 추천 여행지 3곳 각각 조회
                    # 한 여행지에서 오류가 나더라도 나머지 여행지는 계속 조회합니다.
                    for recommendation in (
                        st.session_state.destinations
                    ):

                        destination = (
                            recommendation['destination']
                        )

                        try:
                            transport_ids, results = (
                                get_transport_results(
                                    departure=departure,
                                    arrival=destination,
                                    trip_date=trip_date,
                                    option=option,
                                    time_after=time_after_str
                                )
                            )

                        except Exception as destination_error:
                            print(
                                f'{departure} → {destination} '
                                f'교통편 조회 실패: {destination_error}'
                            )

                            transport_ids = {
                                'train': {
                                    'dep_place_id': None,
                                    'arr_place_id': None
                                },
                                'express_bus': {
                                    'dep_terminal_id': None,
                                    'arr_terminal_id': None
                                },
                                'intercity_bus': {
                                    'dep_terminal_id': None,
                                    'arr_terminal_id': None
                                },
                                'flight': {
                                    'depAirportId': None,
                                    'arrAirportId': None
                                }
                            }

                            results = []

                        transport_results[destination] = {
                            'transport_ids': transport_ids,
                            'results': results
                        }

                # 실제 조회 결과 저장

                st.session_state.transport_results = (
                    transport_results
                )

                # 실제 교통 API 결과를 API 컨텍스트에도 반영
                for api_data in st.session_state.api_context:

                    destination = api_data.get(
                        'destination'
                    )

                    transport_data = transport_results.get(
                        destination,
                        {}
                    )

                    actual_results = transport_data.get(
                        'results',
                        []
                    )

                    api_data['transportation'] = [
                        item
                        for item in actual_results
                        if item.get('transport_type')
                        != 'flight'
                    ]

                    api_data['flights'] = [
                        item
                        for item in actual_results
                        if item.get('transport_type')
                        == 'flight'
                    ]

                # 기존 요청 정보 저장
                st.session_state.transport_requests = [
                    {
                        'departure': departure,
                        'arrival': destination,
                        'option': option,
                        'time_after': time_after_str,
                        'transport_ids': (
                            transport_results[destination]
                            ['transport_ids']
                        )
                    }
                    for destination in transport_results
                ]

                st.rerun()

            except Exception as e:

                st.error(
                    f'교통편 조회 중 오류가 발생했습니다: {e}'
                )

        # ==========================================
        # 건너뛰기
        # ==========================================

        if skip_transport:
            st.session_state.transport_enabled = False
            st.rerun()

    if (
        st.session_state.trip_started
        and st.session_state.transport_enabled is not None
    ):

        st.header('추천 여행지')

        # 추천 결과 전체 가져오기
        recommendations = st.session_state.recommendation_context


        # 추천 여행지 개수만큼 컬럼 생성
        cols = st.columns(len(recommendations))

        # 추천 결과 하나씩 출력
        for i, recommendation in enumerate(recommendations):

            with cols[i]:

                destination = recommendation['destination']
                expense = recommendation['expense']

                st.subheader(destination)

                # 예상 경비
                if expense is not None:

                    # 1인 총 예상 경비
                    base_expense = expense

                    # 1인 1일 예상 경비
                    daily_expense = base_expense / period

                    # 추천 교통편 비용
                    transport_expense = 0
                    recommended_transport_type = None

                    if st.session_state.transport_enabled:

                        transport_data = (
                            st.session_state.transport_results
                            .get(destination, {})
                        )

                        transport_results = (
                            transport_data.get('results', [])
                        )

                        # 추천 기준에 따라 정렬된 결과 중 1순위 교통편
                        if transport_results:
                            recommended_transport = transport_results[0]

                            recommended_transport_type = (
                                recommended_transport.get('transport_type')
                            )

                            transport_price = (
                                recommended_transport.get('price')
                            )

                            if transport_price is not None:
                                # 왕복 교통비
                                transport_expense = transport_price * 2

                    total_expense = base_expense + transport_expense

                    recommendation['daily_expense'] = daily_expense
                    recommendation['base_expense'] = base_expense
                    recommendation['transport_expense'] = transport_expense
                    recommendation['total_expense'] = total_expense

                    st.write(
                        f'1인 1일 예상 경비 : {daily_expense:,.0f}원'
                    )

                    if (
                        st.session_state.transport_enabled
                        and transport_expense > 0
                    ):
                        st.write(
                            f'왕복 교통비: {transport_expense:,}원'
                        )

                    st.metric(
                        '1인 총 예상 경비',
                        f'{total_expense:,.0f}원'
                    )

                else:
                    st.info('예상 경비를 확인할 수 없습니다.')

                # 계획 생성할 여행지 선택
                if st.button(
                    '이 여행지로 여행 계획 만들기',
                    key=f'plan_{destination}'
                ):
                    st.session_state.selected_recommendation = recommendation
                    st.session_state.current_tab = 'K-Guide AI'
                    st.rerun()


# ==========================================
# OpenAI 챗봇
# ==========================================

elif selected_tab == 'K-Guide AI':

    st.header("K-Guide AI")
    st.caption('여행에 대해 궁금한 점 자유롭게 질문')


    # 선택된 여행지 정보
    selected_recommendation = (
        st.session_state.selected_recommendation
    )



    # 선택된 여행지 정보 출력

    if selected_recommendation is not None:

        st.info(
            f"현재 선택한 여행지: "
            f"{selected_recommendation['destination']}"
        )

        total_expense = selected_recommendation.get('total_expense')

        if total_expense is not None:
            st.write(
            f"1인당 예상 총 경비: "
            f"{total_expense:,}원"
        )
        else:
            st.info('예상 총 경비를 확인할 수 없습니다.')

        # ==========================================
        # 사용자 기본 조건 전달 테스트
        # ------------------------------------------
        # st.write('선택 여행지:', selected_recommendation)
        # st.write('출발 날짜:', trip_date)
        # st.write('여행 기간:', period)
        # st.write('테마:', theme)
        # st.write('인원:', num_of_people)
        # ==========================================

        
        # ==========================================
        # 기능 연걸 - 기타 정보
        # ==========================================

        st.divider()
        
        # 숙소, 날씨 정보
        st.header('숙소, 날씨 정보')

        col1, col2 = st.columns(2)

        # API 더미 데이터
        api_context = st.session_state.api_context

        # 현재 선택한 여행지
        selected_destination = selected_recommendation['destination']

        # 선택한 여행지에 해당하는 API 데이터 찾기
        selected_api_context = next(
            (
                data for data in api_context
                if data['destination'] == selected_destination
            ),
            None
        )

        # 숙소
        with col1:
            st.subheader('추천 숙소')

            if selected_api_context:

                hotel_list = selected_api_context.get('accommodations', [])

                if hotel_list:

                    st.caption(f"추천 숙소 ({min(5, len(hotel_list))}곳)")
                    st.caption(f"숙소별 상세 평점 및 실시간 가격은 카카오맵 상세페이지 링크에서 확인 가능합니다.")
                    for i, hotel in enumerate(hotel_list[:5], start=1):

                        # 숙소명
                        st.info(f"{i}. {hotel['name']}")
                        # 주소
                        st.write(f"주소: {hotel['address']}")

                        # 상세보기 및 예약 링크
                        if hotel.get('url'):

                            st.link_button(
                                '상세보기 및 예약',
                                hotel['url']
                            )

                        if i < min(5, len(hotel_list)):
                            st.divider()

                    else: st.info('추천 숙소 정보가 없습니다.')

                else:
                    st.info('숙소 정보를 불러오는 중입니다.')

        # 날씨
        with col2:
            st.subheader('날씨 정보')

            if selected_api_context:

                weather = selected_api_context.get('weather', {})

                if weather:

                    st.caption('실시간 기상 예보')

                    # 날씨
                    st.info(f"날씨: {weather['weather']}")
                    # 기온
                    st.write(
                        f"최고 기온 {weather['max_temp']}°C\n"
                        f"최저 기온 {weather['min_temp']}°C"
                    )
                    # 강수 확률
                    st.write(f"강수 확률: {weather['rain_probability']}%")

                else:
                    st.info('날씨 정보가 없습니다.')

            else:
                st.info('날씨 정보를 불러오는 중입니다.')


        # 맛집, 관광지 추천
        st.header('맛집, 관광지 추천')

        col1, col2 = st.columns(2)

        # 맛집
        with col1:
            st.subheader('추천 맛집')
            
            if selected_api_context:

                restaurant_list = selected_api_context.get('restaurants', [])

                if restaurant_list:

                    st.caption(f'추천 맛집 ({len(restaurant_list)}곳)')

                    for i, restaurant in enumerate(restaurant_list[:3], start=1):

                        # 음식점명 (카테고리)
                        st.info(f"{i}. {restaurant['name']} ({restaurant['category']})")
                        # 주소
                        st.write(f"주소: {restaurant['address']}")
                        # 운영시간
                        st.write(f"운영시간: {restaurant['opening_hours']}")
                        # 대표메뉴
                        # st.write(f"대표메뉴: {restaurant['representative_menu']}")
                        # 특징
                        st.write(f"특징: {restaurant['description']}")

                        # 지도 시각화
                        if(
                            restaurant.get('mapy') is not None
                            and restaurant.get('mapx') is not None
                        ):
                            try:
                                lat = float(restaurant['mapy'])
                                lon = float(restaurant['mapx'])
                                st.map({
                                    'lat':[lat],
                                    'lon':[lon]
                                })     
                            except(TypeError, ValueError):
                                st.info('지도 좌표 정보를 표시할 수 없습니다.')

                        if i < min(3, len(restaurant_list)):
                            st.divider()
                                       
                else:
                    st.info('추천 맛집 정보가 없습니다.')

            else:           
                st.info('맛집 정보를 불러오는 중입니다.')

        # 관광지
        with col2:
            st.subheader('추천 관광지')
            
            if selected_api_context:

                attraction_list = selected_api_context.get('tourist_attractions', [])

                if attraction_list:      

                    for i, attraction in enumerate(attraction_list[:3], start=1):

                        # 광광지명 (카테고리)
                        st.info(f"{i}. {attraction['name']} ({attraction['category']})")
                        # 주소
                        st.write(f"주소: {attraction['address']}")
                        # 운영시간
                        st.write(f"운영시간: {attraction['opening_hours']}")
                        # 특징
                        st.write(f"특징: {attraction['description']}")

                        # 예상 혼잡도
                        congestion_rate = estimate_peak.is_peak_season(trip_date, period, attraction['address'])
                        if congestion_rate == None: # 0이 나오는 경우를 대비해 None과 직접 비교
                            rate_str = '혼잡도를 예상할 수 없습니다'
                        elif congestion_rate >= 0.75:
                            rate_str = '매우 혼잡'
                        elif congestion_rate >= 0.5:
                            rate_str = '혼잡'
                        elif congestion_rate >= 0.25:
                            rate_str = '한적'
                        else:
                            rate_str = '매우 한적'
                        st.write('예상 혼잡도 :', rate_str)

                        # 지도 시각화
                        if(
                            attraction.get('mapy') is not None
                            and attraction.get('mapx') is not None
                        ):
                            try:

                                lat = float(attraction['mapy'])
                                lon = float(attraction['mapx'])

                                st.map({
                                    'lat':[lat],
                                    'lon':[lon]
                                })

                            except(TypeError, ValueError):
                                st.info('지도 좌표 정보를 표시할 수 없습니다.')


                        if i < min(3, len(attraction_list)):
                            st.divider()
                                       
                else:
                    st.info('추천 관광지 정보가 없습니다.')

            else:           
                st.info('관광지 정보를 불러오는 중입니다.')

        # 항공 / 교통

        if st.session_state.transport_enabled:

            st.header('항공편, 교통편')

            # 현재 선택한 여행지의 교통 결과만 가져오기
            transport_data = (
                st.session_state.transport_results
                .get(selected_destination, {})
            )

            transport_results = (
                transport_data.get('results', [])
            )

            if not transport_results:

                if (
                    _normalize_city_for_compare(
                        st.session_state.departure
                    )
                    == _normalize_city_for_compare(
                        selected_destination
                    )
                ):
                    st.info(
                        '출발지와 여행지가 동일 지역이므로 '
                        '교통편 조회를 생략했습니다.'
                    )
                else:
                    st.warning(
                        '조건에 맞는 교통편이 없습니다.'
                    )

            else:

                st.caption(
                    f"출발지: {st.session_state.departure} "
                    f"| 추천 기준: "
                    f"{next(
                        label
                        for label, code in OPTION_OPTIONS.items()
                        if code == st.session_state.transport_option
                        )}"
                    + (
                        f" | {st.session_state.time_after} 이후"
                        if st.session_state.time_after
                        else ""
                    )
                )


                # 추천 기준에 따른 전체 교통편 1순위
                recommended_transport = transport_results[0]

                # 항공
                flights = [
                    item
                    for item in transport_results
                    if item.get('transport_type') == 'flight'
                ]

                # 기차 / 고속버스 / 시외버스
                transportation = [
                    item
                    for item in transport_results
                    if item.get('transport_type') != 'flight'
                ]

                col1, col2 = st.columns(2)

                # 항공편

                with col1:

                    st.subheader('항공편')

                    if flights:

                        for i, flight in enumerate(
                            flights[:3],
                            start=1
                        ):
                            # 전체 교통편 중 추천 1순위인 경우 표시
                            if flight is recommended_transport:
                                st.success(
                                    '추천 1순위 · 예상 경비에 반영'
                                )

                            else:
                                st.caption(
                                    f'항공편 {i}'
                                )

                            _display_transport_item(
                                flight
                            )

                            if i < min(3, len(flights)):
                                st.divider()

                    else:

                        st.info(
                            '조건에 맞는 항공편이 없습니다.'
                        )

                # 교통편

                with col2:

                    st.subheader('교통편')

                    if transportation:

                        for i, transport in enumerate(
                            transportation[:3],
                            start=1
                        ):
                            # 전체 교통편 중 추천 1순위인 경우 표시
                            if transport is recommended_transport:
                                st.success(
                                    '추천 1순위 · 예상 경비에 반영'
                                )

                            else:
                                st.caption(
                                    f'교통편 {i}'
                                )

                            _display_transport_item(
                                transport
                            )

                            if i < min(
                                3,
                                len(transportation)
                            ):
                                st.divider()

                    else:

                        st.info(
                            '조건에 맞는 교통편이 없습니다.'
                        )

    # 대화 기록 출력
    for message in st.session_state.messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

    # 사용자 질문
    if prompt := st.chat_input('질문을 입력하세요!!!'):

        # 화면에 대화 메시지 출력
        st.chat_message('user').markdown(prompt)
        # messages에 대화내용을 추가
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # Responses API를 이용해서 모델 활용
        with st.chat_message('assistant'):
            
        # ==========================================
        # UI 테스트용 출력
        # ------------------------------------------
            answer = 'K-Guide AI가 여행 정보를 분석하고 있습니다.'
            st.markdown(answer)

        st.session_state.messages.append({
            'role': 'assistant',
            'content': answer
        })
        # ==========================================
            # response = client.responses.create(
            #     model='gpt-5.5',

            #     tools=[
            #         {
            #             "type": "web_search",
            #             "search_context_size": "low", # 수집 정보 크기 최소화로 비용 절감
            #             "return_token_budget": 2000   # 검색 전용 토큰 한도를 제한하여 비용 폭증 방어
            #         }
            #     ],
            
            #     instructions=f'''
            #     당신은 한국을 방문한 외국 여행객을 위한 한국 여행 AI 어시스턴트입니다.
            #     사용자의 여행 조건과 질문을 바탕으로 친절하고 구체적인 여행 정보를 제공합니다.
                
            #     사용자의 여행 조건:
            #     - 성별 : {gender}
            #     - 나이 : {age}
            #     - 여행 테마 : {theme}
            #     - 인원수 : {num_of_people}
            #     - 출발 날짜 : {trip_date}
            #     - 여행 기간 : {period}일

            #     현재 추천된 여행지 : {st.session_state.destinations}

            #     최신 정보가 필요한 경우 웹 검색을 활용하세요.
            #     특히 날씨, 운영시간, 가격, 숙소, 맛집, 관광지, 교통편 등
            #     현재 정보가 중요한 질문의 경우에는 웹 검색을 우선으로 활용하세요.
            #     매우 중요: 첫 번째 시도가 실패하더라도 유사한 검색 쿼리를 반복하지 마십시오.
            #     1~2회 검색 내에 정확한 정보를 찾을 수 없는 경우,
            #     검색을 중단하고 보유한 데이터를 바탕으로 최선의 답변을 제공하십시오.
            #     ''',
            #     input=st.session_state.messages,
            #     stream=True,
            #     max_output_tokens=1500
            # )

            # # 스트리밍 청크 생성 함수
            # def gen_chunks():
            #     for event in response:
            #         # delta 텍스트 처리
            #         if hasattr(event, 'delta') and event.delta:
            #             yield event.delta
            #         elif getattr(event, "type", None) == "response.output_text.delta":
            #             yield event.delta

            # # 화면 출력 => 완전한 응답 데이터 저장
            # full_response = st.write_stream(gen_chunks())

        # # 세션에 저장된 대화 메시지에 응답 데이터 저장
        # st.session_state.messages.append(
        #     {
        #         "role":"assistant",
        #         "content": full_response
        #     }
        # )
