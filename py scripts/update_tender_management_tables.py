# update_tender_management_tables.py
import sqlite3
from datetime import datetime

def add_tender_management_tables():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Tenders table - tracks all tenders the company participates in
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS company_tenders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        tender_id TEXT UNIQUE,
        tender_title TEXT,
        procuring_entity TEXT,
        division TEXT,
        procurement_type TEXT,
        official_estimate REAL,
        submission_deadline TIMESTAMP,
        our_bid_amount REAL,
        bid_submitted_by INTEGER,
        bid_submission_date TIMESTAMP,
        bid_status TEXT DEFAULT 'draft',
        evaluation_status TEXT DEFAULT 'pending',
        winning_bid_amount REAL,
        winning_competitor TEXT,
        our_rank INTEGER,
        total_bidders INTEGER,
        award_date DATE,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies (id),
        FOREIGN KEY (bid_submitted_by) REFERENCES users (id)
    )
    ''')
    
    # Tender documents table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tender_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        document_name TEXT,
        document_type TEXT,
        file_path TEXT,
        uploaded_by INTEGER,
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id),
        FOREIGN KEY (uploaded_by) REFERENCES users (id)
    )
    ''')
    
    # Tender team assignments
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tender_team_assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        user_id INTEGER,
        role TEXT,
        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id),
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # Tender milestones/tasks
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tender_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        milestone_name TEXT,
        due_date DATE,
        completed BOOLEAN DEFAULT 0,
        completed_at TIMESTAMP,
        assigned_to INTEGER,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id),
        FOREIGN KEY (assigned_to) REFERENCES users (id)
    )
    ''')
    
    # Bid revisions history
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bid_revisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tender_id INTEGER,
        revision_number INTEGER,
        bid_amount REAL,
        revised_by INTEGER,
        reason TEXT,
        revised_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tender_id) REFERENCES company_tenders (id),
        FOREIGN KEY (revised_by) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Tender management tables added successfully!")

if __name__ == "__main__":
    add_tender_management_tables()