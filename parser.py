import requests
import re
import logging
import urllib3
import time

urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)

API_BASE = "https://middle-api.magnit.ru"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Origin": "https://magnit.ru",
    "Referer": "https://magnit.ru/",
}

DEFAULT_STORES = [
    # Краснодар (ценовая зона B)
    {"code": "992301", "address": "Краснодар, ул. Дзержинского, 42", "city": "Краснодар"},
    {"code": "990101", "address": "Краснодарский край (990101)", "city": "Краснодар"},
    {"code": "990102", "address": "Краснодарский край (990102)", "city": "Краснодар"},
    {"code": "992336", "address": "Краснодарский край (992336)", "city": "Краснодар"},
    {"code": "992338", "address": "Краснодарский край (992338)", "city": "Краснодар"},
    # Ставропольский край (ценовая зона A)
    {"code": "991002", "address": "Ставропольский край (991002)", "city": "Ставропольский край"},
    {"code": "991003", "address": "Ставропольский край (991003)", "city": "Ставропольский край"},
    {"code": "991004", "address": "Ставропольский край (991004)", "city": "Ставропольский край"},
    {"code": "991102", "address": "Ставропольский край (991102)", "city": "Ставропольский край"},
    {"code": "991201", "address": "Ставропольский край (991201)", "city": "Ставропольский край"},
    {"code": "991301", "address": "Ставропольский край (991301)", "city": "Ставропольский край"},
    {"code": "991303", "address": "Ставропольский край (991303)", "city": "Ставропольский край"},
    {"code": "991501", "address": "Ставропольский край (991501)", "city": "Ставропольский край"},
    {"code": "992326", "address": "Ставропольский край (992326)", "city": "Ставропольский край"},
    {"code": "992330", "address": "Ставропольский край (992330)", "city": "Ставропольский край"},
    {"code": "992334", "address": "Ставропольский край (992334)", "city": "Ставропольский край"},
    {"code": "997101", "address": "Ставропольский край (997101)", "city": "Ставропольский край"},
    {"code": "997201", "address": "Ставропольский край (997201)", "city": "Ставропольский край"},
    # Другие регионы (ценовая зона C)
    {"code": "992323", "address": "Южный ФО (992323)", "city": "Другие регионы"},
    {"code": "995101", "address": "Южный ФО (995101)", "city": "Другие регионы"},
    # Москва и СПб
    {"code": "777885", "address": "Москва", "city": "Москва"},
    {"code": "699422", "address": "Санкт-Петербург", "city": "Санкт-Петербург"},
]


def extract_volume(name):
    match = re.search(r'(\d+(?:[.,]\d+)?)\s*(мл|л|г|кг|шт)', name, re.IGNORECASE)
    if match:
        return float(match.group(1).replace(',', '.')), match.group(2).lower()
    return None, None


def calc_price_per_liter(price, name):
    value, unit = extract_volume(name)
    if not value:
        return 0
    if unit == 'мл':
        return round(price / (value / 1000), 2)
    elif unit == 'л':
        return round(price / value, 2)
    return 0


def search_cities(query):
    try:
        r = requests.get(f"{API_BASE}/v1/cities", headers=HEADERS,
                        params={"query": query, "limit": 20}, timeout=15, verify=False)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception as e:
        logging.error(f"Ошибка поиска городов: {e}")
        return []


def check_store_code(code):
    payload = {
        "storeCode": str(code), "storeType": "1", "cityId": "1",
        "catalogType": "1", "includeAdultGoods": True,
        "pagination": {"offset": 0, "limit": 1},
        "sort": {"order": "desc", "type": "discount"},
    }
    try:
        r = requests.post(f"{API_BASE}/v2/goods/search", headers=HEADERS,
                         json=payload, timeout=4, verify=False)
        return r.json().get("pagination", {}).get("totalCount", 0)
    except:
        return 0


def fetch_products_page(store_code, offset=0, limit=50, term=None):
    payload = {
        "storeCode": str(store_code), "storeType": "1", "cityId": "1",
        "catalogType": "1", "includeAdultGoods": True,
        "pagination": {"offset": offset, "limit": limit},
        "sort": {"order": "desc", "type": "discount"},
    }
    if term:
        payload["term"] = term
    try:
        r = requests.post(f"{API_BASE}/v2/goods/search", headers=HEADERS,
                         json=payload, timeout=15, verify=False)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
        return [], False, 0

    items = data.get("items", [])
    pagination = data.get("pagination", {})
    products = []
    for item in items:
        promo = item.get("promotion") or {}
        if not promo.get("isPromotion"):
            continue
        discount = promo.get("discountPercent") or 0
        if discount <= 0:
            continue
        price = item.get("price", 0) / 100
        old_price = (promo.get("oldPrice") or 0) / 100
        stock = item.get("quantity") or 0
        name = item.get("name", "")
        gallery = item.get("gallery") or []
        image = gallery[0].get("url", "") if gallery else ""
        value, unit = extract_volume(name)
        volume_str = f"{value:g} {unit}" if value else ""
        products.append({
            "id": str(item.get("id", "")), "name": name,
            "price": price, "old_price": old_price,
            "discount_percent": discount, "savings": round(old_price - price, 2),
            "image": image, "stock": stock,
            "is_adult": 1 if item.get("isForAdults") else 0,
            "volume": volume_str, "price_per_liter": calc_price_per_liter(price, name),
            "store_code": str(store_code),
        })
    return products, pagination.get("hasMore", False), pagination.get("totalCount", 0)


def parse_store_progressive(store_code, max_items=3000, term=None):
    all_products = []
    offset = 0
    seen_ids = set()
    while len(all_products) < max_items:
        products, has_more, total_count = fetch_products_page(store_code, offset=offset, term=term)
        for p in products:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_products.append(p)
        logging.info(f"  [{store_code}] {len(all_products)}/{total_count}")
        if not has_more or not products or offset >= 10000:
            break
        offset += 50
    return all_products



def scan_range(start, end):
    """Сканирует диапазон кодов, возвращает рабочие."""
    found = []
    for code in range(start, end):
        total = check_store_code(code)
        if total > 0:
            found.append({"code": str(code), "total": total})
    return found


def get_product_stock_in_stores(product_id, store_codes, term=None):
    """Проверяет остаток конкретного товара в нескольких магазинах."""
    results = []
    for code in store_codes:
        payload = {
            "storeCode": str(code), "storeType": "1", "cityId": "1",
            "catalogType": "1", "includeAdultGoods": True,
            "term": term or "",
            "pagination": {"offset": 0, "limit": 50},
            "sort": {"order": "desc", "type": "discount"},
        }
        try:
            r = requests.post(f"{API_BASE}/v2/goods/search", headers=HEADERS,
                             json=payload, timeout=8, verify=False)
            data = r.json()
            for item in data.get("items", []):
                if str(item.get("id")) == str(product_id):
                    promo = item.get("promotion") or {}
                    results.append({
                        "store_code": str(code),
                        "price": item.get("price", 0) / 100,
                        "old_price": (promo.get("oldPrice") or 0) / 100,
                        "discount_percent": promo.get("discountPercent") or 0,
                        "stock": item.get("quantity") or 0,
                    })
                    break
        except:
            pass
        time.sleep(0.2)
    return results