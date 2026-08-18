import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sys
import json

# 현재 파일 기준 상위(최상위) 폴더 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.Ruse import recommend_destination
from model.estimate_expense import estimate_expense
from model.estimate_peak import EstimatePeak

from destination_info.restaurant_attraction import recommend_places
from destination_info.weather_accommodation import get_accommodations, get_weather

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
    # 수도권
    '서울': '김포국제공항',
    '서울특별시': '김포국제공항',
    '경기': '김포국제공항',
    '경기도': '김포국제공항',
    '인천': '인천국제공항',
    '인천광역시': '인천국제공항',

    # 영남권
    '부산': '김해국제공항',
    '부산광역시': '김해국제공항',
    '대구': '대구국제공항',
    '대구광역시': '대구국제공항',
    '울산': '울산공항',
    '울산광역시': '울산공항',
    '경북': '포항경주공항',
    '경상북도': '포항경주공항',
    '경남': '김해국제공항',
    '경상남도': '김해국제공항',

    # 호남권
    '광주': '광주공항',
    '광주광역시': '광주공항',
    '전북': '군산공항',
    '전라북도': '군산공항',
    '전남': '무안국제공항',
    '전라남도': '무안국제공항',

    # 충청권
    # 대전/세종에는 자체 민간공항이 없어 청주공항을 대표 공항으로 사용
    '대전': '청주국제공항',
    '대전광역시': '청주국제공항',
    '세종': '청주국제공항',
    '세종특별시': '청주국제공항',
    '세종특별자치시': '청주국제공항',
    '충북': '청주국제공항',
    '충청북도': '청주국제공항',
    '충남': '청주국제공항',
    '충청남도': '청주국제공항',

    # 강원 / 제주
    '강원': '양양국제공항',
    '강원도': '양양국제공항',
    '강원특별자치도': '양양국제공항',
    '제주': '제주국제공항',
    '제주도': '제주국제공항',
    '제주특별자치도': '제주국제공항',
}


# ==========================================
# 함수
# ==========================================

# ==========================================
# 지역명 정규화
# ==========================================

REGION_ALIASES = {
    # 특별/광역시
    '서울': '서울특별시',
    '서울특별시': '서울특별시',

    '부산': '부산광역시',
    '부산광역시': '부산광역시',

    '대구': '대구광역시',
    '대구광역시': '대구광역시',

    '인천': '인천광역시',
    '인천광역시': '인천광역시',

    '광주': '광주광역시',
    '광주광역시': '광주광역시',

    '대전': '대전광역시',
    '대전광역시': '대전광역시',

    '울산': '울산광역시',
    '울산광역시': '울산광역시',

    '세종': '세종특별시',
    '세종특별시': '세종특별시',
    '세종특별자치시': '세종특별시',

    # 도 / 특별자치도
    '경기': '경기도',
    '경기도': '경기도',

    '강원': '강원도',
    '강원도': '강원도',
    '강원특별자치도': '강원도',

    '충북': '충청북도',
    '충청북도': '충청북도',

    '충남': '충청남도',
    '충청남도': '충청남도',

    '전북': '전라북도',
    '전라북도': '전라북도',
    '전북특별자치도': '전라북도',

    '전남': '전라남도',
    '전라남도': '전라남도',

    '경북': '경상북도',
    '경상북도': '경상북도',

    '경남': '경상남도',
    '경상남도': '경상남도',

    '제주': '제주도',
    '제주도': '제주도',
    '제주특별자치도': '제주도',
}


def _normalize_region_name(city_name):
    """앱에서 사용하는 전국 지역명을 비교용 대표 지역명으로 통일합니다."""
    if not city_name:
        return city_name

    return REGION_ALIASES.get(
        str(city_name).strip(),
        str(city_name).strip()
    )


