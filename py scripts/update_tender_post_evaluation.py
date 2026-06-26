# update_tender_post_evaluation.py
import sqlite3

def update_post_evaluation_schema():
    conn = sqlite3.connect("data/tender_system.db")
    cursor = conn.cursor()
    
    # Add post-evaluation columns to tender_analyses table
    columns_to_add = [
        ("final_submitted_bid", "REAL", "Final bid amount actually submitted"),
        ("is_final_submitted", "BOOLEAN DEFAULT 0", "Whether this was the final submitted bid"),
        ("actual_winning_bid", "REAL", "Actual winning bid amount after award"),
        ("actual_winner", "TEXT", "Name of the actual winner"),
        ("our_rank_actual", "INTEGER", "Our actual rank in the tender"),
        ("total_bidders_actual", "INTEGER", "Total bidders in the tender"),
        ("bid_accuracy_score", "REAL", "How close our bid was to winning bid"),
        ("lessons_learned", "TEXT", "Post-evaluation insights"),
        ("post_evaluation_date", "TIMESTAMP", "When post evaluation was completed")
    ]
    
    for col_name, col_type, col_desc in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE tender_analyses ADD COLUMN {col_name} {col_type}")
            print(f"✓ Added column: {col_name} - {col_desc}")
        except sqlite3.OperationalError:
            print(f"⚠ Column already exists: {col_name}")
    
    # Create index for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_final_submitted ON tender_analyses(is_final_submitted, company_id)")
    
    conn.commit()
    conn.close()
    print("\n✅ Post-evaluation schema updated!")

if __name__ == "__main__":
    update_post_evaluation_schema()