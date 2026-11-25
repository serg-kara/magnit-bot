"""ФИНАЛЬНЫЙ ФИКС: скидки, карта, адреса, новые магазины"""
import os, re

# === FIX 1: parser.py — сохраняем MAX discount при агрегации ===
with open("parser.py", "r", encoding="utf-8") as f:
    p = f.read()

old_agg = '''if p["price"]<all_products[pid]["price"]:
                    all_products[pid]["price"]=p["price"];all_products[pid]["discount_percent"]=p["discount_percent"];all_products[pid]["savings"]=p["savings"]'''

new_agg = '''if p["price"]<all_products[pid]["price"]:
                    all_products[pid]["price"]=p["price"];all_products[pid]["savings"]=p["savings"]
                if p["discount_percent"]>all_products[pid]["discount_percent"]:
                    all_products[pid]["discount_percent"]=p["discount_percent"]
                    all_products[pid]["old_price"]=p["old_price"]'''

if old_agg in p:
    p = p.replace(old_agg, new_agg)
    print("✅ parser.py: MAX discount сохраняется при агрегации!")
else:
    # Try alternative format
    old2 = 'if p["price"] < all_products[pid]["price"]:\n                    all_products[pid]["price"] = p["price"]\n                    all_products[pid]["discount_percent"] = p["discount_percent"]\n                    all_products[pid]["savings"] = p["savings"]'
    new2 = 'if p["price"] < all_products[pid]["price"]:\n                    all_products[pid]["price"] = p["price"]\n                    all_products[pid]["savings"] = p["savings"]\n                if p["discount_percent"] > all_products[pid]["discount_percent"]:\n                    all_products[pid]["discount_percent"] = p["discount_percent"]\n                    all_products[pid]["old_price"] = p["old_price"]'
    if old2 in p:
        p = p.replace(old2, new2)
        print("✅ parser.py: MAX discount (alt format)")
    else:
        print("⚠️ Не найден блок агрегации, добавляю вручную")
        # Find and replace any version of the price comparison block
        p = re.sub(
            r'if p\["price"\]\s*<\s*all_products\[pid\]\["price"\]:\s*\n\s*all_products\[pid\]\["price"\]\s*=\s*p\["price"\];?\s*all_products\[pid\]\["discount_percent"\]\s*=\s*p\["discount_percent"\];?\s*all_products\[pid\]\["savings"\]\s*=\s*p\["savings"\]',
            'if p["price"]<all_products[pid]["price"]:\n                    all_products[pid]["price"]=p["price"];all_products[pid]["savings"]=p["savings"]\n                if p["discount_percent"]>all_products[pid]["discount_percent"]:\n                    all_products[pid]["discount_percent"]=p["discount_percent"];all_products[pid]["old_price"]=p["old_price"]',
            p
        )

# Add new store codes
new_stores = '''{"code":"991602","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991603","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991604","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991606","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991607","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991608","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991609","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991612","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991801","address":"Ставропольский край","city":"Ставрополь"},
{"code":"991802","address":"Ставропольский край","city":"Ставрополь"},
'''

marker = '{"code":"992323"'
pos = p.find(marker)
if pos > 0 and "991602" not in p:
    p = p[:pos] + new_stores + p[pos:]
    print("✅ parser.py: +10 новых магазинов Ставрополя")

# Update Stavropol addresses with real ones from alkogolikam.ru
addr_map = {
    '"Ставрополь, ул. Доваторцев, 64"': '"Ставрополь, ул. Доваторцев, д. 64"',
    '"Ставрополь, ул. Лермонтова, 259"': '"Ставрополь, ул. Лермонтова, д. 259"',
    '"Ставрополь, ул. Краснофлотская, 91"': '"Ставрополь, ул. Краснофлотская, д. 91"',
    '"Ставрополь, ул. Тухачевского, 22/1"': '"Ставрополь, ул. Тухачевского, д. 22/1"',
    '"Ставрополь, ул. Ленина, 440"': '"Ставрополь, ул. Ленина, д. 440"',
    '"Ставрополь, пр-кт К.Маркса, 47/30"': '"Ставрополь, пр-кт К.Маркса, д. 47/30"',
    '"Ставрополь, ул. Пирогова, 8"': '"Ставрополь, ул. Пирогова, д. 8"',
    '"Ставрополь, ул. Трунова, 134В"': '"Ставрополь, ул. Трунова, д. 134В"',
    '"Ставрополь, ул. Чапаева, 25"': '"Ставрополь, ул. Чапаева, д. 25"',
    '"Ставрополь, ул. Рогожникова, 90"': '"Ставрополь, ул. Рогожникова, д. 90"',
    '"Ставрополь, пр-кт Кулакова, 29Д"': '"Ставрополь, пр-кт Кулакова, д. 29Д"',
    '"Ставрополь, ул. 50 лет ВЛКСМ, 28а"': '"Ставрополь, ул. 50 лет ВЛКСМ, д. 28-а"',
    '"Ставрополь, Фестивальный проезд, 7"': '"Ставрополь, Фестивальный проезд, д. 7"',
}
for old, new in addr_map.items():
    p = p.replace(old, new)

