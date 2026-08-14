# 기존 교통 API 호출 함수 모음

import os
from urllib.parse import unquote

import requests
from dotenv import load_dotenv

load_dotenv()

SERVICE_KEY = unquote(os.getenv("DATA_API_KEY", ""))

# ============================================================
# 공공데이터포털(TAGO) 공통 호출 함수
# ============================================================

def _call_tago(service_path, operation, **params):
    """
    공공데이터포털 TAGO API 공통 호출 함수

    .env
    DATA_API_KEY=공공데이터포털 일반 인증키

    params는 각 상세기능의 Request Parameter 이름 그대로 전달합니다.
    """
    url = f"https://apis.data.go.kr/1613000/{service_path}/{operation}"

    request_params = {
        "serviceKey": SERVICE_KEY,
        "_type": "json",
    }

    # None 값은 요청에서 제외
    request_params.update({
        key: value
        for key, value in params.items()
        if value is not None
    })

    response = requests.get(url, params=request_params, timeout=10)
    response.raise_for_status()

    return response.json()


# ============================================================
# 1. 버스 정류소 정보 - BusSttnInfoInqireService (4개)
# ============================================================

def get_nearby_bus_stations(gps_lati, gps_long, page_no=1, num_of_rows=10):
    """1. 좌표기반 근접정류소 목록조회"""
    return _call_tago(
        "BusSttnInfoInqireService",
        "getCrdntPrxmtSttnList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        gpsLati=gps_lati,
        gpsLong=gps_long,
    )


def get_bus_station_no_list(city_code=None, node_nm=None, node_no=None,
                            page_no=1, num_of_rows=10):
    """2. 정류소번호 목록조회"""
    return _call_tago(
        "BusSttnInfoInqireService",
        "getSttnNoList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        cityCode=city_code,
        nodeNm=node_nm,
        nodeNo=node_no,
    )


def get_bus_station_through_routes(city_code, node_id,
                                    page_no=1, num_of_rows=10):
    """3. 정류소별 경유노선 목록조회"""
    return _call_tago(
        "BusSttnInfoInqireService",
        "getSttnThrghRouteList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        cityCode=city_code,
        nodeid=node_id,
    )


