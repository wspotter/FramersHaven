import sqlite3
import os
from pathlib import Path
from app.db import get_connection

def init_admin_tables():
    conn = get_connection()
    cur = conn.cursor()
    
    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON")
    
    # 1. Database Schema Extension
    cur.executescript("""
    -- Users table
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        role TEXT DEFAULT 'admin',  -- 'owner' or 'admin'
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Business info
    CREATE TABLE IF NOT EXISTS business_info (
        id INTEGER PRIMARY KEY,
        company TEXT DEFAULT 'The Printery',
        address TEXT DEFAULT '216 W Court St',
        city TEXT DEFAULT 'Prestonsburg',
        state TEXT DEFAULT 'Kentucky',
        country TEXT DEFAULT 'United States',
        zip TEXT DEFAULT '41653',
        phone TEXT DEFAULT '606-229-0767',
        business_number TEXT,
        bank_account TEXT
    );

    -- App settings (key-value)
    CREATE TABLE IF NOT EXISTS app_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    -- Price rules for components
    CREATE TABLE IF NOT EXISTS price_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        component_type TEXT NOT NULL,  -- 'moulding', 'mat', 'glazing', 'backing', 'printing', 'mounting', 'various', 'assembly', 'royalties'
        pricing_method TEXT NOT NULL,  -- 'cost_markup' or 'price_table'
        markup REAL DEFAULT 4.0,
        factor REAL DEFAULT 0.0,
        costing_method TEXT DEFAULT 'square_area',  -- 'square_area' or 'united_inch'
        min_price REAL DEFAULT 0
    );

    -- Price table entries (half-perimeter based pricing for mouldings)
    CREATE TABLE IF NOT EXISTS price_table_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        price_code TEXT NOT NULL,  -- 'A', 'B', 'C', etc.
        half_perimeter REAL NOT NULL,
        price REAL NOT NULL
    );

    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER REFERENCES orders(id),
        item_name TEXT,
        design_json TEXT,  -- JSON of the full design configuration
        price REAL DEFAULT 0,
        quantity INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS order_statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        sort_order INTEGER DEFAULT 0,
        is_required INTEGER DEFAULT 1
    );
    """)
    
    # Add missing columns to customers if it exists
    cur.execute("PRAGMA table_info(customers)")
    cols = {row[1] for row in cur.fetchall()}
    for col, ddl in [
        ("first_name", "TEXT"), ("last_name", "TEXT"), ("email", "TEXT"), 
        ("company", "TEXT"), ("address", "TEXT"), ("city", "TEXT"), 
        ("zip", "TEXT"), ("country", "TEXT DEFAULT 'United States'"), 
        ("state", "TEXT"), ("phone", "TEXT"), ("web_discount", "REAL DEFAULT 0"), 
        ("tax_exempt", "INTEGER DEFAULT 0")
    ]:
        if col not in cols:
            cur.execute(f"ALTER TABLE customers ADD COLUMN {col} {ddl}")

    # Add missing columns to orders if it exists
    cur.execute("PRAGMA table_info(orders)")
    cols = {row[1] for row in cur.fetchall()}
    for col, ddl in [
        ("customer_id", "INTEGER REFERENCES customers(id)"),
        ("total", "REAL DEFAULT 0"),
        ("balance", "REAL DEFAULT 0"),
        ("created_by", "TEXT"),
        ("notes", "TEXT")
    ]:
        if col not in cols:
            cur.execute(f"ALTER TABLE orders ADD COLUMN {col} {ddl}")

    # 3. Initialize Default Data
    # Public/demo default owner user. Override with PRINTERY_BOOTSTRAP_* in production.
    from app.auth import hash_password
    
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        pw_hash = hash_password(os.getenv("PRINTERY_BOOTSTRAP_PASSWORD", "admin"))
        admin_email = os.getenv("PRINTERY_BOOTSTRAP_EMAIL", "admin@theprintery.biz")
        cur.execute("""
            INSERT INTO users (email, password_hash, role, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
        """, (admin_email, pw_hash, "owner", "Admin", "Printery"))
        
    # Insert default business_info
    cur.execute("SELECT COUNT(*) FROM business_info")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO business_info (id, company) VALUES (1, 'The Printery')")
        
    # Insert default order_statuses
    statuses = [
        ('cancelled', 70, 1),
        ('quote', 10, 1),
        ('pending', 20, 1),
        ('in production', 30, 1),
        ('ready', 40, 1),
        ('shipped', 50, 1),
        ('picked-up', 60, 1)
    ]
    for name, sort, req in statuses:
        cur.execute("INSERT OR IGNORE INTO order_statuses (name, sort_order, is_required) VALUES (?, ?, ?)", (name, sort, req))
        
    # Insert default app_settings
    app_settings_list = [
        ('units', 'imperial'),
        ('tax_rate', '0.06'),
        ('currency', 'USD')
    ]
    for k, v in app_settings_list:
        cur.execute("INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_admin_tables()
    print("Admin tables initialized.")
