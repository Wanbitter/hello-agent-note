from datetime import datetime
import httpx
from urllib.parse import quote



def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def get_my_location():
    try:
        r = httpx.get("http://ip-api.com/json",timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        return f"错误，定位服务调用失败，检查是否打开定位服务{type(e).__name__}"

    city = data.get("city")
    if not city:
        return "错误：定位不到你的城市。请让用户直接告诉你城市名，不要猜。"


    return city

def get_weather(city: str = "") -> str:
    """查实时天气。返回【一句人话】，不返回原始 JSON。"""
    if not city:
        city = get_my_location()
    try:
        r = httpx.get(
            f"https://wttr.in/{quote(city)}",     # ★ ① 中文要 quote，否则 URL 非法
            params={"format": "j1", "lang": "zh"},
            timeout=10,                            # ★ ② 一定要超时
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        # ★ ③ 所有异常都转成文本（拉萨那一课的延续）
        return f"错误：天气服务调用失败（{type(e).__name__}）。请告诉用户稍后再试，不要重复调用。"

    cur = (data.get("current_condition") or [None])[0]
    if not cur:
        # ★ ④ 取字段【之前】先确认结构存在
        return f"错误：查不到『{city}』的天气。请直接告诉用户查不到，不要重试。"

    # 注意：lang_zh 返回的其实是英文，所以直接用 weatherDesc
    desc_list = cur.get("weatherDesc") or [{}]
    desc = desc_list[0].get("value", "未知")

    # ★ ⑤ 只返回一句人话 —— 绝不 str(data)
    return (
        f"{city}当前：{desc}，气温 {cur.get('temp_C')}℃，"
        f"体感 {cur.get('FeelsLikeC')}℃，湿度 {cur.get('humidity')}%，"
        f"风速 {cur.get('windspeedKmph')}km/h"
    )


REGISTRY = {
    "get_current_time": get_current_time,
    "get_weather" : get_weather,
    "get_my_location" : get_my_location,
}
# # 一个工具的参数参数
# {
#     "type": "function",#类型：function 固定写法
#     "function": { #作为function的参数
#         "name": "get_current_time", #写的是工具的名字 固定写法
#         "description": "获取当天的日期和时间，用户询问现在几点，今天几号时必须调用它。",# 对工具的描述
#         "parameters": {"type": "object", "properties": {}}   #<-这里就是参数啊这一行都是参数
#         # "required": ["keyword"],  上面那个{}是空的表示没有必填参数，这一行就是必填参数
#
#
#
#     },
# }

# "properties": {
#     "city": {"type": "string", "description": "城市"},
#     "date": {"type": "string", "description": "日期，例如 2026-09-22"},
# },
# "required": ["city", "date"],        # ← 两个都是必填



SCHEMAS = [
    {
        "type" : "function",
        "function" : {
            "name" : "get_current_time",
            "description" : "获取当天的日期和时间，用户询问现在几点，今天几号时必须调用它。",
            "parameters" : {"type" : "object", "properties" : {}},
        },
    },
    {
        "type" : "function",
        "function" : {
            "name" : "get_weather",
            "description" : "获取指定城市的实时天气。用户询问某地天气、气温、是否下雨时必须调用它。只能查实时天气，查不了未来几天。",
            "parameters" : {
                "type": "object",
                "properties" : {"city" : {"type" : "string","description" : "城市名，例如：北京，上海"}
                },
            },

        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_location",
            "description": "获取用户的地理地址的时候必须调用",
            "parameters": {
                "type": "object",
                "properties": {},
            },

        }
    },
]
if __name__ == "__main__":
    print(get_weather("北京"))
