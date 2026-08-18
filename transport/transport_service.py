# ============================================================
# 교통 통합 조회 함수
# app.py에서는 이 함수 하나만 호출해서 사용
# ============================================================

from transport.api import (
    get_train,
    get_express_bus,
    get_intercity_bus,
    get_domestic_flight_operation_list,
)

from transport.transport_normalizer import (
    normalize_train,
    normalize_express_bus,
    normalize_intercity_bus,
    normalize_flight,
)


# ============================================================
# 공통 함수
# ============================================================

def _extract_items(data):
    """
    공공데이터 API 응답에서 item 목록만 추출합니다.

    API 응답 구조:
    response -> body -> items -> item
    """

    if not isinstance(data, dict):
        return []

    response = data.get("response", data)

    body = (
        response.get("body", {})
        if isinstance(response, dict)
        else {}
    )

    items = (
        body.get("items", {})
        if isinstance(body, dict)
        else {}
    )

    if isinstance(items, dict):
        items = items.get("item", [])

    if isinstance(items, dict):
        return [items]

    if isinstance(items, list):
        return items

    return []


# ============================================================
# 지역명 정규화
# ============================================================

def normalize_city_name(city_name):
    """
    지역명을 비교용 대표 지역명으로 통일합니다.
    """

    if not city_name:
        return ""

    city_name = str(city_name).strip()

    aliases = {
        # 특별시 / 광역시
        "서울": "서울특별시",
        "서울특별시": "서울특별시",

        "부산": "부산광역시",
        "부산광역시": "부산광역시",

        "대구": "대구광역시",
        "대구광역시": "대구광역시",

        "인천": "인천광역시",
        "인천광역시": "인천광역시",

        "광주": "광주광역시",
        "광주광역시": "광주광역시",

        "대전": "대전광역시",
        "대전광역시": "대전광역시",

        "울산": "울산광역시",
        "울산광역시": "울산광역시",

        "세종": "세종특별시",
        "세종특별시": "세종특별시",
        "세종특별자치시": "세종특별시",

        # 도
        "경기": "경기도",
        "경기도": "경기도",

        "강원": "강원도",
        "강원도": "강원도",
        "강원특별자치도": "강원도",

        "충북": "충청북도",
        "충청북도": "충청북도",

        "충남": "충청남도",
        "충청남도": "충청남도",

        "전북": "전라북도",
        "전라북도": "전라북도",
        "전북특별자치도": "전라북도",

        "전남": "전라남도",
        "전라남도": "전라남도",

        "경북": "경상북도",
        "경상북도": "경상북도",

        "경남": "경상남도",
        "경상남도": "경상남도",

        "제주": "제주도",
        "제주도": "제주도",
        "제주특별자치도": "제주도",
    }

    return aliases.get(city_name, city_name)


def is_same_city(departure, arrival):
    """
    출발지와 도착지가 동일 지역인지 확인합니다.
    """

    dep = normalize_city_name(departure)
    arr = normalize_city_name(arrival)

    return dep == arr


# ============================================================
# 동일 지역 교통
# ============================================================

def get_local_transport_options():
    """
    동일 지역 이동용 교통편입니다.

    현재 프로젝트의 api.py에는
    출발지 → 도착지 사이의 실제 시내교통 운임을
    직접 조회하는 API가 없으므로,

    프로젝트에서 사용 중인 서울시 기준 요금을 사용합니다.

    시내버스 : 1,500원
    지하철   : 1,550원

    반환 형식은 장거리 교통 결과와 동일하게
    price 필드를 포함합니다.
    """

    results = []

    # ========================================================
    # 시내버스
    # ========================================================

    results.append({
        "transport_type": "city_bus",
        "name": "시내버스",
        "departure": "지역 내 이동",
        "arrival": "지역 내 이동",
        "departure_time": "",
        "arrival_time": "",
        "duration": None,
        "price": 1500,
        "transfers": 0,
        "description": "서울시 기준 시내버스 교통카드 요금",
    })

    # ========================================================
    # 지하철
    # ========================================================

    results.append({
        "transport_type": "subway",
        "name": "지하철",
        "departure": "지역 내 이동",
        "arrival": "지역 내 이동",
        "departure_time": "",
        "arrival_time": "",
        "duration": None,
        "price": 1550,
        "transfers": 0,
        "description": "서울시 기준 지하철 교통카드 요금",
    })

    return results


# ============================================================
# 장거리 교통 통합 조회
# ============================================================

