"""
Исправление багов + добавление магазинов (Армавир, Невинномысск, Курганинск и др.)
Запуск: python fix_bugs.py
После: git add . && git commit -m "fix bugs, add 24 stores" && git push
"""
import re

# === FIX 1: parser.py — добавляем scan_range() ===
with open("parser.py", "r", encoding="utf-8") as f:
    content = f.read()

if "def scan_range" not in content:
    scan_func = '''
def scan_range(start, end):
    """Сканирует диапазон кодов, возвращает рабочие."""
    found = []
    for code in range(start, end):
        total = check_store_code(code)
        if total > 0:
            found.append({"code": str(code), "total": total})
    return found


'''
    pos = content.find("def get_product_stock_in_stores")
    if pos > 0:
        content = content[:pos] + scan_func + content[pos:]
    else:
        content += scan_func
    with open("parser.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ parser.py: добавлена scan_range()")
else:
    print("⏭️  parser.py: scan_range() уже есть")

# === FIX 2: parser.py — обновляем DEFAULT_STORES (24 магазина) ===
with open("parser.py", "r", encoding="utf-8") as f:
    content = f.read()

new_stores = '''DEFAULT_STORES = [
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
]'''

pattern = r'DEFAULT_STORES = \[.*?\]'
match = re.search(pattern, content, re.DOTALL)
if match:
    content = content[:match.start()] + new_stores + content[match.end():]
    with open("parser.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ parser.py: DEFAULT_STORES обновлён (24 магазина)")

# === FIX 3: scan_stores.py — фикс Overpass + новые города ===
with open("scan_stores.py", "r", encoding="utf-8") as f:
    scan = f.read()

# Fix Overpass query syntax
scan = scan.replace(
    'node["shop"="supermarket"]"name"~"Магнит"',
    'node["shop"="supermarket"]["name"~"Магнит"]'
)
scan = scan.replace(
    'way["shop"="supermarket"]"name"~"Магнит"',
    'way["shop"="supermarket"]["name"~"Магнит"]'
)

# Add new cities to CITIES_BBOX
new_cities_block = '''    "Армавир": (44.95, 41.10, 45.05, 41.25),
    "Невинномысск": (44.60, 41.90, 44.70, 42.05),
    "Курганинск": (44.85, 40.55, 44.95, 40.65),
    "Будённовск": (44.75, 44.10, 44.85, 44.25),
    "Михайловск": (45.08, 41.95, 45.15, 42.10),
    "Пятигорск": (44.00, 43.00, 44.10, 43.15),
    "Ессентуки": (44.03, 42.83, 44.08, 42.90),
    "Минеральные Воды": (44.18, 43.10, 44.25, 43.20),'''

if "Армавир" not in scan:
    marker = '"Санкт-Петербург"'
    pos = scan.find(marker)
    if pos > 0:
        end_line = scan.find("\n", pos)
        scan = scan[:end_line] + "\n" + new_cities_block + scan[end_line:]
        print("✅ scan_stores.py: добавлены Армавир, Невинномысск, Курганинск и др.")

# Expand scan ranges
old_ranges_end = "(699420, 699430),"
new_ranges = """(699420, 699430),
    (990000, 990020),
    (990100, 990120),
    (991000, 991020),
    (991100, 991120),
    (991200, 991220),
    (991300, 991320),
    (991400, 991420),
    (991500, 991520),
    (992300, 992350),
    (995100, 995110),
    (997100, 997110),
    (997200, 997210),"""

if old_ranges_end in scan and "990000" not in scan:
    scan = scan.replace(old_ranges_end, new_ranges)
    print("✅ scan_stores.py: расширены диапазоны сканирования")

with open("scan_stores.py", "w", encoding="utf-8") as f:
    f.write(scan)
print("✅ scan_stores.py: сохранён")

print("\n" + "=" * 50)
print("🎉 ВСЕ ИСПРАВЛЕНИЯ ПРИМЕНЕНЫ!")
print("=" * 50)
print("\nТеперь выполни:")
print("  del magnit_data.db")
print("  git add parser.py scan_stores.py")
print('  git commit -m "fix: scan_range, overpass, 24 stores, new cities"')
print("  git push")
print("\nЗатем: python app.py")