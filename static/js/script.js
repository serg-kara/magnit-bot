(function(){
"use strict";
var citySelect=document.getElementById('city-select'),
    searchInput=document.getElementById('search-input'),
    sortSelect=document.getElementById('sort-select'),
    discountFilter=document.getElementById('discount-filter'),
    adultOnly=document.getElementById('adult-only'),
    favBtn=document.getElementById('favorites-btn'),
    parseBtn=document.getElementById('parse-btn'),
    grid=document.getElementById('products-grid'),
    empty=document.getElementById('empty'),
    stats=document.getElementById('stats'),
    pagination=document.getElementById('pagination'),
    progressBar=document.getElementById('progress-bar'),
    progressFill=document.getElementById('progress-fill'),
    progressText=document.getElementById('progress-text'),
    modal=document.getElementById('product-modal'),
    storesModal=document.getElementById('stores-modal');
var showFavorites=false,currentPage=1,eventSource=null;

function loadCities(){
    fetch('/api/stores/cities').then(function(r){return r.json();}).then(function(cities){
        citySelect.innerHTML='<option value="">Выберите город</option>';
        cities.forEach(function(c){var o=document.createElement('option');o.value=c;o.textContent=c;citySelect.appendChild(o);});
        if(cities.indexOf('Ставрополь')>=0)citySelect.value='Ставрополь';
    });
}
loadCities();

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

function doParse(term){
    var city=citySelect.value;
    if(!city){alert('Выберите город');return;}
    parseBtn.disabled=true;parseBtn.textContent='Загрузка...';
    empty.style.display='none';grid.innerHTML='';pagination.innerHTML='';
    startProgress();
    var body={city:city,max_items:1000};
    if(term)body.search=term;
    fetch('/api/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
    .then(function(r){return r.json();}).then(function(res){
        if(res.status==='success'){stats.textContent=res.count+' товаров · '+res.stores+' магазинов';currentPage=1;loadProducts();}
        else{stats.textContent='Ошибка: '+res.message;empty.style.display='block';empty.textContent=res.message;}
        parseBtn.disabled=false;parseBtn.textContent='Загрузить скидки';
    }).catch(function(e){stats.textContent='Ошибка: '+e.message;parseBtn.disabled=false;parseBtn.textContent='Загрузить скидки';});
}
parseBtn.onclick=function(){doParse(searchInput.value.trim()||null);};

var tagBtns=document.querySelectorAll('.tag-btn');
for(var i=0;i<tagBtns.length;i++){tagBtns[i].onclick=function(){
    for(var j=0;j<tagBtns.length;j++)tagBtns[j].classList.remove('active');
    this.classList.add('active');
    var term=this.getAttribute('data-term');searchInput.value=term;doParse(term||null);
};}

function loadProducts(){
    var p=new URLSearchParams();
    p.set('page',currentPage);p.set('per_page',30);p.set('sort',sortSelect.value);
    if(discountFilter.value>0)p.set('min_discount',discountFilter.value);
    if(searchInput.value.trim())p.set('search',searchInput.value.trim());
    if(adultOnly.checked)p.set('adult_only','1');
    if(showFavorites)p.set('favorites','1');
    fetch('/api/products?'+p.toString()).then(function(r){return r.json();}).then(function(data){
        renderProducts(data.products);renderPagination(data.page,data.pages);
        if(!stats.textContent.includes('товаров'))stats.textContent=data.total+' товаров';
    });
}

function renderProducts(products){
    grid.innerHTML='';
    if(!products.length){empty.style.display='block';empty.textContent=showFavorites?'В избранном пусто':'Нет товаров. Нажмите «Загрузить скидки»';pagination.innerHTML='';return;}
    empty.style.display='none';
    products.forEach(function(p){
        var card=document.createElement('div');card.className='product-card';
        var img=p.image_url?'<img src="'+p.image_url+'" loading="lazy" onerror="this.style.display=\'none\'">':'';
        var vol=p.volume?p.volume+(p.price_per_liter?' · '+p.price_per_liter+' ₽/л':''):'';
        // Get best store address
        var addr='';
        try{var sd=JSON.parse(p.store_code);if(Array.isArray(sd)&&sd.length)addr=sd[0].address||'';}catch(e){}
        card.innerHTML='<div class="card-store">Магнит</div>'+
            '<span class="'+(p.is_favorite?'fav-btn active':'fav-btn')+'" data-id="'+p.magnit_id+'">'+(p.is_favorite?'♥':'♡')+'</span>'+
            img+'<h3>'+p.name+'</h3>'+
            '<div class="price-row"><span class="price-current">'+formatPrice(p.price)+'</span><span class="price-old">'+formatPrice(p.old_price)+'</span></div>'+
            (vol?'<div class="card-meta">'+vol+'</div>':'')+
            (addr?'<div class="card-address">'+addr+'</div>':'')+
            '<div class="discount-badge">−'+p.discount_percent+'%</div>';
        card.onclick=function(e){if(e.target.classList.contains('fav-btn'))return;openModal(p);};
        grid.appendChild(card);
    });
    var btns=grid.querySelectorAll('.fav-btn');
    for(var i=0;i<btns.length;i++){(function(b){b.onclick=function(e){e.stopPropagation();
        var id=b.getAttribute('data-id'),a=b.classList.contains('active');
        fetch(a?'/api/favorites/remove':'/api/favorites/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id})})
        .then(function(){b.classList.toggle('active');b.textContent=a?'♡':'♥';if(showFavorites)loadProducts();});
    };})(btns[i]);}
}

function formatPrice(v){
    var parts=v.toFixed(2).split('.');
    return parts[0]+'<sup>'+parts[1]+'</sup> ₽';
}

function openModal(p){
    document.getElementById('modal-img').src=p.image_url||'';
    document.getElementById('modal-badge').textContent='−'+p.discount_percent+'%';
    document.getElementById('modal-name').textContent=p.name;
    document.getElementById('modal-price').innerHTML=formatPrice(p.price);
    document.getElementById('modal-old-price').innerHTML=formatPrice(p.old_price);
    var meta=[];if(p.volume)meta.push(p.volume);if(p.price_per_liter)meta.push(p.price_per_liter+' ₽/л');if(p.is_adult)meta.push('18+');
    document.getElementById('modal-meta').textContent=meta.join(' · ');
    document.getElementById('modal-savings').textContent='Выгода '+Math.round(p.savings)+' ₽';
    var sd=document.getElementById('modal-stores');sd.innerHTML='';
    try{
        var stores=JSON.parse(p.store_code);
        if(Array.isArray(stores)&&stores.length){
            stores.forEach(function(s,idx){
                var row=document.createElement('div');row.className='store-row'+(idx===0?' best':'');
                row.innerHTML='<span class="store-addr">'+(s.address||s.code)+'</span><span class="store-stock">'+s.stock+' шт</span><span class="store-price">'+s.price.toFixed(2)+' ₽</span>';
                sd.appendChild(row);
            });
        }else{sd.innerHTML='<div style="color:#999">Загрузите скидки для данных по магазинам</div>';}
    }catch(e){sd.innerHTML='<div style="color:#999">Нет данных</div>';}
    modal.style.display='flex';
}
document.getElementById('modal-close').onclick=function(){modal.style.display='none';};
modal.onclick=function(e){if(e.target===modal)modal.style.display='none';};

function renderPagination(page,pages){
    pagination.innerHTML='';if(pages<=1)return;
    var s=Math.max(1,page-3),e=Math.min(pages,page+3);
    if(s>1){addPB(1,page);if(s>2)addDots();}
    for(var i=s;i<=e;i++)addPB(i,page);
    if(e<pages){if(e<pages-1)addDots();addPB(pages,page);}
}
function addPB(n,c){var b=document.createElement('button');b.textContent=n;if(n===c)b.className='active';b.onclick=function(){currentPage=n;loadProducts();window.scrollTo(0,0);};pagination.appendChild(b);}
function addDots(){var s=document.createElement('span');s.textContent='…';s.style.color='#999';pagination.appendChild(s);}

sortSelect.onchange=function(){currentPage=1;loadProducts();};
discountFilter.onchange=function(){currentPage=1;loadProducts();};
adultOnly.onchange=function(){currentPage=1;loadProducts();};
searchInput.onkeydown=function(e){if(e.key==='Enter'){currentPage=1;loadProducts();}};
favBtn.onclick=function(){showFavorites=!showFavorites;favBtn.classList.toggle('active');favBtn.textContent=showFavorites?'Все товары':'♡ Избранное';currentPage=1;loadProducts();};

// Store management
document.getElementById('manage-stores-btn').onclick=function(){loadStoresList();storesModal.style.display='flex';};
document.getElementById('stores-close').onclick=function(){storesModal.style.display='none';loadCities();};
storesModal.onclick=function(e){if(e.target===storesModal){storesModal.style.display='none';loadCities();}};

function loadStoresList(){
    fetch('/api/stores').then(function(r){return r.json();}).then(function(stores){
        var list=document.getElementById('stores-list');list.innerHTML='';
        stores.forEach(function(s){
            var div=document.createElement('div');div.className='store-item';
            div.innerHTML='<span><b>'+s.city+'</b> · '+s.address+' <small style="color:#999">('+s.code+')</small></span><button class="btn-secondary" data-code="'+s.code+'">✕</button>';
            div.querySelector('button').onclick=function(){fetch('/api/stores/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:s.code})}).then(loadStoresList);};
            list.appendChild(div);
        });
    });
}
document.getElementById('add-store-btn').onclick=function(){
    var code=document.getElementById('new-code').value.trim(),address=document.getElementById('new-address').value.trim(),city=document.getElementById('new-city').value.trim();
    if(!code||!city){alert('Укажите код и город');return;}
    fetch('/api/stores/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:code,address:address,city:city})}).then(function(){document.getElementById('new-code').value='';document.getElementById('new-address').value='';loadStoresList();});
};
document.getElementById('scan-btn').onclick=function(){
    var start=parseInt(document.getElementById('scan-start').value),end=parseInt(document.getElementById('scan-end').value),city=document.getElementById('scan-city').value.trim()||'Новые';
    var btn=this;btn.disabled=true;btn.textContent='Сканирую...';startProgress();
    fetch('/api/stores/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start:start,end:end,city:city})})
    .then(function(r){return r.json();}).then(function(res){btn.disabled=false;btn.textContent='📡 Сканировать';if(res.count!==undefined){stats.textContent='Найдено '+res.count;loadStoresList();}}).catch(function(){btn.disabled=false;btn.textContent='📡 Сканировать';});
};
document.getElementById('refresh-btn').onclick=function(){
    var btn=this;btn.disabled=true;btn.textContent='Обновляю...';startProgress();
    fetch('/api/stores/refresh',{method:'POST'}).then(function(r){return r.json();}).then(function(res){btn.disabled=false;btn.textContent='🔄 Обновить';stats.textContent='Обновлено: '+(res.updated||0);loadStoresList();}).catch(function(){btn.disabled=false;btn.textContent='🔄 Обновить';});
};
})();