def _short_region_name(city_name):
    """버스 터미널 API 검색에 사용할 짧은 지역명으로 변환합니다."""
    canonical = _normalize_region_name(city_name)

    short_names = {
        '서울특별시': '서울',
        '부산광역시': '부산',
        '대구광역시': '대구',
        '인천광역시': '인천',
        '광주광역시': '광주',
        '대전광역시': '대전',
        '울산광역시': '울산',
        '세종특별시': '세종',
        '경기도': '경기',
        '강원도': '강원',
        '충청북도': '충북',
        '충청남도': '충남',
        '전라북도': '전북',
        '전라남도': '전남',
        '경상북도': '경북',
        '경상남도': '경남',
        '제주도': '제주',
    }

    return short_names.get(canonical, canonical)



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

    target_name = _normalize_region_name(city_name)

    for item in items:
        item_name = item.get(name_key)

        if _normalize_region_name(item_name) == target_name:
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

    return _short_region_name(city_name)

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
        canonical = _normalize_region_name(city_name)
        airport_name = AIRPORT_NAME_MAP.get(canonical)

    if not airport_name:
        return None

    for item in _extract_items(airport_data):
        if item.get('airportNm') == airport_name:
            return item.get('airportId')

    return None

# 교통수단 지역-ID 매핑
def _normalize_city_for_compare(city_name):
    return _normalize_region_name(city_name)



def _find_station_candidates(city_code, limit=3):
    """
    한 지역의 기차역 후보를 여러 개 반환합니다.
    첫 번째 역 하나만 사용하면 지역 대표역이 실제 장거리 운행에
    사용되지 않는 경우가 있어 후보를 여러 개 확보합니다.
    """
    if not city_code:
        return []

    data = get_train_stations(
        city_code,
        num_of_rows=100
    )

    candidates = []
    seen = set()

    for item in _extract_items(data):
        node_id = item.get('nodeid')
        if node_id and node_id not in seen:
            candidates.append(node_id)
            seen.add(node_id)

        if len(candidates) >= limit:
            break

    return candidates


def _find_terminal_candidates(
    city_name,
    terminal_type,
    limit=3
):
    """
    지역명으로 고속/시외버스터미널 후보를 여러 개 확보합니다.
    대표 터미널 1개만 선택했을 때 운행노선이 없는 경우를 대비합니다.
    """
    normalized_name = _normalize_bus_city_name(city_name)

    if terminal_type == 'express_bus':
        data = get_express_bus_terminal_list(
            terminal_nm=normalized_name,
            num_of_rows=100
        )
        preferred_names = EXPRESS_TERMINAL_PREFERENCE.get(
            normalized_name,
            []
        )
    else:
        data = get_intercity_bus_terminal_list(
            terminal_nm=normalized_name,
            num_of_rows=100
        )
        preferred_names = INTERCITY_TERMINAL_PREFERENCE.get(
            normalized_name,
            []
        )

    terminals = _extract_items(data)

    ordered = []
    seen = set()

    # 대표 터미널을 먼저 넣습니다.
    for preferred_name in preferred_names:
        for terminal in terminals:
            if terminal.get('terminalNm') == preferred_name:
                terminal_id = terminal.get('terminalId')
                if terminal_id and terminal_id not in seen:
                    ordered.append(terminal_id)
                    seen.add(terminal_id)

    # 이후 검색 결과를 후보로 추가합니다.
    for terminal in terminals:
        terminal_id = terminal.get('terminalId')
        if terminal_id and terminal_id not in seen:
            ordered.append(terminal_id)
            seen.add(terminal_id)

        if len(ordered) >= limit:
            break

    return ordered[:limit]


def _find_airport_candidates(city_name, airport_data):
    """
    공항은 지역 대표 공항 1개를 사용하되,
    별칭을 모두 허용합니다.
    """
    airport_id = _find_airport_id(
        city_name,
        airport_data
    )

    return [airport_id] if airport_id else []


