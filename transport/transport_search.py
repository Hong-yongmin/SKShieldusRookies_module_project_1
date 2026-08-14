# 정규화된 교통 데이터를 조건에 따라 검색

def search_transport(
    results,
    departure=None,
    arrival=None,
    option="fast",
    time_after=None,
    time_before=None
):
    """
    교통 통합 검색 함수

    option:
        fast     = 빠른 교통편
        cheap    = 저렴한 교통편
        comfort  = 편한 교통편
        transfer = 환승 적은 교통편
        time     = 원하는 시간대
    """

    filtered = results

    # ============================================================
    # 1. 출발지 필터
    # ============================================================

    if departure:
        filtered = [
            item for item in filtered
            if departure in item.get("departure", "")
        ]

    # ============================================================
    # 2. 도착지 필터
    # ============================================================

    if arrival:
        filtered = [
            item for item in filtered
            if arrival in item.get("arrival", "")
        ]

    # ============================================================
    # 3. 원하는 시간대 필터
    # ============================================================

    if time_after:
        filtered = [
            item for item in filtered
            if item.get("departure_time")
            and item["departure_time"] >= time_after
        ]

    if time_before:
        filtered = [
            item for item in filtered
            if item.get("departure_time")
            and item["departure_time"] <= time_before
        ]

    # ============================================================
    # 4. 빠른 교통편
    # ============================================================

    if option == "fast":

        filtered = [
            item for item in filtered
            if item.get("duration") is not None
        ]

        return sorted(
            filtered,
            key=lambda x: x["duration"]
        )

    # ============================================================
    # 5. 저렴한 교통편
    # ============================================================

    elif option == "cheap":

        filtered = [
            item for item in filtered
            if item.get("price") is not None
        ]

        return sorted(
            filtered,
            key=lambda x: x["price"]
        )

    # ============================================================
    # 6. 편한 교통편
    # ============================================================

    elif option == "comfort":

        return sorted(
            filtered,
            key=lambda x: (
                x.get("transfers", 999),
                x.get("duration", 999999)
            )
        )

    # ============================================================
    # 7. 환승 적은 교통편
    # ============================================================

    elif option == "transfer":

        return sorted(
            filtered,
            key=lambda x: x.get("transfers", 999)
        )

    # ============================================================
    # 8. 원하는 시간대
    # ============================================================

    elif option == "time":

        return sorted(
            filtered,
            key=lambda x: x.get("departure_time", "99:99")
        )

    # ============================================================
    # 잘못된 option
    # ============================================================

    else:

        raise ValueError(
            "option은 fast, cheap, comfort, transfer, time 중 하나여야 합니다."
        )