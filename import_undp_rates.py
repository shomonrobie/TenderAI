# import_undp_rates.py - Import UNDP rates from CSV

import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = "data/tender_system.db"
CSV_PATH = "data/demo/undp.csv"
COMPANY_ID = 3351  # Your company ID
USER_ID = 7738  # Your user ID

def import_undp_rates():
    """Import UNDP rates from CSV"""
    
    print("📥 IMPORTING UNDP RATES")
    print("=" * 60)
    
    # Read CSV
    try:
        df = pd.read_csv(CSV_PATH)
        print(f"✅ Loaded {len(df)} items from {CSV_PATH}")
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return
    
    # Check required columns
    required = ['item_code', 'description', 'unit', 'economy_rate', 'market_rate', 'premium_rate']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"❌ Missing columns: {missing}")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Clean data
    df['item_code'] = df['item_code'].astype(str).str.strip()
    df['description'] = df['description'].astype(str).str.strip()
    df['unit'] = df['unit'].astype(str).str.strip()
    df['economy_rate'] = pd.to_numeric(df['economy_rate'], errors='coerce').fillna(0)
    df['market_rate'] = pd.to_numeric(df['market_rate'], errors='coerce').fillna(0)
    df['premium_rate'] = pd.to_numeric(df['premium_rate'], errors='coerce').fillna(0)
    
    # Remove empty rows
    df = df[df['item_code'].notna() & (df['item_code'] != '')]
    df = df[df['description'].notna() & (df['description'] != '')]
    
    if df.empty:
        print("❌ No valid data found")
        return
    
    print(f"📊 Valid items: {len(df)}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if UNDP book already exists
    cursor.execute("""
        SELECT id FROM tenant_rate_books 
        WHERE tenant_id = ? AND name = 'UNDP Rate Schedule Demo'
    """, (COMPANY_ID,))
    
    existing_book = cursor.fetchone()
    
    if existing_book:
        print(f"⚠️ UNDP Rate Schedule Demo already exists (ID: {existing_book[0]})")
        confirm = input("Delete existing and re-import? (yes/no): ")
        if confirm.lower() != 'yes':
            print("❌ Import cancelled.")
            conn.close()
            return
        
        # Delete existing data
        book_id = existing_book[0]
        cursor.execute("""
            DELETE FROM tenant_pricing_levels 
            WHERE rate_item_id IN (SELECT id FROM tenant_rate_items WHERE rate_book_id = ?)
        """, (book_id,))
        cursor.execute("DELETE FROM tenant_rate_items WHERE rate_book_id = ?", (book_id,))
        cursor.execute("DELETE FROM tenant_rate_versions WHERE rate_book_id = ?", (book_id,))
        cursor.execute("DELETE FROM tenant_rate_books WHERE id = ?", (book_id,))
        print("  ✅ Deleted existing UNDP book")
    
    # Create rate book
    cursor.execute("""
        INSERT INTO tenant_rate_books (
            tenant_id, tenant_type, name, source_type, custom_source,
            description, is_active, is_demo, environment_mode, data_source_type,
            created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        COMPANY_ID,
        'company',
        'UNDP Rate Schedule Demo',
        'CUSTOM',
        'UNDP',
        'UNDP rate schedule for testing and demo',
        1,
        1,
        'DEMO',
        'DEMO',
        USER_ID,
        datetime.now()
    ))
    
    book_id = cursor.lastrowid
    print(f"✅ Created rate book: UNDP Rate Schedule Demo (ID: {book_id})")
    
    # Create version
    cursor.execute("""
        INSERT INTO tenant_rate_versions (
            rate_book_id, version_number, version_name, 
            effective_from, is_current, is_demo,
            notes, created_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        book_id,
        1,
        'UNDP Demo Version 1.0',
        datetime.now().date().isoformat(),
        1,
        1,
        'UNDP rates imported from CSV',
        USER_ID,
        datetime.now()
    ))
    
    version_id = cursor.lastrowid
    print(f"✅ Created version: UNDP Demo Version 1.0 (ID: {version_id})")
    
    # Import items with progress
    items_created = 0
    errors = []
    
    print(f"\n📊 Importing {len(df)} items...")
    
    for idx, row in df.iterrows():
        try:
            item_code = row['item_code']
            description = row['description']
            unit = row['unit']
            economy_rate = float(row['economy_rate'])
            market_rate = float(row['market_rate'])
            premium_rate = float(row['premium_rate'])
            source = str(row.get('source', 'UNDP')).strip()
            notes = str(row.get('notes', '')).strip()
            
            # Create item with base_rate_reference
            cursor.execute("""
                INSERT INTO tenant_rate_items (
                    rate_book_id, item_code, item_description, unit,
                    is_custom, is_demo, is_active,
                    base_rate_reference, created_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book_id,
                item_code,
                description,
                unit,
                1,  # is_custom
                1,  # is_demo
                1,  # is_active
                market_rate,  # base_rate_reference (using market rate as base)
                USER_ID,
                datetime.now()
            ))
            
            item_id = cursor.lastrowid
            
            # Add pricing levels
            pricing_levels = [
                ('AGGRESSIVE', economy_rate),
                ('COMPETITIVE', market_rate),
                ('STANDARD', premium_rate)
            ]
            
            for level, price in pricing_levels:
                cursor.execute("""
                    INSERT INTO tenant_pricing_levels (
                        rate_version_id, rate_item_id, pricing_level,
                        price, currency, is_demo, created_by, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    version_id,
                    item_id,
                    level,
                    price,
                    'BDT',
                    1,  # is_demo
                    USER_ID,
                    datetime.now()
                ))
            
            items_created += 1
            
            # Show progress every 10 items
            if items_created % 10 == 0:
                print(f"  ... imported {items_created} items")
            
        except Exception as e:
            errors.append(f"Row {idx+2}: {e}")
    
    conn.commit()
    
    print(f"\n✅ Imported {items_created} items")
    if errors:
        print(f"\n⚠️ Errors: {len(errors)}")
        for err in errors[:10]:
            print(f"  - {err}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print(f"✅ UNDP Rates Import Complete!")
    print(f"  - Rate Book: UNDP Rate Schedule Demo")
    print(f"  - Items: {items_created}")
    print("=" * 60)


def verify_undp_import():
    """Verify UNDP import"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n🔍 VERIFYING UNDP IMPORT")
    print("=" * 60)
    
    # Check book
    cursor.execute("""
        SELECT * FROM tenant_rate_books 
        WHERE tenant_id = ? AND name = 'UNDP Rate Schedule Demo'
    """, (COMPANY_ID,))
    
    book = cursor.fetchone()
    if not book:
        print("❌ UNDP Rate Schedule Demo not found")
        conn.close()
        return
    
    print(f"📚 Book: {book['name']} (ID: {book['id']})")
    print(f"   Source: {book['source_type']} ({book['custom_source']})")
    print(f"   Demo: {book['is_demo']}, Active: {book['is_active']}")
    
    # Check items
    cursor.execute("""
        SELECT COUNT(*) as count FROM tenant_rate_items 
        WHERE rate_book_id = ?
    """, (book['id'],))
    
    item_count = cursor.fetchone()['count']
    print(f"\n📦 Items: {item_count}")
    
    # Check custom items with base_rate
    cursor.execute("""
        SELECT COUNT(*) as count 
        FROM tenant_rate_items 
        WHERE rate_book_id = ? AND base_rate_reference > 0
    """, (book['id'],))
    
    base_rate_count = cursor.fetchone()['count']
    print(f"   Items with base_rate: {base_rate_count}")
    
    # Check pricing
    cursor.execute("""
        SELECT 
            pl.pricing_level,
            COUNT(*) as count,
            AVG(pl.price) as avg_price,
            MIN(pl.price) as min_price,
            MAX(pl.price) as max_price
        FROM tenant_pricing_levels pl
        JOIN tenant_rate_items ri ON pl.rate_item_id = ri.id
        WHERE ri.rate_book_id = ?
        GROUP BY pl.pricing_level
    """, (book['id'],))
    
    pricing = cursor.fetchall()
    print(f"\n💰 Pricing Levels:")
    for p in pricing:
        print(f"  - {p['pricing_level']}: {p['count']} items, Avg: {p['avg_price']:.2f}, Min: {p['min_price']:.2f}, Max: {p['max_price']:.2f}")
    
    # Show sample items
    cursor.execute("""
        SELECT ri.item_code, ri.item_description, ri.unit,
               pl_agg.price as aggressive,
               pl_comp.price as competitive,
               pl_std.price as standard,
               ri.base_rate_reference
        FROM tenant_rate_items ri
        LEFT JOIN tenant_pricing_levels pl_agg ON ri.id = pl_agg.rate_item_id AND pl_agg.pricing_level = 'AGGRESSIVE'
        LEFT JOIN tenant_pricing_levels pl_comp ON ri.id = pl_comp.rate_item_id AND pl_comp.pricing_level = 'COMPETITIVE'
        LEFT JOIN tenant_pricing_levels pl_std ON ri.id = pl_std.rate_item_id AND pl_std.pricing_level = 'STANDARD'
        WHERE ri.rate_book_id = ?
        LIMIT 10
    """, (book['id'],))
    
    items = cursor.fetchall()
    print(f"\n📋 Sample Items (first 10):")
    for item in items:
        print(f"  {item['item_code']}: {item['item_description'][:35]}...")
        print(f"    Base Rate: {item['base_rate_reference']:.2f}, Aggressive: {item['aggressive']:.2f}, Competitive: {item['competitive']:.2f}, Standard: {item['standard']:.2f}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ VERIFICATION COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        verify_undp_import()
    else:
        import_undp_rates()
        verify_undp_import()