from urllib.parse import quote

import httpx

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


async def geocode(place_name: str, city: str, api_key: str) -> dict | None:
    if not api_key:
        return None

    address = f"{place_name} {city}".strip()
    url = f"{GEOCODING_URL}?address={quote(address)}&key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            r.raise_for_status()
            data: dict = r.json()
    except Exception:
        return None

    results: list = data.get("results", [])
    if not results:
        return None

    location: dict = results[0].get("geometry", {}).get("location", {})
    lat: float | None = location.get("lat")
    lng: float | None = location.get("lng")

    if lat is None or lng is None:
        return None

    return {"lat": lat, "lng": lng}
