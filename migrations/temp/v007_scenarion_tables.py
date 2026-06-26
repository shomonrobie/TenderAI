version = "v007_scenarion_tables"



def up(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("  Creating/Updating Scenario tables...")
     # Main scenarios table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_uuid TEXT UNIQUE NOT NULL,
            company_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            tender_id INTEGER,
            scenario_name TEXT NOT NULL,
            description TEXT,
            
            -- Generation parameters
            official_estimate REAL NOT NULL,
            procurement_type TEXT NOT NULL,
            min_price_pct REAL DEFAULT 0.88,
            max_price_pct REAL DEFAULT 1.08,
            competitor_counts TEXT NOT NULL,  -- JSON array
            bidding_pattern TEXT DEFAULT 'realistic',
            ai_strategy TEXT DEFAULT 'weighted_ensemble',
            random_seed INTEGER DEFAULT 42,
            
            -- Results
            recommended_bid REAL NOT NULL,
            bid_ratio REAL NOT NULL,
            confidence_score REAL NOT NULL,
            expected_win_probability REAL,
            
            -- Scenario data (JSON)
            scenarios_data TEXT NOT NULL,  -- Full scenario details
            competitor_stats TEXT,         -- JSON stats
            
            -- Metadata
            is_favorite BOOLEAN DEFAULT 0,
            view_count INTEGER DEFAULT 0,
            share_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY (company_id) REFERENCES companies(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (tender_id) REFERENCES company_tenders(id)
        )
    """)
    
    # Scenario comments/notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenario_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scenario_id) REFERENCES saved_scenarios(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Scenario sharing table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scenario_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_id INTEGER NOT NULL,
            shared_by_user_id INTEGER NOT NULL,
            shared_with_company_id INTEGER,
            shared_with_email TEXT,
            permission TEXT DEFAULT 'view',  -- view, edit, full
            share_token TEXT UNIQUE,
            expires_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scenario_id) REFERENCES saved_scenarios(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_by_user_id) REFERENCES users(id),
            FOREIGN KEY (shared_with_company_id) REFERENCES companies(id)
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_company ON saved_scenarios(company_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_user ON saved_scenarios(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_tender ON saved_scenarios(tender_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_created ON saved_scenarios(created_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_scenarios_favorite ON saved_scenarios(company_id, is_favorite)")
    
    conn.commit()
    conn.close()
    print("✅ Scenario tables initialized")