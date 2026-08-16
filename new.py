import os
import math
import datetime
import requests
import urllib.parse
from dotenv import load_dotenv

# 1. 환경변수 불러오기 (.env)
load_dotenv()
PUBLIC_DATA_KEY = os.getenv('PUBLIC_DATA_KEY')
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


# ==========================================
# 헬퍼 함수: 카카오 API로 주소/지명 -> 위경도 변환
# ==========================================
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


# ==========================================
# 헬퍼 함수: 위경도 -> 기상청 격자(nx, ny) 변환
# ==========================================
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


# ==========================================
# 1. 숙소 정보 조회 (팀장님 UI 규격 반환)
# ==========================================
def get_accommodations(destination):
    """
    여행지명을 입력 받아 주변 숙소를 검색한 후,
    팀 규격(accommodations) 리스트로 반환합니다.
    """
    address_name, lat, lon = get_lat_lon_from_address(destination)
    
    if not lat or not lon:
        return [{
            "name": f"{destination} 대표 숙소",
            "rating": 4.5,
            "price": 120000,
            "address": f"{destination} 주변",
            "url": "https://map.kakao.com",
            "latitude": 37.5665,
            "longitude": 126.9780
        }]

    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    params = {
        "category_group_code": "AD5", # 숙박 카테고리
        "x": str(lon),
        "y": str(lat),
        "radius": 3000,
        "sort": "accuracy"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        data = res.json()
        
        accommodations = []
        if data.get('documents'):
            for doc in data['documents'][:5]:
                accommodations.append({
                    "name": doc['place_name'],
                    "rating": 4.5,  # API 미제공 항목 기본값 세팅
                    "price": 120000, # 예시 평균가
                    "address": doc['road_address_name'] or doc['address_name'],
                    "url": doc['place_url'],
                    "latitude": float(doc['y']),
                    "longitude": float(doc['x'])
                })
        return accommodations if accommodations else [{
            "name": f"{destination} 추천 숙소",
            "rating": 4.0,
            "price": 100000,
            "address": address_name or destination,
            "url": "https://map.kakao.com",
            "latitude": lat,
            "longitude": lon
        }]

    except Exception as e:
        print(f"숙소 검색 오류: {e}")
        return []


# ==========================================
# 2. 날씨 정보 조회 (팀장님 UI 규격 반환)
# ==========================================
def get_weather(destination):
    """
    여행지명을 입력 받아 기상청 API를 통해 단기 예보를 받아온 후,
    팀 규격(weather) 딕셔너리로 반환합니다.
    """
    address_name, lat, lon = get_lat_lon_from_address(destination)

    # 위치를 못 찾을 시 기본값 반환
    if not lat or not lon:
        return {
            "max_temp": 25,
            "min_temp": 18,
            "weather": "맑음",
            "rain_probability": 10,
            "air_quality": "좋음"
        }

    nx, ny = dfs_xy(lat, lon)
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
            items = data['response']['body']['items']['item']
            
            # 오늘 날짜 예보 수집
            tmps = []
            pop_list = []
            sky_val = '1'

            for item in items:
                category = item['category']
                val = item['fcstValue']
                
                if category == 'TMP':
                    tmps.append(float(val))
                elif category == 'POP':
                    pop_list.append(int(val))
                elif category == 'SKY':
                    sky_val = val

            sky_dict = {'1': '맑음', '3': '구름많음', '4': '흐림'}
            
            return {
                "max_temp": int(max(tmps)) if tmps else 25,
                "min_temp": int(min(tmps)) if tmps else 18,
                "weather": sky_dict.get(sky_val, '맑음'),
                "rain_probability": max(pop_list) if pop_list else 0,
                "air_quality": "보통"
            }

    except Exception as e:
        print("기상청 API 호출 예외 발생:", e)

    # API 에러 시 fallback 기본값
    return {
        "max_temp": 24,
        "min_temp": 17,
        "weather": "맑음",
        "rain_probability": 0,
        "air_quality": "보통"
    }