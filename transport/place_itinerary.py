from place_transport_search import (
    search_place_transport,
    format_place_transport,
)


def build_place_itinerary(
    places,
    option="fast",
    max_routes=1,
):
    """
    추천 장소 목록을 순서대로 받아
    장소와 장소 사이의 이동정보를 생성합니다.

    Parameters
    ----------
    places : list[dict]
        [
            {
                "name": "해운대",
                "latitude": 35.1587,
                "longitude": 129.1604
            },
            ...
        ]

    option : str
        fast     : 빠른 교통편
        cheap    : 저렴한 교통편
        comfort  : 편한 교통편
        transfer : 환승 적은 교통편

    max_routes : int
        각 구간에서 보여줄 경로 개수

    Returns
    -------
    list[dict]
        장소 간 이동정보
    """

    if not places or len(places) < 2:
        return []

    itinerary = []

    for i in range(len(places) - 1):

        departure = places[i]
        arrival = places[i + 1]

        routes = search_place_transport(
            departure_name=departure["name"],
            departure_lat=departure["latitude"],
            departure_lon=departure["longitude"],
            arrival_name=arrival["name"],
            arrival_lat=arrival["latitude"],
            arrival_lon=arrival["longitude"],
            option=option,
        )

        if not routes:
            itinerary.append({
                "departure": departure["name"],
                "arrival": arrival["name"],
                "transport": None,
            })
            continue

        selected_routes = routes[:max_routes]

        itinerary.append({
            "departure": departure["name"],
            "arrival": arrival["name"],
            "transport": [
                format_place_transport(route)
                for route in selected_routes
            ],
        })

    return itinerary
