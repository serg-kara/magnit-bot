"""
ФИНАЛЬНОЕ ОБНОВЛЕНИЕ — полностью перезаписывает все файлы.
Запуск: python final_update.py
После: del magnit_data.db && git add . && git commit -m "final" && git push && python app.py
"""
import os

os.makedirs("templates", exist_ok=True)
os.makedirs("static/js", exist_ok=True)
os.makedirs("static/css", exist_ok=True)

# ==================== parser.py ====================
open("parser.py","w",encoding="utf-8").write('''import requests,re,logging,urllib3,time
from concurrent.futures import ThreadPoolExecutor,as_completed
urllib3.disable_warnings()
logging.basicConfig(level=logging.INFO)
API_BASE="https://middle-api.magnit.ru"
HEADERS={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"application/json","Origin":"https://magnit.ru","Referer":"https://magnit.ru/"}
DEFAULT_STORES=[
{"code":"992301","address":"Краснодар, ул. Дзержинского, 42","city":"Краснодар"},
{"code":"990101","address":"Краснодарский край","city":"Краснодар"},
{"code":"990102","address":"Краснодарский край","city":"Краснодар"},
{"code":"991002","address":"Ставрополь, ул. Доваторцев, 64","city":"Ставрополь"},
{"code":"991003","address":"Ставрополь, ул. Лермонтова, 259","city":"Ставрополь"},
{"code":"991004","address":"Ставрополь, ул. Краснофлотская, 91","city":"Ставрополь"},
{"code":"991102","address":"Ставрополь, ул. Тухачевского, 22/1","city":"Ставрополь"},
{"code":"991201","address":"Ставрополь, ул. Ленина, 440","city":"Ставрополь"},
{"code":"991301","address":"Ставрополь, пр-кт К.Маркса, 47/30","city":"Ставрополь"},
{"code":"991303","address":"Ставрополь, ул. Пирогова, 8","city":"Ставрополь"},
{"code":"991501","address":"Ставрополь, ул. Трунова, 134В","city":"Ставрополь"},
{"code":"992326","address":"Ставрополь, ул. Чапаева, 25","city":"Ставрополь"},
{"code":"992330","address":"Ставрополь, ул. Рогожникова, 90","city":"Ставрополь"},
{"code":"992334","address":"Ставрополь, пр-кт Кулакова, 29Д","city":"Ставрополь"},
{"code":"997101","address":"Ставрополь, ул. 50 лет ВЛКСМ, 28а","city":"Ставрополь"},
{"code":"997201","address":"Ставрополь, Фестивальный проезд, 7","city":"Ставрополь"},
{"code":"992323","address":"Армавир","city":"Армавир"},
{"code":"995101","address":"Невинномысск","city":"Невинномысск"},
{"code":"992336","address":"Курганинск","city":"Курганинск"},
{"code":"992338","address":"Будённовск","city":"Будённовск"},
{"code":"777885","address":"Москва","city":"Москва"},
{"code":"699422","address":"Санкт-Петербург","city":"Санкт-Петербург"},
]
def extract_volume(name):
    m=re.search(r'(\\d+(?:[.,]\\d+)?)\\s*(мл|л|г|кг|шт)',name,re.IGNORECASE)
    return (float(m.group(1).replace(',','.')),m.group(2).lower()) if m else (None,None)
def calc_price_per_liter(price,name):
    v,u=extract_volume(name)
    if not v:return 0
    if u=='мл':return round(price/(v/1000),2)
    if u=='л':return round(price/v,2)
    return 0
def search_cities(query):
    try:
        r=requests.get(f"{API_BASE}/v1/cities",headers=HEADERS,params={"query":query,"limit":20},timeout=15,verify=False)
        return r.json().get("data",[])
    except:return []
def check_store_code(code):
    try:
        r=requests.post(f"{API_BASE}/v2/goods/search",headers=HEADERS,json={"storeCode":str(code),"storeType":"1","cityId":"1","catalogType":"1","includeAdultGoods":True,"pagination":{"offset":0,"limit":1},"sort":{"order":"desc","type":"discount"}},timeout=4,verify=False)
        return r.json().get("pagination",{}).get("totalCount",0)
    except:return 0
def scan_range(start,end):
    found=[]
    for code in range(start,end):
        t=check_store_code(code)
        if t>0:found.append({"code":str(code),"total":t})
    return found
def fetch_products_page(store_code,offset=0,limit=50,term=None):
    payload={"storeCode":str(store_code),"storeType":"1","cityId":"1","catalogType":"1","includeAdultGoods":True,"pagination":{"offset":offset,"limit":limit},"sort":{"order":"desc","type":"discount"}}
    if term:payload["term"]=term
    try:
        r=requests.post(f"{API_BASE}/v2/goods/search",headers=HEADERS,json=payload,timeout=15,verify=False)
        r.raise_for_status();data=r.json()
    except Exception as e:
        logging.error(f"fetch {store_code} off={offset}: {e}");return [],False,0
    items=data.get("items",[]);pag=data.get("pagination",{});products=[]
    for item in items:
        promo=item.get("promotion") or {}
        if not promo.get("isPromotion"):continue
        price=item.get("price",0)/100;old_price=(promo.get("oldPrice") or 0)/100
        discount=promo.get("discountPercent") or 0
        if discount==0 and old_price>price and old_price>0:discount=round((1-price/old_price)*100)
        stock=item.get("quantity") or 0;name=item.get("name","")
        gallery=item.get("gallery") or [];image=gallery[0].get("url","") if gallery else ""
        v,u=extract_volume(name);vol=f"{v:g} {u}" if v else ""
        products.append({"id":str(item.get("id","")),"name":name,"price":price,"old_price":old_price,"discount_percent":discount,"savings":round(old_price-price,2) if old_price>price else 0,"image":image,"stock":stock,"is_adult":1 if item.get("isForAdults") else 0,"volume":vol,"price_per_liter":calc_price_per_liter(price,name),"store_code":str(store_code)})
    return products,pag.get("hasMore",False),pag.get("totalCount",0)
def parse_store_progressive(store_code,max_items=2000,term=None):
    all_p=[];offset=0;seen=set()
    while len(all_p)<max_items:
        prods,more,total=fetch_products_page(store_code,offset=offset,term=term)
        for p in prods:
            if p["id"] not in seen:seen.add(p["id"]);all_p.append(p)
        if not more or not prods or offset>=10000:break
        offset+=50
    return all_p
def parse_stores_parallel(codes_addr,max_items=1000,term=None,progress_callback=None):
    all_products={}
    def parse_one(ca):
        code,addr=ca;prods=parse_store_progressive(code,max_items=max_items,term=term);return code,addr,prods
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(parse_one,ca):ca for ca in codes_addr};done=0
        for f in as_completed(futs):
            code,addr,prods=f.result();done+=1
            if progress_callback:progress_callback(done,len(codes_addr),len(all_products))
            for p in prods:
                pid=p["id"]
                if pid not in all_products:all_products[pid]={**p,"stores":[]}
                all_products[pid]["stores"].append({"code":code,"address":addr,"stock":p["stock"],"price":p["price"],"discount_percent":p["discount_percent"]})
                if p["price"]<all_products[pid]["price"]:
                    all_products[pid]["price"]=p["price"];all_products[pid]["discount_percent"]=p["discount_percent"];all_products[pid]["savings"]=p["savings"]
                all_products[pid]["stock"]+=p["stock"]
    result=list(all_products.values())
    for p in result:p["stores"].sort(key=lambda x:x["price"])
    return result
''')
print("✅ parser.py")

