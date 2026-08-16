from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import json
import os
import random
import re
from urllib.parse import unquote

from duckduckgo_search import DDGS
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
import requests

# ============================================================
# 1. 환경 변수 및 클라이언트 초기화
# ============================================================
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv()
# 관광공사 API 키
TOUR_API_KEY = os.getenv("TOUR_GW_API_KEY") or os.getenv("TOUR_API_KEY")
if TOUR_API_KEY:
    TOUR_API_KEY = unquote(TOUR_API_KEY)

# OpenAI API 클라이언트
load_dotenv()
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"

# 시/도 및 주요 시/군/구 코드 확장 매핑
REGION = {
    "서울": {"areaCode": "1", "sigunguCode": None},
    "인천": {"areaCode": "2", "sigunguCode": None},
    "대전": {"areaCode": "3", "sigunguCode": None},
    "대구": {"areaCode": "4", "sigunguCode": None},
    "광주": {"areaCode": "5", "sigunguCode": None},
    "부산": {"areaCode": "6", "sigunguCode": None},
    "울산": {"areaCode": "7", "sigunguCode": None},
    "세종": {"areaCode": "8", "sigunguCode": None},
    "경기": {"areaCode": "31", "sigunguCode": None},
    "강원": {"areaCode": "32", "sigunguCode": None},
    "강릉": {"areaCode": "32", "sigunguCode": "1"},
    "속초": {"areaCode": "32", "sigunguCode": "5"},
    "충북": {"areaCode": "33", "sigunguCode": None},
    "충남": {"areaCode": "34", "sigunguCode": None},
    "공주": {"areaCode": "34", "sigunguCode": "1"},
    "부여": {"areaCode": "34", "sigunguCode": "7"},
    "경북": {"areaCode": "35", "sigunguCode": None},
    "경주": {"areaCode": "35", "sigunguCode": "2"},
    "안동": {"areaCode": "35", "sigunguCode": "5"},
    "경남": {"areaCode": "36", "sigunguCode": None},
    "전북": {"areaCode": "37", "sigunguCode": None},
    "전주": {"areaCode": "37", "sigunguCode": "12"},
    "전남": {"areaCode": "38", "sigunguCode": None},
    "제주": {"areaCode": "39", "sigunguCode": None}
}

NORMALIZE = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종시": "세종", "세종특별자치시": "세종",
    "경기도": "경기", "강원도": "강원", "강원특별자치도": "강원",
    "충청북도": "충북", "충청남도": "충남", "전라북도": "전북",
    "전북특별자치도": "전북", "전라남도": "전남", "경상북도": "경북",
    "경상남도": "경남", "제주도": "제주",
    "경주시": "경주", "부여군": "부여", "강릉시": "강릉", "속초시": "속초",
    "공주시": "공주", "안동시": "안동", "전주시": "전주"
}

# ============================================================
# 2. 공공 API 수집 & 데이터 처리 함수
# ============================================================
def normalize_region(region):
    region = str(region).strip()
    if region in REGION:
        return region
    if region in NORMALIZE:
        return NORMALIZE[region]
    
    for suffix in ["특별시", "광역시", "특별자치도", "특별자치시", "시", "군", "도"]:
        if region.endswith(suffix):
            base = region[:-len(suffix)]
            if base in REGION:
                return base
                
    return None


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
    if not isinstance(body, dict):
        return "기타"
        
    items = body.get("items", {}).get("item", []) if body else []
    if isinstance(items, dict):
        items = [items]
        
    for item in items:
        if str(item.get("code", "")).strip() == code and item.get("name"):
            return str(item["name"]).strip()
            
    return "기타"


@lru_cache(maxsize=256)
def get_detail_intro(contentid, contenttypeid):
    body = call_api("detailIntro2", {
        "pageNo": 1,
        "numOfRows": 1,
        "contentId": str(contentid),
        "contentTypeId": str(contenttypeid)
    })
    
    if not isinstance(body, dict):
        return {"opening_hours": "정보 없음", "food_type": "정보 없음"}

    items = body.get("items", {}).get("item", []) if body else []
    if isinstance(items, dict):
        items = [items]
        
    if not items:
        return {"opening_hours": "정보 없음", "food_type": "정보 없음"}
    
    item = items[0]
    
    def clean_html(text):
        if not text:
            return ""
        text = re.sub(r'(?i)<br\s*/?>', ' / ', str(text))
        text = re.sub(r'<[^>]*>', '', text)
        return text.strip()

    ctype = str(contenttypeid)
    
    if ctype == "12":
        opening_hours = clean_html(item.get("usetime"))
    elif ctype == "14":
        opening_hours = clean_html(item.get("usetimeculture"))
    elif ctype == "15":
        opening_hours = clean_html(item.get("usetimefestival"))
    elif ctype == "28":
        opening_hours = clean_html(item.get("usetimeleisure"))
    elif ctype == "32":
        opening_hours = clean_html(item.get("infocenterlodging"))
    elif ctype == "38":
        opening_hours = clean_html(item.get("usetimeshopping"))
    elif ctype == "39":
        opening_hours = clean_html(item.get("opentimefood"))
    else:
        opening_hours = clean_html(item.get("usetime"))

    if not opening_hours:
        opening_hours = clean_html(item.get("usetime")) or "정보 없음"

    if ctype == "39":
        menu_text = clean_html(item.get("treatmenu")) or clean_html(item.get("firstmenu"))
        food_type = menu_text if menu_text else "정보 없음"
    else:
        food_type = "해당 없음"
        
    return {
        "opening_hours": opening_hours,
        "food_type": food_type
    }