def _get_transport_candidates(departure, arrival):
    """
    출발/도착 지역에 대해 교통수단별 후보 ID를 구성합니다.
    """
    train_city_codes = get_train_city_codes()

    # API에서 '인천' 계열이 누락되는 경우를 보정합니다.
    train_city_code_fallback = {
        '인천': '23',
        '인천광역시': '23',
    }

    dep_canonical = _normalize_region_name(departure)
    arr_canonical = _normalize_region_name(arrival)

    dep_train_city_code = train_city_code_fallback.get(
        departure
    )
    if dep_train_city_code is None:
        dep_train_city_code = train_city_code_fallback.get(
            dep_canonical
        )

    if dep_train_city_code is None:
        dep_train_city_code = _find_city_code(
            departure,
            train_city_codes,
            name_key='cityname',
            code_key='citycode'
        )

    arr_train_city_code = train_city_code_fallback.get(
        arrival
    )
    if arr_train_city_code is None:
        arr_train_city_code = train_city_code_fallback.get(
            arr_canonical
        )

    if arr_train_city_code is None:
        arr_train_city_code = _find_city_code(
            arrival,
            train_city_codes,
            name_key='cityname',
            code_key='citycode'
        )

    airport_data = get_airport_codes()

    return {
        'train': {
            'dep': _find_station_candidates(
                dep_train_city_code
            ),
            'arr': _find_station_candidates(
                arr_train_city_code
            ),
        },
        'express_bus': {
            'dep': _find_terminal_candidates(
                departure,
                'express_bus'
            ),
            'arr': _find_terminal_candidates(
                arrival,
                'express_bus'
            ),
        },
        'intercity_bus': {
            'dep': _find_terminal_candidates(
                departure,
                'intercity_bus'
            ),
            'arr': _find_terminal_candidates(
                arrival,
                'intercity_bus'
            ),
        },
        'flight': {
            'dep': _find_airport_candidates(
                departure,
                airport_data
            ),
            'arr': _find_airport_candidates(
                arrival,
                airport_data
            ),
        }
    }


def _query_transport_candidates(
    transport_type,
    departure_candidates,
    arrival_candidates,
    trip_date
):
    """
    후보 ID 조합을 순회하면서 실제 API 결과를 확보합니다.
    결과가 나오면 해당 교통수단의 추가 조합 조회를 중단합니다.
    """
    if not departure_candidates or not arrival_candidates:
        return []

    results = []
    seen_keys = set()

    for dep_id in departure_candidates:
        for arr_id in arrival_candidates:

            if dep_id == arr_id:
                continue

            try:
                kwargs = {}

                if transport_type == 'train':
                    kwargs['train'] = {
                        'dep_place_id': dep_id,
                        'arr_place_id': arr_id
                    }

                elif transport_type == 'express_bus':
                    kwargs['express_bus'] = {
                        'dep_terminal_id': dep_id,
                        'arr_terminal_id': arr_id
                    }

                elif transport_type == 'intercity_bus':
                    kwargs['intercity_bus'] = {
                        'dep_terminal_id': dep_id,
                        'arr_terminal_id': arr_id
                    }

                elif transport_type == 'flight':
                    kwargs['flight'] = {
                        'depAirportId': dep_id,
                        'arrAirportId': arr_id
                    }

                current = get_transport_options(
                    transport_types=[transport_type],
                    date=trip_date.strftime('%Y%m%d'),
                    **kwargs
                )

            except Exception as e:
                print(
                    f'{transport_type} 후보 조회 실패: '
                    f'{dep_id} → {arr_id} / {e}'
                )
                continue

            for item in current:
                key = (
                    item.get('transport_type'),
                    item.get('name'),
                    item.get('departure_time'),
                    item.get('arrival_time'),
                    item.get('price'),
                    item.get('departure'),
                    item.get('arrival')
                )

                if key not in seen_keys:
                    results.append(item)
                    seen_keys.add(key)

            # 해당 교통수단에서 결과를 찾았으면 추가 조합은 조회하지 않습니다.
            if results:
                return results

    return results


