import asyncio

from app.agent.enrichment.geocoding import geocode
from app.agent.enrichment.weather import get_weather
from app.agent.state import TravelPlannerState


async def enrich(state: TravelPlannerState) -> dict:
    travel_plan: dict | None = state.get("travel_plan")
    steps: list[str] = list(state.get("intermediate_steps", []))
    maps_key: str = state.get("google_maps_key", "")
    weather_key: str = state.get("weather_api_key", "")

    if travel_plan is None or not travel_plan.get("days"):
        steps.append("enrichment: 无行程数据，跳过富化")
        return {"intermediate_steps": steps}

    if not maps_key and not weather_key:
        steps.append("enrichment: 未配置 API Key，跳过坐标补全和天气查询")
        return {"intermediate_steps": steps}

    days: list = list(travel_plan["days"])
    enriched_days = await _enrich_days(days, maps_key, weather_key, steps)

    steps.append("enrichment: 坐标和天气信息补全完成")
    return {
        "travel_plan": {**travel_plan, "days": enriched_days},
        "intermediate_steps": steps,
    }


async def _enrich_days(
    days: list, maps_key: str, weather_key: str, steps: list[str]
) -> list:
    geocode_tasks: list[tuple[int, int, str]] = []
    geocode_index: list[tuple[int, int]] = []

    for di, day in enumerate(days):
        for ai, act in enumerate(day.get("activities", [])):
            if act.get("lat") is None or act.get("lng") is None:
                address = f"{act.get('name', '')} {day.get('city', '')}"
                geocode_tasks.append((di, ai, address))
                geocode_index.append((di, ai))

    geocode_results: list = []
    if geocode_tasks and maps_key:
        steps.append(f"enrichment: 正在补全 {len(geocode_tasks)} 个地点的坐标...")
        geocode_results = await asyncio.gather(
            *(_geocode_one(addr, maps_key) for _, _, addr in geocode_tasks),
            return_exceptions=True,
        )
        geocode_failures = sum(1 for r in geocode_results if not isinstance(r, dict))
        if geocode_failures > 0:
            steps.append(f"enrichment: {geocode_failures}/{len(geocode_tasks)} 个地点坐标补全失败")

    enriched_activities: dict[int, dict[int, dict]] = {}
    for gi, (di, ai) in enumerate(geocode_index):
        if gi < len(geocode_results) and isinstance(geocode_results[gi], dict):
            enriched_activities.setdefault(di, {})[ai] = geocode_results[gi]

    weather_tasks: list[tuple[int, float, float]] = []
    weather_index: list[int] = []

    for di, day in enumerate(days):
        activities: list = day.get("activities", [])
        lat: float | None = None
        lng: float | None = None

        for ai, act in enumerate(activities):
            if ai in enriched_activities.get(di, {}):
                lat = enriched_activities[di][ai].get("lat")
                lng = enriched_activities[di][ai].get("lng")
                break
            if act.get("lat") is not None:
                lat = act.get("lat")
                lng = act.get("lng")
                break

        if lat is not None and lng is not None:
            weather_tasks.append((di, lat, lng))
            weather_index.append(di)

    weather_results: list = []
    if weather_tasks and weather_key:
        steps.append(f"enrichment: 正在查询 {len(weather_tasks)} 个城市的天气...")
        weather_results = await asyncio.gather(
            *(_weather_one(lat, lng, weather_key) for _, lat, lng in weather_tasks),
            return_exceptions=True,
        )
        weather_failures = sum(1 for r in weather_results if not isinstance(r, dict))
        if weather_failures > 0:
            steps.append(f"enrichment: {weather_failures}/{len(weather_tasks)} 个城市天气查询失败")

    enriched_days: list = []
    for di, day in enumerate(days):
        day_copy: dict = dict(day)
        new_activities: list = []
        for ai, act in enumerate(day.get("activities", [])):
            act_copy: dict = dict(act)
            if ai in enriched_activities.get(di, {}):
                act_copy.update(enriched_activities[di][ai])
            new_activities.append(act_copy)

        day_copy["activities"] = new_activities

        for wi, wdi in enumerate(weather_index):
            if wdi == di and wi < len(weather_results):
                result = weather_results[wi]
                if isinstance(result, dict):
                    day_copy["weather"] = result
                break

        enriched_days.append(day_copy)

    return enriched_days


async def _geocode_one(address: str, key: str) -> dict | None:
    return await geocode(address, "", key)


async def _weather_one(lat: float, lng: float, key: str) -> dict | None:
    return await get_weather(lat, lng, key)