# ==================== app.py ====================
open("app.py","w",encoding="utf-8").write('''from flask import Flask,render_template,request,jsonify,Response
import sqlite3,traceback,json,time
from datetime import datetime
from parser import search_cities,check_store_code,parse_store_progressive,parse_stores_parallel,scan_range,DEFAULT_STORES
app=Flask(__name__);DB_NAME="magnit_data.db"
parse_progress={"current":0,"total":0,"status":"idle","message":""}
@app.after_request
def nc(resp):
    if 'static' in request.path:resp.headers['Cache-Control']='no-store'
    return resp
def get_db():
    c=sqlite3.connect(DB_NAME);c.row_factory=sqlite3.Row;return c
def init_db():
    c=get_db()
    c.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT,magnit_id TEXT UNIQUE,name TEXT,price REAL,old_price REAL,discount_percent INTEGER,savings REAL,store_code TEXT,image_url TEXT,stock INTEGER DEFAULT 0,is_adult INTEGER DEFAULT 0,volume TEXT,price_per_liter REAL,updated_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS favorites(product_id TEXT PRIMARY KEY,added_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS stores(code TEXT PRIMARY KEY,address TEXT,city TEXT,products_count INTEGER DEFAULT 0,lat REAL,lon REAL,added_at TEXT)")
    for col,td in [("products_count","INTEGER DEFAULT 0"),("lat","REAL"),("lon","REAL")]:
        try:c.execute(f"ALTER TABLE stores ADD COLUMN {col} {td}")
        except:pass
    for s in DEFAULT_STORES:c.execute("INSERT OR IGNORE INTO stores(code,address,city,added_at)VALUES(?,?,?,?)",(s['code'],s['address'],s['city'],datetime.now().isoformat()))
    c.commit();c.close()
@app.route('/')
def index():return render_template('index.html')
@app.route('/api/cities')
def api_cities():
    q=request.args.get('q','')
    return jsonify(search_cities(q) if len(q)>=2 else [])
@app.route('/api/stores')
def api_stores():
    city=request.args.get('city','');c=get_db()
    rows=c.execute("SELECT * FROM stores WHERE city=? ORDER BY address",(city,)).fetchall() if city else c.execute("SELECT * FROM stores ORDER BY city,address").fetchall()
    c.close();return jsonify([dict(r) for r in rows])
@app.route('/api/stores/cities')
def api_cities_list():
    c=get_db();rows=c.execute("SELECT DISTINCT city FROM stores ORDER BY city").fetchall();c.close();return jsonify([r[0] for r in rows])
@app.route('/api/stores/save',methods=['POST'])
def save_store():
    d=request.json;c=get_db();c.execute("INSERT OR REPLACE INTO stores(code,address,city,added_at)VALUES(?,?,?,?)",(d['code'],d.get('address',''),d.get('city',''),datetime.now().isoformat()));c.commit();c.close();return jsonify({'status':'ok'})
@app.route('/api/stores/delete',methods=['POST'])
def del_store():
    c=get_db();c.execute("DELETE FROM stores WHERE code=?",(request.json.get('code',''),));c.commit();c.close();return jsonify({'status':'ok'})
@app.route('/api/stores/scan',methods=['POST'])
def scan_stores():
    global parse_progress
    try:
        d=request.json or {};start=int(d.get('start',992300));end=int(d.get('end',992350));city=d.get('city','Новые')
        if end-start>100:end=start+100
        parse_progress={"current":0,"total":end-start,"status":"scanning","message":f"Скан {start}-{end}..."}
        found=scan_range(start,end);c=get_db()
        for s in found:c.execute("INSERT OR IGNORE INTO stores(code,address,city,added_at)VALUES(?,?,?,?)",(s['code'],f"Магнит #{s['code']}",city,datetime.now().isoformat()))
        c.commit();c.close()
        parse_progress={"current":len(found),"total":len(found),"status":"done","message":f"Найдено {len(found)}"}
        return jsonify({'found':found,'count':len(found)})
    except Exception as e:
        traceback.print_exc();parse_progress={"current":0,"total":0,"status":"error","message":str(e)};return jsonify({'error':str(e)}),500
@app.route('/api/stores/refresh',methods=['POST'])
def refresh_stores():
    global parse_progress
    try:
        c=get_db();rows=c.execute("SELECT code FROM stores").fetchall();c.close()
        parse_progress={"current":0,"total":len(rows),"status":"refreshing","message":"Обновление..."}
        upd=0;rem=0
        for i,row in enumerate(rows):
            cnt=check_store_code(row['code']);c=get_db()
            if cnt>0:c.execute("UPDATE stores SET products_count=?,added_at=? WHERE code=?",(cnt,datetime.now().isoformat(),row['code']));upd+=1
            else:c.execute("DELETE FROM stores WHERE code=?",(row['code'],));rem+=1
            c.commit();c.close();parse_progress["current"]=i+1;parse_progress["message"]=f"{i+1}/{len(rows)}";time.sleep(0.1)
        parse_progress={"current":upd,"total":upd,"status":"done","message":f"Обновлено:{upd} удалено:{rem}"}
        return jsonify({'updated':upd,'removed':rem})
    except Exception as e:
        traceback.print_exc();return jsonify({'error':str(e)}),500
@app.route('/api/progress')
def progress():
    def gen():
        last=""
        for _ in range(600):
            msg=json.dumps(parse_progress)
            if msg!=last:yield f"data: {msg}\\n\\n";last=msg
            if parse_progress["status"] in("done","error","idle"):break
            time.sleep(0.3)
    return Response(gen(),mimetype='text/event-stream')
@app.route('/api/parse',methods=['POST'])
def api_parse():
    global parse_progress
    try:
        d=request.json;term=d.get('search') or None;max_items=int(d.get('max_items',1500))
        city=d.get('city','');store_code=d.get('store_code','')
        if store_code and store_code!='all':
            c=get_db();row=c.execute("SELECT code,address FROM stores WHERE code=?",(store_code,)).fetchone();c.close()
            codes=[(row['code'],row['address'])] if row else [(store_code,'')]
        elif city:
            c=get_db();rows=c.execute("SELECT code,address FROM stores WHERE city=?",(city,)).fetchall();c.close()
            codes=[(r['code'],r['address']) for r in rows]
        else:return jsonify({'status':'error','message':'Выберите город или магазин'})
        if not codes:return jsonify({'status':'error','message':'Нет магазинов'})
        parse_progress={"current":0,"total":0,"status":"loading","message":f"Парсинг {len(codes)} магазинов..."}
        def on_prog(done,total,cnt):
            parse_progress["message"]=f"Магазинов:{done}/{total} товаров:{cnt}";parse_progress["current"]=cnt;parse_progress["total"]=cnt
        result=parse_stores_parallel(codes,max_items=max_items,term=term,progress_callback=on_prog)
        if result:
            c=get_db();c.execute("DELETE FROM products")
            for p in result:
                sj=json.dumps(p.get("stores",[]),ensure_ascii=False)
                c.execute("INSERT OR REPLACE INTO products(magnit_id,name,price,old_price,discount_percent,savings,store_code,image_url,stock,is_adult,volume,price_per_liter,updated_at)VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",(p['id'],p['name'],p['price'],p['old_price'],p['discount_percent'],p.get('savings',0),sj,p['image'],p['stock'],p.get('is_adult',0),p.get('volume',''),p.get('price_per_liter',0),datetime.now().isoformat()))
            c.commit();c.close()
        parse_progress={"current":len(result),"total":len(result),"status":"done","message":f"{len(result)} товаров из {len(codes)} маг."}
        return jsonify({'status':'success','count':len(result),'stores':len(codes)})
    except Exception as e:
        traceback.print_exc();parse_progress={"current":0,"total":0,"status":"error","message":str(e)};return jsonify({'status':'error','message':str(e)}),500
@app.route('/api/products')
def api_products():
    md=int(request.args.get('min_discount',0));search=request.args.get('search','');adult=request.args.get('adult_only')=='1'
    favs_only=request.args.get('favorites')=='1';sort=request.args.get('sort','discount_desc')
    page=int(request.args.get('page',1));pp=int(request.args.get('per_page',60))
    c=get_db();q="SELECT * FROM products WHERE stock>0";params=[]
    if md>0:q+=" AND discount_percent>=?";params.append(md)
    if search:q+=" AND name LIKE ?";params.append(f"%{search}%")
    if adult:q+=" AND is_adult=1"
    sm={'discount_desc':'discount_percent DESC','savings_desc':'savings DESC','price_asc':'price ASC','price_desc':'price DESC','stock_desc':'stock DESC'}
    order=sm.get(sort,'discount_percent DESC')
    total=c.execute(q.replace("SELECT *","SELECT COUNT(*)"),params).fetchone()[0]
    q+=f" ORDER BY {order} LIMIT ? OFFSET ?";params.extend([pp,(page-1)*pp])
    prods=[dict(r) for r in c.execute(q,params).fetchall()]
    fav_ids=[r[0] for r in c.execute("SELECT product_id FROM favorites").fetchall()];c.close()
    if favs_only:prods=[p for p in prods if p['magnit_id'] in fav_ids];total=len(prods)
    for p in prods:p['is_favorite']=p['magnit_id'] in fav_ids
    return jsonify({'products':prods,'total':total,'page':page,'per_page':pp,'pages':max(1,(total+pp-1)//pp)})
@app.route('/api/product/<pid>/stores')
def prod_stores(pid):
    c=get_db();prod=c.execute("SELECT * FROM products WHERE magnit_id=?",(pid,)).fetchone();c.close()
    stores=[]
    if prod and prod['store_code']:
        try:
            s=json.loads(prod['store_code'])
            if isinstance(s,list):stores=sorted(s,key=lambda x:x.get('price',99999))
        except:pass
    return jsonify({'product':dict(prod) if prod else None,'stores':stores})
@app.route('/api/favorites/add',methods=['POST'])
def fav_add():
    c=get_db();c.execute("INSERT OR IGNORE INTO favorites(product_id,added_at)VALUES(?,?)",(request.json['product_id'],datetime.now().isoformat()));c.commit();c.close();return jsonify({'status':'ok'})
@app.route('/api/favorites/remove',methods=['POST'])
def fav_rem():
    c=get_db();c.execute("DELETE FROM favorites WHERE product_id=?",(request.json['product_id'],));c.commit();c.close();return jsonify({'status':'ok'})
if __name__=='__main__':
    init_db();print("\\n  http://127.0.0.1:5000\\n");app.run(debug=False,host='127.0.0.1',port=5000,threaded=True)
''')
print("✅ app.py")

