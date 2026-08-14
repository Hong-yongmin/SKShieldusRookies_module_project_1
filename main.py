from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import json
import os
from urllib.parse import unquote

from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import requests

# ============================================================
# 1. 환경 변수 및 클라이언트 초기화
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, "APIKEY.env"))

# 관광공사 API 키
TOUR_API_KEY = os.getenv("TOUR_GW_API_KEY") or os.getenv("TOUR_API_KEY")
if TOUR_API_KEY:
    TOUR_API_KEY = unquote(TOUR_API_KEY)

# OpenAI API 클라이언트
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"

REGION = {
    "서울": "1", "인천": "2", "대전": "3", "대구": "4", "광주": "5",
    "부산": "6", "울산": "7", "세종": "8", "경기": "31", "강원": "32",
    "충북": "33", "충남": "34", "경북": "35", "경남": "36",
    "전북": "37", "전남": "38", "제주": "39"
}

NORMALIZE = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종시": "세종", "세종특별자치시": "세종",
    "경기도": "경기", "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남", "전라북도": "전북",
    "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
    "경상남도": "경남", "제주도": "제주"
}

# ============================================================
# 2. 공공 API 수집 & 데이터 처리 함수
# ============================================================
def normalize_region(region):
    region = str(region).strip()
    return NORMALIZE.get(region, region if region in REGION else None)


def call_api(endpoint, params):
    if not TOUR_API_KEY:
        return None
    params.update({
        "serviceKey": TOUR_API_KEY,
        "MobileOS": "ETC",
        "MobileApp": "SmartTourProject",
        "_type": "json"
    })
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json().get("response", {})
        if data.get("header", {}).get("resultCode") not in (None, "0000"):
            return None
        return data.get("body", {})
    except Exception:
        return None


@lru_cache(maxsize=128)
def get_category(code):
    code = str(code or "").strip()
    if not code:
        return "일반관광"
    
    body = call_api("categoryCode2", {"pageNo": 1, "numOfRows": 50, "cat1": code[:3], "cat2": code[:5]})
    items = body.get("items", {}).get("item", []) if body else []
    if isinstance(items, dict):
        items = [items]
        
    for item in items:
        if str(item.get("code", "")).strip() == code and item.get("name"):
            return str(item["name"]).strip()
            
    return "기타"


@lru_cache(maxsize=128)
def get_places(region, content_type):
    result = []
    area = REGION.get(region)
    if not area:
        return pd.DataFrame()
    
    body = call_api("areaBasedList2", {"pageNo": 1, "numOfRows": 100, "contentTypeId": content_type, "areaCode": area, "arrange": "C"})
    if not body:
        return pd.DataFrame()
        
    items = body.get("items", {}).get("item", [])
    if isinstance(items, dict):
        items = [items]
        
    for x in items:
        name = str(x.get("title", "")).strip()
        if name:
            raw_mapx = str(x.get("mapx", "")).strip()
            raw_mapy = str(x.get("mapy", "")).strip()
            
            try:
                mapx_clean = f"{float(raw_mapx):.4f}" if raw_mapx else ""
            except ValueError:
                mapx_clean = raw_mapx

            try:
                mapy_clean = f"{float(raw_mapy):.4f}" if raw_mapy else ""
            except ValueError:
                mapy_clean = raw_mapy

            result.append({
                "name": name,
                "address": str(x.get("addr1", "")).strip(),
                "cat3": str(x.get("cat3", "")).strip(),
                "contentid": str(x.get("contentid", "")).strip(),
                "mapx": mapx_clean,
                "mapy": mapy_clean
            })
            
    if not result:
        return pd.DataFrame()
    return pd.DataFrame(result).drop_duplicates(["name", "address"]).reset_index(drop=True)


def select_diverse(df, count=3):
    if df.empty:
        return df
    
    df_shuffled = df.sample(frac=1).reset_index(drop=True)
    result, categories, names = [], set(), set()
    
    for _, row in df_shuffled.iterrows():
        if row["name"] in names:
            continue
        cat_code = row.get("cat3", "")
        if cat_code not in categories:
            result.append(row)
            categories.add(cat_code)
            names.add(row["name"])
        if len(result) >= count:
            break
            
    if len(result) < count:
        for _, row in df_shuffled.iterrows():
            if row["name"] not in names:
                result.append(row)
                names.add(row["name"])
            if len(result) >= count:
                break
                
    res_df = pd.DataFrame(result)
    
    if not res_df.empty:
        res_df["category"] = res_df["cat3"].apply(get_category)
        
    return res_df

# ============================================================
# 3. OpenAI Function Calling (커스텀 툴 및 호출)
# ============================================================
def recommend_places(region, theme, age="20대", group="1명", sex="남성"):
    normalized_region = normalize_region(region)
    if not normalized_region:
        return json.dumps({"error": f"'{region}'은(는) 지원하지 않는 지역명입니다."})

    all_types = ["12", "14", "15", "28", "32", "38", "39"]
    tour_data_list = []
    food_df = pd.DataFrame()

    with ThreadPoolExecutor(max_workers=7) as executor:
        future_to_type = {
            executor.submit(get_places, normalized_region, typ): typ for typ in all_types
        }
        for future in as_completed(future_to_type):
            typ = future_to_type[future]
            try:
                data = future.result()
                if not data.empty:
                    if typ == "39":
                        food_df = select_diverse(data, 3)
                    else:
                        tour_data_list.append(data)
            except Exception:
                pass
            
    tour_df = pd.DataFrame()
    if tour_data_list:
        raw_tour = pd.concat(tour_data_list, ignore_index=True).drop_duplicates(["name", "address"])
        tour_df = select_diverse(raw_tour, 3)

    # 🔹 [요청사항 반영] JSON 반환 결과에 description 필드 생성
    if not tour_df.empty:
        tour_df["description"] = tour_df.apply(
            lambda r: f"{normalized_region}에서 즐기기 좋은 대표적인 {r['category']} 명소입니다.", axis=1
        )
    if not food_df.empty:
        food_df["description"] = food_df.apply(
            lambda r: f"{normalized_region} 현지 분위기를 느낄 수 있는 추천 {r['category']} 맛집/카페입니다.", axis=1
        )

    return json.dumps({
        "region": normalized_region,
        "tourist_attractions": tour_df[["name", "category", "address", "mapx", "mapy", "description"]].to_dict(orient="records") if not tour_df.empty else [],
        "restaurants": food_df[["name", "category", "address", "mapx", "mapy", "description"]].to_dict(orient="records") if not food_df.empty else []
    }, ensure_ascii=False)