def get_transport_ids(departure, arrival):

    if not departure or not arrival:
        raise ValueError(
            '출발지 또는 도착지가 없습니다.'
        )

    candidates = _get_transport_candidates(
        departure,
        arrival
    )

    return {
        'train': {
            'dep_place_id': (
                candidates['train']['dep'][0]
                if candidates['train']['dep']
                else None
            ),
            'arr_place_id': (
                candidates['train']['arr'][0]
                if candidates['train']['arr']
                else None
            )
        },
        'express_bus': {
            'dep_terminal_id': (
                candidates['express_bus']['dep'][0]
                if candidates['express_bus']['dep']
                else None
            ),
            'arr_terminal_id': (
                candidates['express_bus']['arr'][0]
                if candidates['express_bus']['arr']
                else None
            )
        },
        'intercity_bus': {
            'dep_terminal_id': (
                candidates['intercity_bus']['dep'][0]
                if candidates['intercity_bus']['dep']
                else None
            ),
            'arr_terminal_id': (
                candidates['intercity_bus']['arr'][0]
                if candidates['intercity_bus']['arr']
                else None
            )
        },
        'flight': {
            'depAirportId': (
                candidates['flight']['dep'][0]
                if candidates['flight']['dep']
                else None
            ),
            'arrAirportId': (
                candidates['flight']['arr'][0]
                if candidates['flight']['arr']
                else None
            )
        }
    }


def _display_transport_item(transport):
    """교통편 1건을 공통 UI 형식으로 표시합니다."""

    transport_type = transport.get('transport_type', '')
    name = transport.get('name') or transport.get('vehicle_name') or '교통편'

    departure = transport.get('departure') or transport.get('dep_place') or ''
    arrival = transport.get('arrival') or transport.get('arr_place') or ''

    departure_time = transport.get('departure_time')
    arrival_time = transport.get('arrival_time')
    duration = transport.get('duration')
    price = transport.get('price')
    transfers = transport.get('transfers')

    icon_map = {
        'train': '🚆',
        'express_bus': '🚌',
        'intercity_bus': '🚌',
        'city_bus': '🚌',
        'subway': '🚇',
        'flight': '✈️',
    }
    icon = icon_map.get(transport_type, '🚍')

    st.markdown(f'### {icon} {name}')

    if transport_type in ('city_bus', 'subway'):
        st.write(f'📍 {departure} → {arrival}')

        if price is not None:
            try:
                price_value = float(price)
                st.write(f'💳 교통카드 기준: {price_value:,.0f}원')
                st.caption(f'왕복 기준: {price_value * 2:,.0f}원')
            except (TypeError, ValueError):
                st.write(f'💳 요금: {price}원')

        description = transport.get('description')
        if description:
            st.caption(description)
        return

    if departure or arrival:
        st.write(f'📍 {departure} → {arrival}')

    if departure_time or arrival_time:
        time_text = ''
        if departure_time:
            time_text += str(departure_time)
        if arrival_time:
            time_text += f' → {arrival_time}'
        st.write(f'🕐 {time_text}')

    if duration is not None:
        try:
            duration_value = int(duration)
            st.write(f'⏱️ 소요시간: {format_duration(duration_value)}')
        except (TypeError, ValueError):
            st.write(f'⏱️ 소요시간: {duration}')

    if price is not None:
        try:
            price_value = float(price)
            st.write(f'💳 요금: {price_value:,.0f}원')
            st.caption(f'왕복 기준: {price_value * 2:,.0f}원')
        except (TypeError, ValueError):
            st.write(f'💳 요금: {price}원')

    if transfers is not None:
        try:
            st.write(f'🔄 환승: {int(transfers)}회')
        except (TypeError, ValueError):
            st.write(f'🔄 환승: {transfers}')

def create_file(client, file_path):
    with open(file_path, 'rb') as file_content:
        result = client.files.create(
            file=file_content,
            purpose='assistants'
        )
    return result.id

