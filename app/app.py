import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os

# from modules.functions import recommend_destination
from model.Ruse import recommend_destination
from model.estimate_expense import estimate_expense
from model.estimate_peak import EstimatePeak

from main import recommend_places
from new import get_accommodations, get_weather


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
if 'transport_request' not in st.session_state:
    st.session_state.transport_request = None


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
    st.session_state.transport_request = None

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
# 더미 API 데이터
# 실제 API 연결 전 UI 테스트를 위한 더미 데이터
# ==========================================

def create_dummy_api_context(destinations):

    api_context = []

    for destination in destinations:

        # 여행지별 더미 데이터
        data = {

            'destination': destination,

            'accommodations': [
                {
                    'name': f'{destination} K-Guide 호텔',
                    'rating': 4.7,
                    'price': 120000,
                    'address': f'{destination} 중심가',
                    'url': 'https://example.com',
                    'latitude': 37.5665,
                    'longitude': 126.9780
                }
            ],

            'restaurants': [
                {
                    'name': f'{destination} 대표 맛집',
                    'category': '한식',
                    'rating': 4.6,
                    'price': 20000,
                    'address': f'{destination} 맛집거리',
                    'opening_hours': '11:00~21:00',
                    'url': 'https://example.com',
                    'latitude': 37.5665,
                    'longitude': 126.9780
                }
            ],

            'weather': {
                'max_temp': 32,
                'min_temp': 21,
                'weather': '맑음',
                'rain_probability': 20,
                'air_quality': '좋음'
            },

            'attractions': [
                {
                    'name': f'{destination} 대표 관광지',
                    'category': '문화관광',
                    'description': f'{destination}의 대표적인 관광 명소입니다.',
                    'rating': 4.8,
                    'address': f'{destination} 관광지',
                    'opening_hours': '09:00~18:00',
                    'url': 'https://example.com',
                    'latitude': 37.5665,
                    'longitude': 126.9780
                }
            ],

            'flights': [
                {
                    'transport_type': 'flight',
                    'name': '대한항공',
                    'departure': '김포공항',
                    'arrival': destination,
                    'departure_time': '09:30',
                    'arrival_time': '10:40',
                    'duration': 70,
                    'price': 85000,
                    'price_type': 'api',
                    'transfers': 0
                }
            ],

            'transportation': [
                {
                    'transport_type': 'train',
                    'name': 'KTX',
                    'departure': '서울역',
                    'arrival': destination,
                    'departure_time': '09:30',
                    'arrival_time': '10:40',
                    'duration': 120,
                    'price': 50000,
                    'price_type': 'api',
                    'transfers': 0
                }
            ]
        }

        api_context.append(data)

    return api_context

# ==========================================
# API 데이터
# 날씨, 관광지, 숙소, 맛집 정보
# ==========================================
def create_api_context(destinations):
    api_context = []

    for destination in destinations:
        restaurant_attraction = recommend_places(destination, theme)
        data = {
            'destination' : destination,
            'accomadations' : get_accommodations(destination),
            'weather' : get_weather(destination),
            'restaraunts': restaurant_attraction['restaurants'],
            'attractions' : restaurant_attraction['tourist_attractions']
        }

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
                    gender,
                    age,
                    num_of_people,
                    theme
                )

                # 추천 결과가 없는 경우
                if not st.session_state.destinations:
                    raise ValueError('추천 여행지가 없습니다.')
        
                # 성수기 비수기 / 경비 계산
                st.write('여행지별 정보 분석 중...')

                recommendation_context=[]

                for destination in st.session_state.destinations:
# 성수기 여부 표시 위치 변경 예정 --------------------------------
                    # # 성수기 / 비수기
                    # try:
                    #     peak = estimate_peak.is_peak_season(
                    #         trip_date,
                    #         period,
                    #         destination
                    #     )
                    # except Exception:
                    #     peak = None
#---------------------------------------------------------------
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
                        'destination': destination,
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

    if st.session_state.trip_started:

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
# 성수기 여부 표시 위치 변경 예정 --------------------------------
                # peak = recommendation['peak_season']
                # # 성수기 / 비수기 표시
                # if peak >= 0.75:
                #     st.warning('매우 혼잡할 것으로 예상됩니다.')
                # elif peak >= 0.5:
                #     st.warning('혼잡할 것으로 예상됩니다.')
                # elif peak >= 0.25:
                #     st.success('한적할 것으로 예상됩니다.')
                # elif peak < 0.25 :
                #     st.success('매우 한적할 것으로 예상됩니다.')
                # else:
                #     st.info('성수기 여부를 확인할 수 없습니다.')
