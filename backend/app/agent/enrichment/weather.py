import httpx

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


async def get_weather(lat: float, lng: float, api_key: str) -> dict | None:
    if not api_key:
        return None

    url = (
        f"{WEATHER_URL}?lat={lat}&lon={lng}&units=metric"
        f"&lang=zh_cn&appid={api_key}"
    )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            data: dict = r.json()
    except Exception:
        return None

    weather_list: list = data.get("weather", [])
    main: dict = data.get("main", {})

    return {
        "description": weather_list[0]["description"] if weather_list else "未知",
        "temp": round(main.get("temp", 0)),
        "temp_min": round(main.get("temp_min", 0)),
        "temp_max": round(main.get("temp_max", 0)),
        "humidity": main.get("humidity", 0),
    }