# ==================== templates/index.html ====================
open("templates/index.html","w",encoding="utf-8").write('''<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Скидки Магнита</title><link rel="stylesheet" href="/static/css/style.css?v=10"></head><body>
<header><div class="header-top"><h1>🍷 Скидки Магнита</h1><span class="subtitle" id="stats"></span></div>
<div class="controls-row"><select id="city-select"><option value="">Выберите город</option></select><select id="store-select"><option value="all">Все магазины города</option></select><button id="parse-btn" class="btn-primary">Загрузить скидки</button><button id="map-btn" class="btn-secondary">🗺️ Карта</button><button id="manage-stores-btn" class="btn-secondary">⚙️ Магазины</button></div>
<div class="controls-row"><input type="text" id="search-input" placeholder="Искать товары"><select id="sort-select"><option value="discount_desc">По скидке</option><option value="savings_desc">По выгоде ₽</option><option value="price_asc">Сначала дешевле</option><option value="price_desc">Сначала дороже</option><option value="stock_desc">По остатку</option></select><label class="checkbox-label"><input type="checkbox" id="adult-only"> Только 18+</label><button id="favorites-btn">♡ Избранное</button></div>
<div class="quick-search"><button class="tag-btn active" data-term="">Всё</button><button class="tag-btn" data-term="вино">Вино</button><button class="tag-btn" data-term="пиво">Пиво</button><button class="tag-btn" data-term="водка">Водка</button><button class="tag-btn" data-term="виски">Виски</button><button class="tag-btn" data-term="коньяк">Коньяк</button><button class="tag-btn" data-term="шампанское">Игристое</button><button class="tag-btn" data-term="ликёр">Ликёры</button><button class="tag-btn" data-term="сыр">Сыр</button><button class="tag-btn" data-term="кофе">Кофе</button></div>
<div id="progress-bar" class="progress-bar" style="display:none"><div class="progress-fill" id="progress-fill"></div><span class="progress-text" id="progress-text"></span></div></header>
<main><div id="products-grid" class="products-grid"></div><div id="load-more" class="load-more" style="display:none">Загрузка...</div><div id="empty" class="empty">Выберите город и нажмите «Загрузить скидки»</div></main>
<div id="product-modal" class="modal" style="display:none"><div class="modal-content"><button class="modal-close" id="modal-close">✕</button><div class="modal-body"><div class="modal-image"><img id="modal-img" src=""><div class="modal-badge" id="modal-badge"></div></div><div class="modal-info"><h2 id="modal-name"></h2><div class="modal-price"><span class="price-current" id="modal-price"></span> <span class="price-old" id="modal-old-price"></span></div><div class="modal-meta" id="modal-meta"></div><div class="modal-savings" id="modal-savings"></div><h3>Где купить</h3><div id="modal-stores" class="modal-stores"></div></div></div></div></div>
<div id="map-modal" class="modal" style="display:none"><div class="modal-content modal-wide"><button class="modal-close" id="map-close">✕</button><h2 style="margin-bottom:12px">🗺️ Магазины на карте</h2><div id="yandex-map" style="width:100%;height:500px;border-radius:8px"></div></div></div>
<div id="stores-modal" class="modal" style="display:none"><div class="modal-content modal-wide"><button class="modal-close" id="stores-close">✕</button><h2 style="margin-bottom:12px">Управление магазинами</h2><div class="store-actions"><input type="text" id="new-code" placeholder="Код"><input type="text" id="new-address" placeholder="Адрес"><input type="text" id="new-city" placeholder="Город"><button id="add-store-btn" class="btn-primary">Добавить</button></div><div class="store-actions"><input type="number" id="scan-start" placeholder="От" value="992340"><input type="number" id="scan-end" placeholder="До" value="992400"><input type="text" id="scan-city" placeholder="Город"><button id="scan-btn" class="btn-secondary">📡 Сканировать</button><button id="refresh-btn" class="btn-secondary">🔄 Обновить</button></div><div id="stores-list" class="stores-list"></div></div></div>
<script src="https://api-maps.yandex.ru/2.1/?lang=ru_RU"></script><script src="/static/js/script.js?v=10"></script></body></html>''')
print("✅ index.html")

