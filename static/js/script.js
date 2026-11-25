(function() {
    "use strict";
    var citySelect = document.getElementById('city-select');
    var storeSelect = document.getElementById('store-select');
    var allCityCheck = document.getElementById('all-city');
    var searchInput = document.getElementById('search-input');
    var sortSelect = document.getElementById('sort-select');
    var discountFilter = document.getElementById('discount-filter');
    var stockFilter = document.getElementById('stock-filter');
    var adultOnly = document.getElementById('adult-only');
    var favBtn = document.getElementById('favorites-btn');
    var parseBtn = document.getElementById('parse-btn');
    var grid = document.getElementById('products-grid');
    var loading = document.getElementById('loading');
    var empty = document.getElementById('empty');
    var stats = document.getElementById('stats');
    var pagination = document.getElementById('pagination');
    var progressBar = document.getElementById('progress-bar');
    var progressFill = document.getElementById('progress-fill');
    var progressText = document.getElementById('progress-text');
    var modal = document.getElementById('product-modal');

    var showFavorites = false;
    var currentPage = 1;
    var currentTerm = '';
    var eventSource = null;

    // === Города и магазины ===
    function loadCities() {
        fetch('/api/stores/cities').then(function(r){return r.json();}).then(function(cities) {
            citySelect.innerHTML = '<option value="">Все города</option>';
            cities.forEach(function(c) {
                var opt = document.createElement('option');
                opt.value = c; opt.textContent = c;
                citySelect.appendChild(opt);
            });
            // Выбираем Ставрополь по умолчанию если есть
            if (cities.indexOf('Ставрополь') >= 0) {
                citySelect.value = 'Ставрополь';
            }
            loadStores();
        });
    }

    function loadStores() {
        var city = citySelect.value;
        var url = '/api/stores' + (city ? '?city=' + encodeURIComponent(city) : '');
        fetch(url).then(function(r){return r.json();}).then(function(stores) {
            storeSelect.innerHTML = '<option value="">Выберите магазин</option>';
            stores.forEach(function(s) {
                var opt = document.createElement('option');
                opt.value = s.code;
                opt.textContent = s.address + ' (' + s.code + ')';
                storeSelect.appendChild(opt);
            });
            if (stores.length > 0) storeSelect.value = stores[0].code;
        });
    }

    citySelect.onchange = loadStores;
    loadCities();

    // === Прогресс через SSE ===
    function startProgress() {
        progressBar.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = 'Начинаем загрузку...';
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/progress');
        eventSource.onmessage = function(e) {
            var data = JSON.parse(e.data);
            progressText.textContent = data.message + ' (' + data.current + ' товаров)';
            if (data.total > 0) {
                progressFill.style.width = Math.min(100, (data.current / Math.max(data.total, 1)) * 100) + '%';
            } else {
                progressFill.style.width = '50%';
            }
            if (data.status === 'done' || data.status === 'error') {
                eventSource.close();
                setTimeout(function() { progressBar.style.display = 'none'; }, 2000);
            }
        };
        eventSource.onerror = function() { if(eventSource) eventSource.close(); };
    }

    // === Парсинг ===
    function doParse(term) {
        var storeCode = storeSelect.value;
        var city = citySelect.value;
        var allCity = allCityCheck.checked;

        if (!storeCode && !allCity) { alert('Выберите магазин или включите «Все магазины города»'); return; }

        parseBtn.disabled = true;
        parseBtn.textContent = '⏳ Загрузка...';
        loading.style.display = 'block';
        empty.style.display = 'none';
        grid.innerHTML = '';
        pagination.innerHTML = '';
        startProgress();

        var body = { max_items: 3000, all_city: allCity, city: city };
        if (storeCode) body.store_code = storeCode;
        if (term) body.search = term;

        fetch('/api/parse', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(body)
        }).then(function(r){return r.json();}).then(function(res) {
            if (res.status === 'success') {
                stats.textContent = '✅ ' + res.count + ' товаров из ' + res.stores + ' магазинов';
                currentPage = 1;
                loadProducts();
            } else {
                stats.textContent = '❌ ' + res.message;
                empty.style.display = 'block';
                empty.textContent = res.message;
            }
            loading.style.display = 'none';
            parseBtn.disabled = false;
            parseBtn.textContent = '🔄 Загрузить скидки';
        }).catch(function(e) {
            stats.textContent = '❌ ' + e.message;
            loading.style.display = 'none';
            parseBtn.disabled = false;
            parseBtn.textContent = '🔄 Загрузить скидки';
        });
    }

    parseBtn.onclick = function() { doParse(searchInput.value.trim() || null); };

    // === Теги быстрого поиска — запускают НОВЫЙ парсинг ===
    var tagBtns = document.querySelectorAll('.tag-btn');
    for (var i = 0; i < tagBtns.length; i++) {
        tagBtns[i].onclick = function() {
            for (var j = 0; j < tagBtns.length; j++) tagBtns[j].classList.remove('active');
            this.classList.add('active');
            currentTerm = this.getAttribute('data-term');
            searchInput.value = currentTerm;
            doParse(currentTerm || null);
        };
    }

    // === Загрузка товаров из БД ===
    function loadProducts() {
        var params = new URLSearchParams();
        params.set('page', currentPage);
        params.set('per_page', 30);
        params.set('sort', sortSelect.value);
        if (discountFilter.value > 0) params.set('min_discount', discountFilter.value);
        if (stockFilter.value > 0) params.set('min_stock', stockFilter.value);
        if (searchInput.value.trim()) params.set('search', searchInput.value.trim());
        if (adultOnly.checked) params.set('adult_only', '1');
        if (showFavorites) params.set('favorites', '1');

        fetch('/api/products?' + params.toString()).then(function(r){return r.json();}).then(function(data) {
            renderProducts(data.products);
            renderPagination(data.page, data.pages, data.total);
            if (!stats.textContent.startsWith('✅')) stats.textContent = data.total + ' товаров';
        });
    }

    function renderProducts(products) {
        grid.innerHTML = '';
        if (!products.length) {
            empty.style.display = 'block';
            empty.textContent = showFavorites ? 'В избранном пусто' : 'Нет товаров. Нажмите «Загрузить скидки»';
            pagination.innerHTML = '';
            return;
        }
        empty.style.display = 'none';

        products.forEach(function(p) {
            var card = document.createElement('div');
            card.className = 'product-card';
            var stockClass = p.stock <= 5 ? 'stock low' : 'stock';
            var imgHtml = p.image_url ? '<img src="' + p.image_url + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">' : '';
            var adultHtml = p.is_adult ? '<span class="adult-badge">18+</span>' : '';
            var volHtml = p.volume ? '<div class="price-per-liter">' + p.volume + (p.price_per_liter ? ' · ' + p.price_per_liter + ' ₽/л' : '') + '</div>' : '';
            var savingsHtml = p.savings > 0 ? '<span class="savings-badge">-' + Math.round(p.savings) + '₽</span>' : '';
            
            // Store count from JSON
            var storeCount = 1;
            try { var sd = JSON.parse(p.store_code); if (Array.isArray(sd)) storeCount = sd.length; } catch(e) {}
            var storeInfo = storeCount > 1 ? '<span class="store-count">' + storeCount + ' маг.</span>' : '';

            card.innerHTML = '<div class="discount-badge">−' + p.discount_percent + '%</div>' + savingsHtml + adultHtml +
                '<span class="' + (p.is_favorite ? 'fav-btn active' : 'fav-btn') + '" data-id="' + p.magnit_id + '">' + (p.is_favorite ? '⭐' : '☆') + '</span>' +
                imgHtml + '<h3>' + p.name + '</h3>' +
                '<div class="price-row"><span class="price-current">' + p.price.toFixed(2) + ' ₽</span><span class="price-old">' + p.old_price.toFixed(2) + ' ₽</span></div>' +
                volHtml +
                '<div class="card-footer"><span class="' + stockClass + '">Остаток: ' + p.stock + ' шт</span>' + storeInfo + '</div>';
            
            // Клик по карточке — открыть детали
            card.onclick = function(e) {
                if (e.target.classList.contains('fav-btn')) return;
                openProductModal(p);
            };
            grid.appendChild(card);
        });

        // Избранное
        var btns = grid.querySelectorAll('.fav-btn');
        for (var i = 0; i < btns.length; i++) {
            (function(btn) {
                btn.onclick = function(e) {
                    e.stopPropagation();
                    var id = btn.getAttribute('data-id');
                    var active = btn.classList.contains('active');
                    fetch(active ? '/api/favorites/remove' : '/api/favorites/add', {
                        method:'POST', headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({product_id: id})
                    }).then(function() {
                        btn.classList.toggle('active');
                        btn.textContent = active ? '☆' : '⭐';
                        if (showFavorites) loadProducts();
                    });
                };
            })(btns[i]);
        }
    }

    // === Модальное окно товара ===
    function openProductModal(p) {
        document.getElementById('modal-img').src = p.image_url || '';
        document.getElementById('modal-badge').textContent = '−' + p.discount_percent + '%';
        document.getElementById('modal-name').textContent = p.name;
        document.getElementById('modal-price').textContent = p.price.toFixed(2) + ' ₽';
        document.getElementById('modal-old-price').textContent = p.old_price.toFixed(2) + ' ₽';
        
        var meta = [];
        if (p.volume) meta.push(p.volume);
        if (p.price_per_liter) meta.push(p.price_per_liter + ' ₽/л');
        if (p.is_adult) meta.push('18+');
        document.getElementById('modal-meta').textContent = meta.join(' · ');
        document.getElementById('modal-savings').textContent = 'Выгода: ' + Math.round(p.savings) + ' ₽';

        // Загружаем магазины
        var storesDiv = document.getElementById('modal-stores');
        storesDiv.innerHTML = '<div style="color:#888">Загрузка...</div>';
        
        var city = citySelect.value;
        fetch('/api/product/' + p.magnit_id + '/stores?city=' + encodeURIComponent(city))
        .then(function(r){return r.json();}).then(function(data) {
            storesDiv.innerHTML = '';
            var stores = data.stores || [];
            if (!stores.length) {
                storesDiv.innerHTML = '<div style="color:#888">Данные по магазинам недоступны. Загрузите скидки с включённым «Все магазины города»</div>';
                return;
            }
            stores.sort(function(a,b){ return a.price - b.price; });
            stores.forEach(function(s, idx) {
                var row = document.createElement('div');
                row.className = 'store-row' + (idx === 0 ? ' best' : '');
                row.innerHTML = '<span class="store-addr">' + (s.address || s.code) + '</span>' +
                    '<span class="store-stock">' + s.stock + ' шт</span>' +
                    '<span class="store-price">' + s.price.toFixed(2) + ' ₽</span>';
                storesDiv.appendChild(row);
            });
        });

        modal.style.display = 'flex';
    }

    document.getElementById('modal-close').onclick = function() { modal.style.display = 'none'; };
    modal.onclick = function(e) { if (e.target === modal) modal.style.display = 'none'; };

    // === Пагинация ===
    function renderPagination(page, pages, total) {
        pagination.innerHTML = '';
        if (pages <= 1) return;
        var start = Math.max(1, page - 3), end = Math.min(pages, page + 3);
        if (start > 1) { addPageBtn(1, page); if (start > 2) addDots(); }
        for (var i = start; i <= end; i++) addPageBtn(i, page);
        if (end < pages) { if (end < pages-1) addDots(); addPageBtn(pages, page); }
    }
    function addPageBtn(n, cur) {
        var b = document.createElement('button');
        b.textContent = n;
        if (n === cur) b.className = 'active';
        b.onclick = function() { currentPage = n; loadProducts(); window.scrollTo(0,0); };
        pagination.appendChild(b);
    }
    function addDots() { var s = document.createElement('span'); s.textContent = '...'; s.style.color = '#666'; pagination.appendChild(s); }

    // === Фильтры ===
    sortSelect.onchange = function() { currentPage = 1; loadProducts(); };
    discountFilter.onchange = function() { currentPage = 1; loadProducts(); };
    stockFilter.onchange = function() { currentPage = 1; loadProducts(); };
    adultOnly.onchange = function() { currentPage = 1; loadProducts(); };
    searchInput.onkeydown = function(e) { if (e.key === 'Enter') { currentPage = 1; loadProducts(); } };
    favBtn.onclick = function() {
        showFavorites = !showFavorites;
        favBtn.classList.toggle('active');
        favBtn.textContent = showFavorites ? '📋 Все' : '⭐ Избранное';
        currentPage = 1; loadProducts();
    };
})();