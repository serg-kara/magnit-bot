"""
Первоначальное сканирование магазинов Магнит.
1. Находит рабочие коды магазинов через API
2. Получает адреса через Overpass API (OpenStreetMap)
3. Сохраняет всё в локальную БД

Запуск: python scan_stores.py
"""
import sqlite3
import requests
import urllib3
import time
import json
from datetime import datetime

urllib3.disable_warnings()

DB_NAME = "magnit_data.db"
API_BASE = "https://middle-api.magnit.ru"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://magnit.ru",
    "Referer": "https://magnit.ru/",
}

# Диапазоны кодов для сканирования
RANGES = [
    (990000, 990010),
    (90100, 90110),
    (991000, 991010),
    (991100, 991110),
    (991200, 991210),
    (991300, 991310),
    (991400, 991410),
    (991500, 991510),
    (992300, 992340),
    (993000, 993010),
    (993100, 993110),
    (993200, 993210),
    (993400, 993410),
    (994200, 994210),
    (995100, 995110),
    (996000, 996010),
    (996400, 996410),
    (997100, 997110),
    (997200, 997210),
    (777880, 777890),
    (699420, 699430),
]

# Координаты городов для Overpass (lat_min, lon_min, lat_max, lon_max)
CITIES_BBOX = {
    "Ставрополь": (44.95, 41.85, 45.10, 42.05),
    "Краснодар": (44.95, 38.85, 45.10, 39.10),
    "Армавир": (44.95, 41.10, 45.05, 41.25),
    "Невинномысск": (44.60, 41.90, 44.70, 42.05),
    "Будённовск": (44.75, 44.10, 44.85, 44.25),
    "Курганинск": (44.85, 40.55, 44.95, 40.65),
    "Михайловск": (45.08, 41.95, 45.15, 42.10),
    "Пятигорск": (44.00, 43.00, 44.10, 43.15),
    "Ессентуки": (44.03, 42.83, 44.08, 42.90),
    "Минеральные Воды": (44.18, 43.10, 44.25, 43.20),
    "Москва": (55.70, 37.55, 55.80, 37.70),
    "Санкт-Петербург": (59.90, 30.25, 59.97, 30.40),
}


def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute('''CREATE TABLE IF NOT EXISTS stores (
        code TEXT PRIMARY KEY, address TEXT, city TEXT,
        products_count INTEGER DEFAULT 0, lat REAL, lon REAL, added_at TEXT)''')
    # Добавляем колонки если их нет (миграция)
    try:
        conn.execute("ALTER TABLE stores ADD COLUMN products_count INTEGER DEFAULT 0")
    except:
        pass
    try:
        conn.execute("ALTER TABLE stores ADD COLUMN lat REAL")
    except:
        pass
    try:
        conn.execute("ALTER TABLE stores ADD COLUMN lon REAL")
    except:
        pass
    conn.commit()
    return conn


def check_code(code):
    payload = {
        "storeCode": str(code), "storeType": "1", "cityId": "1",
        "catalogType": "1", "includeAdultGoods": True,
        "pagination": {"offset": 0, "limit": 1},
        "sort": {"order": "desc", "type": "discount"},
    }
    try:
        r = requests.post(f"{API_BASE}/v2/goods/search", headers=HEADERS,
                         json=payload, timeout=4, verify=False)
        data = r.json()
        return data.get("pagination", {}).get("totalCount", 0)
    except:
        return 0


