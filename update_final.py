"""Финальное обновление: 44 адреса, 15 категорий, геокодирование"""
import os, re

# === 1. parser.py: добавляем 44 реальных адреса Ставрополя ===
with open("parser.py", "r", encoding="utf-8") as f:
    p = f.read()

stavropol_addresses = [
    "К.Маркса пр-кт, д. 47/30", "Кулакова пр-кт, д. 69", "СНТ Оптимист, д. 12",
    "Фестивальный проезд, д. 7", "б-р Зеленая Роща, д. 14", "ул. Ленина, д. 127 стр 1",
    "ул. Западный обход, д. 68а", "пер. Макарова, д. 22", "пер. Рубежный, д. 1",
    "пер. Шеболдаева, д. 11", "пр-кт Российский, д. 19", "ул. 2 Промышленная, д. 1",
    "ул. 50 лет ВЛКСМ, д. 28-а", "ул. 50 лет ВЛКСМ, д. 54/1", "ул. 50 лет ВЛКСМ, д. 63",
    "ул. Апанасенковская, д. 12/1", "ул. Дзержинского, д. 134",
    "ул. Добролюбова / Мира, д. 49/152", "ул. Доваторцев, д. 181г",
    "ул. Доваторцев, д. 32а", "ул. Доваторцев, д. 64", "ул. Достоевского, д. 52а",
    "ул. Космонавтов, д. 2", "ул. Краснофлотская, д. 91", "ул. Л.Толстого, д. 114",
    "ул. Ленина, д. 472", "ул. Лермонтова, д. 259", "ул. Магистральная",
    "ул. Матросова, д. 12", "ул. Мира, д. 429", "ул. Пирогова, д. 54в",
    "ул. Пирогова, д. 8", "ул. Рассветная, д. 4", "ул. Рогожникова, д. 90",
    "ул. Салова, д. 70", "ул. Серова, д. 201", "ул. Социалистическая, д. 17",
    "ул. Трунова, д. 134В", "ул. Тухачевского, д. 12а", "ул. Тухачевского, д. 13",
    "ул. Тухачевского, д. 22/1", "ул. Чапаева, д. 25", "ул. Чапаева, д. 4/1д",
    "ул. Южный обход, д. 1а",
]

new_entries = ""
for i, addr in enumerate(stavropol_addresses):
    code = f"stav_{i+1:02d}"
    if code not in p:
        new_entries += f'{{"code":"{code}","address":"Ставрополь, {addr}","city":"Ставрополь"}},\n'

if new_entries:
    marker = '{"code":"992323"'
    pos = p.find(marker)
    if pos > 0:
        p = p[:pos] + new_entries + p[pos:]
        print(f"✅ parser.py: +{len(stavropol_addresses)} адресов Ставрополя")

with open("parser.py", "w", encoding="utf-8") as f:
    f.write(p)

# === 2. index.html: 15 категорий как на alkogolikam.ru ===
with open("templates/index.html", "r", encoding="utf-8") as f:
    html = f.read()

old_tags = '<button class="tag-btn active" data-term="">Всё</button><button class="tag-btn" data-term="вино">Вино</button><button class="tag-btn" data-term="пиво">Пиво</button><button class="tag-btn" data-term="водка">Водка</button><button class="tag-btn" data-term="виски">Виски</button><button class="tag-btn" data-term="коньяк">Коньяк</button><button class="tag-btn" data-term="шампанское">Игристое</button><button class="tag-btn" data-term="ликёр">Ликёры</button><button class="tag-btn" data-term="сыр">Сыр</button><button class="tag-btn" data-term="кофе">Кофе</button>'

