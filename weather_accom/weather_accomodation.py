from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import datetime
import json
import math
import os
from urllib.parse import unquote

from dotenv import load_dotenv
from openai import OpenAI
import requests

# ============================================================
# 1. 환경 변수 및 클라이언트 초기화
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "APIKEY.env"))
load_dotenv()  # 기존 .env 파일 호환

PUBLIC_DATA_KEY = os.getenv('PUBLIC_DATA_KEY')
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

# ============================================================
# 2. 캐싱 및 도우미 함수 (Address, Math)
# ============================================================
@lru_cache(maxsize=128)
def get_lat_lon_from_address(address_text):
    if not KAKAO_REST_API_KEY:
        return None, None, None

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
        if res.status_code == 200:
            data = res.json()
            if data.get('documents'):
                doc = data['documents'][0]
                address_name = doc.get('address_name') or doc.get('place_name')
                return address_name, float(doc['y']), float(doc['x'])
    except Exception as e:
        print(f"[디버그] 카카오 키워드 검색 오류: {e}")

    try:
        addr_url = "https://dapi.kakao.com/v2/local/search/address.json"
        res_addr = requests.get(addr_url, headers=headers, params={"query": search_query}, timeout=5)
        if res_addr.status_code == 200:
            data_addr = res_addr.json()
            if data_addr.get('documents'):
                doc = data_addr['documents'][0]
                return doc['address_name'], float(doc['y']), float(doc['x'])
    except Exception as e:
        print(f"[디버그] 카카오 주소 검색 오류: {e}")

    return None, None, None


@lru_cache(maxsize=128)
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

# ============================================================
# 3. 데이터 수집 함수 (Weather & Accommodations)
# ============================================================
def search_accommodations(lat, lon, radius=5000, target_region=""):
    if not KAKAO_REST_API_KEY:
        return []

    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }

    query_text = f"{target_region} 호텔" if target_region else "호텔"
    params = {
        "query": query_text,
        "size": 15,
        "sort": "accuracy"
    }

    if not target_region and lat and lon:
        params["x"] = str(lon)
        params["y"] = str(lat)
        params["radius"] = radius

    accommodations = []
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get('documents'):
                for doc in data['documents']:
                    addr = doc.get('road_address_name') or doc.get('address_name', '')
                    if not target_region or target_region in addr or target_region[:2] in addr:
                        accommodations.append({
                            'name': doc['place_name'],
                            'address': addr,
                            'url': doc.get('place_url', ''),
                            'latitude': float(doc['y']),
                            'longitude': float(doc['x'])
                        })
                    if len(accommodations) >= 5:
                        break
    except Exception as e:
        print(f"[디버그] 숙소 검색 오류: {e}")

    return accommodations


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

    service_key = unquote(PUBLIC_DATA_KEY) if PUBLIC_DATA_KEY else ""

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

    weather_info = {
        'max_temp': 25,
        'min_temp': 15,
        'weather': '맑음 ☀️',
        'rain_probability': 0
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('response', {}).get('header', {}).get('resultCode') == '00':
                items = data['response']['body']['items']['item']
                temps, pop_list, sky_counts = [], [], []
                sky_dict = {'1': '맑음 ☀️', '3': '구름많음 ⛅', '4': '흐림 ☁️'}

                for item in items:
                    category = item['category']
                    val = item['fcstValue']
                    if category == 'TMP':
                        temps.append(float(val))
                    elif category == 'POP':
                        pop_list.append(int(val))
                    elif category == 'SKY':
                        sky_counts.append(val)

                if temps:
                    weather_info['max_temp'] = int(max(temps))
                    weather_info['min_temp'] = int(min(temps))
                if pop_list:
                    weather_info['rain_probability'] = max(pop_list)
                if sky_counts:
                    most_sky = max(set(sky_counts), key=sky_counts.count)
                    weather_info['weather'] = sky_dict.get(most_sky, '맑음 ☀️')
    except Exception as e:
        print(f"[디버그] 기상청 API 호출 예외: {e}")

    return weather_info

# ============================================================
# 4. 메인 서비스 함수 (병렬 처리 탑재)
# ============================================================
def get_weather_and_accommodations(destination_name, client_obj=None):
    addr, lat, lon = get_lat_lon_from_address(destination_name)

    if not lat or not lon:
        return json.dumps({
            "error": f"'{destination_name}'의 위치 정보를 찾을 수 없습니다."
        }, ensure_ascii=False)

    nx, ny = dfs_xy(lat, lon)

    accommodations = []
    weather = {}

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_acc = executor.submit(search_accommodations, lat, lon, 5000, destination_name)
        future_weather = executor.submit(fetch_weather_data, nx, ny)

        accommodations = future_acc.result()
        weather = future_weather.result()

    result = {
        "destination": destination_name,
        "address": addr,
        "weather": weather,
        "accommodations": accommodations
    }

    return json.dumps(result, ensure_ascii=False)

# ============================================================
# 5. OpenAI Function Calling 연동 (TOOLS 및 프롬프트)
# ============================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather_and_accommodations",
            "description": "지정된 여행 목적지/지역의 단기 날씨 예보와 주변 추천 숙소 목록을 가져옵니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination_name": {
                        "type": "string",
                        "description": "조회할 지역/목적지 명칭 (예: 서울, 용산구, 강릉, 제주도)"
                    }
                },
                "required": ["destination_name"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "get_weather_and_accommodations": get_weather_and_accommodations
}


