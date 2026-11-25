"""Добавляет реальные адреса Курганинска + скрипт для браузера"""
import os

# === 1. parser.py: заменяем placeholder адреса Курганинска на реальные ===
with open("parser.py", "r", encoding="utf-8") as f:
    p = f.read()

# Replace generic Kurganinsk addresses with real ones from magnit.ru screenshot
replacements = {
    '"Курганинск (зона 11.99)"': None,  # will be replaced individually
    '"Курганинск"': '"Курганинск, ул Партизанская, д 215"',
}

# Map existing codes to real addresses
code_addr_map = {
    "992336": "Курганинск, ул Партизанская, д 215",
    "992338": "Курганинск, ул Р.Люксембург, д 263",
    "992341": "Курганинск, ул Энгельса, д 314",
    "992349": "Курганинск, ул Р.Люксембург, д 423",
    "992358": "Курганинск, ул Матросова, д 186",
    "992359": "Курганинск, ул Кочергина, д 158",
    "992364": "Курганинск, ул Ленина, д 100",
    "992365": "Курганинск, ул Красная, д 50",
}

for code, addr in code_addr_map.items():
    # Find the store entry and replace address
    import re
    pattern = rf'(\{{"code":"{code}","address":")[^"]*(")'
    replacement = rf'\g<1>{addr}\g<2>'
    p_new = re.sub(pattern, replacement, p)
    if p_new != p:
        p = p_new
        print(f"✅ {code} → {addr}")

with open("parser.py", "w", encoding="utf-8") as f:
    f.write(p)

# === 2. Создаём HTML-страницу для вытягивания магазинов из magnit.ru ===
# Эта страница открывается в браузере пользователя, загружает magnit.ru/shops
# через iframe или fetch, и извлекает адреса магазинов для выбранного города.
# Поскольку magnit.ru блокирует cross-origin запросы, используем другой подход:
# страница показывает инструкцию + bookmarklet который пользователь запускает на magnit.ru

os.makedirs("tools", exist_ok=True)

bookmarklet_html = '''<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8"><title>Извлечение магазинов Магнит</title>
<style>body{font-family:sans-serif;max-width:800px;margin:40px auto;padding:20px}
h1{color:#c00}pre{background:#f5f5f5;padding:15px;border-radius:8px;overflow-x:auto;font-size:12px}
.step{margin:20px 0;padding:15px;background:#fff3cd;border-radius:8px}
button{padding:10px 20px;background:#c00;color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px}
textarea{width:100%;height:200px;font-family:monospace;font-size:12px}
</style></head><body>
<h1>🏪 Извлечение магазинов из magnit.ru</h1>
<p>Этот инструмент поможет получить адреса и координаты магазинов для любого города.</p>

<div class="step">
<h3>Шаг 1: Откройте magnit.ru</h3>
<p>Перейдите на <a href="https://magnit.ru" target="_blank">magnit.ru</a>, нажмите «Выберите магазин», выберите нужный город (Курганинск, Невинномысск, Армавир).</p>
</div>

<div class="step">
<h3>Шаг 2: Запустите скрипт в консоли браузера</h3>
<p>На странице magnit.ru нажмите F12 → Console → вставьте этот код:</p>
<pre id="script-code">// Извлекает магазины из DOM страницы magnit.ru
(function(){
    var stores = [];
    // Ищем элементы списка магазинов
    var items = document.querySelectorAll('[class*="store"], [class*="shop"], [class*="pickup"]');
    items.forEach(function(el){
        var text = el.textContent.trim();
        if(text.includes('Магнит') && text.length > 10 && text.length < 200){
            stores.push(text.replace(/\\s+/g,' '));
        }
    });
    // Также ищем через Яндекс.Карты маркеры
    if(typeof ymaps !== 'undefined'){
        try {
            var maps = document.querySelectorAll('[class*="map"]');
            console.log('Found map elements:', maps.length);
        } catch(e){}
    }
    // Альтернативный поиск по тексту страницы
    var body = document.body.innerText;
    var lines = body.split('\\n').filter(function(l){
        return l.includes('Магнит') && (l.includes('ул') || l.includes('пр-кт') || l.includes('пер.'));
    });
    var result = {stores: [...new Set(stores)], addressLines: [...new Set(lines)]};
    console.log(JSON.stringify(result, null, 2));
    copy(JSON.stringify(result, null, 2));
    alert('Скопировано в буфер! Найдено: ' + result.stores.length + ' магазинов, ' + result.addressLines.length + ' адресов');
})();</pre>
<button onclick="navigator.clipboard.writeText(document.getElementById('script-code').textContent).then(()=>alert('Скрипт скопирован!'))">📋 Копировать скрипт</button>
</div>

<div class="step">
<h3>Шаг 3: Вставьте результат сюда</h3>
<textarea id="result" placeholder='Вставьте JSON из консоли браузера...'></textarea>
<button onclick="parseResult()">Обработать</button>
<pre id="output"></pre>
</div>

<script>
function parseResult(){
    try {
        var data = JSON.parse(document.getElementById('result').value);
        var output = '=== Найденные магазины ===\\n';
        if(data.stores) data.stores.forEach(function(s,i){ output += (i+1) + '. ' + s + '\\n'; });
        if(data.addressLines) data.addressLines.forEach(function(s,i){ output += 'Адрес: ' + s + '\\n'; });
        document.getElementById('output').textContent = output;
    } catch(e){
        document.getElementById('output').textContent = 'Ошибка парсинга: ' + e.message;
    }
}
</script>
</body></html>'''

with open("tools/extract_stores.html", "w", encoding="utf-8") as f:
    f.write(bookmarklet_html)
print("✅ tools/extract_stores.html: инструмент для извлечения магазинов")

# === 3. Скрипт для Overpass API (запускается на компьютере пользователя) ===
overpass_script = '''"""
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
    print(f"\\n🔍 {city}...")
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
print(f"\\n🎉 Итого добавлено: {total} магазинов с координатами!")
print("Перезапустите python app.py и откройте карту.")
'''

with open("get_osm_stores.py", "w", encoding="utf-8") as f:
    f.write(overpass_script)
print("✅ get_osm_stores.py: скрипт Overpass для получения адресов+координат")

print("\n" + "="*50)
print("🎉 ГОТОВО!")
print("="*50)
print("\nЧто сделано:")
print("  📍 Курганинск: 8 реальных адресов из скриншота magnit.ru")
print("  🔧 tools/extract_stores.html: инструмент для браузера")
print("  🗺️ get_osm_stores.py: получает адреса+координаты из OSM")
print("\nЗапусти:")
print("  del magnit_data.db")
print("  git add . && git commit -m 'real addresses, osm tool' && git push")
print("  python app.py")
print("\nДля получения магазинов Невинномысска/Армавира:")
print("  Вариант 1: python get_osm_stores.py (получит из OpenStreetMap)")
print("  Вариант 2: открой tools/extract_stores.html в браузере")
print("             следуй инструкции для извлечения с magnit.ru")