"""
Получает магазины Магнит из OpenStreetMap с повторными попытками.
Запуск: python get_osm_stores.py
Если Overpass недоступен - использует Nominatim как fallback.
"""
import requests, json, sqlite3, time, urllib3
urllib3.disable_warnings()

DB_NAME = "magnit_data.db"

CITIES = {
    "Ставрополь": (44.95, 41.85, 45.10, 42.05),
    "Курганинск": (44.83, 40.53, 44.93, 40.63),
    "Невинномысск": (44.58, 41.88, 44.72, 42.08),
    "Армавир": (44.93, 41.05, 45.07, 41.20),
    "Михайловск": (45.06, 41.93, 45.16, 42.12),
    "Будённовск": (44.73, 44.08, 44.87, 44.27),
    "Краснодар": (44.95, 38.85, 45.10, 39.10),
}

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

def fetch_overpass(city, bbox, retries=3):
    lat_min, lon_min, lat_max, lon_max = bbox
    query = f'[out:json][timeout:30];(node["shop"="supermarket"]["name"~"Магнит"]({lat_min},{lon_min},{lat_max},{lon_max});way["shop"="supermarket"]["name"~"Магнит"]({lat_min},{lon_min},{lat_max},{lon_max}););out center;'
    
    for attempt in range(retries):
        for server in SERVERS:
            try:
                r = requests.post(server, data={"data": query},
                                headers={"User-Agent": "MagnitBot/1.0"}, timeout=35, verify=False)
                if r.status_code == 200:
                    elements = r.json().get("elements", [])
                    if elements:
                        return elements
                    print(f"  {server.split('/')[2]}: 0 results, trying next...")
                elif r.status_code == 429 or r.status_code == 502:
                    print(f"  {server.split('/')[2]}: overloaded, waiting...")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"  {server.split('/')[2]}: HTTP {r.status_code}")
            except Exception as e:
                print(f"  {server.split('/')[2]}: {type(e).__name__}")
        if attempt < retries - 1:
            wait = 10 * (attempt + 1)
            print(f"  Retry in {wait}s...")
            time.sleep(wait)
    return []

def fetch_nominatim(city):
    """Fallback: поиск через Nominatim"""
    stores = []
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params={
            "q": f"Магнит {city}", "format": "json", "limit": 50, "addressdetails": 1
        }, headers={"User-Agent": "MagnitBot/1.0"}, timeout=15, verify=False)
        if r.status_code == 200:
            for item in r.json():
                addr = item.get("address", {})
                road = addr.get("road", "")
                house = addr.get("house_number", "")
                lat, lon = float(item["lat"]), float(item["lon"])
                if road:
                    stores.append({"tags": {"addr:street": road, "addr:housenumber": house, "name": "Магнит"}, "lat": lat, "lon": lon})
    except:
        pass
    return stores

conn = sqlite3.connect(DB_NAME)
for col in ['lat', 'lon']:
    try: conn.execute(f"ALTER TABLE stores ADD COLUMN {col} REAL")
    except: pass

total = 0
for city, bbox in CITIES.items():
    print(f"\n🔍 {city}...")
    elements = fetch_overpass(city, bbox)
    
    if not elements:
        print("  Overpass недоступен, пробуем Nominatim...")
        elements = fetch_nominatim(city)
    
    count = 0
    for el in elements:
        tags = el.get("tags", {})
        lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
        lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
        street = tags.get("addr:street", "")
        house = tags.get("addr:housenumber", "")
        if lat and lon:
            addr = f"{city}, {street}, д. {house}" if street else f"{city}, Магнит"
            code = f"osm_{city}_{count}"
            conn.execute("INSERT OR REPLACE INTO stores (code, address, city, lat, lon, added_at) VALUES (?,?,?,?,?,datetime('now'))",
                        (code, addr, city, lat, lon))
            count += 1
            if count <= 3:
                print(f"  📍 {addr} ({lat:.4f}, {lon:.4f})")
    if count > 3:
        print(f"  ... и ещё {count-3}")
    conn.commit()
    total += count
    print(f"  ✅ Найдено: {count}")
    time.sleep(3)

conn.close()
print(f"\n🎉 Итого: {total} магазинов с координатами!")
if total == 0:
    print("\n⚠️ Overpass и Nominatim недоступны.")
    print("Используйте кнопку 📍 Геокодировать в интерфейсе приложения")
    print("или откройте 🗺️ Карта — она автоматически геокодирует адреса.")
else:
    print("Перезапустите python app.py → 🗺️ Карта")
