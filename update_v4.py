"""
Update v4: бесконечная прокрутка, карта магазинов, выбор магазина, убран фильтр %
"""
import os, re

# ============================================================
# 1. HTML — новый интерфейс с картой и выбором магазина
# ============================================================
html_code = '''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Скидки Магнита</title>
    <link rel="stylesheet" href="/static/css/style.css?v=9">
</head>
<body>
    <header>
        <div class="header-top">
            <h1>🍷 Скидки Магнита</h1>
            <span class="subtitle" id="stats"></span>
        </div>
        <div class="controls-row">
            <select id="city-select"><option value="">Выберите город</option></select>
            <select id="store-select"><option value="all">Все магазины города</option></select>
            <button id="parse-btn" class="btn-primary">Загрузить скидки</button>
            <button id="map-btn" class="btn-secondary">🗺️ Карта</button>
            <button id="manage-stores-btn" class="btn-secondary">⚙️ Магазины</button>
        </div>
        <div class="controls-row">
            <input type="text" id="search-input" placeholder="Искать товары">
            <select id="sort-select">
                <option value="discount_desc">По скидке</option>
                <option value="savings_desc">По выгоде ₽</option>
                <option value="price_asc">Сначала дешевле</option>
                <option value="price_desc">Сначала дороже</option>
                <option value="stock_desc">По остатку</option>
            </select>
            <label class="checkbox-label"><input type="checkbox" id="adult-only"> Только 18+</label>
            <button id="favorites-btn">♡ Избранное</button>
        </div>
        <div class="quick-search">
            <button class="tag-btn active" data-term="">Всё</button>
            <button class="tag-btn" data-term="вино">Вино</button>
            <button class="tag-btn" data-term="пиво">Пиво</button>
            <button class="tag-btn" data-term="водка">Водка</button>
            <button class="tag-btn" data-term="виски">Виски</button>
            <button class="tag-btn" data-term="коньяк">Коньяк</button>
            <button class="tag-btn" data-term="шампанское">Игристое</button>
            <button class="tag-btn" data-term="ликёр">Ликёры</button>
            <button class="tag-btn" data-term="сыр">Сыр</button>
            <button class="tag-btn" data-term="кофе">Кофе</button>
        </div>
        <div id="progress-bar" class="progress-bar" style="display:none">
            <div class="progress-fill" id="progress-fill"></div>
            <span class="progress-text" id="progress-text"></span>
        </div>
    </header>
    <main>
        <div id="products-grid" class="products-grid"></div>
        <div id="load-more" class="load-more" style="display:none">Загрузка...</div>
        <div id="empty" class="empty">Выберите город и нажмите «Загрузить скидки»</div>
    </main>

    <!-- Модалка товара -->
    <div id="product-modal" class="modal" style="display:none">
        <div class="modal-content">
            <button class="modal-close" id="modal-close">✕</button>
            <div class="modal-body">
                <div class="modal-image"><img id="modal-img" src=""><div class="modal-badge" id="modal-badge"></div></div>
                <div class="modal-info">
                    <h2 id="modal-name"></h2>
                    <div class="modal-price"><span class="price-current" id="modal-price"></span> <span class="price-old" id="modal-old-price"></span></div>
                    <div class="modal-meta" id="modal-meta"></div>
                    <div class="modal-savings" id="modal-savings"></div>
                    <h3>Где купить</h3>
                    <div id="modal-stores" class="modal-stores"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Модалка карты -->
    <div id="map-modal" class="modal" style="display:none">
        <div class="modal-content modal-wide">
            <button class="modal-close" id="map-close">✕</button>
            <h2 style="margin-bottom:12px">🗺️ Магазины на карте</h2>
            <div id="yandex-map" style="width:100%;height:500px;border-radius:8px;"></div>
        </div>
    </div>

    <!-- Модалка управления магазинами -->
    <div id="stores-modal" class="modal" style="display:none">
        <div class="modal-content modal-wide">
            <button class="modal-close" id="stores-close">✕</button>
            <h2 style="margin-bottom:12px">Управление магазинами</h2>
            <div class="store-actions">
                <input type="text" id="new-code" placeholder="Код">
                <input type="text" id="new-address" placeholder="Адрес">
                <input type="text" id="new-city" placeholder="Город">
                <button id="add-store-btn" class="btn-primary">Добавить</button>
            </div>
            <div class="store-actions">
                <input type="number" id="scan-start" placeholder="От" value="992340">
                <input type="number" id="scan-end" placeholder="До" value="992400">
                <input type="text" id="scan-city" placeholder="Город">
                <button id="scan-btn" class="btn-secondary">📡 Сканировать</button>
                <button id="refresh-btn" class="btn-secondary">🔄 Обновить</button>
            </div>
            <div id="stores-list" class="stores-list"></div>
        </div>
    </div>

    <script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU" type="text/javascript"></script>
    <script src="/static/js/script.js?v=9"></script>
</body>
</html>'''

