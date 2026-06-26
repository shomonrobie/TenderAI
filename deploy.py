# deploy.py

import subprocess
import sys
import os

def run_migrations():
    """Run database migrations"""
    print("📦 Running database migrations...")
    result = subprocess.run([sys.executable, "migrations/run_migrations.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"❌ Migrations failed: {result.stderr}")
        return False
    return True

def start_app():
    """Start the Streamlit app"""
    print("🚀 Starting TenderAI application...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "main.py", "--server.port=8501"])

if __name__ == "__main__":
    print("=" * 50)
    print("TenderAI Deployment Script")
    print("=" * 50)
    
    if run_migrations():
        start_app()
    else:
        print("Deployment aborted due to migration failure.")