def get_bus_station_city_codes(page_no=1, num_of_rows=10):
    """4. 도시코드 목록 조회"""
    return _call_tago(
        "BusSttnInfoInqireService",
        "getCtyCodeList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


# ============================================================
# 2. 버스 노선 정보 - BusRouteInfoInqireService (4개)
# ============================================================

def get_city_bus_route(city_code, route_id):
    """1. 노선정보항목 조회"""
    return _call_tago(
        "BusRouteInfoInqireService",
        "getRouteInfoIem",
        cityCode=city_code,
        routeId=route_id,
    )


def get_city_bus_route_no_list(city_code, route_no=None,
                                page_no=1, num_of_rows=10):
    """2. 노선번호 목록 조회"""
    return _call_tago(
        "BusRouteInfoInqireService",
        "getRouteNoList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        cityCode=city_code,
        routeNo=route_no,
    )


def get_city_bus_route_stations(city_code, route_id,
                                page_no=1, num_of_rows=10):
    """3. 노선별 경유정류소목록 조회"""
    return _call_tago(
        "BusRouteInfoInqireService",
        "getRouteAcctoThrghSttnList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        cityCode=city_code,
        routeId=route_id,
    )


def get_city_bus_city_codes(page_no=1, num_of_rows=10):
    """4. 도시코드 목록 조회"""
    return _call_tago(
        "BusRouteInfoInqireService",
        "getCtyCodeList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


# ============================================================
# 3. 지하철 정보 - SubwayInfo (4개)
# ============================================================

def get_subway_station(station_name, page_no=1, num_of_rows=10):
    """1. 키워드기반 지하철역 목록 조회"""
    return _call_tago(
        "SubwayInfo",
        "GetKwrdFndSubwaySttnList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        subwayStationName=station_name,
    )


def get_subway_exit_bus_routes(subway_station_id,
                               page_no=1, num_of_rows=10):
    """2. 지하철역출구별 버스노선 목록 조회"""
    return _call_tago(
        "SubwayInfo",
        "GetSubwaySttnExitAcctoBusRouteList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        subwayStationId=subway_station_id,
    )


def get_subway_exit_facilities(subway_station_id,
                               page_no=1, num_of_rows=10):
    """3. 지하철역출구별 주변 시설 목록 조회"""
    return _call_tago(
        "SubwayInfo",
        "GetSubwaySttnExitAcctoCfrFcltyList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        subwayStationId=subway_station_id,
    )


def get_subway_schedule(
    subway_station_id,
    daily_type_code,
    up_down_type_code,
    page_no=1,
    num_of_rows=10,
):
    """4. 지하철역별 시간표 목록 조회

    daily_type_code:
        01 = 평일
        02 = 토요일
        03 = 일요일

    up_down_type_code:
        U = 상행
        D = 하행
    """
    return _call_tago(
        "SubwayInfo",
        "GetSubwaySttnAcctoSchdulList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        subwayStationId=subway_station_id,
        dailyTypeCode=daily_type_code,
        upDownTypeCode=up_down_type_code,
    )


# ============================================================
# 4. 시외버스 정보 - SuburbsBusInfo (4개)
# ============================================================

def get_intercity_bus_terminal_list(terminal_nm=None, city_code=None,
                                     page_no=1, num_of_rows=10):
    """1. 시외버스 터미널 목록 조회"""
    return _call_tago(
        "SuburbsBusInfo",
        "GetSuberbsBusTrminlList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        terminalNm=terminal_nm,
        cityCode=city_code,
    )


def get_intercity_bus(dep_terminal_id, arr_terminal_id, dep_date,
                       page_no=1, num_of_rows=10):
    """2. 출/도착지 기반 시외버스정보 조회"""
    return _call_tago(
        "SuburbsBusInfo",
        "GetStrtpntAlocFndSuberbsBusInfo",
        pageNo=page_no,
        numOfRows=num_of_rows,
        depTerminalId=dep_terminal_id,
        arrTerminalId=arr_terminal_id,
        depPlandTime=dep_date,
    )


def get_intercity_bus_city_codes(page_no=1, num_of_rows=10):
    """3. 도시코드 목록 조회"""
    return _call_tago(
        "SuburbsBusInfo",
        "GetCtyCodeList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


def get_intercity_bus_grades(page_no=1, num_of_rows=10):
    """4. 시외버스 등급 목록 조회"""
    return _call_tago(
        "SuburbsBusInfo",
        "GetSuberbsBusGradList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


# ============================================================
# 5. 열차 정보 - TrainInfo (4개)
# ============================================================

def get_train_city_codes(page_no=1, num_of_rows=10):
    """1. 도시코드 목록 조회"""
    return _call_tago(
        "TrainInfo",
        "GetCtyCodeList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


def get_train(dep_place_id, arr_place_id, dep_date,
              train_grade_code=None, page_no=1, num_of_rows=10):
    """2. 출/도착지 기반 열차정보 조회"""
    return _call_tago(
        "TrainInfo",
        "GetStrtpntAlocFndTrainInfo",
        pageNo=page_no,
        numOfRows=num_of_rows,
        depPlaceId=dep_place_id,
        arrPlaceId=arr_place_id,
        depPlandTime=dep_date,
        trainGradeCode=train_grade_code,
    )


def get_train_stations(city_code, page_no=1, num_of_rows=10):
    """3. 시/도별 기차역 목록 조회"""
    return _call_tago(
        "TrainInfo",
        "GetCtyAcctoTrainSttnList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        cityCode=city_code,
    )


def get_train_vehicle_types(page_no=1, num_of_rows=10):
    """4. 차량종류 목록 조회"""
    return _call_tago(
        "TrainInfo",
        "GetVhcleKndList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


# ============================================================
# 6. 고속버스 정보 - ExpBusInfo (4개)
# ============================================================

def get_express_bus(dep_terminal_id, arr_terminal_id, dep_date,
                    page_no=1, num_of_rows=10):
    """1. 출/도착지 기반 고속버스정보 조회"""
    return _call_tago(
        "ExpBusInfo",
        "GetStrtpntAlocFndExpbusInfo",
        pageNo=page_no,
        numOfRows=num_of_rows,
        depTerminalId=dep_terminal_id,
        arrTerminalId=arr_terminal_id,
        depPlandTime=dep_date,
    )


def get_express_bus_terminal_list(terminal_nm=None, city_code=None,
                                  page_no=1, num_of_rows=10):
    """2. 고속버스터미널 목록 조회"""
    return _call_tago(
        "ExpBusInfo",
        "GetExpBusTrminlList",
        pageNo=page_no,
        numOfRows=num_of_rows,
        terminalNm=terminal_nm,
        cityCode=city_code,
    )


def get_express_bus_grades(page_no=1, num_of_rows=10):
    """3. 고속버스등급 목록 조회"""
    return _call_tago(
        "ExpBusInfo",
        "GetExpBusGradList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


def get_express_bus_city_codes(page_no=1, num_of_rows=10):
    """4. 도시코드 목록 조회"""
    return _call_tago(
        "ExpBusInfo",
        "GetCtyCodeList",
        pageNo=page_no,
        numOfRows=num_of_rows,
    )


# ============================================================
# 7. 공항 코드 - B551178/airport-code (1개)
# ============================================================

def get_airport_codes():
    """공항 코드 정보 조회"""
    url = "https://apis.data.go.kr/B551178/airport-code/info"

    params = {
        "serviceKey": SERVICE_KEY,
        "type": "json",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    return response.json()


# ============================================================
# 8. 국내 항공 운항 - DmstcFlightNvgInfo (3개)
# ============================================================

def get_domestic_flight_operation_list(**params):
    """1. 항공운항정보 목록 조회"""
    return _call_tago(
        "DmstcFlightNvgInfo",
        "GetFlightOpratInfoList",
        **params,
    )


def get_domestic_airport_list(**params):
    """2. 공항 목록 조회"""
    return _call_tago(
        "DmstcFlightNvgInfo",
        "GetArprtList",
        **params,
    )


def get_airline_list(**params):
    """3. 항공사 목록 조회"""
    return _call_tago(
        "DmstcFlightNvgInfo",
        "GetAirmanList",
        **params,
    )


# ============================================================
# 9. 실시간 항공기 운항 - B551178/flight-status (5개)
# ============================================================

def get_flight_arrival(**params):
    """1. 보험사용 항공편 지연·결항 결과 조회"""
    return _call_b551178("flight-status", "arrival", **params)


def get_flight_depart(**params):
    """2. 보험사용 항공편 지연·결항 출발 운항편 조회"""
    return _call_b551178("flight-status", "depart", **params)


def get_flight_taxfree(**params):
    """3. 면세점용 여객기 실시간 운항조회"""
    return _call_b551178("flight-status", "taxfree", **params)


def get_flight_status_info(**params):
    """4. 실시간 운항정보"""
    return _call_b551178("flight-status", "info", **params)


def get_flight_status_detail(**params):
    """5. 실시간 항공운항 현황 상세조회"""
    return _call_b551178("flight-status", "detail", **params)


# ============================================================
# 10. 항공기 운항 스케줄 - B551178/flight-schedule (4개)
# ============================================================

def get_flight_schedule_int(**params):
    """1. 국제선 운항 스케줄"""
    return _call_b551178("flight-schedule", "int", **params)


def get_flight_schedule_taxfree_int(**params):
    """2. 면세점용 여객기 국제선 운항 항공기 스케줄"""
    return _call_b551178("flight-schedule", "taxfree-int", **params)


def get_flight_schedule_taxfree_dom(**params):
    """3. 국내선 항공기 스케줄(면세점용)"""
    return _call_b551178("flight-schedule", "taxfree-dom", **params)


def get_flight_schedule_dom(**params):
    """4. 국내선/국제선 운항스케줄"""
    return _call_b551178("flight-schedule", "dom", **params)


def _call_b551178(service, operation, **params):
    """
    B551178 계열 API 공통 호출.
    실제 상세기능별 Request Parameter가 서로 다르므로
    명세의 파라미터명을 그대로 **params로 전달합니다.
    """
    url = f"https://apis.data.go.kr/B551178/{service}/{operation}"

    request_params = {
        "serviceKey": SERVICE_KEY,
        "type": "json",
    }

    request_params.update({
        key: value
        for key, value in params.items()
        if value is not None
    })

    response = requests.get(url, params=request_params, timeout=10)
    response.raise_for_status()

    return response.json()