@lru_cache(maxsize=128)
def get_places(region, content_type):
    result = []
    region_info = REGION.get(region)
    if not region_info:
        return pd.DataFrame()
    
    params = {
        "pageNo": 1,
        "numOfRows": 100,
        "contentTypeId": content_type,
        "areaCode": region_info["areaCode"],
        "arrange": "C"
    }
    
    if region_info.get("sigunguCode"):
        params["sigunguCode"] = region_info["sigunguCode"]
    
    body = call_api("areaBasedList2", params)
    if not isinstance(body, dict):
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
                "contenttypeid": content_type,
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
def get_description_template(region, category, is_food=False):
    if is_food:
        templates = [
            f"{region} 현지 분위기를 온전히 느낄 수 있는 추천 {category} 맛집/카페입니다.",
            f"입맛을 사로잡는 매력적인 {region}의 인기 {category} 전문점입니다.",
            f"현지인들도 즐겨 찾는 분위기 좋은 {region} {category} 공간입니다.",
            f"특유의 맛과 즐거움이 가득한 {region} 지역의 {category}입니다.",
            f"식도락 여행에서 빼놓을 수 없는 {region}의 매력적인 {category} 맛집입니다.",
            f"든든하고 맛있는 한 끼를 즐기기 좋은 {region}의 {category} 장소입니다.",
            f"신선한 재료와 뛰어난 맛으로 입소문 난 {region}의 대표 {category}입니다.",
            f"여행의 피로를 사르르 녹여줄 {region} 감성 가득한 {category} 맛집이에요.",
            f"오감만족 미식 여행을 완성해 줄 {region}의 소문난 {category}입니다.",
            f"남녀노소 누구나 맛있게 즐길 수 있는 {region} 지역의 {category} 명소입니다.",
            f"특색 있는 메뉴로 발길이 끊이지 않는 {region}의 핫플 {category}입니다.",
            f"한 번 맛보면 잊을 수 없는 여운을 주는 {region}의 {category} 전문점입니다."
        ]
    else:
        templates = [
            f"{region}에서 즐기기 좋은 대표적인 {category} 명소입니다.",
            f"아름다운 풍경과 볼거리가 가득한 {region}의 인기 {category}입니다.",
            f"특별한 추억을 남기기 좋은 {region} 지역의 {category}입니다.",
            f"여행 중 꼭 한번 들러볼 만한 매력적인 {region}의 {category}입니다.",
            f"발길이 머무는 곳마다 감동을 주는 {region}의 매력 만점 {category}입니다.",
            f"다채로운 매력을 뽐내는 {region}의 필수 방문 {category} 코스입니다.",
            f"탁 트인 전경과 이색적인 즐거움이 있는 {region}의 {category} 스팟입니다.",
            f"사진을 남기기 좋고 둘러보는 재미가 쏠쏠한 {region}의 {category}입니다.",
            f"역사와 문화, 자연의 조화가 아름다운 {region}의 대표 {category}입니다.",
            f"일상에서 벗어나 힐링하기 딱 좋은 {region}의 힐링 {category} 명소예요.",
            f"방문객들에게 언제나 큰 사랑을 받는 {region}의 베스트 {category}입니다.",
            f"숨은 포토존과 볼거리가 가득한 {region}의 매력적인 {category} 공간입니다."
        ]
    return random.choice(templates)