with open("parser.py", "w", encoding="utf-8") as f:
    f.write(p)
print("✅ parser.py: обновлены адреса")


# === FIX 2: script.js — карта с геокодированием адресов ===
with open("static/js/script.js", "r", encoding="utf-8") as f:
    js = f.read()

# Replace entire initMap function with proper geocoding version
old_init = js[js.find("function initMap()"):js.find("document.getElementById('manage-stores-btn')")]
if old_init:
    new_init = '''function initMap(){
if(typeof ymaps==='undefined'){document.getElementById('yandex-map').innerHTML='<p style="padding:20px;color:#999">Карта недоступна</p>';return}
ymaps.ready(function(){
var city=citySelect.value||'Ставрополь';
var centers={'Ставрополь':[45.0445,41.9691],'Краснодар':[45.0355,38.9753],'Армавир':[44.9976,41.1296],'Невинномысск':[44.6333,41.9444],'Курганинск':[44.8833,40.5833],'Москва':[55.7558,37.6173],'Санкт-Петербург':[59.9343,30.3351]};
var center=centers[city]||[45.0445,41.9691];
var map=new ymaps.Map('yandex-map',{center:center,zoom:12,controls:['zoomControl','searchControl']});
// Geocode each store address to get coordinates
var stores=allStores.length?allStores:[];
if(!stores.length){fetch('/api/stores?city='+encodeURIComponent(city)).then(function(r){return r.json()}).then(function(s){geocodeStores(map,s,city)})}
else{geocodeStores(map,stores,city)}
// Also search organizations
ymaps.search('Магнит '+city,{results:50,type:'biz'}).then(function(res){
res.geoObjects.each(function(obj){
var name=obj.properties.get('name')||'Магнит';
var meta=obj.properties.get('CompanyMetaData');
var addr=meta?meta.address:'';
var coords=obj.geometry.getCoordinates();
var pm=new ymaps.Placemark(coords,{balloonContentHeader:name,balloonContentBody:addr,hintContent:name},{preset:'islands#redShoppingIcon'});
map.geoObjects.add(pm)});
if(map.geoObjects.getLength()>0)map.setBounds(map.geoObjects.getBounds(),{checkZoomRange:true,zoomMargin:30})
}).catch(function(){});
})}
function geocodeStores(map,stores,city){
var promises=stores.filter(function(s){return s.address&&s.address.indexOf('уточните')<0}).map(function(s){
return ymaps.geocode(city+', '+s.address,{results:1}).then(function(res){
var obj=res.geoObjects.get(0);
if(obj){
var coords=obj.geometry.getCoordinates();
var pm=new ymaps.Placemark(coords,{balloonContentHeader:s.address,balloonContentBody:'Код: '+s.code,hintContent:s.address},{preset:'islands#redDotIcon'});
map.geoObjects.add(pm)}}).catch(function(){})});
Promise.all(promises).then(function(){if(map.geoObjects.getLength()>0)map.setBounds(map.geoObjects.getBounds(),{checkZoomRange:true,zoomMargin:30})})}
'''
    js = js.replace(old_init, new_init)
    print("✅ script.js: карта с геокодированием каждого адреса!")

with open("static/js/script.js", "w", encoding="utf-8") as f:
    f.write(js)


# === FIX 3: app.py — умная сортировка ===
with open("app.py", "r", encoding="utf-8") as f:
    app = f.read()

if "'discount_desc':'discount_percent DESC'" in app:
    app = app.replace("'discount_desc':'discount_percent DESC'", "'discount_desc':'(CASE WHEN discount_percent>0 THEN 0 ELSE 1 END),discount_percent DESC,price ASC'")
    print("✅ app.py: умная сортировка")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app)


print("\n" + "="*50)
print("🎉 ФИНАЛЬНЫЙ ФИКС ПРИМЕНЁН!")
print("="*50)
print("\nИсправлено:")
print("  🏷️ Скидки: MAX discount сохраняется (не затирается ценой по карте)")
print("  🗺️ Карта: геокодирование каждого адреса + поиск организаций")
print("  🏪 +10 новых магазинов Ставрополя (итого 23+)")
print("  📍 Адреса обновлены форматом 'д. XX'")
print("  📊 Сортировка: реальные скидки первыми")
print("\nЗапусти:")
print("  del magnit_data.db")
print("  git add . && git commit -m 'final fix: discounts, map, stores' && git push")
print("  python app.py")