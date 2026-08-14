import os
import math
import datetime
import requests
import urllib.parse
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# 1. 환경변수 불러오기 (.env)
load_dotenv()
PUBLIC_DATA_KEY = os.getenv('PUBLIC_DATA_KEY')
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# Streamlit 기본 설정
st.set_page_config(page_title="전국 여행 날씨 & 숙소 안내 챗봇", page_icon="🌤️", layout="centered")
st.title("🌤️ 여행 날씨 & 숙소 안내 챗봇")
st.caption("카카오 API + 기상청 단기예보 API + OpenAI 연동")


# --- Helper 1: 카카오 API로 주소/지명 변환 ---
def get_lat_lon_from_address(address_text):
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    
    clean_text = address_text
    for word in ['날씨', '숙소', '호텔', '펜션', '게하', '게스트하우스', '모텔', '추천', '알려줘', '어때', '정보', '예보', '오늘', '내일', '주말', '어떻게']:
        clean_text = clean_text.replace(word, '')
    clean_text = clean_text.strip()
    search_query = clean_text if clean_text else address_text

    try:
        url = "https://dapi.kakao.com/v2/local/search/keyword.json"
        res = requests.get(url, headers=headers, params={"query": search_query}, timeout=5)
        data = res.json()

        if data.get('documents'):
            doc = data['documents'][0]
            address_name = doc.get('address_name') or doc.get('place_name')
            return address_name, float(doc['y']), float(doc['x'])
    except Exception as e:
        print(f"카카오 키워드 검색 오류: {e}")

    try:
        addr_url = "https://dapi.kakao.com/v2/local/search/address.json"
        res_addr = requests.get(addr_url, headers=headers, params={"query": search_query}, timeout=5)
        data_addr = res_addr.json()
        if data_addr.get('documents'):
            doc = data_addr['documents'][0]
            return doc['address_name'], float(doc['y']), float(doc['x'])
    except Exception as e:
        print(f"카카오 주소 검색 오류: {e}")

    return None, None, None


# --- Helper 2: 카카오 API로 주변 숙박업소 검색 ---
def search_accommodations(lat, lon, radius=3000):
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    params = {
        "category_group_code": "AD5",
        "x": str(lon),
        "y": str(lat),
        "radius": radius,
        "sort": "accuracy"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        
        places = []
        if data.get('documents'):
            for doc in data['documents'][:5]:
                category = doc['category_name'].split(' > ')[-1] if ' > ' in doc['category_name'] else doc['category_name']
                places.append({
                    "name": doc['place_name'],
                    "category": category,
                    "address": doc['road_address_name'] or doc['address_name'],
                    "phone": doc['phone'] if doc['phone'] else "전화번호 정보 없음",
                    "url": doc['place_url']
                })
        return places
    except Exception as e:
        print(f"숙소 검색 오류: {e}")
        return []


# --- Helper 3: 위경도 -> 기상청 격자(nx, ny) 변환 ---
def dfs_xy(lat, lon):
    RE, GRID, SLAT1, SLAT2, OLON, OLAT, XO, YO = 6371.00877, 5.0, 30.0, 60.0, 126.0, 38.0, 43, 136
    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1, slat2 = SLAT1 * DEGRAD, SLAT2 * DEGRAD
    olon, olat = OLON * DEGRAD, OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (math.pow(sf, sn) * math.cos(slat1)) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = (re * sf) / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + (lat) * DEGRAD * 0.5)
    ra = (re * sf) / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi: theta -= 2.0 * math.pi
    if theta < -math.pi: theta += 2.0 * math.pi
    theta *= sn

    nx = math.floor(ra * math.sin(theta) + XO + 0.5)
    ny = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    return int(nx), int(ny)


# --- Helper 4: 기상청 단기예보 API 호출 ---
def fetch_weather_data(nx, ny):
    url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'
    
    now = datetime.datetime.now()
    if now.hour < 2:
        base_date = (now - datetime.timedelta(days=1)).strftime("%Y%m%d")
        base_time = "2300"
    else:
        base_date = now.strftime("%Y%m%d")
        times = [2, 5, 8, 11, 14, 17, 20, 23]
        latest_hour = max([t for t in times if t <= now.hour])
        base_time = f"{latest_hour:02d}00"

    service_key = urllib.parse.unquote(PUBLIC_DATA_KEY) if PUBLIC_DATA_KEY else ""

    params = {
        'serviceKey': service_key,
        'pageNo': '1',
        'numOfRows': '1000',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': str(nx),
        'ny': str(ny)
    }
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('response', {}).get('header', {}).get('resultCode') == '00':
            return data['response']['body']['items']['item']
    except Exception as e:
        print("기상청 API 호출 예외 발생:", e)
        
    return None