def get_transport_results(
    departure,
    arrival,
    trip_date,
    option,
    time_after=None,
):

    # 동일 지역은 해당 여행지만 교통편 조회를 건너뜁니다.
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

        # 동일 지역은 장거리 교통 API를 조회하지 않고
        # 서울시 기준 시내버스 / 지하철 요금을 사용합니다.
        # 실제 출발지·도착지 간 노선이 아니라 동일 지역 내 이동의
        # 대표 교통비 기준으로 사용합니다.
        local_transit_results = [
            {
                'transport_type': 'city_bus',
                'name': '시내버스',
                'departure': departure,
                'arrival': arrival,
                'departure_time': None,
                'arrival_time': None,
                'duration': None,
                'price': 1500,
                'price_type': '서울시 기준',
                'transfers': 0,
                'description': '동일 지역 이동 시 서울시 기준 시내버스 교통카드 요금'
            },
            {
                'transport_type': 'subway',
                'name': '지하철',
                'departure': departure,
                'arrival': arrival,
                'departure_time': None,
                'arrival_time': None,
                'duration': None,
                'price': 1550,
                'price_type': '서울시 기준',
                'transfers': 0,
                'description': '동일 지역 이동 시 서울시 기준 지하철 교통카드 요금'
            }
        ]

        # 추천 기준에 따라 동일 지역의 대표 교통수단 순서를 조정합니다.
        if option == 'cheap':
            local_transit_results.sort(
                key=lambda x: x.get('price', 999999)
            )
        elif option == 'transfer':
            local_transit_results.sort(
                key=lambda x: x.get('transfers', 999999)
            )
        else:
            # fast / comfort / time은 실제 노선 소요시간 API를
            # 조회하지 않으므로 서울시 기준 시내버스를 기본 1순위로 둡니다.
            pass

        print('동일 지역 시내교통 결과:')
        for item in local_transit_results:
            print(
                f"{item['name']} | {item['price']}원 | "
                f"왕복 {item['price'] * 2}원"
            )

        return empty_ids, local_transit_results

    candidates = _get_transport_candidates(
        departure,
        arrival
    )

    transport_ids = {
        'train': {
            'dep_place_id': (
                candidates['train']['dep'][0]
                if candidates['train']['dep']
                else None
            ),
            'arr_place_id': (
                candidates['train']['arr'][0]
                if candidates['train']['arr']
                else None
            )
        },
        'express_bus': {
            'dep_terminal_id': (
                candidates['express_bus']['dep'][0]
                if candidates['express_bus']['dep']
                else None
            ),
            'arr_terminal_id': (
                candidates['express_bus']['arr'][0]
                if candidates['express_bus']['arr']
                else None
            )
        },
        'intercity_bus': {
            'dep_terminal_id': (
                candidates['intercity_bus']['dep'][0]
                if candidates['intercity_bus']['dep']
                else None
            ),
            'arr_terminal_id': (
                candidates['intercity_bus']['arr'][0]
                if candidates['intercity_bus']['arr']
                else None
            )
        },
        'flight': {
            'depAirportId': (
                candidates['flight']['dep'][0]
                if candidates['flight']['dep']
                else None
            ),
            'arrAirportId': (
                candidates['flight']['arr'][0]
                if candidates['flight']['arr']
                else None
            )
        }
    }

    # 교통수단별로 독립 조회합니다.
    # 한 교통수단의 0건/오류가 다른 교통수단 조회를 막지 않습니다.
    results = []

    for transport_type in (
        'train',
        'express_bus',
        'intercity_bus',
        'flight'
    ):
        type_results = _query_transport_candidates(
            transport_type=transport_type,
            departure_candidates=candidates[transport_type]['dep'],
            arrival_candidates=candidates[transport_type]['arr'],
            trip_date=trip_date
        )

        results.extend(type_results)

    print('====================================')
    print('교통 API 조회 테스트')
    print(f'출발지: {departure}')
    print(f'도착지: {arrival}')
    print(f'날짜: {trip_date.strftime("%Y%m%d")}')
    print(f'추천 기준: {option}')
    print(f'시간 조건: {time_after}')
    print('교통수단 후보:')
    print(candidates)
    print(f'대표 교통수단 ID: {transport_ids}')
    print(f'API 원본 결과: {len(results)}건')

    if results:
        print('출발시간 목록:')
        print([
            item.get('departure_time')
            for item in results
        ])

    # 시간 필터
    if time_after:
        results = [
            item for item in results
            if item.get('departure_time')
            and item['departure_time'] >= time_after
        ]

        print(
            f'시간 필터 적용 후: {len(results)}건'
        )

    # 추천 기준 적용
    if option == 'fast':
        results.sort(
            key=lambda x: (
                x.get('duration')
                if x.get('duration') is not None
                else 999999
            )
        )

    elif option == 'cheap':
        results.sort(
            key=lambda x: (
                x.get('price')
                if x.get('price') is not None
                else 999999999
            )
        )

    elif option == 'comfort':
        results.sort(
            key=lambda x: (
                x.get('transfers')
                if x.get('transfers') is not None
                else 999999,
                x.get('duration')
                if x.get('duration') is not None
                else 999999
            )
        )

    elif option == 'transfer':
        results.sort(
            key=lambda x: (
                x.get('transfers')
                if x.get('transfers') is not None
                else 999999
            )
        )

    elif option == 'time':
        results.sort(
            key=lambda x: x.get(
                'departure_time',
                '99:99'
            )
        )

    print('====================================')

    return transport_ids, results

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

