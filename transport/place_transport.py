# 위도, 경도로 장소간 카카오 대중교통 경로 조회

import os
import requests
from dotenv import load_dotenv

load_dotenv()

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

PUBLIC_TRANSPORT_URL = (
    "https://dapi.kakao.com/v2/routing/publictraffic"
)


def get_place_transport(
    departure_name,
    departure_lat,
    departure_lon,
    arrival_name,
    arrival_lat,
    arrival_lon,
):
    """
    두 장소의 좌표를 이용해 대중교통 경로를 조회합니다.
    """

    if not KAKAO_REST_API_KEY:
        raise ValueError(
            "KAKAO_REST_API_KEY가 .env에 설정되어 있지 않습니다."
        )

    headers = {
        "Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"
    }

    params = {
        "start_x": departure_lon,
        "start_y": departure_lat,
        "s_name": departure_name,
        "end_x": arrival_lon,
        "end_y": arrival_lat,
        "e_name": arrival_name,
        "input_coord": "WGS84",
        "output_coord": "WGS84",
    }

    response = requests.get(
        PUBLIC_TRANSPORT_URL,
        headers=headers,
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("status") != "OK":
        return []

    routes = []

    for route in data.get("routes", []):

        properties = route.get("properties", {})

        route_type = properties.get("type", "")

        if route_type == "BUS":
            transport_type = "버스"

        elif route_type == "SUBWAY":
            transport_type = "지하철"

        elif route_type == "BUS_AND_SUBWAY":
            transport_type = "버스 + 지하철"

        else:
            transport_type = route_type

        total_distance = properties.get(
            "totalDistance", 0
        )

        total_time = properties.get(
            "totalTime", 0
        )

        transfers = properties.get(
            "transfers", 0
        )

        fare_data = properties.get(
            "fare", {}
        )

        fare = fare_data.get(
            "value",
            fare_data.get("min", 0)
        )

        distance_km = round(
            total_distance / 1000,
            1
        )

        duration_min = round(
            total_time / 60
        )

        vehicles = []

        for step in route.get("steps", []):

            step_properties = step.get(
                "properties", {}
            )

            for vehicle in step_properties.get(
                "vehicles", []
            ):

                vehicle_name = vehicle.get("name")

                if vehicle_name:
                    vehicles.append(vehicle_name)

        vehicles = list(
            dict.fromkeys(vehicles)
        )

        routes.append({
            "transport_type": transport_type,
            "name": (
                " → ".join(vehicles)
                if vehicles
                else transport_type
            ),
            "departure": departure_name,
            "arrival": arrival_name,
            "distance": distance_km,
            "duration": duration_min,
            "price": fare,
            "transfers": transfers,
            "price_type": "kakao_public",
        })

    routes.sort(
        key=lambda x: x["duration"]
    )

    return routes