"""
Pricing engine for FramersHaven.
Supports two methods:
1. Cost & Markup: price = (cost * markup) + factor
2. Price Table: look up price based on half-perimeter (width + height)
"""

import sqlite3
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass


# QuoteRequest for the simple quote API and tests. Field order supports positional init.
@dataclass
class QuoteRequest:
    width_in: float
    height_in: float
    moulding_cost_ft: float
    mat_cost_sqft: float
    glazing_cost_sqft: float = 0.0
    labor_flat: float = 0.0
    mat_border_in: float = 2.0
    tax_rate: float = 0.06
    extra_line_items: Optional[Dict[str, float]] = None


@dataclass
class QuoteResult:
    perimeter_ft: float
    area_sqft: float
    line_items: Dict[str, float]
    subtotal: float
    tax: float
    total: float

from app.db import get_connection
def get_price_rule(component_type: str) -> Dict[str, Any]:
    """Fetch pricing rule for a specific component type."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM price_rules WHERE component_type = ?", (component_type,))
    rule = cur.fetchone()
    conn.close()
    
    if rule:
        return dict(rule)
    
    # Fallback defaults if rule not found in DB
    defaults = {
        'moulding': {'pricing_method': 'cost_markup', 'markup': 3.0, 'factor': 5.0},
        'mat': {'pricing_method': 'cost_markup', 'markup': 2.5, 'factor': 3.0, 'costing_method': 'square_area', 'min_price': 5.0},
        'glazing': {'pricing_method': 'cost_markup', 'markup': 2.0, 'factor': 0.0, 'costing_method': 'square_area', 'min_price': 0},
        'backing': {'pricing_method': 'cost_markup', 'markup': 2.0, 'factor': 0.0, 'costing_method': 'square_area', 'min_price': 0},
    }
    return defaults.get(component_type, {'pricing_method': 'cost_markup', 'markup': 1.0, 'factor': 0.0})

# Moulding pricing
def calculate_moulding_price(sku: str, width: float, height: float) -> dict:
    """
    Calculate moulding price based on:
    - Look up the moulding's price_code from catalog_items (via metadata_json)
    - If pricing_method is 'price_table': use half_perimeter (w+h) to look up price
    - If pricing_method is 'cost_markup': price = (cost_per_ft * perimeter) * markup + factor
    Returns: {price, method, perimeter, price_code, base_price, markup, factor}
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM catalog_items WHERE sku = ? AND category = 'moulding'", (sku,))
    item = cur.fetchone()
    
    if not item:
        conn.close()
        return {"price": 0, "error": "Moulding not found"}

    rule = get_price_rule('moulding')
    method = rule.get('pricing_method', 'cost_markup')
    markup = rule.get('markup', 1.0)
    factor = rule.get('factor', 0.0)
    
    # Perimeter in feet for cost_markup
    # perimeter = 2 * (w + h) / 12
    perimeter_ft = (2 * (width + height)) / 12.0
    half_perimeter = width + height
    
    price = 0.0
    price_code = None
    
    import json
    metadata = {}
    if item['metadata_json']:
        try:
            metadata = json.loads(item['metadata_json'])
            price_code = metadata.get('price_code')
        except:
            pass

    if method == 'price_table' and price_code:
        # Find the smallest half_perimeter >= our half_perimeter for this code
        cur.execute("""
            SELECT price FROM price_table_entries 
            WHERE price_code = ? AND half_perimeter >= ? 
            ORDER BY half_perimeter ASC LIMIT 1
        """, (price_code, half_perimeter))
        row = cur.fetchone()
        if row:
            price = row['price']
        else:
            # Fallback to the largest available if none found
            cur.execute("""
                SELECT price FROM price_table_entries 
                WHERE price_code = ? 
                ORDER BY half_perimeter DESC LIMIT 1
            """, (price_code,))
            row = cur.fetchone()
            price = row['price'] if row else 0.0
    else:
        # cost_markup
        cost_per_ft = item['cost']
        price = (cost_per_ft * perimeter_ft) * markup + factor
        method = 'cost_markup'

    conn.close()
    return {
        "price": round(max(price, 0), 2),
        "method": method,
        "perimeter": round(perimeter_ft, 2),
        "half_perimeter": half_perimeter,
        "price_code": price_code,
        "base_price": item['cost'],
        "markup": markup,
        "factor": factor
    }

