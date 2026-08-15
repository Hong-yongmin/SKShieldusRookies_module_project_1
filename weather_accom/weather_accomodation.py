import os
import math
import datetime
import requests
import urllib.parse
from dotenv import load_dotenv

# 환경변수 로드 (카카오, 공공데이터 키)
load_dotenv()
PUBLIC_DATA_KEY = os.getenv('PUBLIC_DATA_KEY')
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')


# --- Helper 1: 카카오 API로 주소/지명 변환 (위경도 가져오기) ---
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
def search_accommodations(lat, lon, radius=5000, target_region=""):
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    
    # "용산구 호텔", "영등포구 숙소" 형식으로 쿼리 구성
    query_text = f"{target_region} 호텔" if target_region else "호텔"
    
    # 💡 핵심: 지역명으로 검색할 땐 x, y, radius 제한을 없애야 그 '구' 전체 숙소가 잘 나옵니다!
    params = {
        "query": query_text,
        "size": 15,          # 검색 결과를 15개까지 가져옴
        "sort": "accuracy"
    }

    # 만약 target_region이 지정 안 되어있다면(좌표 기반 검색) 좌표 파라미터 추가
    if not target_region and lat and lon:
        params["x"] = str(lon)
        params["y"] = str(lat)
        params["radius"] = radius

    accommodations = []
    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        
        if data.get('documents'):
            for doc in data['documents']:
                addr = doc['road_address_name'] or doc['address_name']
                
                # 주소에 target_region(예: 용산구)이 들어있는 진짜 해당 지역 숙소만 채택
                if not target_region or target_region in addr:
                    accommodations.append({
                        'name': doc['place_name'],
                        'rating': 4.5,
                        'price': 100000,
                        'address': addr,
                        'url': doc['place_url'],
                        'latitude': float(doc['y']),
                        'longitude': float(doc['x'])
                    })
                    
                if len(accommodations) >= 5:
                    break
    except Exception as e:
        print(f"숙소 검색 오류: {e}")
        
    return accommodations


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

    weather_info = {
        'max_temp': 25,
        'min_temp': 15,
        'weather': '맑음',
        'rain_probability': 0,
        'air_quality': '보통'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('response', {}).get('header', {}).get('resultCode') == '00':
            items = data['response']['body']['items']['item']
            
            temps, pop_list, sky_counts = [], [], []
            sky_dict = {'1': '맑음', '3': '구름많음', '4': '흐림'}

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
                weather_info['weather'] = sky_dict.get(most_sky, '맑음')

    except Exception as e:
        print("기상청 API 호출 예외 발생:", e)
        
    return weather_info


# ==========================================
# 메인 통합 함수 (app.py에서 호출할 함수)
# ==========================================
def get_weather_and_accommodations(destination_name, client=None):
    addr, lat, lon = get_lat_lon_from_address(destination_name)
    
    if not lat or not lon:
        return [], {'max_temp': '-', 'min_temp': '-', 'weather': '정보 없음', 'rain_probability': 0, 'air_quality': '-'}

    # 💡 destination_name("용산구", "제주도", "부산" 등)을 그대로 전달!
    accommodations = search_accommodations(lat, lon, radius=5000, target_region=destination_name)
    # 2. 날씨 조회
    nx, ny = dfs_xy(lat, lon)
    weather = fetch_weather_data(nx, ny)

    # 3. 필요 시 전달받은 client 객체를 활용해 LLM 가공 로직 수행 가능
    # if client is not None:
    #     response = client.chat.completions.create(...)

    return accommodations, weather