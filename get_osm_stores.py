"""
Получает адреса и координаты магазинов Магнит через OpenStreetMap Overpass API.
Запуск: python get_osm_stores.py
Работает с вашего компьютера (Overpass доступен из России).
"""
import requests, json, sqlite3, time

DB_NAME = "magnit_data.db"

CITIES = {
    "Курганинск": (44.85, 40.55, 44.95, 40.65),
    "Невинномысск": (44.60, 41.90, 44.70, 42.05),
    "Армавир": (44.95, 41.10, 45.05, 41.25),
    "Ставрополь": (44.95, 41.85, 45.10, 42.05),
    "Михайловск": (45.08, 41.95, 45.15, 42.10),
    "Будённовск": (44.75, 44.10, 44.85, 44.25),
}

def fetch_stores(city, bbox):
    lat_min, lon_min, lat_max, lon_max = bbox
    query = f"""[out:json][timeout:20];
    (
      node["shop"="supermarket"]["name"~"Магнит"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["shop"="supermarket"]["name"~"Магнит"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out center;"""
    
    for server in ["https://overpass-api.de/api/interpreter", 
                   "https://overpass.kumi.systems/api/interpreter"]:
        try:
            r = requests.post(server, data={"data": query}, 
                            headers={"User-Agent": "MagnitBot/1.0"}, timeout=25)
            if r.status_code == 200:
                return r.json().get("elements", [])
        except:
            continue
    return []

conn = sqlite3.connect(DB_NAME)
total = 0

for city, bbox in CITIES.items():
    print(f"\n🔍 {city}...")
    elements = fetch_stores(city, bbox)
    count = 0
    for el in elements:
        tags = el.get("tags", {})
        lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
        lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
        street = tags.get("addr:street", "")
        house = tags.get("addr:housenumber", "")
        name = tags.get("name", "Магнит")
        
        if street and lat and lon:
            addr = f"{city}, {street}, д. {house}"
            code = f"osm_{city}_{count}"
            conn.execute("INSERT OR REPLACE INTO stores (code, address, city, lat, lon, added_at) VALUES (?,?,?,?,?,datetime('now'))",
                        (code, addr, city, lat, lon))
            count += 1
            print(f"  📍 {addr} ({lat:.4f}, {lon:.4f})")
    
    conn.commit()
    total += count
    print(f"  ✅ Найдено: {count}")
    time.sleep(2)

conn.close()
print(f"\n🎉 Итого добавлено: {total} магазинов с координатами!")
print("Перезапустите python app.py и откройте карту.")
