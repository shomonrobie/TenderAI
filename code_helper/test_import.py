import sys
import os

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Python path includes: {current_dir}")
print(f"Utils folder exists: {os.path.exists(os.path.join(current_dir, 'utils'))}")
print(f"Bid generators exists: {os.path.exists(os.path.join(current_dir, 'utils', 'bid_generators.py'))}")

# Try the import
try:
    from utils.bid_generators import _generate_competitor_bids
    print("✓ utils.bid_generators imported successfully")
except Exception as e:
    print(f"✗ Failed to import utils.bid_generators: {e}")

# Try helpers import
try:
    from utils.helpers import _generate_and_download_pdf
    print("✓ utils.helpers imported successfully")
except Exception as e:
    print(f"✗ Failed to import utils.helpers: {e}")

# Try analysis_history import
try:
    from modules.analysis_history import show_analysis_history
    print("✓ modules.analysis_history imported successfully")
except Exception as e:
    print(f"✗ Failed to import modules.analysis_history: {e}")

print("\nTesting function call:")
try:
    result = _generate_competitor_bids(1000000, 3, 'moderate')
    print(f"✓ Function works! Generated {len(result)} competitor bids")
except Exception as e:
    print(f"✗ Function failed: {e}")