st.title('✈️ K-Guide')
st.caption('AI 기반 맞춤형 한국 여행 추천 서비스')


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

if "tools" not in st.session_state:
    file_id = create_file(client, 'data/한국관광공사_OpenAPI_관광지_시군구_코드정보_v1.0.xlsx')
    vector_store = client.vector_stores.create(
        name='signgu base'
    )
    client.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=file_id
    )
    st.session_state.tools = [
                    {
                        "type": "web_search",
                        "search_context_size": "low", # 수집 정보 크기 최소화로 비용 절감
                        #"return_token_budget": 2000   # 검색 전용 토큰 한도를 제한하여 비용 폭증 방어
                    },
                    {
                        'type' : 'function',
                        'name' : 'is_peak_season',
                        'description' : '여행날짜, 여행기간, 관광지 주소를 받아 해당 기간 동안 그 장소의 방문자수 비율을 예측',
                        'parameters' : {
                            'type' : 'object',
                            'properties' : {
                                "trip_date": {
                                    "type": "string",
                                    "description" : "여행을 가는 날짜."
                                    },
                                "trip_period" : {
                                    "type": "number",
                                    "description" : "여행 기간"
                                    },
                                "destination" : {
                                    "type":"string",
                                    "description" : "관광지의 주소. 주소는 최소한 벡터 스토어에 저장된 파일의 sigunguNm 까지는 포함해야 한다."
                                    }
                            },
                        'required' : ["trip_date", "trip_period", "destination"],
                        'additionalProperties' : False
                        },
                        'strict' : True
                    },
                    {
                        'type' : 'file_search',
                        'vector_store_ids' : [vector_store.id]
                    }
                ]

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
st.sidebar.title('📝 여행 정보 입력')

