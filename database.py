import aiosqlite
from datetime import datetime

DB_NAME = "magnit_data.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            magnit_id TEXT,
            name TEXT,
            price REAL,
            old_price REAL,
            discount_percent INTEGER,
            store_code TEXT,
            store_address TEXT,
            image_url TEXT,
            stock INTEGER DEFAULT 0,
            is_adult INTEGER DEFAULT 0,
            volume TEXT,
            price_per_liter REAL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(magnit_id, store_code)
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS favorites (
            product_id TEXT PRIMARY KEY,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        await db.commit()

async def save_products(products):
    async with aiosqlite.connect(DB_NAME) as db:
        for p in products:
            await db.execute('''INSERT OR REPLACE INTO products
                (magnit_id, name, price, old_price, discount_percent, store_code, store_address,
                 image_url, stock, is_adult, volume, price_per_liter, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (p['id'], p['name'], p['price'], p['old_price'], p['discount_percent'],
                 p['store_code'], p.get('store_address',''), p['image'], p['stock'],
                 p.get('is_adult',0), p.get('volume',''), p.get('price_per_liter',0),
                 datetime.now()))
        await db.commit()

async def get_products(store_code=None, min_discount=0, search=None, adult_only=False, limit=200):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM products WHERE discount_percent > 0 AND stock > 0"
        params = []
        if store_code:
            query += " AND store_code = ?"
            params.append(store_code)
        if min_discount > 0:
            query += " AND discount_percent >= ?"
            params.append(min_discount)
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        if adult_only:
            query += " AND is_adult = 1"
        query += " ORDER BY discount_percent DESC LIMIT ?"
        params.append(limit)
        cursor = await db.execute(query, params)
        return [dict(row) for row in await cursor.fetchall()]

async def add_favorite(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO favorites (product_id) VALUES (?)", (product_id,))
        await db.commit()

async def remove_favorite(product_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM favorites WHERE product_id = ?", (product_id,))
        await db.commit()

async def get_favorites():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT product_id FROM favorites")
        return [row[0] for row in await cursor.fetchall()]