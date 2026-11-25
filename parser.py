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
    {"code": "992301", "address": "ул. Дзержинского, 42", "city": "Краснодар"},
    {"code": "992303", "address": "ул. Красная, 176", "city": "Краснодар"},
    {"code": "992304", "address": "ул. Ставропольская, 140", "city": "Краснодар"},
    {"code": "992305", "address": "ул. Российская, 257", "city": "Краснодар"},
    {"code": "992307", "address": "ул. Восточно-Кругликовская, 68", "city": "Краснодар"},
    {"code": "992309", "address": "ул. Северная, 389", "city": "Краснодар"},
    {"code": "992310", "address": "ул. Кубанская Набережная, 37", "city": "Краснодар"},
    {"code": "992311", "address": "ул. им. Тургенева, 174", "city": "Краснодар"},
    {"code": "992312", "address": "ул. Монтажников, 2", "city": "Краснодар"},
    {"code": "992313", "address": "ул. Петра Метальникова, 5", "city": "Краснодар"},
    {"code": "992314", "address": "ул. Героя Аверкиева, 16", "city": "Краснодар"},
    {"code": "992315", "address": "ул. Пригородная, 100", "city": "Краснодар"},
    {"code": "992316", "address": "ул. Ялтинская, 129", "city": "Краснодар"},
    {"code": "992318", "address": "ул. Уральская, 166", "city": "Краснодар"},
    {"code": "992320", "address": "ул. Сормовская, 202", "city": "Краснодар"},
    {"code": "992322", "address": "ул. Тюляева, 33", "city": "Краснодар"},
    {"code": "991003", "address": "Магнит (Ставропольский край?)", "city": "Ставрополь"},
    {"code": "991201", "address": "Магнит (Ставропольский край?)", "city": "Ставрополь"},
    {"code": "991301", "address": "Магнит (Ставропольский край?)", "city": "Ставрополь"},
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