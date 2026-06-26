# tests/run_tests.py
import sys
import os
import warnings

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import test framework (mocks st.session_state if needed)
from tests.test_automation import (
    FunctionDiscoverer, 
    TestConfig, 
    TestExecutor, 
    ReportGenerator, 
    UserRole,
    IS_STREAMLIT_RUNNING
)

def run_tests():
    print("🚀 Initializing TenderAI Test Suite...")
    
    # 1. Import main module
    try:
        import main as app_module
        print("✅ Successfully imported main.py")
    except Exception as e:
        print(f"❌ Failed to import main.py: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. Discover functions FROM THE MAIN MODULE
    functions = FunctionDiscoverer.discover_functions(module=app_module)
    
    if not functions:
        print("⚠️  No functions found. Check naming patterns.")
        return
    
    print(f"🔍 Discovered {len(functions)} testable functions")
    
    # 3. Separate pure logic vs UI functions
    # UI functions will FAIL in CLI mode because they call st.markdown(), st.columns(), etc.
    UI_PATTERNS = ['_page', 'render_', 'display_', 'main', 'initialize_session_state']
    pure_funcs = {
        k: v for k, v in functions.items() 
        if not any(k.endswith(p) or k.startswith(p) for p in UI_PATTERNS)
    }
    
    if IS_STREAMLIT_RUNNING:
        test_funcs = functions  # Test everything in Streamlit UI
        print("🌐 Running in Streamlit UI mode: Testing ALL functions")
    else:
        test_funcs = pure_funcs
        print(f"🖥️ Running in CLI mode: Testing {len(pure_funcs)} pure logic functions (UI functions skipped)")
    
    # 4. Configure test
    config = TestConfig(
        roles_to_test=[UserRole.PUBLIC, UserRole.SYSTEM_ADMIN, UserRole.COMPANY_ADMIN],
        target_functions=list(test_funcs.keys()),
        delay_between_tests_ms=50,
        max_execution_time_per_test_sec=15,
        enable_verbose_logging=False,  # Set True to see debug output
        output_dir="test_reports/cli",
        generate_html_report=False,
        capture_session_state=False  # Faster in CLI
    )
    
    # 5. Execute
    print("\n⏳ Running tests...")
    executor = TestExecutor(config)
    results = executor.run_all_tests(test_funcs)
    
    # 6. Report
    reporter = ReportGenerator(results, config)
    
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total:      {reporter.summary['total_tests']:>3}")
    print(f"✅ Passed:   {reporter.summary['passed']:>3}")
    print(f"❌ Failed:   {reporter.summary['failed']:>3}")
    print(f"💥 Errors:   {reporter.summary['errors']:>3}")
    print(f"📈 Pass Rate: {reporter.summary['pass_rate']:.1f}%")
    print("="*60)
    
    if reporter.summary['failed'] > 0 or reporter.summary['errors'] > 0:
        print("\n❌ FAILED/ERROR DETAILS:")
        for r in results:
            if r.status.name in ['FAILED', 'ERROR']:
                err_msg = (r.error_message or 'No details')[:150]
                print(f"  • {r.test_name}")
                print(f"    Error: {err_msg}\n")
    
    # Save reports
    json_path = reporter.generate_json_report()
    csv_path = reporter.generate_csv_report()
    print(f"📄 JSON Report: {json_path}")
    print(f"📄 CSV Report:  {csv_path}")
    
    # Exit code for CI/CD
    if reporter.summary['pass_rate'] >= 90:
        print("\n✅ All critical tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️ Pass rate {reporter.summary['pass_rate']}% is below 90% threshold")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()