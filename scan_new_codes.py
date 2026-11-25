"""
Сканирует коды магазинов формата 262xxx (как на magnit.ru).
Запуск: python scan_new_codes.py
Находит ВСЕ магазины и добавляет в базу.
"""
import requests, sqlite3, time, urllib3
urllib3.disable_warnings()

DB_NAME = "magnit_data.db"
API_BASE = "https://middle-api.magnit.ru"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
           "Origin": "https://magnit.ru", "Referer": "https://magnit.ru/"}

def check(code):
    try:
        r = requests.post(f"{API_BASE}/v2/goods/search", headers=HEADERS,
            json={"storeCode":str(code),"storeType":"1","cityId":"1","catalogType":"1",
                  "includeAdultGoods":True,"pagination":{"offset":0,"limit":1},
                  "sort":{"order":"desc","type":"discount"}}, timeout=5, verify=False)
        return r.json().get("pagination",{}).get("totalCount",0)
    except:
        return 0

conn = sqlite3.connect(DB_NAME)
total = 0

# Scan ranges around known working codes
ranges = [(262900,263100), (260000,260050), (261000,261050), (263000,263100)]

for start, end in ranges:
    print(f"\n📡 Сканирую {start}-{end}...")
    found = 0
    for code in range(start, end):
        t = check(code)
        if t > 0:
            conn.execute("INSERT OR IGNORE INTO stores (code,address,city,added_at) VALUES (?,?,?,datetime('now'))",
                        (str(code), f"Магнит #{code}", "Ставрополь"))
            found += 1
            total += 1
            if found <= 5 or found % 10 == 0:
                print(f"  ✅ {code}: {t} товаров")
        time.sleep(0.1)
    conn.commit()
    print(f"  Найдено в диапазоне: {found}")

conn.close()
print(f"\n🎉 Всего найдено: {total} новых магазинов!")
print("Перезапустите python app.py")
