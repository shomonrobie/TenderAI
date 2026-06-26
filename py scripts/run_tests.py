# tests/run_tests.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from tests.test_automation import run_quick_test_suite
import json

if __name__ == "__main__":
    print("🚀 Running automated tests...")
    result = run_quick_test_suite()
    print(json.dumps(result['summary'], indent=2))
    
    if result['failed_tests']:
        print("\n❌ FAILED TESTS:")
        for t in result['failed_tests'][:5]:
            print(f"  • {t['test_name']}: {t['error_message']}")