# ==================== static/css/style.css ====================
open("static/css/style.css","w",encoding="utf-8").write('''*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f5f5f5;color:#333;min-height:100vh}header{background:#fff;padding:12px 20px;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,.08)}.header-top{display:flex;align-items:center;gap:12px;margin-bottom:10px}h1{font-size:1.2em;color:#c00;font-weight:700}.subtitle{color:#666;font-size:.8em}.controls-row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:8px}input[type="text"],input[type="number"],select{padding:7px 10px;border:1px solid #ddd;border-radius:6px;background:#fff;color:#333;font-size:13px}input[type="text"]{width:200px}select{max-width:250px}input:focus,select:focus{outline:none;border-color:#c00}button{padding:7px 14px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600;transition:all .15s}.btn-primary{background:#c00;color:#fff;font-size:13px;padding:9px 18px}.btn-primary:hover{background:#e00}.btn-primary:disabled{background:#999;cursor:wait}.btn-secondary{background:#f0f0f0;color:#333;border:1px solid #ddd}.btn-secondary:hover{background:#e8e8e8}#favorites-btn{background:#fff8e1;color:#f57f17;border:1px solid #ffe082}#favorites-btn.active{background:#ffc107;color:#333}.checkbox-label{display:flex;align-items:center;gap:4px;font-size:12px;color:#666;cursor:pointer;white-space:nowrap}.quick-search{display:flex;gap:5px;align-items:center;flex-wrap:wrap;margin-bottom:8px}.tag-btn{background:#fff;color:#555;padding:5px 12px;font-size:12px;border:1px solid #ddd;border-radius:20px}.tag-btn:hover,.tag-btn.active{background:#c00;color:#fff;border-color:#c00}.progress-bar{position:relative;height:26px;background:#eee;border-radius:6px;overflow:hidden;margin-top:8px}.progress-fill{height:100%;background:linear-gradient(90deg,#c00,#ff4444);transition:width .3s;width:0%}.progress-text{position:absolute;top:0;left:0;right:0;text-align:center;line-height:26px;font-size:11px;color:#333;font-weight:600}main{max-width:1400px;margin:16px auto;padding:0 16px}.products-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}.product-card{background:#fff;border-radius:10px;padding:10px;position:relative;cursor:pointer;transition:box-shadow .2s;border:1px solid #eee}.product-card:hover{box-shadow:0 4px 16px rgba(0,0,0,.1)}.card-store{font-size:10px;color:#c00;font-weight:700;margin-bottom:4px}.discount-badge{position:absolute;bottom:8px;left:8px;background:#c00;color:#fff;padding:2px 7px;border-radius:4px;font-weight:bold;font-size:11px}.fav-btn{position:absolute;top:8px;right:8px;font-size:18px;cursor:pointer;z-index:2;opacity:.3;transition:opacity .2s}.fav-btn:hover,.fav-btn.active{opacity:1}.product-card img{width:100%;height:160px;object-fit:contain;margin:4px 0 8px}.product-card h3{font-size:11px;line-height:1.35;min-height:30px;margin-bottom:6px;color:#333;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.price-row{display:flex;align-items:baseline;gap:6px;margin-bottom:2px}.price-current{font-size:16px;font-weight:700;color:#333}.price-old{font-size:12px;color:#999;text-decoration:line-through}.card-meta{font-size:10px;color:#888;margin-bottom:2px}.card-address{font-size:10px;color:#666;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.empty{text-align:center;padding:60px 20px;color:#999;font-size:14px}.load-more{text-align:center;padding:20px;color:#999;font-size:13px}.modal{position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.4);z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px}.modal-content{background:#fff;border-radius:12px;max-width:850px;width:100%;max-height:90vh;overflow-y:auto;position:relative;padding:28px}.modal-wide{max-width:950px}.modal-close{position:absolute;top:12px;right:16px;background:none;color:#999;font-size:24px;padding:4px 8px;z-index:10}.modal-close:hover{color:#333}.modal-body{display:flex;gap:28px}.modal-image{flex:0 0 280px;position:relative}.modal-image img{width:100%;height:280px;object-fit:contain;background:#fafafa;border-radius:8px}.modal-badge{position:absolute;bottom:8px;left:8px;background:#c00;color:#fff;padding:4px 10px;border-radius:4px;font-weight:bold;font-size:15px}.modal-info{flex:1}.modal-info h2{font-size:15px;line-height:1.4;margin-bottom:12px;font-weight:600}.modal-price{margin-bottom:8px}.modal-price .price-current{font-size:28px}.modal-price .price-old{font-size:16px}.modal-meta{font-size:12px;color:#888;margin-bottom:8px}.modal-savings{background:#e8f5e9;color:#2e7d32;padding:6px 12px;border-radius:6px;font-size:13px;font-weight:600;margin-bottom:16px;display:inline-block}.modal-info h3{font-size:14px;margin-bottom:10px;color:#555}.modal-stores{display:flex;flex-direction:column;gap:5px}.store-row{display:flex;justify-content:space-between;align-items:center;padding:9px 12px;background:#fafafa;border-radius:6px;font-size:12px;border:1px solid #eee}.store-row.best{background:#e8f5e9;border-color:#4caf50}.store-row .store-addr{color:#333;flex:1}.store-row .store-stock{color:#4caf50;font-weight:600;margin:0 12px;white-space:nowrap}.store-row .store-price{color:#c00;font-weight:bold;white-space:nowrap}.store-actions{display:flex;gap:6px;margin:10px 0;flex-wrap:wrap;align-items:center}.store-actions input{flex:1;min-width:100px}.stores-list{max-height:400px;overflow-y:auto;margin-top:10px}.store-item{display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-bottom:1px solid #f0f0f0;font-size:11px}.store-item:hover{background:#fafafa}.store-item button{padding:3px 8px;font-size:10px}@media(max-width:1200px){.products-grid{grid-template-columns:repeat(4,1fr)}}@media(max-width:900px){.products-grid{grid-template-columns:repeat(3,1fr)}}@media(max-width:600px){.products-grid{grid-template-columns:repeat(2,1fr);gap:8px}.product-card img{height:120px}.controls-row{flex-direction:column;align-items:stretch}input[type="text"],select{width:100%;max-width:100%}.modal-body{flex-direction:column}.modal-image{flex:none}.quick-search{overflow-x:auto;flex-wrap:nowrap}}''')
print("✅ style.css")

