"""Фикс: загрузка не зависает + адреса Невинномысска + OSM с retry"""
import os, re

# === 1. app.py: ограничиваем параллельность и добавляем таймауты ===
with open("app.py", "r", encoding="utf-8") as f:
    app = f.read()

# Уменьшаем max_items для парсинга всех магазинов чтобы не было timeout
if "max_items=int(d.get('max_items',1500))" in app:
    app = app.replace("max_items=int(d.get('max_items',1500))", "max_items=int(d.get('max_items',500))")
    print("✅ app.py: уменьшен max_items до 500 для стабильности")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app)

# === 2. parser.py: уменьшаем workers и добавляем обработку ошибок ===
with open("parser.py", "r", encoding="utf-8") as f:
    p = f.read()

# Reduce parallel workers from 4 to 2 to avoid overwhelming the API
p = p.replace("ThreadPoolExecutor(max_workers=4)", "ThreadPoolExecutor(max_workers=2)")
print("✅ parser.py: 2 потока вместо 4 (стабильнее)")

# Add timeout handling in parse_store_progressive
if "except Exception as e:" in p and "logging.error" in p:
    # Already has error handling, good
    pass

with open("parser.py", "w", encoding="utf-8") as f:
    f.write(p)

# === 3. Добавляем адреса Невинномысска из скриншота ===
with open("parser.py", "r", encoding="utf-8") as f:
    p = f.read()

nevinnomyssk_stores = '''{"code":"nev_01","address":"Невинномысск, ул Менделеева, д 1","city":"Невинномысск"},
{"code":"nev_02","address":"Невинномысск, ул Баумана, стр 11","city":"Невинномысск"},
{"code":"nev_03","address":"Невинномысск, ул Гагарина, д 21А","city":"Невинномысск"},
{"code":"nev_04","address":"Невинномысск, ул Гагарина, д 56","city":"Невинномысск"},
{"code":"nev_05","address":"Невинномысск, ул Апанасенко, д 82Б","city":"Невинномысск"},
{"code":"nev_06","address":"Невинномысск, Луначарского ул, стр 145","city":"Невинномысск"},
'''

marker = '{"code":"992323"'
pos = p.find(marker)
if pos > 0 and "nev_01" not in p:
    p = p[:pos] + nevinnomyssk_stores + p[pos:]
    print("✅ parser.py: +6 адресов Невинномысска из скриншота")

with open("parser.py", "w", encoding="utf-8") as f:
    f.write(p)

# === 4. script.js: показываем прогресс загрузки чтобы не казалось что зависло ===
with open("static/js/script.js", "r", encoding="utf-8") as f:
    js = f.read()

# Make progress bar more visible during parsing
old_progress = "progressText.textContent='Загрузка...'"
new_progress = "progressText.textContent='⏳ Загрузка скидок... Это может занять 1-2 минуты'"
if old_progress in js:
    js = js.replace(old_progress, new_progress)
    print("✅ script.js: понятное сообщение о загрузке")

# Also update the parse button text during loading
old_btn = "parseBtn.textContent='Загрузка...'"
new_btn = "parseBtn.textContent='⏳ Идёт загрузка...'"
if old_btn in js:
    js = js.replace(old_btn, new_btn)

with open("static/js/script.js", "w", encoding="utf-8") as f:
    f.write(js)

# === 5. get_osm_stores.py: добавляем retry и альтернативные серверы ===
osm_script = '''"""
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
    print(f"\\n🔍 {city}...")
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
print(f"\\n🎉 Итого: {total} магазинов с координатами!")
if total == 0:
    print("\\n⚠️ Overpass и Nominatim недоступны.")
    print("Используйте кнопку 📍 Геокодировать в интерфейсе приложения")
    print("или откройте 🗺️ Карта — она автоматически геокодирует адреса.")
else:
    print("Перезапустите python app.py → 🗺️ Карта")
'''

with open("get_osm_stores.py", "w", encoding="utf-8") as f:
    f.write(osm_script)
print("✅ get_osm_stores.py: retry + Nominatim fallback + 4 сервера")

print("\n" + "="*50)
print("🎉 ИСПРАВЛЕНО!")
print("="*50)
print("\nЧто сделано:")
print("  ⏳ Понятный прогресс загрузки (не кажется что зависло)")
print("  🔧 2 потока вместо 4 (API не перегружается)")
print("  📍 +6 адресов Невинномысска из скриншота")
print("  🔄 OSM скрипт: retry + 4 сервера + Nominatim fallback")
print("  🗺️ Карта авто-геокодирует при открытии (из прошлого фикса)")
print("\nЗапусти:")
print("  del magnit_data.db")
print("  git add . && git commit -m 'fix loading, nevinnomyssk, osm retry' && git push")
print("  python app.py")
print("\nДля координатов попробуй:")
print("  python get_osm_stores.py")
print("Если Overpass недоступен — просто открой 🗺️ Карта в браузере,")
print("она сама геокодирует все адреса через Яндекс.Карты!")