def ask_ai(messages_history):
    if not client:
        return "⚠️ OpenAI API 키가 설정되지 않았습니다. APIKEY.env 환경변수를 확인해주세요."

    system_instruction = """당신은 여행 날씨 및 숙소 추천 전문 AI 안내 가이드입니다.
사용자가 특정 지역의 날씨나 숙소 정보를 요구하면 반드시 'get_weather_and_accommodations' 툴을 호출하세요.

툴 응답 데이터를 확보하면 아래 마크다운 양식을 엄격하게 준수하여 답변하세요:

### 🌤️ [목적지] 날씨 및 추천 숙소 안내

#### 🌡️ 실시간 기상 예보
* **날씨 상태**: [weather]
* **기온 정보**: 최저 [min_temp]°C / 최고 [max_temp]°C
* **강수 확률**: [rain_probability]%

#### 🏨 추천 숙박업소 (최대 5곳)
1. **[숙소명]**
   * 📍 주소: [address]
   * 🔗 [상세보기 및 예약 링크]([url])
2. **[숙소명]**
   * 📍 주소: [address]
   * 🔗 [상세보기 및 예약 링크]([url])

💡 *숙소별 상세 평점 및 실시간 가격은 카카오맵 상세페이지 링크에서 확인 가능합니다.*

* 규칙:
1. 숙소 정보에 '평점'이나 '가격' 항목을 절대 표시하지 마세요.
2. 숙소 목록이 끝난 후 반드시 "💡 숙소별 상세 평점 및 실시간 가격은 카카오맵 상세페이지 링크에서 확인 가능합니다." 안내 문구를 출력하세요.
"""

    system_msg = {"role": "system", "content": system_instruction}
    full_messages = [system_msg] + messages_history

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        tools=TOOLS,
        tool_choice="auto"
    )

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        full_messages.append(response_message)
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_to_call = AVAILABLE_FUNCTIONS[func_name]
            func_args = json.loads(tool_call.function.arguments)

            func_response = func_to_call(**func_args)

            if isinstance(func_response, (dict, list)):
                func_response_str = json.dumps(func_response, ensure_ascii=False)
            else:
                func_response_str = str(func_response)

            full_messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": func_response_str,
            })

        second_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages
        )
        return second_response.choices[0].message.content
    else:
        return response_message.content

# ============================================================
# 6. 터미널 단독 실행 및 테스트 모드
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI 스마트 날씨 & 숙소 안내 가이드 (터미널 단독 모드)")
    print("    (종료하려면 'q' 또는 'exit'를 입력하세요)")
    print("=" * 60)

    welcome_msg = "안녕하세요! ☁️ 어디로 여행을 떠나시나요? 지역명을 알려주시면 날씨와 숙소를 추천해 드립니다!"
    print(f"\n🤖 AI 가이드:\n{welcome_msg}\n")
    print("-" * 60)

    messages_history = [{"role": "assistant", "content": welcome_msg}]

    while True:
        try:
            user_input = input("\n👤 사용자: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 프로그램을 종료합니다.")
            break

        if user_input.lower() in ["q", "exit", "quit", "종료"]:
            print("\n👋 프로그램을 종료합니다.")
            break

        if not user_input:
            continue

        messages_history.append({"role": "user", "content": user_input})
        print("\n🔄 날씨/숙소 API 데이터 조회 및 AI 응답 생성 중...")
        ai_reply = ask_ai(messages_history)

        print("\n" + "=" * 60)
        print(ai_reply)
        print("=" * 60)

        messages_history.append({"role": "assistant", "content": ai_reply})