# ============================================================
# 교통 통합 조회 함수
# app.py에서는 이 함수 하나만 호출해서 사용
# ============================================================

from api import (
    get_train,
    get_express_bus,
    get_intercity_bus,
    get_domestic_flight_operation_list,
)

from transport_normalizer import (
    normalize_train,
    normalize_express_bus,
    normalize_intercity_bus,
    normalize_flight,
)


def _extract_items(data):
    """
    공공데이터 API 응답에서 item 목록만 추출합니다.

    API 응답 구조가
    response -> body -> items -> item
    형태인 경우를 기준으로 합니다.
    """

    if not isinstance(data, dict):
        return []

    response = data.get("response", data)
    body = response.get("body", {}) if isinstance(response, dict) else {}
    items = body.get("items", {}) if isinstance(body, dict) else {}

    if isinstance(items, dict):
        items = items.get("item", [])

    if isinstance(items, dict):
        return [items]

    if isinstance(items, list):
        return items

    return []


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

    Parameters
    ----------
    transport_types : list[str]
        조회할 교통수단

        예:
        ["train", "express_bus", "intercity_bus", "flight"]

    date : str
        출발 날짜
        예: "20260814"

    train : dict
        {
            "dep_place_id": "NAT010000",
            "arr_place_id": "NAT010971"
        }

    express_bus : dict
        {
            "dep_terminal_id": "NAEK010",
            "arr_terminal_id": "NAEK000"
        }

    intercity_bus : dict
        {
            "dep_terminal_id": "NAI0671801",
            "arr_terminal_id": "NAI3438001"
        }

    flight : dict
        {
            "depAirportId": "GMP",
            "arrAirportId": "CJU"
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

        data = get_train(
            dep_place_id=train["dep_place_id"],
            arr_place_id=train["arr_place_id"],
            dep_date=date,
        )

        for item in _extract_items(data):
            results.append(
                normalize_train(item)
            )

    # ========================================================
    # 2. 고속버스
    # ========================================================

    if "express_bus" in transport_types and express_bus:

        data = get_express_bus(
            dep_terminal_id=express_bus["dep_terminal_id"],
            arr_terminal_id=express_bus["arr_terminal_id"],
            dep_date=date,
        )

        for item in _extract_items(data):
            results.append(
                normalize_express_bus(item)
            )

    # ========================================================
    # 3. 시외버스
    # ========================================================

    if "intercity_bus" in transport_types and intercity_bus:

        data = get_intercity_bus(
            dep_terminal_id=intercity_bus["dep_terminal_id"],
            arr_terminal_id=intercity_bus["arr_terminal_id"],
            dep_date=date,
        )

        for item in _extract_items(data):
            results.append(
                normalize_intercity_bus(item)
            )

    # ========================================================
    # 4. 국내 항공
    # ========================================================

    if "flight" in transport_types and flight:

        data = get_domestic_flight_operation_list(
            depAirportId=flight["depAirportId"],
            arrAirportId=flight["arrAirportId"],
        )

        for item in _extract_items(data):
            results.append(
                normalize_flight(item)
            )

    return results