"""Сканирует магазины для Курганинска, Армавира, Невинномысска.
Запуск: python scan_other_cities.py
"""
import requests, sqlite3, time, urllib3
urllib3.disable_warnings()
DB="magnit_data.db"
API="https://middle-api.magnit.ru/v2/goods/search"
H={"User-Agent":"Mozilla/5.0","Accept":"application/json","Origin":"https://magnit.ru","Referer":"https://magnit.ru/"}

def check(code):
    try:
        r=requests.post(API,headers=H,json={"storeCode":str(code),"storeType":"1","cityId":"1","catalogType":"1","includeAdultGoods":True,"pagination":{"offset":0,"limit":1},"sort":{"order":"desc","type":"discount"}},timeout=5,verify=False)
        return r.json().get("pagination",{}).get("totalCount",0)
    except:return 0

conn=sqlite3.connect(DB)
# Known codes for other cities from previous scans
city_codes={
    "Курганинск":["992336","992338","992341","992349","992358","992359","992364","992365"],
    "Невинномысск":["995101"],
    "Армавир":["992323"],
}

# Also scan 262xxx range for these cities (different pricing zones)
# Курганинск zone price=11.99, Невинномысск might be different
ranges=[(262800,262900),(263100,263200),(261000,261100)]

for start,end in ranges:
    print(f"\n📡 {start}-{end}...")
    found=0
    for code in range(start,end):
        t=check(code)
        if t>0:
            conn.execute("INSERT OR IGNORE INTO stores(code,address,city,added_at)VALUES(?,?,?,datetime('now'))",(str(code),f"Магнит #{code}","Ставропольский край"))
            found+=1
            if found<=3:print(f"  ✅ {code}: {t}")
        time.sleep(0.1)
    conn.commit()
    print(f"  Найдено: {found}")

conn.close()
print("\n🎉 Готово! Перезапустите python app.py")
