# API 공통 데이터 형식으로 변환

from datetime import datetime


def normalize_train(item):
    """열차 API 응답을 공통 데이터 형식으로 변환"""

    dep_time = datetime.strptime(
        item["depplandtime"], "%Y%m%d%H%M%S"
    )

    arr_time = datetime.strptime(
        item["arrplandtime"], "%Y%m%d%H%M%S"
    )

    duration = int(
        (arr_time - dep_time).total_seconds() // 60
    )

    return {
        "transport_type": "train",
        "name": item.get("traingradename", ""),
        "departure": item.get("depplacename", ""),
        "arrival": item.get("arrplacename", ""),
        "departure_time": dep_time.strftime("%H:%M"),
        "arrival_time": arr_time.strftime("%H:%M"),
        "duration": duration,
        "price": int(item["adultcharge"]) if item.get("adultcharge") else None,
        "transfers": 0
    }

def normalize_express_bus(item):
    """고속버스 API 응답을 공통 데이터 형식으로 변환"""

    dep_time = datetime.strptime(
        str(item["depPlandTime"]), "%Y%m%d%H%M"
    )

    arr_time = datetime.strptime(
        str(item["arrPlandTime"]), "%Y%m%d%H%M"
    )

    duration = int(
        (arr_time - dep_time).total_seconds() // 60
    )

    return {
        "transport_type": "express_bus",
        "name": item.get("gradeNm", "고속버스"),
        "departure": item.get("depPlaceNm", ""),
        "arrival": item.get("arrPlaceNm", ""),
        "departure_time": dep_time.strftime("%H:%M"),
        "arrival_time": arr_time.strftime("%H:%M"),
        "duration": duration,
        "price": int(item["charge"]) if item.get("charge") else None,
        "transfers": 0
    }

def normalize_intercity_bus(item):
    """시외버스 API 응답을 공통 데이터 형식으로 변환"""

    dep_time = datetime.strptime(
        str(item["depPlandTime"]), "%Y%m%d%H%M%S"
    )

    arr_time = datetime.strptime(
        str(item["arrPlandTime"]), "%Y%m%d%H%M%S"
    )

    duration = int(
        (arr_time - dep_time).total_seconds() // 60
    )

    return {
        "transport_type": "intercity_bus",
        "name": item.get("gradeNm", "시외버스"),
        "departure": item.get("depPlaceNm", ""),
        "arrival": item.get("arrPlaceNm", ""),
        "departure_time": dep_time.strftime("%H:%M"),
        "arrival_time": arr_time.strftime("%H:%M"),
        "duration": duration,
        "price": int(item["charge"]) if item.get("charge") else None,
        "transfers": 0
    }

def normalize_city_bus(item, bus_type="간선"):
    """시내버스 API 응답 + 서울시 기준요금을 공통 데이터 형식으로 변환"""

    # 서울시 기준 성인 교통카드 요금
    fare_table = {
        "간선": 1500,
        "지선": 1500,
        "순환": 1400,
        "광역": 3000,
        "심야": 2500,
        "마을": 1200
    }

    price = fare_table.get(bus_type, 1500)

    # API의 운행시간은 HHMM 형태
    start_time = str(item.get("startvehicletime", ""))

    if len(start_time) == 4:
        departure_time = (
            f"{start_time[:2]}:{start_time[2:]}"
        )
    else:
        departure_time = start_time

    end_time = str(item.get("endvehicletime", ""))

    if len(end_time) == 4:
        arrival_time = (
            f"{end_time[:2]}:{end_time[2:]}"
        )
    else:
        arrival_time = end_time

    return {
        "transport_type": "city_bus",
        "name": f"{bus_type}버스 {item.get('routeno', '')}",
        "departure": item.get("startnodenm", ""),
        "arrival": item.get("endnodenm", ""),
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "duration": None,
        "price": price,
        "price_type": "standard",
        "transfers": 0
    }


def normalize_subway(item):
    """지하철 운임 API 응답을 공통 데이터 형식으로 변환"""

    return {
        "transport_type": "subway",
        "name": "지하철",
        "departure": item.get("dptreStnNm", ""),
        "arrival": item.get("arvlStnNm", ""),
        "departure_time": "",
        "arrival_time": "",
        "duration": None,
        "price": int(item["gnrlCardFare"]) if item.get("gnrlCardFare") else None,
        "price_type": "api",
        "transfers": 0
    }


def normalize_flight(item):
    """국내 항공 운항정보 API 응답을 공통 데이터 형식으로 변환"""

    dep_time = datetime.strptime(
        str(item["depPlandTime"]),
        "%Y%m%d%H%M"
    )

    arr_time = datetime.strptime(
        str(item["arrPlandTime"]),
        "%Y%m%d%H%M"
    )

    duration = int(
        (arr_time - dep_time).total_seconds() // 60
    )

    return {
        "transport_type": "flight",
        "name": item.get("airlineNm", ""),
        "departure": item.get("depAirportNm", ""),
        "arrival": item.get("arrAirportNm", ""),
        "departure_time": dep_time.strftime("%H:%M"),
        "arrival_time": arr_time.strftime("%H:%M"),
        "duration": duration,
        "price": item.get("economyCharge"),
        "price_type": "api",
        "transfers": 0
    }

def normalize_taxi(
    departure,
    arrival,
    duration,
    distance_km,
    price
):
    """택시 길찾기 결과를 공통 데이터 형식으로 변환"""

    return {
        "transport_type": "taxi",
        "name": "택시",
        "departure": departure,
        "arrival": arrival,
        "departure_time": "",
        "arrival_time": "",
        "duration": duration,
        "price": price,
        "price_type": "estimated",
        "transfers": 0
    }