# --- Helper 5: 기상 데이터 정제 ---
def summarize_weather(items):
    if not items:
        return None

    sky_dict = {'1': '맑음 ☀️', '3': '구름많음 ⛅', '4': '흐림 ☁️'}
    daily_data = {}

    for item in items:
        fcst_date = item['fcstDate']
        category = item['category']
        val = item['fcstValue']

        if fcst_date not in daily_data:
            daily_data[fcst_date] = {'sky': [], 'tmp': [], 'pty': []}

        if category == 'SKY': daily_data[fcst_date]['sky'].append(val)
        elif category == 'TMP': daily_data[fcst_date]['tmp'].append(float(val))
        elif category == 'PTY': daily_data[fcst_date]['pty'].append(val)

    summary_text = ""
    for fcst_date, values in list(daily_data.items())[:5]:
        min_tmp = int(min(values['tmp'])) if values['tmp'] else '-'
        max_tmp = int(max(values['tmp'])) if values['tmp'] else '-'
        most_sky = max(set(values['sky']), key=values['sky'].count) if values['sky'] else '1'
        sky_status = sky_dict.get(most_sky, '맑음 ☀️')
        
        has_rain = any(p != '0' for p in values['pty'])
        if has_rain:
            sky_status += " / 🌧️ 비·눈 예보"

        summary_text += f"- **{fcst_date[:4]}-{fcst_date[4:6]}-{fcst_date[6:]}**: {sky_status} | 최저 **{min_tmp}°C** / 최고 **{max_tmp}°C**\n"

    return summary_text


# --- Helper 6: OpenAI 답변 생성 (디자인 강화 프롬프트) ---
def generate_gpt_response(user_prompt, location_name, weather_summary, accommodations):
    system_instruction = (
        "당신은 친절한 여행 가이드입니다. "
        "응답은 시각적으로 보기 좋게 마크다운 문법(제목, 구분선, 이모지, 볼드체 등)을 적극적으로 활용하여 작성하세요.\n\n"
        "작성 형태 예시:\n"
        "### 📍 [지역명] 여행 날씨 예보\n"
        "(날씨 정보 요약)\n\n"
        "---\n"
        "### 🏨 추천 숙소 Best 5\n"
        "각 숙소별로 아래 형식으로 보여주세요:\n"
        "1. **숙소명** (`카테고리`)\n"
        "   - 📌 주소: ...\n"
        "   - 📞 전화: ...\n"
        "   - 🔗 [카카오맵으로 위치 확인하기](링크)\n"
    )
    
    acc_text = ""
    if accommodations:
        acc_text = "주변 추천 숙소 목록:\n"
        for idx, acc in enumerate(accommodations, 1):
            acc_text += f"{idx}. 이름: {acc['name']} | 카테고리: {acc['category']} | 주소: {acc['address']} | 전화: {acc['phone']} | 링크: {acc['url']}\n"
    else:
        acc_text = "주변 숙소 정보가 없습니다."

    user_content = f"사용자 질문: {user_prompt}\n위치: {location_name}\n\n[날씨 정보]\n{weather_summary}\n\n[{acc_text}]"

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API 오류: {e}")
        return f"📍 **[{location_name}] 날씨 및 숙소 안내**\n\n{weather_summary}\n\n{acc_text}"


# --- Streamlit UI ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "안녕하세요! 궁금하신 **지역명**(예: 강릉, 부산 해운대, 제주도)을 입력해주시면 **날씨와 주변 추천 숙소**를 예쁘게 정리해 드릴게요! 🏖️"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("여행지나 궁금한 지역을 입력하세요..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    with st.spinner("위치, 날씨 및 주변 숙소 정보를 불러오는 중... ⏳"):
        address_name, lat, lon = get_lat_lon_from_address(prompt)

        if address_name and lat and lon:
            nx, ny = dfs_xy(lat, lon)
            items = fetch_weather_data(nx, ny)
            weather_summary = summarize_weather(items)
            accommodations = search_accommodations(lat, lon)

            if weather_summary:
                bot_response = generate_gpt_response(prompt, address_name, weather_summary, accommodations)
            else:
                bot_response = f"⚠️ **{address_name}** 지역의 날씨 데이터를 불러오는 데 실패했습니다."
        else:
            bot_response = "❌ 정확한 위치를 찾을 수 없습니다. 구체적인 지명이나 주소를 입력해 주세요!"

    st.session_state.messages.append({"role": "assistant", "content": bot_response})
    st.chat_message("assistant").write(bot_response)