# Mat pricing  
def calculate_mat_price(sku: str, width: float, height: float) -> dict:
    """
    Calculate mat price based on:
    - Costing method: 'square_area' (w*h/144) or 'united_inch' (w+h)
    - If pricing_method is 'price_table': use half_perimeter (w+h) to look up price
    - If pricing_method is 'cost_markup': price = (area * cost) * markup + factor
    - Respect minimum price if set
    Returns: {price, method, area, markup, factor, min_price, price_code}
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM catalog_items WHERE sku = ? AND category = 'mat'", (sku,))
    item = cur.fetchone()
    
    if not item:
        conn.close()
        return {"price": 0, "error": "Mat not found"}
    
    rule = get_price_rule('mat')
    method = rule.get('pricing_method', 'cost_markup')
    costing_method = rule.get('costing_method', 'square_area')
    markup = rule.get('markup', 1.0)
    factor = rule.get('factor', 0.0)
    min_price = rule.get('min_price', 0.0)
    
    import json
    price_code = None
    if item['metadata_json']:
        try:
            metadata = json.loads(item['metadata_json'])
            price_code = metadata.get('price_code')
        except:
            pass
            
    half_perimeter = width + height
    price = 0.0
    
    if method == 'price_table' and price_code:
        cur.execute("""
            SELECT price FROM price_table_entries 
            WHERE price_code = ? AND half_perimeter >= ? 
            ORDER BY half_perimeter ASC LIMIT 1
        """, (price_code, half_perimeter))
        row = cur.fetchone()
        if row:
            price = row['price']
        else:
            cur.execute("""
                SELECT price FROM price_table_entries 
                WHERE price_code = ? 
                ORDER BY half_perimeter DESC LIMIT 1
            """, (price_code,))
            row = cur.fetchone()
            price = row['price'] if row else 0.0
    else:
        cost_basis = item['cost']
        if costing_method == 'united_inch':
            area_val = width + height
        else: # square_area
            area_val = (width * height) / 144.0
        price = (area_val * cost_basis) * markup + factor
        price = max(price, min_price)
        method = costing_method
        
    conn.close()
    return {
        "price": round(price, 2),
        "method": method,
        "area": round(width + height, 2) if costing_method == 'united_inch' else round((width * height) / 144.0, 2),
        "markup": markup,
        "factor": factor,
        "min_price": min_price,
        "price_code": price_code
    }

# Glazing pricing
def calculate_glazing_price(sku: str, width: float, height: float) -> dict:
    """
    Calculate glazing price:
    - If pricing_method is 'price_table': use half_perimeter (w+h) to look up price
    - If pricing_method is 'cost_markup': price_per_sqft * area (sq ft)
    Respect min_size and max_size constraints
    Returns: {price, area_sqft, price_per_sqft, price_code, method}
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM catalog_items WHERE sku = ? AND category = 'glazing'", (sku,))
    item = cur.fetchone()
    
    if not item:
        conn.close()
        return {"price": 0, "error": "Glazing not found"}

    rule = get_price_rule('glazing')
    method = rule.get('pricing_method', 'cost_markup')
    markup = rule.get('markup', 1.0)
    factor = rule.get('factor', 0.0)
    
    import json
    price_code = None
    if item['metadata_json']:
        try:
            metadata = json.loads(item['metadata_json'])
            price_code = metadata.get('price_code')
        except:
            pass
            
    half_perimeter = width + height
    price = 0.0
    area_sqft = (width * height) / 144.0
    
    if method == 'price_table' and price_code:
        cur.execute("""
            SELECT price FROM price_table_entries 
            WHERE price_code = ? AND half_perimeter >= ? 
            ORDER BY half_perimeter ASC LIMIT 1
        """, (price_code, half_perimeter))
        row = cur.fetchone()
        if row:
            price = row['price']
        else:
            cur.execute("""
                SELECT price FROM price_table_entries 
                WHERE price_code = ? 
                ORDER BY half_perimeter DESC LIMIT 1
            """, (price_code,))
            row = cur.fetchone()
            price = row['price'] if row else 0.0
    else:
        price = (area_sqft * item['cost']) * markup + factor
        method = 'cost_markup'
    
    conn.close()
    return {
        "price": round(max(price, 0), 2),
        "area_sqft": round(area_sqft, 2),
        "price_per_sqft": item['cost'],
        "markup": markup,
        "price_code": price_code,
        "method": method
    }