# 추천 내용 전체 초기화
if st.sidebar.button('🔄 추천 내용 초기화'):

    st.session_state.current_tab = '여행 추천'
    st.session_state.destinations = []
    st.session_state.selected_recommendation = None
    st.session_state.recommendation_context = []

    st.session_state.hotel_list = []
    st.session_state.restaurant_list = []
    st.session_state.attraction_list = []

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
    if st.sidebar.button('✨ 여행 추천 받기'):

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
        st.subheader('🚆 이동 정보 설정')

        st.write('항공편 및 교통편도 함께 추천받으시겠습니까?')
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

        st.header('🗺️ 추천 여행지')

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

                            # 1순위 추천 교통편의 요금을 왕복 교통비로 합산
                            # 항공뿐 아니라 기차/고속버스/시외버스도 동일하게 처리합니다.
                            transport_price = recommended_transport.get('price')

                            if transport_price is not None:
                                try:
                                    transport_price = float(transport_price)
                                    # 왕복 교통비
                                    transport_expense = int(transport_price * 2)
                                except (TypeError, ValueError):
                                    # 가격 데이터가 숫자로 변환되지 않는 경우에는
                                    # 기존처럼 교통비를 0원으로 처리합니다.
                                    transport_expense = 0

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
                    elif (
                        st.session_state.transport_enabled
                        and recommended_transport_type == 'local'
                    ):
                        st.info(
                            '🚌🚇 동일 지역 이동: 시내버스 / 지하철 이용 권장'
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

    st.header("🤖 K-Guide AI")
    st.caption('여행에 대해 궁금한 점을 자유롭게 질문해보세요.')


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
        st.header('🏨 숙소 · 🌤️ 날씨')

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
            st.subheader('🏨 추천 숙소')

            if selected_api_context:

                hotel_list = selected_api_context.get('accommodations', [])
                st.session_state.hotel_list = hotel_list

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
                                '🔗 상세보기 및 예약',
                                hotel['url']
                            )

                        if i < min(5, len(hotel_list)):
                            st.divider()

                else: 
                    st.info('추천 숙소 정보가 없습니다.')

            else:
                st.info('숙소 정보를 불러오는 중입니다.')

        # 날씨
        with col2:
            st.subheader('🌤️ 날씨 정보')

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
        st.header('🍽️ 맛집 · 📍 관광지')

        col1, col2 = st.columns(2)

        # 맛집
        with col1:
            st.subheader('🍽️ 추천 맛집')
            
            if selected_api_context:

                restaurant_list = selected_api_context.get('restaurants', [])
                st.session_state.restaurant_list = restaurant_list

                if restaurant_list:

                    st.caption(f'추천 맛집 ({len(restaurant_list)}곳)')

                    for i, restaurant in enumerate(restaurant_list[:3], start=1):

                        # 음식점명 (카테고리)
                        st.info(f"{i}. {restaurant['name']} ({restaurant['category']})")
                        # 주소
                        st.write(f"주소: {restaurant['address']}")
                        # 운영시간
                        st.write(f"운영시간: {restaurant['opening_hours'].replace('~', r'\~')}")
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
            st.subheader('📍 추천 관광지')
            
            if selected_api_context:

                attraction_list = selected_api_context.get('tourist_attractions', [])
                st.session_state.attraction_list = attraction_list

                if attraction_list:      

                    for i, attraction in enumerate(attraction_list[:3], start=1):

                        # 광광지명 (카테고리)
                        st.info(f"{i}. {attraction['name']} ({attraction['category']})")
                        # 주소
                        st.write(f"주소: {attraction['address']}")
                        # 운영시간
                        st.write(f"운영시간: {attraction['opening_hours'].replace('~', r'\~')}")
                        # 특징
                        st.write(f"특징: {attraction['description']}")

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

            st.header('✈️ 항공편 · 🚆 교통편')

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
                        '동일 지역 이동으로 시내버스·지하철 기준 교통편을 적용했습니다.'
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

                    st.subheader('✈️ 항공편')

                    if flights:

                        for i, flight in enumerate(
                            flights[:3],
                            start=1
                        ):
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

                    st.subheader('🚆 교통편')

                    if transportation:

                        for i, transport in enumerate(
                            transportation[:3],
                            start=1
                        ):
                            st.caption(
                                f'교통편 {i}'
                            )

                            # 동일 지역이면 서울시 기준 시내버스 / 지하철
                            # 결과가 일반 교통편과 동일한 형태로 출력됩니다.
                            _display_transport_item(transport)

                            if transport.get('transport_type') in (
                                'city_bus',
                                'subway'
                            ):
                                st.caption(
                                    transport.get(
                                        'description',
                                        '동일 지역 이동은 서울시 기준 시내교통 요금을 적용합니다.'
                                    )
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
    if prompt := st.chat_input('여행에 대해 궁금한 점을 입력하세요.'):

        # 화면에 대화 메시지 출력
        st.chat_message('user').markdown(prompt)
        # messages에 대화내용을 추가
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

        # Responses API를 이용해서 모델 활용
        with st.chat_message('assistant'):
        # # ==========================================
        # # UI 테스트용 출력
        # # ------------------------------------------
        #     answer = 'K-Guide AI가 여행 정보를 분석하고 있습니다.'
        #     st.markdown(answer)

        # st.session_state.messages.append({
        #     'role': 'assistant',
        #     'content': answer
        # })
        # ==========================================
            response = client.responses.create(
                model='gpt-5.5',
                tools=st.session_state.tools,
                instructions=f'''
                당신은 한국을 방문한 외국 여행객을 위한 한국 여행 AI 어시스턴트입니다.
                사용자의 여행 조건과 질문을 바탕으로 친절하고 구체적인 여행 정보를 제공합니다.
                
                사용자의 여행 조건:
                - 성별 : {gender}
                - 나이 : {age}
                - 여행 테마 : {theme}
                - 인원수 : {num_of_people}
                - 출발 날짜 : {trip_date}
                - 여행 기간 : {period}일

                현재 추천된 여행지 : {st.session_state.destinations}
                현재 선택된 여행지 : {st.session_state.selected_recommendation}
                현재 추천된 숙소 : {st.session_state.hotel_list}
                현재 추천된 맛집 : {st.session_state.restaurant_list}
                현재 추천된 관광지 : {st.session_state.attraction_list}

                최신 정보가 필요한 경우 웹 검색을 활용하세요.
                특히 날씨, 운영시간, 가격, 숙소, 맛집, 관광지, 교통편 등
                현재 정보가 중요한 질문의 경우에는 웹 검색을 우선으로 활용하세요.

                사용자가 관광지의 혼잡도나 성수기 여부 등에 대해 질문하면 function calling 결과로 나온
                방문자수를 기반으로하여 답변하세요.

                매우 중요: 첫 번째 시도가 실패하더라도 유사한 검색 쿼리를 반복하지 마십시오.
                1~2회 검색 내에 정확한 정보를 찾을 수 없는 경우,
                검색을 중단하고 보유한 데이터를 바탕으로 최선의 답변을 제공하십시오.
                ''',
                input=st.session_state.messages,
                # stream=True,
                max_output_tokens=1500
            )

            for item in response.output:
                if item.type == 'function_call':
                    input_msg = st.session_state.messages + response.output
                    args = json.loads(item.arguments)
                    pred_tounum = estimate_peak.is_peak_season(**args)
                    input_msg.append({
                        'type' : 'function_call_output',
                        'call_id' : item.call_id,
                        'output' : str(pred_tounum)
                    })

                    response = client.responses.create(
                        model = 'gpt-5.5',
                        input = input_msg,
                        tools = st.session_state.tools
                    )
                    break


            # # 스트리밍 청크 생성 함수
            # def gen_chunks():
            #     for event in response:
            #         # delta 텍스트 처리
            #         if hasattr(event, 'delta') and event.delta:
            #             yield event.delta
            #         elif getattr(event, "type", None) == "response.output_text.delta":
            #             yield event.delta

            # 화면 출력 => 완전한 응답 데이터 저장
            # full_response = st.write_stream(gen_chunks())
            st.write(response.output_text)

        # 세션에 저장된 대화 메시지에 응답 데이터 저장
        st.session_state.messages.append(
            {
                "role":"assistant",
                "content": response.output_text
            }
        )