def fetch_osm_stores(city_name, bbox):
    """Получает магазины Магнит из OpenStreetMap через Overpass API."""
    lat_min, lon_min, lat_max, lon_max = bbox
    query = f'''[out:json][timeout:15];
    (
      node["shop"="supermarket"]["name"~"Магнит"]({lat_min},{lon_min},{lat_max},{lon_max});
      way["shop"="supermarket"]["name"~"Магнит"]({lat_min},{lon_min},{lat_max},{lon_max});
    );
    out center;'''
    
    try:
        r = requests.post("https://overpass-api.de/api/interpreter",
                         data={"data": query},
                         headers={"User-Agent": "MagnitBot/1.0"},
                         timeout=20, verify=False)
        if r.status_code == 200:
            data = r.json()
            stores = []
            for el in data.get("elements", []):
                tags = el.get("tags", {})
                lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
                lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
                street = tags.get("addr:street", "")
                house = tags.get("addr:housenumber", "")
                name = tags.get("name", "Магнит")
                addr = f"{street}, д. {house}" if street else ""
                if addr:
                    stores.append({"address": addr, "lat": lat, "lon": lon, "name": name})
            return stores
    except Exception as e:
        print(f"  ⚠️ Overpass ошибка для {city_name}: {e}")
    
    # Fallback: пробуем зеркало
    try:
        r = requests.post("https://overpass.kumi.systems/api/interpreter",
                         data={"data": query},
                         headers={"User-Agent": "MagnitBot/1.0"},
                         timeout=20, verify=False)
        if r.status_code == 200:
            data = r.json()
            stores = []
            for el in data.get("elements", []):
                tags = el.get("tags", {})
                lat = el.get("lat") or (el.get("center", {}) or {}).get("lat")
                lon = el.get("lon") or (el.get("center", {}) or {}).get("lon")
                street = tags.get("addr:street", "")
                house = tags.get("addr:housenumber", "")
                addr = f"{street}, д. {house}" if street else ""
                if addr:
                    stores.append({"address": addr, "lat": lat, "lon": lon})
            return stores
    except:
        pass
    
    return []


def main():
    conn = init_db()
    
    # === ЭТАП 1: Сканирование кодов ===
    print("=" * 50)
    print("📡 ЭТАП 1: Сканирование кодов магазинов")
    print("=" * 50)
    
    total_found = 0
    total_scanned = 0
    
    for start, end in RANGES:
        print(f"\n  Сканирую {start}-{end}...")
        for code in range(start, end):
            total_scanned += 1
            count = check_code(code)
            if count > 0:
                total_found += 1
                conn.execute("""INSERT OR IGNORE INTO stores 
                    (code, address, city, products_count, added_at) VALUES (?,?,?,?,?)""",
                    (str(code), f"Магнит #{code}", "Не определён", count, datetime.now().isoformat()))
                conn.commit()
                print(f"    ✅ {code}: {count} товаров")
            time.sleep(0.05)
    
    print(f"\n  📊 Просканировано: {total_scanned}, найдено: {total_found}")
    
    # === ЭТАП 2: Получение адресов из OSM ===
    print("\n" + "=" * 50)
    print("🗺️ ЭТАП 2: Получение адресов из OpenStreetMap")
    print("=" * 50)
    
    all_osm_stores = {}
    for city_name, bbox in CITIES_BBOX.items():
        print(f"\n  Ищу магазины в: {city_name}...")
        stores = fetch_osm_stores(city_name, bbox)
        if stores:
            all_osm_stores[city_name] = stores
            print(f"    ✅ Найдено {len(stores)} магазинов:")
            for s in stores[:5]:
                print(f"      📍 {s['address']}")
            if len(stores) > 5:
                print(f"      ... и ещё {len(stores)-5}")
        else:
            print(f"    ⚠️ Не найдено (Overpass недоступен?)")
        time.sleep(1)
    
    # === ЭТАП 3: Сохранение адресов в БД ===
    print("\n" + "=" * 50)
    print("💾 ЭТАП 3: Сохранение в базу данных")
    print("=" * 50)
    
    saved_addresses = 0
    for city_name, stores in all_osm_stores.items():
        for s in stores:
            # Создаём запись с адресом (без кода - код привяжем позже)
            addr = f"{city_name}, {s['address']}"
            conn.execute("""INSERT OR REPLACE INTO stores 
                (code, address, city, lat, lon, added_at) VALUES (?,?,?,?,?,?)""",
                (f"osm_{saved_addresses}", addr, city_name, 
                 s.get('lat'), s.get('lon'), datetime.now().isoformat()))
            saved_addresses += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n  💾 Сохранено адресов: {saved_addresses}")
    print(f"\n{'=' * 50}")
    print("🎉 ГОТОВО!")
    print(f"{'=' * 50}")
    print(f"\n  Найдено кодов магазинов: {total_found}")
    print(f"  Найдено адресов (OSM): {saved_addresses}")
    print(f"\n  Теперь запустите: python app.py")
    print(f"  В интерфейсе «⚙️ Магазины» привяжите коды к адресам.")
    print(f"\n  💡 Совет: откройте magnit.ru → Выберите магазин →")
    print(f"     F12 → Application → Cookies → shopCode = ваш код")


if __name__ == "__main__":
    main()