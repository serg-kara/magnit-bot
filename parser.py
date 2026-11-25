import requests
import re
import logging
import urllib3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    # Краснодар
    {"code": "992301", "address": "Краснодар, ул. Дзержинского, 42", "city": "Краснодар"},
    {"code": "990101", "address": "Краснодарский край", "city": "Краснодар"},
    {"code": "990102", "address": "Краснодарский край", "city": "Краснодар"},
    {"code": "992336", "address": "Краснодарский край", "city": "Краснодар"},
    {"code": "992338", "address": "Краснодарский край", "city": "Краснодар"},
    # Ставрополь — реальные адреса из alkogolikam.ru
    {"code": "991002", "address": "Ставрополь, ул. Доваторцев, д. 64", "city": "Ставрополь"},
    {"code": "991003", "address": "Ставрополь, ул. Лермонтова, д. 259", "city": "Ставрополь"},
    {"code": "991004", "address": "Ставрополь, ул. Краснофлотская, д. 91", "city": "Ставрополь"},
    {"code": "991102", "address": "Ставрополь, ул. Тухачевского, д. 22/1", "city": "Ставрополь"},
    {"code": "991201", "address": "Ставрополь, ул. Ленина, д. 440", "city": "Ставрополь"},
    {"code": "991301", "address": "Ставрополь, К.Маркса пр-кт, д. 47/30", "city": "Ставрополь"},
    {"code": "991303", "address": "Ставрополь, ул. Пирогова, д. 8", "city": "Ставрополь"},
    {"code": "991501", "address": "Ставрополь, ул. Трунова, д. 134В", "city": "Ставрополь"},
    {"code": "992326", "address": "Ставрополь, ул. Чапаева, д. 25", "city": "Ставрополь"},
    {"code": "992330", "address": "Ставрополь, ул. Рогожникова, д. 90", "city": "Ставрополь"},
    {"code": "992334", "address": "Ставрополь, Кулакова пр-кт, д. 29Д", "city": "Ставрополь"},
    {"code": "997101", "address": "Ставрополь, ул. 50 лет ВЛКСМ, д. 28-а", "city": "Ставрополь"},
    {"code": "997201", "address": "Ставрополь, Фестивальный проезд, д. 7", "city": "Ставрополь"},
    # Другие регионы
    {"code": "992323", "address": "Южный ФО", "city": "Другие регионы"},
    {"code": "995101", "address": "Южный ФО", "city": "Другие регионы"},
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


def scan_range(start, end):
    found = []
    for code in range(start, end):
        total = check_store_code(code)
        if total > 0:
            found.append({"code": str(code), "total": total})
    return found


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
        logging.error(f"Ошибка запроса {store_code}: {e}")
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


def parse_store_progressive(store_code, max_items=2000, term=None):
    all_products = []
    offset = 0
    seen_ids = set()
    while len(all_products) < max_items:
        products, has_more, total_count = fetch_products_page(store_code, offset=offset, term=term)
        for p in products:
            if p["id"] not in seen_ids:
                seen_ids.add(p["id"])
                all_products.append(p)
        if not has_more or not products or offset >= 10000:
            break
        offset += 50
    return all_products


def parse_stores_parallel(codes_with_addresses, max_items=1000, term=None, progress_callback=None):
    """Параллельный парсинг нескольких магазинов. В 4 раза быстрее."""
    all_products = {}
    
    def parse_one(code_addr):
        code, address = code_addr
        products = parse_store_progressive(code, max_items=max_items, term=term)
        return code, address, products
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(parse_one, ca): ca for ca in codes_with_addresses}
        done_count = 0
        for future in as_completed(futures):
            code, address, products = future.result()
            done_count += 1
            if progress_callback:
                progress_callback(done_count, len(codes_with_addresses), len(all_products))
            for p in products:
                pid = p["id"]
                if pid not in all_products:
                    all_products[pid] = {**p, "stores": []}
                all_products[pid]["stores"].append({
                    "code": code, "address": address,
                    "stock": p["stock"], "price": p["price"],
                    "discount_percent": p["discount_percent"]
                })
                if p["price"] < all_products[pid]["price"]:
                    all_products[pid]["price"] = p["price"]
                    all_products[pid]["discount_percent"] = p["discount_percent"]
                    all_products[pid]["savings"] = p["savings"]
                all_products[pid]["stock"] += p["stock"]
    
    result = list(all_products.values())
    for p in result:
        p["stores"].sort(key=lambda x: x["price"])
    return result