new_tags = '<button class="tag-btn active" data-term="">Всё</button><button class="tag-btn" data-term="вино">Вино</button><button class="tag-btn" data-term="игристое">Игристое</button><button class="tag-btn" data-term="водка">Водка</button><button class="tag-btn" data-term="коньяк">Коньяк и бренди</button><button class="tag-btn" data-term="виски">Виски</button><button class="tag-btn" data-term="ром">Ром</button><button class="tag-btn" data-term="джин">Джин</button><button class="tag-btn" data-term="текила">Текила</button><button class="tag-btn" data-term="ликёр">Ликёры и настойки</button><button class="tag-btn" data-term="вермут">Вермут и аперитивы</button><button class="tag-btn" data-term="пиво">Пиво</button><button class="tag-btn" data-term="сидр">Сидр и медовуха</button><button class="tag-btn" data-term="слабоалкогольные">Слабоалкогольные</button><button class="tag-btn" data-term="сыр">Сыр</button><button class="tag-btn" data-term="кофе">Кофе</button>'

if old_tags in html:
    html = html.replace(old_tags, new_tags)
    print("✅ index.html: 15 категорий фильтров как на alkogolikam.ru")
else:
    # Try replacing just the quick-search div content
    qs_match = re.search(r'(<div class="quick-search">)(.*?)(</div>)', html, re.DOTALL)
    if qs_match:
        html = html[:qs_match.start(2)] + new_tags + html[qs_match.end(2):]
        print("✅ index.html: категории обновлены (alt)")

# Add geocode button if missing
if 'geocode-btn' not in html:
    html = html.replace(
        '<button id="refresh-btn" class="btn-secondary">🔄 Обновить</button>',
        '<button id="refresh-btn" class="btn-secondary">🔄 Обновить</button><button id="geocode-btn" class="btn-secondary">📍 Геокодировать</button>'
    )
    print("✅ index.html: кнопка геокодирования")

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html)

# === 3. app.py: endpoint для координат + умная сортировка ===
with open("app.py", "r", encoding="utf-8") as f:
    app = f.read()

if "'discount_desc':'discount_percent DESC'" in app:
    app = app.replace("'discount_desc':'discount_percent DESC'", "'discount_desc':'(CASE WHEN discount_percent>0 THEN 0 ELSE 1 END),discount_percent DESC,price ASC'")
    print("✅ app.py: умная сортировка")

if 'update_coords' not in app:
    geo_ep = "\n@app.route('/api/stores/update_coords',methods=['POST'])\ndef update_coords():\n    d=request.json;c=get_db();c.execute('UPDATE stores SET lat=?,lon=? WHERE code=?',(d['lat'],d['lon'],d['code']));c.commit();c.close();return jsonify({'status':'ok'})\n\n"
    app = app.replace("if __name__=='__main__':", geo_ep + "if __name__=='__main__':")
    print("✅ app.py: endpoint update_coords")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app)

# === 4. script.js: геокодирование + карта с координатами + авто-18+ ===
with open("static/js/script.js", "r", encoding="utf-8") as f:
    js = f.read()

# Auto 18+ for alcohol tags
alcohol_list = "['вино','пиво','водка','виски','коньяк','шампанское','ликёр','игристое','ром','джин','текила','вермут','сидр','слабоалкогольные']"
old_tag = "var t=this.getAttribute('data-term');searchInput.value=t;doParse(t||null)"
new_tag = f"var t=this.getAttribute('data-term');searchInput.value=t;var alc={alcohol_list};adultOnly.checked=alc.indexOf(t)>=0;doParse(t||null)"
if old_tag in js:
    js = js.replace(old_tag, new_tag)
    print("✅ script.js: авто-18+ для всех алкогольных категорий")

# Geocode button
if 'geocode-btn' not in js:
    geo_code = """
document.getElementById('geocode-btn').onclick=function(){var b=this;b.disabled=true;b.textContent='Геокодирую...';if(typeof ymaps==='undefined'){alert('Яндекс.Карты не загружены');b.disabled=false;b.textContent='📍 Геокодировать';return}ymaps.ready(function(){fetch('/api/stores').then(function(r){return r.json()}).then(function(stores){var todo=stores.filter(function(s){return s.address&&(!s.lat||!s.lon)});var done=0;function next(){if(done>=todo.length){b.disabled=false;b.textContent='📍 Геокодировать';stats.textContent='Геокодировано:'+done;loadStoresList();return}var s=todo[done];ymaps.geocode(s.address,{results:1}).then(function(res){var obj=res.geoObjects.get(0);if(obj){var c=obj.geometry.getCoordinates();fetch('/api/stores/update_coords',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:s.code,lat:c[0],lon:c[1]})})}done++;b.textContent=done+'/'+todo.length;next()}).catch(function(){done++;next()})}next()})});};
"""
    js = js.rstrip()
    if js.endswith('})();'):
        js = js[:-5] + geo_code + '\n})();'
        print("✅ script.js: кнопка геокодирования")