def web_search(query):
    return json.dumps({
        "query": query,
        "result": f"'{query}'에 대한 웹 검색 완료: 이용 전 운영시간 및 예약 여부 재확인을 권장합니다."
    }, ensure_ascii=False)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_places",
            "description": "지역, 여행 테마, 연령대, 인원수를 기반으로 관광지 3곳과 음식점 3곳을 각각 추천합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "여행 지역 (예: 서울, 세종, 부산, 경남 등)"},
                    "theme": {"type": "string", "description": "여행 테마 (예: 식도락, 쇼핑, 자연경관, K-POP, 휴양, 역사 등)"},
                    "age": {"type": "string", "description": "연령대 (예: 20대, 30대 등)"},
                    "group": {"type": "string", "description": "여행 인원수 (예: 1명, 2명, 3명 이상)"},
                    "sex": {"type": "string", "description": "성별 (예: 남성, 여성)"}
                },
                "required": ["region", "theme"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "관광지나 음식점의 최신 웹 정보를 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 키워드"}
                },
                "required": ["query"]
            }
        }
    }
]

AVAILABLE_FUNCTIONS = {
    "recommend_places": recommend_places,
    "web_search": web_search
}


def ask_ai(messages_history):
    if not client:
        return "⚠️ OpenAI API 키가 설정되지 않았습니다. APIKEY.env 파일을 확인해주세요."

    system_instruction = """당신은 전문 한국 관광/맛집 AI 가이드입니다.
사용자의 요청에서 여행 지역이나 테마가 확인되면 반드시 'recommend_places' 툴을 호출하세요.
툴 호출 결과를 받으면 정확히 아래 서식 양식(마크다운)을 지켜서 답변을 출력하세요.

### 📌 [지역명] 추천 여행 코스

### 🏰 추천 관광지 (3곳)

1. **[장소명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
2. **[장소명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
3. **[장소명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]

### 🍽️ 추천 맛집 (3곳)

1. **[식당/카페명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
2. **[식당/카페명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
3. **[식당/카페명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]

* 출력 규칙:
1. 좌표(mapy, mapx)는 전달받은 데이터 텍스트 그대로(소수점 4자리) 사용하세요.
2. 각 번호(1, 2, 3) 바로 아래 세부 정보는 반드시 공백 3칸 후 '* '를 입력하여 하위 불릿 리스트로 생성하세요.
3. 관광지와 맛집을 절대 섞지 말고 각각 1, 2, 3번으로 정렬하세요.
4. 전화번호나 연락처 항목은 절대로 포함하지 마세요.
"""

    system_msg = {"role": "system", "content": system_instruction}
    full_messages = [system_msg] + messages_history

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=full_messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        full_messages.append(response_message)
        for tool_call in tool_calls:
            func_name = tool_call.function.name
            func_to_call = AVAILABLE_FUNCTIONS[func_name]
            func_args = json.loads(tool_call.function.arguments)
            func_response = func_to_call(**func_args)
            
            full_messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": func_response,
            })
            
        second_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=full_messages
        )
        return second_response.choices[0].message.content
    else:
        return response_message.content

# ============================================================
# 4. 직접 실행 (CLI 터미널 대화용)
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 AI 스마트 한국 여행 플래너 (터미널 단독 실행 모드)")
    print("   (종료하려면 'q' 또는 'exit'를 입력하세요)")
    print("=" * 60)

    # 1. 초기 매뉴얼 안내 문구 설정
    welcome_msg = "안녕하세요! ✈️ 어떤 한국 여행 정보를 찾으시나요?\n예를 들어 '여자 2명이서 부여 백제 유적 구경하고, 그 지역의 맛있는 한식을 먹고 싶어' 와 같이 자유롭게 질문해 보세요!"
    
    # 2. 터미널에 초기 매뉴얼 먼저 출력
    print(f"\n🤖 AI 가이드:\n{welcome_msg}\n")
    print("-" * 60)

    # 3. 초기 대화 기록에 매뉴얼 등록 (AI 맥락 유지용)
    messages_history = [
        {"role": "assistant", "content": welcome_msg}
    ]

    # 4. 대화 루프 시작
    while True:
        user_input = input("\n👤 사용자: ").strip()
        
        if user_input.lower() in ["q", "exit", "quit", "종료"]:
            print("\n👋 프로그램을 종료합니다.")
            break

        if not user_input:
            continue

        messages_history.append({"role": "user", "content": user_input})

        print("\n🔄 API 데이터 수집 및 AI 답변 생성 중...")
        ai_reply = ask_ai(messages_history)

        print("\n" + "=" * 60)
        print(ai_reply)
        print("=" * 60)

        messages_history.append({"role": "assistant", "content": ai_reply})