def recommend_places(region, theme, age="20대", group="1명", sex="남성"):
    normalized_region = normalize_region(region)
    if not normalized_region:
        return {"error": f"'{region}'은(는) 지원하지 않는 지역명입니다."}

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
            except Exception as e:
                print(f"[디버그] API 수집 중 예외 발생 (contentType: {typ}): {e}")
            
    tour_df = pd.DataFrame()
    if tour_data_list:
        raw_tour = pd.concat(tour_data_list, ignore_index=True).drop_duplicates(["name", "address"])
        tour_df = select_diverse(raw_tour, 3)

    for df, default_type in [(tour_df, "12"), (food_df, "39")]:
        if not df.empty:
            hours_list = []
            food_types_list = []
            for _, r in df.iterrows():
                ctype = r.get("contenttypeid", default_type)
                detail = get_detail_intro(r["contentid"], ctype)
                hours_list.append(detail["opening_hours"])
                food_types_list.append(detail.get("food_type", "해당 없음"))
            df["opening_hours"] = hours_list
            if default_type == "39":
                df["food_type"] = food_types_list

    if not tour_df.empty:
        tour_df["description"] = tour_df.apply(
            lambda r: get_description_template(normalized_region, r['category']), axis=1
        )
    if not food_df.empty:
        food_df["description"] = food_df.apply(
            lambda r: get_description_template(normalized_region, r['category'], is_food=True), axis=1
        )

    if tour_df.empty and food_df.empty:
        return {"error": f"'{region}' 지역에 등록된 공공 API 데이터가 없습니다."}

    # 🔹 첫 번째 코드와 동일하게 JSON 문자열 반환 (인터페이스 호환 유지)
    return {
        "region": normalized_region,
        "tourist_attractions": tour_df[["name", "category", "address", "mapx", "mapy", "description", "opening_hours"]].to_dict(orient="records") if not tour_df.empty else [],
        "restaurants": food_df[["name", "category", "address", "mapx", "mapy", "description", "opening_hours", "food_type"]].to_dict(orient="records") if not food_df.empty else []
    }


def web_search(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            if not results:
                return json.dumps({"query": query, "result": "검색 결과가 없습니다."}, ensure_ascii=False)
            
            search_summaries = []
            for r in results:
                title = r.get("title", "")
                body = r.get("body", "")
                search_summaries.append(f"- 제목: {title}\n  내용: {body}")
            
            return json.dumps({
                "query": query,
                "result": "\n".join(search_summaries)
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"query": query, "result": f"웹 검색 중 오류 발생: {str(e)}"}, ensure_ascii=False)


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_places",
            "description": "지역, 여행 테마, 연령대, 인원수를 기반으로 관광지 3곳과 음식점 3곳을 각각 추천합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "description": "여행 지역 (예: 서울, 경주, 부여, 제주 등)"},
                    "theme": {"type": "string", "description": "여행 테마 (예: 식도락, 쇼핑, 자연경관 등)"},
                    "age": {"type": "string", "description": "연령대"},
                    "group": {"type": "string", "description": "인원수"},
                    "sex": {"type": "string", "description": "성별"}
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

정상적인 데이터를 확보하면 아래 서식 양식(마크다운)을 엄격하게 지켜서 답변을 출력하세요.
### 📌 [지역명] 추천 여행 코스
### 🏰 추천 관광지 (3곳)
1. **[장소명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🕒 운영시간: [opening_hours]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
2. **[장소명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🕒 운영시간: [opening_hours]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
3. **[장소명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🕒 운영시간: [opening_hours]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]

### 🍽️ 추천 맛집 (3곳)
1. **[식당/카페명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🕒 운영시간: [opening_hours]
   * 🍽️ 대표 메뉴: [food_type]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
2. **[식당/카페명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🕒 운영시간: [opening_hours]
   * 🍽️ 대표 메뉴: [food_type]
   * 🌐 좌표: 위도 [mapy], 경도 [mapx]
   * 💡 특징: [이곳을 추천하는 이유 및 description 활용]
3. **[식당/카페명]** ([카테고리명])
   * 📍 주소: [주소]
   * 🕒 운영시간: [opening_hours]
   * 🍽️ 대표 메뉴: [food_type]
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
            
            # 툴 응답을 OpenAI API 규격(문자열)에 맞게 안전하게 처리
            if isinstance(func_response, (dict, list)):
                func_response_str = json.dumps(func_response, ensure_ascii=False)
            else:
                func_response_str = str(func_response)
            
            full_messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": func_name,
                "content": func_response_str,
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
    print("    (종료하려면 'q' 또는 'exit'를 입력하세요)")
    print("=" * 60)
    
    welcome_msg = (
        "안녕하세요! ✈️ 어떤 한국 여행 정보를 찾으시나요?\n"
        "예를 들어 '경주 여행 코스 추천해줘' 나 '부여 맛집 알려줘' 처럼 자유롭게 질문해 보세요!"
    )
    
    print(f"\n🤖 AI 가이드:\n{welcome_msg}\n")
    print("-" * 60)

    messages_history = [
        {"role": "assistant", "content": welcome_msg}
    ]

    while True:
        try:
            user_input = input("\n👤 사용자: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n👋 프로그램을 종료합니다.")
            break
        
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