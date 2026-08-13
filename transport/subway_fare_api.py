# 지히철 출발역, 도착역 기준 요금 조회

import os
import requests
import xmltodict
from urllib.parse import unquote
from dotenv import load_dotenv

load_dotenv()

SERVICE_KEY = unquote(os.getenv("DATA_API_KEY", ""))

BASE_URL = "https://apis.data.go.kr/B553766/fare2/getRltmFare2"


def get_subway_fare(
    departure_code,
    departure_name,
    arrival_code,
    arrival_name
):
    """출발역과 도착역 사이의 지하철 운임 조회"""

    params = {
        "serviceKey": SERVICE_KEY,
        "depStnCd": departure_code,
        "depStnNm": departure_name,
        "arvlStnCd": arrival_code,
        "arvlStnNm": arrival_name,
        "type": "xml"
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=10
    )

    print("상태 코드:", response.status_code)

    response.raise_for_status()

    data = xmltodict.parse(response.text)

    items = data["response"]["body"]["items"].get("item", [])

    # 결과가 1개일 경우 리스트로 변환
    if isinstance(items, dict):
        items = [items]

    # 출발역 → 도착역에 해당하는 데이터 찾기
    for item in items:

        if (
            item.get("dptreStnNm") == departure_name
            and item.get("arvlStnNm") == arrival_name
        ):
            return item

    return None