os.makedirs("templates", exist_ok=True)
with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(html_code)
print("✅ index.html: карта + выбор магазина + убран фильтр %")


# ============================================================
# 2. CSS — добавлены стили для infinite scroll и карты
# ============================================================
with open("static/css/style.css", "r", encoding="utf-8") as f:
    css = f.read()

# Add new styles
css += '''
.load-more{text-align:center;padding:20px;color:#999;font-size:13px}
.products-grid{grid-template-columns:repeat(5,1fr)}
@media(max-width:1200px){.products-grid{grid-template-columns:repeat(4,1fr)}}
@media(max-width:900px){.products-grid{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.products-grid{grid-template-columns:repeat(2,1fr)}}
#store-select{min-width:200px}
'''

with open("static/css/style.css", "w", encoding="utf-8") as f:
    f.write(css)
print("✅ style.css: стили для infinite scroll")


# ============================================================
# 3. JS — полная переработка: infinite scroll, карта, выбор магазина
# ============================================================
js_code = '''(function(){
"use strict";
var citySelect=document.getElementById('city-select'),
    storeSelect=document.getElementById('store-select'),
    searchInput=document.getElementById('search-input'),
    sortSelect=document.getElementById('sort-select'),
    adultOnly=document.getElementById('adult-only'),
    favBtn=document.getElementById('favorites-btn'),
    parseBtn=document.getElementById('parse-btn'),
    grid=document.getElementById('products-grid'),
    empty=document.getElementById('empty'),
    stats=document.getElementById('stats'),
    loadMore=document.getElementById('load-more'),
    progressBar=document.getElementById('progress-bar'),
    progressFill=document.getElementById('progress-fill'),
    progressText=document.getElementById('progress-text'),
    modal=document.getElementById('product-modal'),
    storesModal=document.getElementById('stores-modal'),
    mapModal=document.getElementById('map-modal');

var showFavorites=false, currentPage=1, totalPages=1, isLoading=false, eventSource=null;
var allStores=[];

// === Города и магазины ===
function loadCities(){
    fetch('/api/stores/cities').then(function(r){return r.json();}).then(function(cities){
        citySelect.innerHTML='<option value="">Выберите город</option>';
        cities.forEach(function(c){var o=document.createElement('option');o.value=c;o.textContent=c;citySelect.appendChild(o);});
        if(cities.indexOf('Ставрополь')>=0){citySelect.value='Ставрополь';loadStoresForCity();}
    });
}

function loadStoresForCity(){
    var city=citySelect.value;
    if(!city){storeSelect.innerHTML='<option value="all">Все магазины города</option>';return;}
    fetch('/api/stores?city='+encodeURIComponent(city)).then(function(r){return r.json();}).then(function(stores){
        allStores=stores;
        storeSelect.innerHTML='<option value="all">Все магазины города ('+stores.length+')</option>';
        stores.forEach(function(s){
            var o=document.createElement('option');o.value=s.code;
            o.textContent=s.address||('Магнит #'+s.code);
            storeSelect.appendChild(o);
        });
    });
}
citySelect.onchange=loadStoresForCity;
loadCities();

// === Прогресс ===
function startProgress(){
    progressBar.style.display='block';progressFill.style.width='0%';progressText.textContent='Загрузка...';
    if(eventSource)eventSource.close();
    eventSource=new EventSource('/api/progress');
    eventSource.onmessage=function(e){
        var d=JSON.parse(e.data);
        progressText.textContent=d.message;
        progressFill.style.width=d.total>0?Math.min(100,(d.current/d.total)*100)+'%':'50%';
        if(d.status==='done'||d.status==='error'){eventSource.close();setTimeout(function(){progressBar.style.display='none';},2000);}
    };
    eventSource.onerror=function(){if(eventSource)eventSource.close();};
}

// === Парсинг ===
function doParse(term){
    var city=citySelect.value;
    if(!city){alert('Выберите город');return;}
    parseBtn.disabled=true;parseBtn.textContent='Загрузка...';
    empty.style.display='none';grid.innerHTML='';
    startProgress();
    var body={city:city,max_items:1500};
    var storeCode=storeSelect.value;
    if(storeCode&&storeCode!=='all')body.store_code=storeCode;
    if(term)body.search=term;
    fetch('/api/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json();}).then(function(res){
        if(res.status==='success'){stats.textContent=res.count+' товаров · '+res.stores+' магазинов';currentPage=1;grid.innerHTML='';loadProducts();}
        else{stats.textContent='Ошибка: '+res.message;empty.style.display='block';empty.textContent=res.message;}
        parseBtn.disabled=false;parseBtn.textContent='Загрузить скидки';
    }).catch(function(e){stats.textContent='Ошибка: '+e.message;parseBtn.disabled=false;parseBtn.textContent='Загрузить скидки';});
}
parseBtn.onclick=function(){doParse(searchInput.value.trim()||null);};

// === Теги ===
var tagBtns=document.querySelectorAll('.tag-btn');
for(var i=0;i<tagBtns.length;i++){tagBtns[i].onclick=function(){
    for(var j=0;j<tagBtns.length;j++)tagBtns[j].classList.remove('active');
    this.classList.add('active');
    var term=this.getAttribute('data-term');searchInput.value=term;doParse(term||null);
};}

// === Infinite Scroll ===
function loadProducts(){
    if(isLoading)return;
    isLoading=true;
    loadMore.style.display='block';
    var p=new URLSearchParams();
    p.set('page',currentPage);p.set('per_page',60);p.set('sort',sortSelect.value);
    if(searchInput.value.trim())p.set('search',searchInput.value.trim());
    if(adultOnly.checked)p.set('adult_only','1');
    if(showFavorites)p.set('favorites','1');
    fetch('/api/products?'+p.toString()).then(function(r){return r.json();}).then(function(data){
        totalPages=data.pages;
        appendProducts(data.products);
        currentPage++;
        isLoading=false;
        loadMore.style.display=currentPage<=totalPages?'block':'none';
        if(!grid.children.length){empty.style.display='block';empty.textContent=showFavorites?'В избранном пусто':'Нет товаров';}
        else{empty.style.display='none';}
    }).catch(function(){isLoading=false;loadMore.style.display='none';});
}

function appendProducts(products){
    products.forEach(function(p){
        var card=document.createElement('div');card.className='product-card';
        var img=p.image_url?'<img src="'+p.image_url+'" loading="lazy" onerror="this.style.display=\\\'none\\\'">':'';
        var vol=p.volume?p.volume+(p.price_per_liter?' · '+p.price_per_liter+' ₽/л':''):'';
        var addr='';
        try{var sd=JSON.parse(p.store_code);if(Array.isArray(sd)&&sd.length)addr=sd[0].address||'';}catch(e){}
        var badge=p.discount_percent>0?'−'+p.discount_percent+'%':'Акция';
        card.innerHTML='<div class="card-store">Магнит</div>'+
            '<span class="'+(p.is_favorite?'fav-btn active':'fav-btn')+'" data-id="'+p.magnit_id+'">'+(p.is_favorite?'♥':'♡')+'</span>'+
            img+'<h3>'+p.name+'</h3>'+
            '<div class="price-row"><span class="price-current">'+formatPrice(p.price)+'</span><span class="price-old">'+formatPrice(p.old_price)+'</span></div>'+
            (vol?'<div class="card-meta">'+vol+'</div>':'')+
            (addr?'<div class="card-address">'+addr+'</div>':'')+