# ==================== static/js/script.js ====================
open("static/js/script.js","w",encoding="utf-8").write('''(function(){
"use strict";
var citySelect=document.getElementById('city-select'),storeSelect=document.getElementById('store-select'),searchInput=document.getElementById('search-input'),sortSelect=document.getElementById('sort-select'),adultOnly=document.getElementById('adult-only'),favBtn=document.getElementById('favorites-btn'),parseBtn=document.getElementById('parse-btn'),grid=document.getElementById('products-grid'),empty=document.getElementById('empty'),stats=document.getElementById('stats'),loadMore=document.getElementById('load-more'),progressBar=document.getElementById('progress-bar'),progressFill=document.getElementById('progress-fill'),progressText=document.getElementById('progress-text'),modal=document.getElementById('product-modal'),storesModal=document.getElementById('stores-modal'),mapModal=document.getElementById('map-modal');
var showFavorites=false,currentPage=1,totalPages=1,isLoading=false,eventSource=null,allStores=[];
function loadCities(){fetch('/api/stores/cities').then(function(r){return r.json()}).then(function(cities){citySelect.innerHTML='<option value="">Выберите город</option>';cities.forEach(function(c){var o=document.createElement('option');o.value=c;o.textContent=c;citySelect.appendChild(o)});if(cities.indexOf('Ставрополь')>=0){citySelect.value='Ставрополь';loadStoresForCity()}})}
function loadStoresForCity(){var city=citySelect.value;if(!city){storeSelect.innerHTML='<option value="all">Все магазины города</option>';return}fetch('/api/stores?city='+encodeURIComponent(city)).then(function(r){return r.json()}).then(function(stores){allStores=stores;storeSelect.innerHTML='<option value="all">Все магазины ('+stores.length+')</option>';stores.forEach(function(s){var o=document.createElement('option');o.value=s.code;o.textContent=s.address||('Магнит #'+s.code);storeSelect.appendChild(o)})})}
citySelect.onchange=loadStoresForCity;loadCities();
function startProgress(){progressBar.style.display='block';progressFill.style.width='0%';progressText.textContent='Загрузка...';if(eventSource)eventSource.close();eventSource=new EventSource('/api/progress');eventSource.onmessage=function(e){var d=JSON.parse(e.data);progressText.textContent=d.message;progressFill.style.width=d.total>0?Math.min(100,(d.current/d.total)*100)+'%':'50%';if(d.status==='done'||d.status==='error'){eventSource.close();setTimeout(function(){progressBar.style.display='none'},2000)}};eventSource.onerror=function(){if(eventSource)eventSource.close()}}
function doParse(term){var city=citySelect.value;if(!city){alert('Выберите город');return}parseBtn.disabled=true;parseBtn.textContent='Загрузка...';empty.style.display='none';grid.innerHTML='';startProgress();var body={city:city,max_items:1500};var sc=storeSelect.value;if(sc&&sc!=='all')body.store_code=sc;if(term)body.search=term;fetch('/api/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).then(function(r){return r.json()}).then(function(res){if(res.status==='success'){stats.textContent=res.count+' товаров · '+res.stores+' магазинов';currentPage=1;grid.innerHTML='';loadProducts()}else{stats.textContent='Ошибка: '+res.message;empty.style.display='block';empty.textContent=res.message}parseBtn.disabled=false;parseBtn.textContent='Загрузить скидки'}).catch(function(e){stats.textContent='Ошибка: '+e.message;parseBtn.disabled=false;parseBtn.textContent='Загрузить скидки'})}
parseBtn.onclick=function(){doParse(searchInput.value.trim()||null)};
var tagBtns=document.querySelectorAll('.tag-btn');for(var i=0;i<tagBtns.length;i++){tagBtns[i].onclick=function(){for(var j=0;j<tagBtns.length;j++)tagBtns[j].classList.remove('active');this.classList.add('active');var t=this.getAttribute('data-term');searchInput.value=t;doParse(t||null)}}
function loadProducts(){if(isLoading)return;isLoading=true;loadMore.style.display='block';var p=new URLSearchParams();p.set('page',currentPage);p.set('per_page',60);p.set('sort',sortSelect.value);if(searchInput.value.trim())p.set('search',searchInput.value.trim());if(adultOnly.checked)p.set('adult_only','1');if(showFavorites)p.set('favorites','1');fetch('/api/products?'+p.toString()).then(function(r){return r.json()}).then(function(data){totalPages=data.pages;appendProducts(data.products);currentPage++;isLoading=false;loadMore.style.display=currentPage<=totalPages?'block':'none';if(!grid.children.length){empty.style.display='block';empty.textContent=showFavorites?'В избранном пусто':'Нет товаров'}else empty.style.display='none'}).catch(function(){isLoading=false;loadMore.style.display='none'})}
function appendProducts(products){products.forEach(function(p){var card=document.createElement('div');card.className='product-card';var img=p.image_url?'<img src="'+p.image_url+'" loading="lazy" onerror="this.style.display=\\\'none\\\'">':'';var vol=p.volume?p.volume+(p.price_per_liter?' · '+p.price_per_liter+' ₽/л':''):'';var addr='';try{var sd=JSON.parse(p.store_code);if(Array.isArray(sd)&&sd.length)addr=sd[0].address||''}catch(e){}var badge=p.discount_percent>0?'−'+p.discount_percent+'%':'Акция';card.innerHTML='<div class="card-store">Магнит</div><span class="'+(p.is_favorite?'fav-btn active':'fav-btn')+'" data-id="'+p.magnit_id+'">'+(p.is_favorite?'♥':'♡')+'</span>'+img+'<h3>'+p.name+'</h3><div class="price-row"><span class="price-current">'+fmtP(p.price)+'</span><span class="price-old">'+fmtP(p.old_price)+'</span></div>'+(vol?'<div class="card-meta">'+vol+'</div>':'')+(addr?'<div class="card-address">'+addr+'</div>':'')+'<div class="discount-badge">'+badge+'</div>';card.onclick=function(e){if(e.target.classList.contains('fav-btn'))return;openModal(p)};grid.appendChild(card)});var btns=grid.querySelectorAll('.fav-btn:not([data-bound])');for(var i=0;i<btns.length;i++){(function(b){b.setAttribute('data-bound','1');b.onclick=function(e){e.stopPropagation();var id=b.getAttribute('data-id'),a=b.classList.contains('active');fetch(a?'/api/favorites/remove':'/api/favorites/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:id})}).then(function(){b.classList.toggle('active');b.textContent=a?'♡':'♥'})}})(btns[i])}}
window.addEventListener('scroll',function(){if(isLoading||currentPage>totalPages)return;if(window.innerHeight+window.scrollY>=document.body.offsetHeight-300)loadProducts()});
function fmtP(v){var parts=v.toFixed(2).split('.');return parts[0]+'<sup>'+parts[1]+'</sup> ₽'}
function openModal(p){document.getElementById('modal-img').src=p.image_url||'';document.getElementById('modal-badge').textContent=p.discount_percent>0?'−'+p.discount_percent+'%':'Акция';document.getElementById('modal-name').textContent=p.name;document.getElementById('modal-price').innerHTML=fmtP(p.price);document.getElementById('modal-old-price').innerHTML=fmtP(p.old_price);var meta=[];if(p.volume)meta.push(p.volume);if(p.price_per_liter)meta.push(p.price_per_liter+' ₽/л');if(p.is_adult)meta.push('18+');document.getElementById('modal-meta').textContent=meta.join(' · ');document.getElementById('modal-savings').textContent='Выгода '+Math.round(p.savings)+' ₽';var sd=document.getElementById('modal-stores');sd.innerHTML='';try{var stores=JSON.parse(p.store_code);if(Array.isArray(stores)&&stores.length){stores.forEach(function(s,idx){var row=document.createElement('div');row.className='store-row'+(idx===0?' best':'');row.innerHTML='<span class="store-addr">'+(s.address||s.code)+'</span><span class="store-stock">'+s.stock+' шт</span><span class="store-price">'+s.price.toFixed(2)+' ₽</span>';sd.appendChild(row)})}else sd.innerHTML='<div style="color:#999">Нет данных</div>'}catch(e){sd.innerHTML='<div style="color:#999">Нет данных</div>'}modal.style.display='flex'}
document.getElementById('modal-close').onclick=function(){modal.style.display='none'};modal.onclick=function(e){if(e.target===modal)modal.style.display='none'};
sortSelect.onchange=function(){currentPage=1;grid.innerHTML='';loadProducts()};adultOnly.onchange=function(){currentPage=1;grid.innerHTML='';loadProducts()};searchInput.onkeydown=function(e){if(e.key==='Enter'){currentPage=1;grid.innerHTML='';loadProducts()}};favBtn.onclick=function(){showFavorites=!showFavorites;favBtn.classList.toggle('active');favBtn.textContent=showFavorites?'Все товары':'♡ Избранное';currentPage=1;grid.innerHTML='';loadProducts()};
document.getElementById('map-btn').onclick=function(){mapModal.style.display='flex';setTimeout(initMap,200)};document.getElementById('map-close').onclick=function(){mapModal.style.display='none'};mapModal.onclick=function(e){if(e.target===mapModal)mapModal.style.display='none'};
function initMap(){if(typeof ymaps==='undefined'){document.getElementById('yandex-map').innerHTML='<p style="padding:20px;color:#999">Карта недоступна</p>';return}ymaps.ready(function(){var city=citySelect.value||'Ставрополь';var centers={'Ставрополь':[45.0445,41.9691],'Краснодар':[45.0355,38.9753],'Армавир':[44.9976,41.1296],'Невинномысск':[44.6333,41.9444],'Курганинск':[44.8833,40.5833],'Москва':[55.7558,37.6173],'Санкт-Петербург':[59.9343,30.3351]};var center=centers[city]||[45.0445,41.9691];var map=new ymaps.Map('yandex-map',{center:center,zoom:12,controls:['zoomControl']});ymaps.geocode(city+' Магнит',{results:30}).then(function(res){res.geoObjects.each(function(obj){var pm=new ymaps.Placemark(obj.geometry.getCoordinates(),{balloonContentHeader:obj.properties.get('name')||'Магнит',balloonContentBody:obj.properties.get('description')||''},{preset:'islands#redDotIcon'});map.geoObjects.add(pm)})})})}
document.getElementById('manage-stores-btn').onclick=function(){loadStoresList();storesModal.style.display='flex'};document.getElementById('stores-close').onclick=function(){storesModal.style.display='none';loadCities()};storesModal.onclick=function(e){if(e.target===storesModal){storesModal.style.display='none';loadCities()}};
function loadStoresList(){fetch('/api/stores').then(function(r){return r.json()}).then(function(stores){var list=document.getElementById('stores-list');list.innerHTML='';stores.forEach(function(s){var div=document.createElement('div');div.className='store-item';div.innerHTML='<span><b>'+s.city+'</b> · '+s.address+' <small style="color:#999">('+s.code+')</small></span><button class="btn-secondary">✕</button>';div.querySelector('button').onclick=function(){fetch('/api/stores/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:s.code})}).then(loadStoresList)};list.appendChild(div)})})}
document.getElementById('add-store-btn').onclick=function(){var code=document.getElementById('new-code').value.trim(),addr=document.getElementById('new-address').value.trim(),city=document.getElementById('new-city').value.trim();if(!code||!city){alert('Укажите код и город');return}fetch('/api/stores/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:code,address:addr,city:city})}).then(function(){document.getElementById('new-code').value='';document.getElementById('new-address').value='';loadStoresList()})};
document.getElementById('scan-btn').onclick=function(){var s=parseInt(document.getElementById('scan-start').value),e=parseInt(document.getElementById('scan-end').value),c=document.getElementById('scan-city').value.trim()||'Новые';var b=this;b.disabled=true;b.textContent='Сканирую...';startProgress();fetch('/api/stores/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({start:s,end:e,city:c})}).then(function(r){return r.json()}).then(function(res){b.disabled=false;b.textContent='📡 Сканировать';if(res.count!==undefined){stats.textContent='Найдено '+res.count;loadStoresList()}}).catch(function(){b.disabled=false;b.textContent='📡 Сканировать'})};
document.getElementById('refresh-btn').onclick=function(){var b=this;b.disabled=true;b.textContent='Обновляю...';startProgress();fetch('/api/stores/refresh',{method:'POST'}).then(function(r){return r.json()}).then(function(res){b.disabled=false;b.textContent='🔄 Обновить';stats.textContent='Обновлено: '+(res.updated||0);loadStoresList()}).catch(function(){b.disabled=false;b.textContent='🔄 Обновить'})};
})();''')
print("✅ script.js")

print("\n"+"="*50)
print("🎉 ВСЕ ФАЙЛЫ ПЕРЕЗАПИСАНЫ!")
print("="*50)
print("\nВыполни:")
print("  del magnit_data.db")
print("  git add .")
print('  git commit -m "final: all fixes, infinite scroll, map, store select"')
print("  git push")
print("  python app.py")