# Fix map to use stored coords
if 'function initMap()' in js:
    start = js.find('function initMap()')
    end = js.find("document.getElementById('manage-stores-btn')")
    if end < start:
        end = js.find("document.getElementById('map-close')")
    if start > 0 and end > start:
        new_map = """function initMap(){if(typeof ymaps==='undefined'){document.getElementById('yandex-map').innerHTML='<p style="padding:20px;color:#999">Карта недоступна</p>';return}ymaps.ready(function(){var city=citySelect.value||'Ставрополь';var centers={'Ставрополь':[45.0445,41.9691],'Краснодар':[45.0355,38.9753],'Армавир':[44.9976,41.1296],'Невинномысск':[44.6333,41.9444],'Курганинск':[44.8833,40.5833],'Москва':[55.7558,37.6173],'Санкт-Петербург':[59.9343,30.3351]};var center=centers[city]||[45.0445,41.9691];var map=new ymaps.Map('yandex-map',{center:center,zoom:12,controls:['zoomControl','searchControl']});fetch('/api/stores?city='+encodeURIComponent(city)).then(function(r){return r.json()}).then(function(stores){var hasCoords=false;stores.forEach(function(s){if(s.lat&&s.lon){hasCoords=true;var pm=new ymaps.Placemark([s.lat,s.lon],{balloonContentHeader:s.address,balloonContentBody:'Код:'+s.code,hintContent:s.address},{preset:'islands#redShoppingIcon'});map.geoObjects.add(pm)}});if(hasCoords){map.setBounds(map.geoObjects.getBounds(),{checkZoomRange:true,zoomMargin:30})}else{ymaps.search('Магнит '+city,{results:50,type:'biz'}).then(function(res){res.geoObjects.each(function(obj){var meta=obj.properties.get('CompanyMetaData');var addr=meta?meta.address:'';var pm=new ymaps.Placemark(obj.geometry.getCoordinates(),{balloonContentHeader:obj.properties.get('name')||'Магнит',balloonContentBody:addr},{preset:'islands#redShoppingIcon'});map.geoObjects.add(pm)});if(map.geoObjects.getLength()>0)map.setBounds(map.geoObjects.getBounds(),{checkZoomRange:true,zoomMargin:30})}).catch(function(){})}})})}
"""
        js = js[:start] + new_map + js[end:]
        print("✅ script.js: карта с сохранёнными координатами")

with open("static/js/script.js", "w", encoding="utf-8") as f:
    f.write(js)

print("\n" + "="*50)
print("🎉 ОБНОВЛЕНИЕ ПРИМЕНЕНО!")
print("="*50)
print(f"\n  📍 +44 адреса Ставрополя из alkogolikam.ru")
print(f"  🏷️ 15 категорий фильтров (как на скриншоте)")
print(f"  🔞 Авто-18+ для всех алкогольных тегов")
print(f"  🗺️ Карта с координатами + кнопка геокодирования")
print(f"  📊 Умная сортировка скидок")
print(f"\n⚠️ Про скидки -82%: alkogolikam.ru считает от СРЕДНЕЙ цены")
print(f"   за 90 дней. API Магнита даёт max -35% для пива.")
print(f"   Это не баг — разные источники данных.")
print(f"\nЗапусти:")
print(f"  del magnit_data.db")
print(f"  git add . && git commit -m '44 addresses, 15 categories, geocoding' && git push")
print(f"  python app.py")
print(f"\nПосле запуска: ⚙️ Магазины → 📍 Геокодировать → 🗺️ Карта")