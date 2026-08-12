import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os

from modules.functions import recommend_destination, is_peak_season, estimate_expense
# ==========================================
# API 환경 설정
# ==========================================

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

if not api_key:
    st.error('api key가 존재하지 않습니다.')
    st.stop()

client = OpenAI(api_key=api_key)

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

# 추천 여행지 결과 저장
if 'destinations' not in st.session_state:
    st.session_state.destinations = []

# 여행 추천 실행 여부 저장
if 'trip_started' not in st.session_state:
    st.session_state.trip_started = False

# 챗봇 대화 기록 저장
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 사용자 입력 영역
# ==========================================

# 사이드바
st.sidebar.title('사용자 입력 조건')

# 추천 내용 전체 초기화
if st.sidebar.button('추천 내용 초기화'):

    st.session_state.destinations = []
    st.session_state.trip_started = False
    st.session_state.messages = []

    st.rerun()

# 성별
gender = st.sidebar.selectbox(
    '성별',
    ['남성', '여성']
)

# 나이
age = st.sidebar.number_input(
    '나이',
    min_value=1,
    max_value=100,
    value=20
)

# 여행 테마
theme = st.sidebar.selectbox(
    '여행 테마',
    [
        '자연', '맛집', '문화', '액티비티', '휴양'
    ]
)

# 인원수
num_of_people = st.sidebar.number_input(
    '인원수',
    min_value=1,
    max_value=30,
    value=2
)

# 여행 날짜
trip_date = st.sidebar.date_input(
    '출발 날짜'
)

# 여행 기간
period = st.sidebar.number_input(
    '여행 기간',
    min_value=1,
    max_value=30,
    value=3
)

# ==========================================
# 메뉴 선택
# ==========================================

selected_tab = st.radio(
    '메뉴',
    ['여행 추천', 'K-Guide AI'],
    horizontal=True,
    label_visibility='collapsed'
)

# ==========================================
# 기능 연결 - 여행 추천 결과
# ==========================================

if selected_tab == '여행 추천':
                
    # 추천 시작 버튼
    if st.sidebar.button('여행 추천 받기'):

        with st.status('맞춤 여행지를 분석합니다...', expanded=True) as status:

            st.write('여행지 선호도 분석 중...')

            # 여행지 추천
            st.session_state.destinations = recommend_destination(
                gender,
                age,
                theme,
                num_of_people
            )

            st.write('추천 여행지 분석 완료')

            status.update(
                label='여행지 추천 완료!',
                state='complete',
                expanded=False
            )

            st.session_state.trip_started = True

    if st.session_state.trip_started:

        st.header('추천 여행지')

        destinations = st.session_state.destinations

        cols = st.columns(len(destinations))

        for i, destination in enumerate(destinations):

            with cols[i]:

                st.subheader(destination)

                # 성수기/비수기
                peak = is_peak_season(
                    trip_date,
                    destination
                )

                if peak:
                    st.warning('성수기입니다.')
                else:
                    st.success('비수기입니다.')

                # 예상 경비
                expense = estimate_expense(
                    period,
                    destination,
                    num_of_people,
                    theme
                )

                st.metric(
                    '예상 경비',
                    f'{expense:,}원'
                )

        # ==========================================
        # 기능 연걸 - 기타 정보
        # UI만 구성, 하드코딩
        # ==========================================

        st.divider()

        # 숙소, 음식점 정보
        st.header('숙소, 음식점 정보')

        col1, col2 = st.columns(2)

        with col1:
            st.subheader('추천 숙소')

            st.info('000호텔')
            st.write('별점:4.7')
            st.write('1박 약 120,000원')
            st.write('위치정보')

        with col2:
            st.subheader('추천 맛집')
            
            st.info('제주 흑돼지')
            st.write('별점:4.7')
            st.write('1인분 약 20,000원')
            st.write('위치정보')


        # 날씨, 관광지 추천
        st.header('날씨, 관광지 추천')

        col1, col2 = st.columns(2)

        with col1:
            st.subheader('날씨 정보')

            st.info('최고 기온, 최저 기온')
            st.write('맑음')
            st.write('강수 확률 : 00%')
            st.write('미세먼지 농도 : 양호')

        with col2:
            st.subheader('추천 관광지')

            st.info('000해수욕장')
            st.write('숙소에서 거리')
            st.write('테마')

        # 항공편, 교통편
        st.header('항공편, 교통편')

        col1, col2 = st.columns(2)

        with col1:
            st.subheader('항공편')

            st.info('00항공')
            st.write('가격')
            st.write('출발 시간')
            st.write('소요 시간')

        with col2:
            st.subheader('교통편')

            st.info('대중교통')
            st.write('소요시간')
            st.write('가격')

# ==========================================
# OpenAI 챗봇
# ==========================================

elif selected_tab == 'K-Guide AI':

    st.header("K-Guide AI")
    st.caption('여행에 대해 궁금한 점 자유롭게 질문')

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
            #             "type": "web_search"
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
            #     ''',
            #     input=st.session_state.messages,
            #     stream=True
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