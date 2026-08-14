# 여러 추천 장소를 순서대로 연결해서 장소간 이동 정보 생성

from place_transport import get_place_transport


def search_place_transport(
    departure_name,
    departure_lat,
    departure_lon,
    arrival_name,
    arrival_lat,
    arrival_lon,
    option="fast",
):
    """
    두 장소 사이의 대중교통 경로를 조회하고
    원하는 조건에 따라 정렬합니다.

    option
    - fast     : 빠른 교통편
    - cheap    : 저렴한 교통편
    - comfort  : 편한 교통편
    - transfer : 환승 적은 교통편
    """

    routes = get_place_transport(
        departure_name=departure_name,
        departure_lat=departure_lat,
        departure_lon=departure_lon,
        arrival_name=arrival_name,
        arrival_lat=arrival_lat,
        arrival_lon=arrival_lon,
    )

    if not routes:
        return []

    if option == "fast":
        routes.sort(
            key=lambda x: x.get("duration", 999999)
        )

    elif option == "cheap":
        routes.sort(
            key=lambda x: (
                x.get("price", 999999),
                x.get("duration", 999999),
            )
        )

    elif option == "comfort":
        routes.sort(
            key=lambda x: (
                x.get("transfers", 999999),
                x.get("duration", 999999),
            )
        )

    elif option == "transfer":
        routes.sort(
            key=lambda x: (
                x.get("transfers", 999999),
                x.get("duration", 999999),
            )
        )

    else:
        raise ValueError(
            "option은 fast, cheap, comfort, transfer 중 하나여야 합니다."
        )

    return routes


def format_place_transport(route):
    """
    UI에서 사용하기 편한 형태로 변환합니다.
    """

    return {
        "type": route.get("transport_type", ""),
        "route": route.get("name", ""),
        "departure": route.get("departure", ""),
        "arrival": route.get("arrival", ""),
        "distance": route.get("distance", 0),
        "duration": route.get("duration", 0),
        "price": route.get("price", 0),
        "transfers": route.get("transfers", 0),
    }