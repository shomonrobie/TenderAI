# run_schema.py
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock streamlit if not available
try:
    import streamlit as st
except ImportError:
    import streamlit as st
    # Mock streamlit for schema execution
    class MockStreamlit:
        @staticmethod
        def error(msg):
            print(f"❌ {msg}")
        @staticmethod
        def success(msg):
            print(f"✅ {msg}")
        @staticmethod
        def info(msg):
            print(f"ℹ️ {msg}")
        @staticmethod
        def warning(msg):
            print(f"⚠️ {msg}")
        @staticmethod
        def markdown(msg):
            print(msg)
        @staticmethod
        def title(msg):
            print(f"\n📌 {msg}\n{'='*50}")
    st = MockStreamlit()

# Import and run schema
from database.schema import DatabaseSchema

if __name__ == "__main__":
    print("🔧 Running database schema...")
    schema = DatabaseSchema("data/tender_system.db")
    schema.create_all_tables()
    print("✅ Schema execution complete!")