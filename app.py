from flask import Flask,render_template,request,jsonify,Response
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
            if msg!=last:yield f"data: {msg}\n\n";last=msg
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
    init_db();print("\n  http://127.0.0.1:5000\n");app.run(debug=False,host='127.0.0.1',port=5000,threaded=True)
