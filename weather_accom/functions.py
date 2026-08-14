import os
import math
import datetime
import requests
import urllib.parse
from dotenv import load_dotenv

# .env 환경변수 로드
load_dotenv()
PUBLIC_DATA_KEY = os.getenv('PUBLIC_DATA_KEY')
KAKAO_REST_API_KEY = os.getenv('KAKAO_REST_API_KEY')


# -------------------------------------------------------------
# 1. 카카오 API: 장소(지역명) -> 위경도 변환
# -------------------------------------------------------------
def get_lat_lon(location_name):
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    try:
        res = requests.get(url, headers=headers, params={"query": location_name}, timeout=5)
        data = res.json()
        if data.get('documents'):
            doc = data['documents'][0]
            return float(doc['y']), float(doc['x'])
    except Exception as e:
        print(f"위경도 변환 오류: {e}")
    return None, None


# -------------------------------------------------------------
# 2. 카카오 API: 주변 숙소 조회 (app.py 포맷 맞춤)
# -------------------------------------------------------------
def get_accommodations(lat, lon):
    if not lat or not lon:
        return []
    
    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }
    # AD5 = 숙박 카테고리 코드
    params = {
        "category_group_code": "AD5",
        "x": str(lon),
        "y": str(lat),
        "radius": 3000,
        "sort": "accuracy"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        documents = res.json().get('documents', [])
        
        accommodations = []
        for doc in documents[:5]: # 상위 5개 추출
            accommodations.append({
                'name': doc.get('place_name'),
                'rating': 4.5, # 카카오 기본 검색 API는 별점이 없어 기본값 설정
                'price': 100000, # 기본 1박 가격 세팅 (필요 시 수정)
                'address': doc.get('road_address_name') or doc.get('address_name'),
                'url': doc.get('place_url'),
                'latitude': float(doc.get('y')),
                'longitude': float(doc.get('x'))
            })
        return accommodations
    except Exception as e:
        print(f"숙소 조회 실패: {e}")
        return []


# -------------------------------------------------------------
# 3. 기상청 좌표 변환 (위경도 -> nx, ny 격자)
# -------------------------------------------------------------
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
    return int(math.floor(ra * math.sin(theta) + XO + 0.5)), int(math.floor(ro - ra * math.cos(theta) + YO + 0.5))


# -------------------------------------------------------------
# 4. 기상청 API: 날씨 정보 조회 (app.py 포맷 맞춤)
# -------------------------------------------------------------
def get_weather(lat, lon):
    if not lat or not lon:
        return {'max_temp': 25, 'min_temp': 15, 'weather': '맑음', 'rain_probability': 0, 'air_quality': '좋음'}

    nx, ny = dfs_xy(lat, lon)
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
    url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'
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

    try:
        res = requests.get(url, params=params, timeout=10)
        items = res.json()['response']['body']['items']['item']
        
        tmps, pop_list, sky_list = [], [], []
        for item in items:
            if item['category'] == 'TMP': tmps.append(float(item['fcstValue']))
            elif item['category'] == 'POP': pop_list.append(int(item['fcstValue']))
            elif item['category'] == 'SKY': sky_list.append(item['fcstValue'])

        sky_map = {'1': '맑음', '3': '구름많음', '4': '흐림'}
        most_sky = max(set(sky_list), key=sky_list.count) if sky_list else '1'

        return {
            'max_temp': int(max(tmps)) if tmps else 25,
            'min_temp': int(min(tmps)) if tmps else 15,
            'weather': sky_map.get(most_sky, '맑음'),
            'rain_probability': max(pop_list) if pop_list else 0,
            'air_quality': '좋음'
        }
    except Exception as e:
        print(f"날씨 API 호출 오류: {e}")
        return {'max_temp': 25, 'min_temp': 15, 'weather': '맑음', 'rain_probability': 0, 'air_quality': '좋음'}


# -------------------------------------------------------------
# 5. app.py와 직접 연결할 최종 함수
# -------------------------------------------------------------
def get_weather_and_accommodation(destination):
    """
    여행지 이름(예: '강릉')을 입력받아
    app.py 규격에 딱 맞는 weather, accommodations 데이터만 반환합니다.
    """
    lat, lon = get_lat_lon(destination)
    accommodations = get_accommodations(lat, lon)
    weather = get_weather(lat, lon)

    return {
        'accommodations': accommodations,
        'weather': weather
    }