#---------------------------------------------------------------
                # 예상 경비
                if expense is not None:
                    st.metric(
                        '예상 경비',
                        f'{expense:,}원'
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

        st.write(
            f"예상 경비: "
            f"{selected_recommendation['expense']:,}원"
        )
# 성수기 여부 표시 위치 변경 예정 --------------------------------
        # if selected_recommendation['peak_season'] >= 0.75:
        #     st.write('매우 혼잡')
        # elif selected_recommendation['peak_season'] >= 0.5:
        #     st.write('혼잡')
        # elif selected_recommendation['peak_season'] >= 0.25:
        #     st.write('한적')
        # elif selected_recommendation['peak_season'] < 0.25:
        #     st.write('매우 한적')
        # else:
        #     st.write('성수기 정보 확인 불가')
#--------------------------------------------------------------

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
        
        # 숙소, 음식점 정보
        st.header('숙소, 음식점 정보')

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

                    hotel = hotel_list[0]
                    # 숙소명
                    st.info(hotel['name'])
                    # 별점
                    st.write(f"별점: {hotel['rating']}")
                    # 가격
                    st.write(f"1박 약 {hotel['price']:,}원")
                    # 주소
                    st.write(f"주소: {hotel['address']}")

                    # url
                    if hotel.get('url'):

                        st.link_button(
                            '상세정보',
                            hotel['url']
                        )

                    # 지도 시각화
                    if(
                        hotel.get('latitude') is not None
                        and hotel.get('longitude') is not None
                    ):
                        st.map({
                            'lat':[hotel['latitude']],
                            'lon':[hotel['longitude']]
                        })

                    else: st.info('추천 숙소 정보가 없습니다.')

                else:
                    st.info('숙소 정보를 불러오는 중입니다.')

        # 맛집
        with col2:
            st.subheader('추천 맛집')
            
            if selected_api_context:

                restaurant_list = selected_api_context.get('restaurants', [])

                if restaurant_list:

                    restaurant = restaurant_list[0]
                    # 음식점명
                    st.info(restaurant['name'])
                    # 음식 종류
                    st.write(f"음식 종류: {restaurant['category']}")
                    # 별점
                    st.write(f"별점: {restaurant['rating']}")
                    # 가격
                    st.write(f"가격: 약 {restaurant['price']:,}원")
                    # 주소
                    st.write(f"주소: {restaurant['address']}")
                    # 영업시간
                    st.write(f"영업시간: {restaurant['opening_hours']}")

                    # url
                    if restaurant.get('url'):

                        st.link_button(
                            '상세 정보',
                            restaurant['url']
                        )

                    # 지도 시각화
                    if(
                        restaurant.get('latitude') is not None
                        and restaurant.get('longitude') is not None
                    ):
                        st.map({
                            'lat':[restaurant['latitude']],
                            'lon':[restaurant['longitude']]
                        })     
                                       
                else:
                    st.info('추천 맛집 정보가 없습니다.')

            else:           
                st.info('맛집 정보를 불러오는 중입니다.')


        # 날씨, 관광지 추천
        st.header('날씨, 관광지 추천')

        col1, col2 = st.columns(2)

        # 날씨
        with col1:
            st.subheader('날씨 정보')

            if selected_api_context:

                weather = selected_api_context.get('weather', {})

                if weather:
                    # 기온
                    st.info(
                        f"최고 {weather['max_temp']}°C\n"
                        f"최저 {weather['min_temp']}°C"
                    )
                    # 날씨
                    st.write(f"날씨: {weather['weather']}")
                    # 강수 확률
                    st.write(f"강수 확률: {weather['rain_probability']}%")
                    # 미세먼지
                    st.write(f"미세먼지: {weather['air_quality']}")

                else:
                    st.info('날씨 정보가 없습니다.')

            else:
                st.info('날씨 정보를 불러오는 중입니다.')


        with col2:
            st.subheader('추천 관광지')

            if selected_api_context:

                attraction_list = selected_api_context.get(
                    'attractions',
                    []
                )

                if attraction_list:

                    attraction = attraction_list[0]
                    # 관광지명
                    st.info( attraction['name'])
                    # 관광지 테마
                    st.write(f"테마: {attraction['category']}")
                    # 설명
                    st.write(attraction['description'])
                    # 예상 혼잡도
                    congestion_rate = estimate_peak.is_peak_season(trip_date, period, attraction['address'])
                    st.write('예상 혼잡도 :')
                    if congestion_rate == None: # 0이 나오는 경우를 대비해 None과 직접 비교
                        st.write('혼잡도를 예상할 수 없습니다')
                    elif congestion_rate >= 0.75:
                        st.write('매우 혼잡')
                    elif congestion_rate >= 0.5:
                        st.write('혼잡')
                    elif congestion_rate >= 0.25:
                        st.write('한적')
                    else:
                        st.write('매우 한적')
                    # 별점
                    st.write(f"별점: {attraction['rating']}")
                    # 주소
                    st.write(f"주소: {attraction['address']}")
                    # 운영시간
                    st.write(f"운영시간: {attraction['opening_hours']}")

                    # url
                    if attraction.get('url'):

                        st.link_button(
                            '상세 정보',
                            attraction['url']
                        )

                    # 지도 시각화
                    if(
                        attraction.get('latitude') is not None
                        and attraction.get('longitude') is not None
                    ):
                        st.map({
                            'lat':[attraction['latitude']],
                            'lon':[attraction['longitude']]
                        })

                else:
                    st.info('추천 관광지 정보가 없습니다.')

            else:
                st.info('관광지 정보를 불러오는 중입니다.')


        # ==========================================
        # 항공 / 교통 정보 설정
        # ==========================================   
        
        if (
            selected_recommendation is not None
            and st.session_state.transport_enabled is None
        ):
            st.subheader('이동 정보 설정')

            st.write('항공편 및 교통편 정보를 함께 추천 받으시겠습니까?')


            col1, col2 = st.columns(2)

            with col1:

                departure = st.selectbox(
                    '출발 지역',
                    DEPARTURE_OPTIONS
                )

            with col2:

                arrival = selected_recommendation['destination']

                st.text_input(
                    '도착 지역',
                    value=arrival,
                    disabled=True
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
                    '이 시간 이후 출발',
                    value=None
                )

            else:

                time_after = None

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    '입력하고 추천받기',
                    use_container_width=True
                ):

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

                    # API 요청 데이터
                    st.session_state.transport_request = {
                        'departure': departure,
                        'arrival': selected_recommendation['destination'],
                        'option': OPTION_OPTIONS[transport_option_label],
                        'time_after': (
                            time_after.strftime('%H:%M')
                            if time_after is not None
                            else None
                        )
                    }
                    st.rerun()

            with col2:

                if st.button(
                    '건너뛰기',
                    use_container_width=True
                ):

                    st.session_state.transport_enabled = False
                    st.session_state.departure = None
                    st.session_state.transport_option = None
                    st.session_state.time_after = None
                    st.session_state.transport_request = None

                    st.rerun()

        if st.session_state.transport_enabled:
            # 항공편, 교통편
            st.header('항공편, 교통편')

            col1, col2 = st.columns(2)

            # 항공편
            with col1:
                st.subheader('항공편')

                if selected_api_context:

                    flights = selected_api_context.get(
                        'flights',
                        []
                    )

                    if flights:

                        flight = flights[0]

                        # 항공사
                        st.info(flight['name'])

                        # 출발 / 도착
                        st.write(f"{flight['departure']} ➤ {flight['arrival']}")

                        # 출발 / 도착 시간
                        st.write(f"출발: {flight['departure_time']}")
                        st.write(f"도착: {flight['arrival_time']}")

                        # 소요 시간
                        if flight['duration'] is not None:
                            st.write(f"소요 시간: {format_duration(flight['duration'])}")

                        # 가격
                        if flight['price'] is not None:
                            st.write(f"가격: {flight['price']:,}원")

                    else:
                        st.info('항공편 정보가 없습니다.')

                else:
                    st.info('항공편 정보를 불러오는 중입니다.')


            # 교통편
            with col2:
                st.subheader('교통편')

                if selected_api_context:

                    transportation = selected_api_context.get(
                        'transportation',
                        []
                    )

                    if transportation:

                        transport = transportation[0]
                        # 교통수단
                        st.info(transport['name'])

                        # 교통수단 종류
                        st.write(f"교통수단: {transport['transport_type']}")
                        
                        # 출발 / 도착
                        st.write(f"{transport['departure']} ➤ {transport['arrival']}")

                        # 출발 / 도착 시간
                        st.write(f"출발: {transport['departure_time']}")
                        st.write(f"도착: {transport['arrival_time']}")

                        # 소요 시간
                        if transport['duration'] is not None:
                            st.write(f"소요 시간: {format_duration(transport['duration'])}")

                        # 가격
                        if transport['price'] is not None:
                            st.write(f"가격: {transport['price']:,}원")

                    else:
                        st.info('교통편 정보가 없습니다.')

                else:
                    st.info('교통편 정보를 불러오는 중입니다.')


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
