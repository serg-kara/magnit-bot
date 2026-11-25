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
    # Миграция: добавляем колонки если их нет
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