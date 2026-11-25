from flask import Flask, render_template, request, jsonify, Response
import sqlite3
import traceback
import json
import time
from datetime import datetime
from parser import (search_cities, check_store_code, fetch_products_page,
                    parse_store_progressive, scan_range, DEFAULT_STORES)

app = Flask(__name__)
DB_NAME = "magnit_data.db"
parse_progress = {"current": 0, "total": 0, "status": "idle", "message": ""}


@app.after_request
def add_no_cache(response):
    if 'static' in request.path:
        response.headers['Cache-Control'] = 'no-store'
    return response


def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        magnit_id TEXT UNIQUE, name TEXT, price REAL, old_price REAL,
        discount_percent INTEGER, savings REAL, store_code TEXT,
        image_url TEXT, stock INTEGER DEFAULT 0, is_adult INTEGER DEFAULT 0,
        volume TEXT, price_per_liter REAL, updated_at TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS favorites (
        product_id TEXT PRIMARY KEY, added_at TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS stores (
        code TEXT PRIMARY KEY, address TEXT, city TEXT,
        products_count INTEGER DEFAULT 0, lat REAL, lon REAL, added_at TEXT)''')
    for col, typedef in [("products_count", "INTEGER DEFAULT 0"), ("lat", "REAL"), ("lon", "REAL")]:
        try:
            conn.execute(f"ALTER TABLE stores ADD COLUMN {col} {typedef}")
        except:
            pass
    for s in DEFAULT_STORES:
        conn.execute("INSERT OR IGNORE INTO stores (code, address, city, added_at) VALUES (?,?,?,?)",
                    (s['code'], s['address'], s['city'], datetime.now().isoformat()))
    conn.commit()
    conn.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/cities')
def api_cities():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    return jsonify(search_cities(q))


@app.route('/api/stores')
def api_stores():
    city = request.args.get('city', '')
    conn = get_db()
    if city:
        rows = conn.execute("SELECT * FROM stores WHERE city = ? ORDER BY address", (city,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM stores ORDER BY city, address").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/stores/cities')
def api_store_cities():
    conn = get_db()
    rows = conn.execute("SELECT DISTINCT city FROM stores ORDER BY city").fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])


@app.route('/api/stores/save', methods=['POST'])
def api_save_store():
    data = request.json
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO stores (code, address, city, added_at) VALUES (?,?,?,?)",
                (data['code'], data.get('address',''), data.get('city',''), datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/stores/delete', methods=['POST'])
def api_delete_store():
    code = request.json.get('code', '')
    conn = get_db()
    conn.execute("DELETE FROM stores WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/stores/scan', methods=['POST'])
def api_scan_stores():
    global parse_progress
    try:
        data = request.json or {}
        start = int(data.get('start', 992300))
        end = int(data.get('end', 992350))
        city = data.get('city', 'Новые магазины')
        if end - start > 100:
            end = start + 100
        parse_progress = {"current": 0, "total": end - start, "status": "scanning",
                         "message": f"Сканирование {start}-{end}..."}
        found = scan_range(start, end)
        conn = get_db()
        for s in found:
            conn.execute("INSERT OR IGNORE INTO stores (code, address, city, added_at) VALUES (?,?,?,?)",
                        (s['code'], f"Магнит #{s['code']} ({s['total']} тов.)", city, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        parse_progress = {"current": len(found), "total": len(found), "status": "done",
                         "message": f"Найдено {len(found)} магазинов"}
        return jsonify({'found': found, 'count': len(found)})
    except Exception as e:
        traceback.print_exc()
        parse_progress = {"current": 0, "total": 0, "status": "error", "message": str(e)}
        return jsonify({'error': str(e)}), 500


@app.route('/api/progress')
def api_progress():
    def generate():
        last_msg = ""
        for _ in range(600):
            msg = json.dumps(parse_progress)
            if msg != last_msg:
                yield f"data: {msg}\n\n"
                last_msg = msg
            if parse_progress["status"] in ("done", "error", "idle"):
                break
            time.sleep(0.3)
    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/parse', methods=['POST'])
def api_parse():
    global parse_progress
    try:
        data = request.json
        term = data.get('search') or None
        max_items = int(data.get('max_items', 2000))
        city = data.get('city', '')
        store_code = data.get('store_code', '')

        if city:
            conn = get_db()
            rows = conn.execute("SELECT code, address FROM stores WHERE city = ?", (city,)).fetchall()
            conn.close()
            codes = [(r['code'], r['address']) for r in rows]
        elif store_code:
            codes = [(store_code, '')]
        else:
            return jsonify({'status': 'error', 'message': 'Выберите город или магазин'})

        if not codes:
            return jsonify({'status': 'error', 'message': f'Нет магазинов в городе {city}'})

        parse_progress = {"current": 0, "total": 0, "status": "loading",
                         "message": f"Парсинг {len(codes)} магазинов..."}

        all_products = {}
        for idx, (code, address) in enumerate(codes):
            parse_progress["message"] = f"Магазин {code} ({idx+1}/{len(codes)})..."
            products = parse_store_progressive(code, max_items=max_items, term=term)
            for p in products:
                pid = p["id"]
                if pid not in all_products:
                    all_products[pid] = {**p, "stores": []}
                all_products[pid]["stores"].append({
                    "code": code, "address": address,
                    "stock": p["stock"], "price": p["price"],
                    "discount_percent": p["discount_percent"]
                })
                if p["price"] < all_products[pid]["price"]:
                    all_products[pid]["price"] = p["price"]
                    all_products[pid]["discount_percent"] = p["discount_percent"]
                    all_products[pid]["savings"] = p["savings"]
                all_products[pid]["stock"] += p["stock"]
            parse_progress["current"] = len(all_products)
            parse_progress["total"] = len(all_products)

        result = list(all_products.values())
        for p in result:
            p["stores"].sort(key=lambda x: x["price"])

        if result:
            conn = get_db()
            conn.execute("DELETE FROM products")
            for p in result:
                stores_json = json.dumps(p.get("stores", []), ensure_ascii=False)
                conn.execute('''INSERT OR REPLACE INTO products
                    (magnit_id, name, price, old_price, discount_percent, savings,
                     store_code, image_url, stock, is_adult, volume, price_per_liter, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (p['id'], p['name'], p['price'], p['old_price'], p['discount_percent'],
                     p.get('savings', 0), stores_json, p['image'], p['stock'],
                     p.get('is_adult', 0), p.get('volume', ''), p.get('price_per_liter', 0),
                     datetime.now().isoformat()))
            conn.commit()
            conn.close()

        parse_progress = {"current": len(result), "total": len(result), "status": "done",
                         "message": f"✅ {len(result)} товаров из {len(codes)} магазинов"}
        return jsonify({'status': 'success', 'count': len(result), 'stores': len(codes)})
    except Exception as e:
        traceback.print_exc()
        parse_progress = {"current": 0, "total": 0, "status": "error", "message": str(e)}
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/products')
def api_products():
    min_discount = int(request.args.get('min_discount', 0))
    search = request.args.get('search', '')
    adult_only = request.args.get('adult_only') == '1'
    favorites_only = request.args.get('favorites') == '1'
    sort_by = request.args.get('sort', 'discount_desc')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 30))
    min_stock = int(request.args.get('min_stock', 0))

    conn = get_db()
    query = "SELECT * FROM products WHERE discount_percent > 0 AND stock > 0"
    params = []
    if min_discount > 0:
        query += " AND discount_percent >= ?"; params.append(min_discount)
    if search:
        query += " AND name LIKE ?"; params.append(f"%{search}%")
    if adult_only:
        query += " AND is_adult = 1"
    if min_stock > 0:
        query += " AND stock >= ?"; params.append(min_stock)

    sort_map = {
        'discount_desc': 'discount_percent DESC', 'savings_desc': 'savings DESC',
        'price_asc': 'price ASC', 'price_desc': 'price DESC', 'stock_desc': 'stock DESC',
    }
    order = sort_map.get(sort_by, 'discount_percent DESC')
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = conn.execute(count_query, params).fetchone()[0]
    query += f" ORDER BY {order} LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    rows = conn.execute(query, params).fetchall()
    products = [dict(r) for r in rows]
    favs = [r[0] for r in conn.execute("SELECT product_id FROM favorites").fetchall()]
    conn.close()

    if favorites_only:
        products = [p for p in products if p['magnit_id'] in favs]
        total = len(products)
    for p in products:
        p['is_favorite'] = p['magnit_id'] in favs
    return jsonify({'products': products, 'total': total, 'page': page,
                    'per_page': per_page, 'pages': max(1, (total + per_page - 1) // per_page)})


@app.route('/api/product/<product_id>/stores')
def api_product_stores(product_id):
    conn = get_db()
    prod = conn.execute("SELECT * FROM products WHERE magnit_id = ?", (product_id,)).fetchone()
    conn.close()
    store_data = []
    if prod and prod['store_code']:
        try:
            saved = json.loads(prod['store_code'])
            if isinstance(saved, list):
                store_data = sorted(saved, key=lambda x: x.get('price', 99999))
        except:
            pass
    return jsonify({'product': dict(prod) if prod else None, 'stores': store_data})


@app.route('/api/favorites/add', methods=['POST'])
def api_fav_add():
    conn = get_db()
    conn.execute("INSERT OR IGNORE INTO favorites (product_id, added_at) VALUES (?,?)",
                (request.json['product_id'], datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/favorites/remove', methods=['POST'])
def api_fav_remove():
    conn = get_db()
    conn.execute("DELETE FROM favorites WHERE product_id = ?", (request.json['product_id'],))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})


@app.route('/api/stores/refresh', methods=['POST'])
def api_refresh_stores():
    global parse_progress
    try:
        conn = get_db()
        rows = conn.execute("SELECT code FROM stores").fetchall()
        conn.close()
        parse_progress = {"current": 0, "total": len(rows), "status": "refreshing",
                         "message": f"Обновление {len(rows)} магазинов..."}
        updated = 0
        removed = 0
        for i, row in enumerate(rows):
            code = row['code']
            count = check_store_code(code)
            conn = get_db()
            if count > 0:
                conn.execute("UPDATE stores SET products_count = ?, added_at = ? WHERE code = ?",
                            (count, datetime.now().isoformat(), code))
                updated += 1
            else:
                conn.execute("DELETE FROM stores WHERE code = ?", (code,))
                removed += 1
            conn.commit()
            conn.close()
            parse_progress["current"] = i + 1
            parse_progress["message"] = f"Проверено {i+1}/{len(rows)}..."
            time.sleep(0.1)
        parse_progress = {"current": updated, "total": updated, "status": "done",
                         "message": f"✅ Обновлено: {updated}, удалено: {removed}"}
        return jsonify({'updated': updated, 'removed': removed})
    except Exception as e:
        traceback.print_exc()
        parse_progress = {"current": 0, "total": 0, "status": "error", "message": str(e)}
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    init_db()
    print("\n  http://127.0.0.1:5000\n")
    app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)