# Backing pricing
def calculate_backing_price(sku: str, width: float, height: float) -> dict:
    """
    Calculate backing price:
    - If pricing_method is 'price_table': use half_perimeter (w+h) to look up price
    - If pricing_method is 'cost_markup': price_per_sqft * area (sq ft)
    Returns: {price, area_sqft, price_per_sqft, price_code, method}
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM catalog_items WHERE sku = ? AND category = 'backing'", (sku,))
    item = cur.fetchone()
    
    if not item:
        conn.close()
        return {"price": 0, "error": "Backing not found"}

    rule = get_price_rule('backing')
    method = rule.get('pricing_method', 'cost_markup')
    markup = rule.get('markup', 1.0)
    factor = rule.get('factor', 0.0)
    
    import json
    price_code = None
    if item['metadata_json']:
        try:
            metadata = json.loads(item['metadata_json'])
            price_code = metadata.get('price_code')
        except:
            pass
            
    half_perimeter = width + height
    price = 0.0
    area_sqft = (width * height) / 144.0
    
    if method == 'price_table' and price_code:
        cur.execute("""
            SELECT price FROM price_table_entries 
            WHERE price_code = ? AND half_perimeter >= ? 
            ORDER BY half_perimeter ASC LIMIT 1
        """, (price_code, half_perimeter))
        row = cur.fetchone()
        if row:
            price = row['price']
        else:
            cur.execute("""
                SELECT price FROM price_table_entries 
                WHERE price_code = ? 
                ORDER BY half_perimeter DESC LIMIT 1
            """, (price_code,))
            row = cur.fetchone()
            price = row['price'] if row else 0.0
    else:
        price = (area_sqft * item['cost']) * markup + factor
        method = 'cost_markup'
    
    conn.close()
    return {
        "price": round(max(price, 0), 2),
        "area_sqft": round(area_sqft, 2),
        "price_per_sqft": item['cost'],
        "markup": markup,
        "price_code": price_code,
        "method": method
    }

# Additional charges
def calculate_additional_charge(category: str, base_price: float = 0) -> dict:
    """
    Calculate charges for: printing, subject_mounting, frame_mounting, 
    various, assembly, royalties
    Uses the price_rules table
    """
    rule = get_price_rule(category)
    markup = rule.get('markup', 1.0)
    factor = rule.get('factor', 0.0)
    
    # If base_price is 0, we might just be using the factor as a flat fee
    price = (base_price * markup) + factor
    
    return {
        "category": category,
        "price": round(max(price, 0), 2),
        "markup": markup,
        "factor": factor
    }

# Full quote calculation
def calculate_quote(req_or_items, tax_rate: float = 0.06, discount_pct: float = 0):
    """
    Backwards-compatible calculator.

    If passed a QuoteRequest instance, use the simplified local-first pricing contract
    expected by `app.main` and the tests. Otherwise, fall back to the existing
    item-list behavior.
    """
    # New-style call: QuoteRequest
    if isinstance(req_or_items, QuoteRequest):
        req: QuoteRequest = req_or_items
        # Basic validation
        if req.width_in <= 0:
            raise ValueError("width_in must be positive")
        if req.height_in <= 0:
            raise ValueError("height_in must be positive")
        if req.moulding_cost_ft < 0 or req.mat_cost_sqft < 0 or req.glazing_cost_sqft < 0:
            raise ValueError("cost inputs must be non-negative")

        # Compute outside sizes including mat border
        outside_w = req.width_in + 2 * req.mat_border_in
        outside_h = req.height_in + 2 * req.mat_border_in
        area_sqft = (outside_w * outside_h) / 144.0
        # perimeter in feet (outside frame perimeter)
        perimeter_in = 2 * (outside_w + outside_h)
        perimeter_ft = perimeter_in / 12.0

        line_items: Dict[str, float] = {}
        # moulding priced per foot
        moulding_price = round(req.moulding_cost_ft * perimeter_ft, 2)
        line_items["moulding"] = moulding_price
        # mat priced per sqft
        mat_price = round(req.mat_cost_sqft * area_sqft, 2)
        line_items["mat"] = mat_price
        # glazing priced per sqft
        glazing_price = round(req.glazing_cost_sqft * area_sqft, 2)
        line_items["glazing"] = glazing_price
        # labor as flat
        labor_price = round(float(req.labor_flat or 0), 2)
        if labor_price:
            line_items["labor"] = labor_price
        # extra line items passed in
        for k, v in (req.extra_line_items or {}).items():
            line_items[str(k)] = round(float(v), 2)

        subtotal = round(sum(line_items.values()), 2)
        tax = round(subtotal * float(req.tax_rate), 2)
        total = round(subtotal + tax, 2)

        return QuoteResult(perimeter_ft=round(perimeter_ft, 2), area_sqft=round(area_sqft, 4), line_items=line_items, subtotal=subtotal, tax=tax, total=total)

    # Legacy behavior: list of item dicts
    items: list = req_or_items
    line_items = []
    subtotal = 0.0

    for item in items:
        sku = item.get('sku')
        w = float(item.get('width', 0))
        h = float(item.get('height', 0))
        item_type = item.get('type')

        result = {"type": item_type, "sku": sku, "price": 0}

        if item_type == 'moulding':
            result.update(calculate_moulding_price(sku, w, h))
        elif item_type == 'mat':
            result.update(calculate_mat_price(sku, w, h))
        elif item_type == 'glazing':
            result.update(calculate_glazing_price(sku, w, h))
        elif item_type == 'backing':
            result.update(calculate_backing_price(sku, w, h))
        elif item_type in ['printing', 'mounting', 'frame_mounting', 'various', 'assembly', 'royalties']:
            base = float(item.get('base_price', 0))
            result.update(calculate_additional_charge(item_type, base))

        line_items.append(result)
        subtotal += result.get('price', 0)

    discount = subtotal * (discount_pct / 100.0)
    taxable_amount = subtotal - discount
    tax = taxable_amount * tax_rate
    total = taxable_amount + tax

    return {
        "line_items": line_items,
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "tax": round(tax, 2),
        "total": round(total, 2),
    }

# Price table management
def get_price_table() -> List[Dict[str, Any]]:
    """Get all price table entries grouped by price_code"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM price_table_entries ORDER BY price_code, half_perimeter")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def update_price_table(code: str, half_perimeter: float, price: float):
    """Update or insert a price table entry"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO price_table_entries (price_code, half_perimeter, price)
        VALUES (?, ?, ?)
        ON CONFLICT(price_code, half_perimeter) DO UPDATE SET price = excluded.price
    """, (code, half_perimeter, price))
    conn.commit()
    conn.close()

def get_price_rules() -> List[Dict[str, Any]]:
    """Get all price rules"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM price_rules")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def update_price_rule(component_type: str, method: str, markup: float, 
                       factor: float = 0, costing_method: str = 'square_area',
                       min_price: float = 0):
    """Update a price rule"""
    conn = get_connection()
    cur = conn.cursor()
    # Check if exists
    cur.execute("SELECT id FROM price_rules WHERE component_type = ?", (component_type,))
    row = cur.fetchone()
    if row:
        cur.execute("""
            UPDATE price_rules 
            SET pricing_method = ?, markup = ?, factor = ?, costing_method = ?, min_price = ?
            WHERE component_type = ?
        """, (method, markup, factor, costing_method, min_price, component_type))
    else:
        cur.execute("""
            INSERT INTO price_rules (component_type, pricing_method, markup, factor, costing_method, min_price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (component_type, method, markup, factor, costing_method, min_price))
    conn.commit()
    conn.close()