def get_transport_options(
    transport_types,
    date,
    train=None,
    express_bus=None,
    intercity_bus=None,
    flight=None,
):
    """
    여러 교통수단을 하나의 함수에서 통합 조회합니다.

    동일 지역은 이 함수에서 처리하지 않고
    get_local_transport_options()에서 처리합니다.

    Parameters
    ----------
    transport_types : list[str]
        조회할 교통수단

    date : str
        출발 날짜
        예: "20260818"

    train : dict
        {
            "dep_place_id": "...",
            "arr_place_id": "..."
        }

    express_bus : dict
        {
            "dep_terminal_id": "...",
            "arr_terminal_id": "..."
        }

    intercity_bus : dict
        {
            "dep_terminal_id": "...",
            "arr_terminal_id": "..."
        }

    flight : dict
        {
            "depAirportId": "...",
            "arrAirportId": "..."
        }

    Returns
    -------
    list[dict]
        정규화된 통합 교통 데이터
    """

    results = []

    # ========================================================
    # 1. 열차
    # ========================================================

    if "train" in transport_types and train:

        dep_place_id = train.get("dep_place_id")
        arr_place_id = train.get("arr_place_id")

        # 도착역 ID가 없는 경우 조회하지 않음
        if dep_place_id and arr_place_id:

            data = get_train(
                dep_place_id=dep_place_id,
                arr_place_id=arr_place_id,
                dep_date=date,
            )

            for item in _extract_items(data):

                normalized = normalize_train(item)

                if normalized:
                    results.append(normalized)

    # ========================================================
    # 2. 고속버스
    # ========================================================

    if "express_bus" in transport_types and express_bus:

        dep_terminal_id = express_bus.get("dep_terminal_id")
        arr_terminal_id = express_bus.get("arr_terminal_id")

        if dep_terminal_id and arr_terminal_id:

            data = get_express_bus(
                dep_terminal_id=dep_terminal_id,
                arr_terminal_id=arr_terminal_id,
                dep_date=date,
            )

            for item in _extract_items(data):

                normalized = normalize_express_bus(item)

                if normalized:
                    results.append(normalized)

    # ========================================================
    # 3. 시외버스
    # ========================================================

    if "intercity_bus" in transport_types and intercity_bus:

        dep_terminal_id = intercity_bus.get("dep_terminal_id")
        arr_terminal_id = intercity_bus.get("arr_terminal_id")

        if dep_terminal_id and arr_terminal_id:

            data = get_intercity_bus(
                dep_terminal_id=dep_terminal_id,
                arr_terminal_id=arr_terminal_id,
                dep_date=date,
            )

            for item in _extract_items(data):

                normalized = normalize_intercity_bus(item)

                if normalized:
                    results.append(normalized)

    # ========================================================
    # 4. 국내 항공
    # ========================================================

    if "flight" in transport_types and flight:

        dep_airport_id = flight.get("depAirportId")
        arr_airport_id = flight.get("arrAirportId")

        if dep_airport_id and arr_airport_id:

            data = get_domestic_flight_operation_list(
                depAirportId=dep_airport_id,
                arrAirportId=arr_airport_id,
            )

            for item in _extract_items(data):

                normalized = normalize_flight(item)

                if normalized:
                    results.append(normalized)

    return results


# ============================================================
# 최종 통합 조회 함수
# app.py에서는 이 함수 하나만 호출
# ============================================================

def get_transport_options_with_local(
    departure,
    arrival,
    transport_types,
    date,
    train=None,
    express_bus=None,
    intercity_bus=None,
    flight=None,
):
    """
    장거리 / 동일 지역 교통을 하나의 함수에서 처리합니다.

    동일 지역:
        시내버스 + 지하철

    다른 지역:
        기차 + 고속버스 + 시외버스 + 항공
    """

    # ========================================================
    # 동일 지역
    # ========================================================

    if is_same_city(departure, arrival):

        print("=" * 60)
        print(
            f"동일 지역 교통 조회: "
            f"{departure} → {arrival}"
        )
        print("서울시 기준 시내버스 / 지하철 요금을 사용합니다.")
        print("=" * 60)

        return {
            "local": True,
            "transport_ids": {},
        }, get_local_transport_options()

    # ========================================================
    # 장거리
    # ========================================================

    results = get_transport_options(
        transport_types=transport_types,
        date=date,
        train=train,
        express_bus=express_bus,
        intercity_bus=intercity_bus,
        flight=flight,
    )

    return {
        "local": False,
        "transport_ids": {
            "train": train,
            "express_bus": express_bus,
            "intercity_bus": intercity_bus,
            "flight": flight,
        },
    }, results