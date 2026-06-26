# =============================================================================
# 🧪 AUTOMATED TEST FRAMEWORK - test_automation.py
# Place this in a new file: tests/test_automation.py
# =============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import json
import logging
import traceback
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
import hashlib
import sys
import os
import warnings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import main
from main import *
# =============================================================================
# 🖥️ CLI CONTEXT DETECTION & SAFE MOCK
# Place this IMMEDIATELY after imports, before any other code
# =============================================================================
import warnings

# Suppress Streamlit warnings BEFORE any Streamlit API calls
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*Session state.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Check if running under Streamlit server
IS_STREAMLIT_RUNNING = getattr(st, 'runtime', None) and st.runtime.exists()

if not IS_STREAMLIT_RUNNING:
    # ✅ FIXED: Recursion-safe session state mock
    class CLI_SessionState(dict):
        def __getattr__(self, key):
            if key in self:
                return self[key]
            raise AttributeError(f"'session_state' has no attribute '{key}'")
        
        def __setattr__(self, key, value):
            self[key] = value
        
        def __contains__(self, key):
            return super().__contains__(key)  # ← CRITICAL: Avoids recursion
        
        def to_dict(self): return dict(self)
        def clear(self): super().clear()
        def pop(self, key, default=None): return super().pop(key, default)
        def get(self, key, default=None): return super().get(key, default)
    
    st.session_state = CLI_SessionState()
    # Only print if verbose mode
    if os.getenv('TEST_VERBOSE', 'false').lower() == 'true':
        print("🔧 CLI Mode: Session state mocked (recursion-safe)")
            
# Import your main app modules
# from main import *  # Or import specific functions

# =============================================================================
# 🔧 DEBUG CONFIGURATION - Self-contained for test module
# =============================================================================


# Debug mode: Check environment variable or default to True for tests
DEBUG_MODE = os.getenv('TEST_DEBUG_MODE', 'true').lower() == 'true'

def debug_print(*args, **kwargs):
    """
    Conditional print for debugging in test automation.
    Works independently of main.py's debug_print.
    """
    if DEBUG_MODE:
        # Add timestamp and module prefix for clarity
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] [TEST-AUTO] ", end="")
        print(*args, **kwargs, flush=True)  # flush=True ensures output appears immediately

# Optional: Setup logging for test module
import logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG_MODE else logging.INFO,
    format='%(asctime)s [TEST-AUTO] %(levelname)s: %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

# =============================================================================
# 📊 TEST CONFIGURATION & CONSTANTS
# =============================================================================

class UserRole(Enum):
    """Supported user roles for testing"""
    PUBLIC = "public"
    FREE_USER = "free_user"
    BASIC_USER = "basic_user"
    PROFESSIONAL_USER = "professional_user"
    ENTERPRISE_USER = "enterprise_user"
    COMPANY_ADMIN = "company_admin"
    SYSTEM_ADMIN = "admin"


class TestStatus(Enum):
    """Test execution status"""
    PENDING = auto()
    RUNNING = auto()
    PASSED = auto()
    FAILED = auto()
    SKIPPED = auto()
    ERROR = auto()


@dataclass
class TestResult:
    """Container for individual test results"""
    test_name: str
    function_name: str
    role_tested: UserRole
    status: TestStatus
    execution_time_ms: float
    error_message: Optional[str] = None
    debug_output: List[str] = field(default_factory=list)
    session_state_snapshot: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert test result to dictionary with guaranteed keys"""
        return {
            'test_name': self.test_name or 'Unknown',
            'function_name': self.function_name or 'Unknown',
            'role_tested': self.role_tested.value if self.role_tested else 'unknown',
            'status': self.status.name if self.status else 'UNKNOWN',
            'execution_time_ms': round(self.execution_time_ms, 2) if self.execution_time_ms else 0.0,
            'error_message': str(self.error_message) if self.error_message else None,
            'debug_lines': len(self.debug_output) if self.debug_output else 0,
            'timestamp': self.timestamp.isoformat() if self.timestamp else datetime.now().isoformat()
        }


@dataclass
class TestConfig:
    """Configuration for automated testing"""
    # Roles to test
    roles_to_test: List[UserRole] = field(default_factory=lambda: list(UserRole))
    
    # Functions/pages to test (None = test all discovered functions)
    target_functions: Optional[List[str]] = None
    
    # Test data overrides
    test_tender_data: Dict = field(default_factory=lambda: {
        'tender_id': 'TEST-TND-001',
        'tender_title': 'Automated Test Tender - Road Construction Project',
        'procuring_entity': 'Test Procuring Authority',
        'division': 'Dhaka',
        'district': 'Dhaka',
        'thana': 'Gulshan',
        'construction_type': 'works',
        'official_estimate': 10000000.000,  # 3 decimal precision
        'submission_deadline': (datetime.now() + timedelta(days=30)).isoformat(),
    })
    
    test_competitor_bids: List[float] = field(default_factory=lambda: [
        9200000.123, 9350000.456, 9100000.789, 9450000.012, 9280000.345
    ])
    
    # Debug settings
    enable_verbose_logging: bool = True
    capture_session_state: bool = True
    screenshot_on_failure: bool = False  # Requires additional setup
    
    # Execution settings
    delay_between_tests_ms: int = 100  # Avoid rate limiting
    max_execution_time_per_test_sec: int = 30
    
    # Output settings
    output_dir: str = "test_reports"
    generate_html_report: bool = True
    generate_json_report: bool = True
    generate_csv_report: bool = True


# =============================================================================
# 🎭 ROLE SIMULATOR - Mimics different user sessions
# =============================================================================

class RoleSimulator:
    """Simulates different user roles by manipulating session state"""
    
    # Pre-defined test user profiles
    TEST_PROFILES = {
        UserRole.PUBLIC: {
            'logged_in': False,
            'user_id': None,
            'company_id': None,
            'user_role': None,
            'subscription_plan': None,
        },
        UserRole.FREE_USER: {
            'logged_in': True,
            'user_id': 99001,
            'company_id': 5001,
            'user_role': 'user',
            'subscription_plan': 'free',
            'subscription_status': 'active',
            'full_name': 'Test Free User',
            'user_email': 'free@test.com',
            'company_name': 'Test Free Company',
        },
        UserRole.BASIC_USER: {
            'logged_in': True,
            'user_id': 99002,
            'company_id': 5002,
            'user_role': 'user',
            'subscription_plan': 'basic',
            'subscription_status': 'active',
            'full_name': 'Test Basic User',
            'user_email': 'basic@test.com',
            'company_name': 'Test Basic Company',
        },
        UserRole.PROFESSIONAL_USER: {
            'logged_in': True,
            'user_id': 99003,
            'company_id': 5003,
            'user_role': 'user',
            'subscription_plan': 'professional',
            'subscription_status': 'active',
            'full_name': 'Test Pro User',
            'user_email': 'pro@test.com',
            'company_name': 'Test Pro Company',
        },
        UserRole.ENTERPRISE_USER: {
            'logged_in': True,
            'user_id': 99004,
            'company_id': 5004,
            'user_role': 'user',
            'subscription_plan': 'enterprise',
            'subscription_status': 'active',
            'full_name': 'Test Enterprise User',
            'user_email': 'enterprise@test.com',
            'company_name': 'Test Enterprise Company',
        },
        UserRole.COMPANY_ADMIN: {
            'logged_in': True,
            'user_id': 99005,
            'company_id': 5005,
            'user_role': 'company_admin',
            'subscription_plan': 'professional',
            'subscription_status': 'active',
            'full_name': 'Test Company Admin',
            'user_email': 'admin@testcompany.com',
            'company_name': 'Test Company Ltd',
        },
        UserRole.SYSTEM_ADMIN: {
            'logged_in': True,
            'user_id': 1,
            'company_id': None,
            'user_role': 'admin',
            'subscription_plan': 'enterprise',
            'subscription_status': 'active',
            'full_name': 'System Administrator',
            'user_email': 'sysadmin@tenderai.com',
            'company_name': None,
        },
    }
    
    @classmethod
    def apply_role(cls, role: UserRole, reset_first: bool = True) -> Dict[str, Any]:
        """
        Apply a role's session state to the current Streamlit session.
        Returns the applied state for verification.
        """
        if reset_first:
            cls.reset_session_state()
        
        profile = cls.TEST_PROFILES.get(role, cls.TEST_PROFILES[UserRole.PUBLIC])
        
        # Apply profile to session state
        for key, value in profile.items():
            st.session_state[key] = value
        
        # Add role-specific defaults
        if role != UserRole.PUBLIC:
            st.session_state.setdefault('analysis_competitor_bids', [])
            st.session_state.setdefault('current_analysis_record', None)
            st.session_state.setdefault('last_saved_analysis_id', None)
        
        debug_print(f"🎭 Applied role: {role.value} | User: {profile.get('full_name', 'N/A')}")
        return profile
    
    @classmethod
    def reset_session_state(cls, preserve_keys: List[str] = None) -> None:
        """Reset session state to clean slate"""
        preserve_keys = preserve_keys or ['debug_mode', 'TEST_MODE']
        
        for key in list(st.session_state.keys()):
            if key not in preserve_keys:
                del st.session_state[key]
        
        # Re-initialize essential keys
        from main import initialize_session_state  # Import from your main.py
        initialize_session_state()
        
        debug_print("🧹 Session state reset complete")


# =============================================================================
# 🔍 FUNCTION DISCOVERER - Auto-finds testable functions
# =============================================================================

class FunctionDiscoverer:
    """Discovers and catalogs testable functions in the application"""
    
    # Patterns for functions to test
    TESTABLE_PATTERNS = [
        lambda name: name.endswith('_page'),           # Page renderers
        lambda name: name.startswith('calculate_'),     # Calculation functions
        lambda name: name.startswith('parse_'),         # Parsing functions
        lambda name: name.startswith('render_'),        # UI renderers
        lambda name: name.startswith('display_'),       # Display functions
        lambda name: 'callback' in name.lower(),        # Callbacks
    ]
    
    # Functions to explicitly exclude from testing
    EXCLUDE_FUNCTIONS = [
        'main', 'initialize_session_state', 'setup_logging', 'debug_print',
        '_save_analysis_callback',  # Already tested via integration
    ]
    
    @classmethod
    def discover_functions(cls, module=None) -> Dict[str, Callable]:
        """
        Discover testable functions from a module.
        If module is None, searches current globals.
        """
        import inspect
        
        # Get the namespace to search
        namespace = module.__dict__ if module else globals()
        
        discovered = {}
        
        for name, obj in namespace.items():
            # Skip non-functions
            if not inspect.isfunction(obj) and not inspect.ismethod(obj):
                continue
            
            # Skip excluded functions
            if name in cls.EXCLUDE_FUNCTIONS:
                continue
            
            # Check if matches testable patterns
            if any(pattern(name) for pattern in cls.TESTABLE_PATTERNS):
                discovered[name] = obj
                debug_print(f"🔍 Discovered testable function: {name}")
        
        return discovered
    
    @classmethod
    def get_function_signature(cls, func: Callable) -> Dict:
        """Extract function signature for test data generation"""
        import inspect
        
        sig = inspect.signature(func)
        params = {}
        
        for name, param in sig.parameters.items():
            params[name] = {
                'default': param.default if param.default != inspect.Parameter.empty else None,
                'annotation': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                'kind': param.kind.name,
            }
        
        return {
            'name': func.__name__,
            'parameters': params,
            'return_annotation': str(sig.return_annotation) if sig.return_annotation != inspect.Parameter.empty else 'Any',
        }


# =============================================================================
# 🧪 TEST EXECUTOR - Runs tests and collects results
# =============================================================================

class TestExecutor:
    """Executes automated tests with role simulation and debug collection"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.debug_buffer: List[str] = []
        self.start_time: Optional[float] = None
        
        # Setup logging capture
        self._setup_debug_capture()
    
    def _setup_debug_capture(self) -> None:
        """Setup handlers to capture debug output"""
        # Create custom handler that captures to our buffer
        class DebugCaptureHandler(logging.Handler):
            def __init__(self, executor_ref):
                super().__init__()
                self.executor = executor_ref
            
            def emit(self, record):
                msg = self.format(record)
                self.executor.debug_buffer.append(f"[{record.levelname}] {msg}")
        
        # Add handler to root logger
        handler = DebugCaptureHandler(self)
        handler.setLevel(logging.DEBUG if self.config.enable_verbose_logging else logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)
    
    def _capture_debug_output(self) -> List[str]:
        """Retrieve and clear captured debug output"""
        output = self.debug_buffer.copy()
        self.debug_buffer.clear()
        return output
    
    def _safe_execute_function(self, func: Callable, args: tuple = (), kwargs: dict = None, 
                             timeout_sec: int = None) -> tuple:
        """
        Safely execute a function with timeout and error handling.
        Returns: (success: bool, result_or_error: Any, execution_time_ms: float)
        """
        import signal
        from contextlib import contextmanager
        
        kwargs = kwargs or {}
        timeout = timeout_sec or self.config.max_execution_time_per_test_sec
        start = time.time()
        
        # Timeout handler for Unix systems
        @contextmanager
        def timeout_context(seconds):
            if sys.platform != 'win32':
                def handler(signum, frame):
                    raise TimeoutError(f"Function execution exceeded {seconds}s timeout")
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
            else:
                # Windows fallback: no timeout, just execute
                yield
        
        try:
            with timeout_context(timeout):
                result = func(*args, **kwargs)
                exec_time = (time.time() - start) * 1000
                return True, result, exec_time
                
        except TimeoutError as e:
            exec_time = (time.time() - start) * 1000
            return False, f"TIMEOUT: {str(e)}", exec_time
            
        except Exception as e:
            exec_time = (time.time() - start) * 1000
            error_details = f"{type(e).__name__}: {str(e)}"
            if self.config.enable_verbose_logging:
                error_details += f"\n{traceback.format_exc()}"
            return False, error_details, exec_time
    
    def _generate_test_data(self, func: Callable, role: UserRole) -> Dict:
        """Generate appropriate test data for a function based on its signature"""
        import inspect
        
        sig = FunctionDiscoverer.get_function_signature(func)
        test_data = {}
        
        for param_name, param_info in sig['parameters'].items():
            # Skip self/cls parameters
            if param_name in ['self', 'cls']:
                continue
            
            # Use config overrides for known parameters
            if param_name == 'official_estimate':
                test_data[param_name] = self.config.test_tender_data.get('official_estimate', 10000000.0)
            elif param_name == 'competitor_bids':
                test_data[param_name] = self.config.test_competitor_bids
            elif param_name == 'risk_tolerance':
                test_data[param_name] = 'moderate'
            elif param_name == 'comparison':
                # Generate mock comparison data
                test_data[param_name] = {
                    'basic': {
                        'method': 'Test Basic',
                        'optimal_bid': 9200000.123,
                        'bid_ratio': 0.92,
                        'win_probability': 0.65,
                        'confidence_score': 0.70,
                        'risk_level': 'MEDIUM',
                        'risk_color': '🟡',
                    },
                    'advanced': {
                        'method': 'Test Advanced',
                        'optimal_bid': 9350000.456,
                        'bid_ratio': 0.935,
                        'win_probability': 0.72,
                        'confidence_score': 0.82,
                        'risk_level': 'LOW',
                        'risk_color': '🟢',
                    },
                    'enhanced': {
                        'method': 'Test Enhanced',
                        'optimal_bid': 9450000.789,
                        'bid_ratio': 0.945,
                        'win_probability': 0.78,
                        'confidence_score': 0.88,
                        'risk_level': 'LOW',
                        'risk_color': '🟢',
                    },
                }
            elif param_name == 'analysis_record':
                test_data[param_name] = self.config.test_tender_data.copy()
            elif param_info['default'] is not None:
                test_data[param_name] = param_info['default']
            elif 'int' in param_info['annotation'].lower():
                test_data[param_name] = 1
            elif 'float' in param_info['annotation'].lower():
                test_data[param_name] = 1.000
            elif 'str' in param_info['annotation'].lower() or 'string' in param_info['annotation'].lower():
                test_data[param_name] = f'test_{param_name}'
            elif 'bool' in param_info['annotation'].lower():
                test_data[param_name] = False
            elif 'list' in param_info['annotation'].lower():
                test_data[param_name] = []
            elif 'dict' in param_info['annotation'].lower():
                test_data[param_name] = {}
            else:
                test_data[param_name] = None  # Will use function default if available
        
        return test_data
    
    def run_single_test(self, func_name: str, func: Callable, role: UserRole) -> TestResult:
        """Run a single test for a function with a specific role"""
        debug_print(f"🧪 Running test: {func_name} | Role: {role.value}")
        
        # Apply role to session state
        RoleSimulator.apply_role(role, reset_first=True)
        
        # Generate test data
        test_data = self._generate_test_data(func, role)
        
        # Clear debug buffer before execution
        self.debug_buffer.clear()
        
        # Execute function
        success, result, exec_time = self._safe_execute_function(
            func, 
            args=(), 
            kwargs=test_data,
            timeout_sec=self.config.max_execution_time_per_test_sec
        )
        
        # Capture results
        debug_output = self._capture_debug_output()
        session_snapshot = st.session_state.to_dict() if self.config.capture_session_state else {}
        
        # Determine status
        if success:
            # Additional validation for page functions
            if func_name.endswith('_page'):
                # Check if page rendered without errors (basic heuristic)
                if any('error' in line.lower() for line in debug_output if 'exception' in line.lower()):
                    status = TestStatus.FAILED
                else:
                    status = TestStatus.PASSED
            else:
                status = TestStatus.PASSED
            error_msg = None
        else:
            status = TestStatus.FAILED if 'TIMEOUT' not in str(result) else TestStatus.ERROR
            error_msg = str(result)
        
        # Create result object
        test_result = TestResult(
            test_name=f"{func_name}_{role.value}",
            function_name=func_name,
            role_tested=role,
            status=status,
            execution_time_ms=exec_time,
            error_message=error_msg,
            debug_output=debug_output[:50],  # Limit to first 50 lines
            session_state_snapshot=session_snapshot,
        )
        
        # Log result
        status_icon = {
            TestStatus.PASSED: "✅",
            TestStatus.FAILED: "❌",
            TestStatus.ERROR: "💥",
            TestStatus.SKIPPED: "⏭️",
        }.get(status, "❓")
        
        debug_print(f"{status_icon} Test complete: {test_result.test_name} | {exec_time:.0f}ms")
        
        # Delay between tests
        if self.config.delay_between_tests_ms > 0:
            time.sleep(self.config.delay_between_tests_ms / 1000)
        
        return test_result
    
    def run_all_tests(self, functions: Dict[str, Callable] = None) -> List[TestResult]:
        """Run all configured tests"""
        debug_print("🚀 Starting automated test suite")
        self.start_time = time.time()
        self.results.clear()
        
        # Discover functions if not provided
        if functions is None:
            functions = FunctionDiscoverer.discover_functions()
            debug_print(f"🔍 Discovered {len(functions)} testable functions")
        
        # Filter to target functions if specified
        if self.config.target_functions:
            functions = {k: v for k, v in functions.items() if k in self.config.target_functions}
            debug_print(f"🎯 Testing {len(functions)} targeted functions")
        
        total_tests = len(functions) * len(self.config.roles_to_test)
        completed = 0
        
        # Run tests
        for func_name, func in functions.items():
            for role in self.config.roles_to_test:
                try:
                    result = self.run_single_test(func_name, func, role)
                    self.results.append(result)
                except Exception as e:
                    # Catch any unexpected errors in test execution
                    self.results.append(TestResult(
                        test_name=f"{func_name}_{role.value}",
                        function_name=func_name,
                        role_tested=role,
                        status=TestStatus.ERROR,
                        execution_time_ms=0,
                        error_message=f"Test execution error: {str(e)}\n{traceback.format_exc()}",
                    ))
                
                completed += 1
                if completed % 10 == 0:
                    debug_print(f"📊 Progress: {completed}/{total_tests} tests completed")
        
        total_time = time.time() - self.start_time
        debug_print(f"✅ Test suite complete: {len(self.results)} tests in {total_time:.1f}s")
        
        return self.results


    # =============================================================================
    # 📈 REPORT GENERATOR - Creates test reports
    # =============================================================================

class ReportGenerator:
    """Generates test reports in multiple formats"""
    
    def __init__(self, results: List['TestResult'], config: 'TestConfig'):
        self.results = results
        self.config = config
        self.summary = self._calculate_summary()
    
    def _calculate_summary(self) -> Dict:
        """Calculate test summary statistics"""
        total = len(self.results)
        if total == 0:
            return {
                'total_tests': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0,
                'pass_rate': 0.0, 'avg_execution_time_ms': 0.0, 'role_breakdown': {},
                'generated_at': datetime.now().isoformat()
            }
            
        passed = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        errors = sum(1 for r in self.results if r.status == TestStatus.ERROR)
        skipped = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)
        
        avg_time = float(np.mean([r.execution_time_ms for r in self.results])) if self.results else 0.0
        
        # Per-role breakdown
        role_stats = {}
        for role in UserRole:
            role_results = [r for r in self.results if r.role_tested == role]
            if role_results:
                role_pass_rate = (sum(1 for r in role_results if r.status == TestStatus.PASSED) / len(role_results)) * 100
                role_stats[role.value] = {
                    'total': len(role_results),
                    'passed': sum(1 for r in role_results if r.status == TestStatus.PASSED),
                    'pass_rate': round(role_pass_rate, 1),
                }
        
        return {
            'total_tests': total,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'skipped': skipped,
            'pass_rate': round((passed / total) * 100, 1),
            'avg_execution_time_ms': round(avg_time, 2),
            'role_breakdown': role_stats,
            'generated_at': datetime.now().isoformat(),
        }
    
    def generate_html_report(self, filepath: Optional[str] = None) -> str:
        """Generate interactive HTML report"""
        filepath = filepath or os.path.join(self.config.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Simplified HTML for brevity (full version available if needed)
        html = f"""<!DOCTYPE html>
            <html><head><meta charset="UTF-8"><title>TenderAI Test Report</title>
            <style>body{{font-family:sans-serif;margin:2rem;background:#f8fafc}}.summary{{display:flex;gap:1rem;margin-bottom:2rem}}.card{{background:#fff;padding:1rem;border-radius:8px;flex:1;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}table{{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden}}th,td{{padding:0.5rem 1rem;text-align:left;border-bottom:1px solid #eee}}.status{{padding:0.25rem 0.5rem;border-radius:12px;font-size:0.85rem}}</style></head>
            <body><h1>🧪 TenderAI Test Report</h1><p>Generated: {self.summary['generated_at']}</p>
            <div class="summary">
            <div class="card"><h3>Total</h3><strong>{self.summary['total_tests']}</strong></div>
            <div class="card"><h3>✅ Passed</h3><strong>{self.summary['passed']}</strong></div>
            <div class="card"><h3>❌ Failed</h3><strong>{self.summary['failed']}</strong></div>
            <div class="card"><h3>📊 Pass Rate</h3><strong>{self.summary['pass_rate']}%</strong></div>
            </div>
            <table><tr><th>Test</th><th>Function</th><th>Role</th><th>Status</th><th>Time (ms)</th><th>Error</th></tr>
            {"".join(f"<tr><td>{r.test_name}</td><td>{r.function_name}</td><td>{r.role_tested.value}</td><td class='status'>{r.status.name}</td><td>{r.execution_time_ms:.0f}</td><td>{r.error_message or '-'}</td></tr>" for r in self.results)}
            </table></body></html>"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        return filepath
    
    def generate_json_report(self, filepath: Optional[str] = None) -> str:
        filepath = filepath or os.path.join(self.config.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        report = {
            'summary': self.summary,
            'results': [r.to_dict() for r in self.results],
            'config': {'roles_tested': [r.value for r in self.config.roles_to_test]}
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        return filepath
    
    def generate_csv_report(self, filepath: Optional[str] = None) -> str:
        filepath = filepath or os.path.join(self.config.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(filepath, index=False)
        return filepath
    
    def generate_all_reports(self) -> Dict[str, str]:
        reports = {}
        try: reports['html'] = self.generate_html_report()
        except Exception as e: print(f"HTML report failed: {e}")
        try: reports['json'] = self.generate_json_report()
        except Exception as e: print(f"JSON report failed: {e}")
        try: reports['csv'] = self.generate_csv_report()
        except Exception as e: print(f"CSV report failed: {e}")
        return reports
    
        

    def _safe_results_to_dataframe(results: List[TestResult]) -> pd.DataFrame:
        """
        Safely convert TestResult list to DataFrame with guaranteed columns.
        Handles empty lists and missing attributes gracefully.
        """
        if not results:
            # Return empty DataFrame with expected schema
            return pd.DataFrame(columns=[
                'test_name', 'function_name', 'role_tested', 'status',
                'execution_time_ms', 'error_message', 'debug_lines', 'timestamp'
            ])
        
        # Convert with explicit None handling
        rows = []
        for r in results:
            try:
                row = r.to_dict()
                # Ensure all expected keys exist
                for key in ['test_name', 'function_name', 'role_tested', 'status', 
                        'execution_time_ms', 'error_message']:
                    if key not in row:
                        row[key] = None
                rows.append(row)
            except Exception as e:
                debug_print(f"⚠️ Failed to convert result to dict: {e}")
                continue
        
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=['test_name', 'function_name', 'role_tested', 'status', 'execution_time_ms', 'error_message'])
    def generate_html_report(self, filepath: str = None) -> str:
        """Generate interactive HTML report"""
        filepath = filepath or os.path.join(self.config.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TenderAI - Automated Test Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; background: #f5f7fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; }}
                .header {{ background: linear-gradient(135deg, #1e3c72, #2a5298); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; }}
                .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
                .card {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; }}
                .card h3 {{ margin: 0 0 0.5rem 0; color: #666; font-size: 0.9rem; }}
                .card .value {{ font-size: 2rem; font-weight: bold; color: #1e3c72; }}
                .card.passed .value {{ color: #22c55e; }}
                .card.failed .value {{ color: #ef4444; }}
                .card.errors .value {{ color: #f97316; }}
                table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                th, td {{ padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #eee; }}
                th {{ background: #f8fafc; font-weight: 600; color: #334155; }}
                tr:hover {{ background: #f8fafc; }}
                .status {{ padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.85rem; font-weight: 500; }}
                .status.PASSED {{ background: #dcfce7; color: #166534; }}
                .status.FAILED {{ background: #fee2e2; color: #991b1b; }}
                .status.ERROR {{ background: #ffedd5; color: #9a3412; }}
                .status.SKIPPED {{ background: #f1f5f9; color: #475569; }}
                .chart-container {{ background: white; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .debug-toggle {{ cursor: pointer; color: #667eea; font-size: 0.9rem; }}
                .debug-content {{ display: none; background: #1e293b; color: #e2e8f0; padding: 1rem; border-radius: 6px; font-family: monospace; font-size: 0.8rem; max-height: 200px; overflow-y: auto; margin-top: 0.5rem; }}
                .filter-section {{ background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; }}
                .filter-section select, .filter-section input {{ margin: 0 0.5rem; padding: 0.4rem 0.8rem; border: 1px solid #cbd5e1; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🧪 TenderAI Automated Test Report</h1>
                    <p>Generated: {self.summary['generated_at']}</p>
                </div>
                
                <div class="summary-cards">
                    <div class="card">
                        <h3>Total Tests</h3>
                        <div class="value">{self.summary['total_tests']}</div>
                    </div>
                    <div class="card passed">
                        <h3>✅ Passed</h3>
                        <div class="value">{self.summary['passed']}</div>
                    </div>
                    <div class="card failed">
                        <h3>❌ Failed</h3>
                        <div class="value">{self.summary['failed']}</div>
                    </div>
                    <div class="card errors">
                        <h3>💥 Errors</h3>
                        <div class="value">{self.summary['errors']}</div>
                    </div>
                    <div class="card">
                        <h3>Pass Rate</h3>
                        <div class="value">{self.summary['pass_rate']}%</div>
                    </div>
                    <div class="card">
                        <h3>Avg Time</h3>
                        <div class="value">{self.summary['avg_execution_time_ms']}ms</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>📊 Results by Role</h3>
                    <canvas id="roleChart" height="100"></canvas>
                </div>
                
                <div class="filter-section">
                    <strong>Filter:</strong>
                    <select id="roleFilter" onchange="filterTable()">
                        <option value="">All Roles</option>
                        {''.join([f'<option value="{role.value}">{role.value}</option>' for role in UserRole])}
                    </select>
                    <select id="statusFilter" onchange="filterTable()">
                        <option value="">All Statuses</option>
                        <option value="PASSED">✅ Passed</option>
                        <option value="FAILED">❌ Failed</option>
                        <option value="ERROR">💥 Error</option>
                        <option value="SKIPPED">⏭️ Skipped</option>
                    </select>
                    <input type="text" id="searchFilter" placeholder="Search function..." onkeyup="filterTable()">
                </div>
                
                <table id="resultsTable">
                    <thead>
                        <tr>
                            <th>Test Name</th>
                            <th>Function</th>
                            <th>Role</th>
                            <th>Status</th>
                            <th>Time (ms)</th>
                            <th>Error</th>
                            <th>Debug</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join([self._result_row_html(r) for r in self.results])}
                    </tbody>
                </table>
            </div>
            
            <script>
                // Role breakdown chart
                const roleData = {self._chart_data_json()};
                new Chart(document.getElementById('roleChart'), {{
                    type: 'bar',
                    data: {{
                        labels: Object.keys(roleData),
                        datasets: [{{
                            label: 'Pass Rate (%)',
                            data: Object.values(roleData).map(r => r.pass_rate),
                            backgroundColor: Object.values(roleData).map(r => r.pass_rate >= 90 ? '#22c55e' : r.pass_rate >= 70 ? '#eab308' : '#ef4444'),
                        }}]
                    }},
                    options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true, max: 100 }} }} }}
                }});
                
                // Table filtering
                function filterTable() {{
                    const roleFilter = document.getElementById('roleFilter').value.toLowerCase();
                    const statusFilter = document.getElementById('statusFilter').value.toLowerCase();
                    const searchFilter = document.getElementById('searchFilter').value.toLowerCase();
                    const rows = document.querySelectorAll('#resultsTable tbody tr');
                    
                    rows.forEach(row => {{
                        const role = row.cells[2].textContent.toLowerCase();
                        const status = row.cells[3].textContent.toLowerCase();
                        const func = row.cells[1].textContent.toLowerCase();
                        const testName = row.cells[0].textContent.toLowerCase();
                        
                        const matchRole = !roleFilter || role.includes(roleFilter);
                        const matchStatus = !statusFilter || status.includes(statusFilter);
                        const matchSearch = !searchFilter || func.includes(searchFilter) || testName.includes(searchFilter);
                        
                        row.style.display = (matchRole && matchStatus && matchSearch) ? '' : 'none';
                    }});
                }}
                
                // Debug toggle
                document.querySelectorAll('.debug-toggle').forEach(toggle => {{
                    toggle.addEventListener('click', function() {{
                        const content = this.nextElementSibling;
                        content.style.display = content.style.display === 'block' ? 'none' : 'block';
                        this.textContent = content.style.display === 'block' ? '🔽 Hide Debug' : '🔍 Show Debug';
                    }});
                }});
            </script>
        </body>
        </html>
        """
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        debug_print(f"📄 HTML report generated: {filepath}")
        return filepath

    def _result_row_html(self, result: TestResult) -> str:
        """Generate HTML table row for a test result"""
        debug_html = ""
        if result.debug_output:
            debug_content = "\\n".join(result.debug_output[:10])  # First 10 lines
            debug_html = f"""
            <span class="debug-toggle" onclick="event.stopPropagation()">🔍 Show Debug</span>
            <div class="debug-content">{debug_content}{'... (truncated)' if len(result.debug_output) > 10 else ''}</div>
            """
        
        error_html = f"<small style='color: #ef4444;'>{result.error_message[:50]}{'...' if result.error_message and len(result.error_message) > 50 else ''}</small>" if result.error_message else "-"
        
        return f"""
        <tr>
            <td><strong>{result.test_name}</strong></td>
            <td>{result.function_name}</td>
            <td>{result.role_tested.value}</td>
            <td><span class="status {result.status.name}">{result.status.name}</span></td>
            <td>{result.execution_time_ms:.0f}</td>
            <td>{error_html}</td>
            <td>{debug_html}</td>
        </tr>
        """

    def _chart_data_json(self) -> str:
        """Generate JSON for role breakdown chart"""
        return json.dumps({
            role: stats for role, stats in self.summary['role_breakdown'].items()
        })

    def generate_json_report(self, filepath: str = None) -> str:
        """Generate machine-readable JSON report"""
        filepath = filepath or os.path.join(self.config.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        report = {
            'summary': self.summary,
            'results': [r.to_dict() for r in self.results],
            'config': {
                'roles_tested': [r.value for r in self.config.roles_to_test],
                'functions_tested': len(set(r.function_name for r in self.results)),
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)
        
        debug_print(f"📄 JSON report generated: {filepath}")
        return filepath

    def generate_csv_report(self, filepath: str = None) -> str:
        """Generate CSV report for spreadsheet analysis"""
        filepath = filepath or os.path.join(self.config.output_dir, f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        df = pd.DataFrame([r.to_dict() for r in self.results])
        df.to_csv(filepath, index=False)
        
        debug_print(f"📄 CSV report generated: {filepath}")
        return filepath

    def generate_all_reports(self) -> Dict[str, str]:
        """Generate all configured report formats"""
        reports = {}
        
        if self.config.generate_html_report:
            reports['html'] = self.generate_html_report()
        if self.config.generate_json_report:
            reports['json'] = self.generate_json_report()
        if self.config.generate_csv_report:
            reports['csv'] = self.generate_csv_report()
        
        return reports


# =============================================================================
# 🎛️ MAIN TEST RUNNER - Streamlit Integration
# =============================================================================

def run_automated_tests_ui() -> None:
    """
    Streamlit UI for running automated tests.
    Call this function to launch the test runner interface.
    """
    st.set_page_config(page_title="🧪 TenderAI Test Runner", layout="wide")
    
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; border-radius: 12px; color: white; margin-bottom: 2rem;">
        <h1 style="margin: 0;">🧪 Automated Test Runner</h1>
        <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">Test all functions with different user roles</p>
    </div>
    """, unsafe_allow_html=True)
    
    # =============================================================================
    # ⚙️ CONFIGURATION SECTION
    # =============================================================================
    with st.expander("⚙️ Test Configuration", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 👥 Roles to Test")
            selected_roles = st.multiselect(
                "Select user roles",
                options=[r.value for r in UserRole],
                default=['public', 'free_user', 'professional_user', 'admin'],
                help="Test functions with different permission levels"
            )
        
        with col2:
            st.markdown("### 🎯 Target Functions")
            target_option = st.radio(
                "Functions to test",
                options=["All discovered functions", "Specific functions only"],
                index=0
            )
            
            if target_option == "Specific functions only":
                # Discover functions for selection
                functions = FunctionDiscoverer.discover_functions()
                selected_functions = st.multiselect(
                    "Select functions",
                    options=list(functions.keys()),
                    default=[f for f in functions.keys() if 'analysis' in f.lower() or 'page' in f.lower()]
                )
            else:
                selected_functions = None
        
        with col3:
            st.markdown("### ⚡ Execution Settings")
            delay = st.slider("Delay between tests (ms)", 0, 1000, 100)
            timeout = st.number_input("Max time per test (seconds)", 10, 120, 30)
            verbose = st.checkbox("Verbose logging", value=True)
    
    # =============================================================================
    # 🚀 EXECUTION SECTION
    # =============================================================================
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    
    with col2:
        run_button = st.button("🚀 Run Tests", type="primary", use_container_width=True)
        
        if run_button:
            with st.spinner("🔍 Discovering functions..."):
                # Build config
                config = TestConfig(
                    roles_to_test=[UserRole(r) for r in selected_roles],
                    target_functions=selected_functions if target_option == "Specific functions only" else None,
                    delay_between_tests_ms=delay,
                    max_execution_time_per_test_sec=timeout,
                    enable_verbose_logging=verbose,
                )
                
                # Discover functions
                functions = FunctionDiscoverer.discover_functions()
                st.info(f"🔍 Found {len(functions)} testable functions")
                
                # Run tests
                executor = TestExecutor(config)
                results = executor.run_all_tests(functions)
                
                # Generate reports
                reporter = ReportGenerator(results, config)
                reports = reporter.generate_all_reports()
                
                # Store in session for display
                st.session_state.test_results = results
                st.session_state.test_summary = reporter.summary
                st.session_state.test_reports = reports
                
                st.success(f"✅ Tests complete! {reporter.summary['passed']}/{reporter.summary['total_tests']} passed")
    
    # =============================================================================
    # 📊 RESULTS DISPLAY
    # =============================================================================
    if 'test_results' in st.session_state:
        st.markdown("---")
        st.markdown("## 📊 Test Results")
        
        summary = st.session_state.test_summary
        
        # Summary cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tests", summary['total_tests'])
        with col2:
            st.metric("✅ Passed", summary['passed'], delta=f"{summary['pass_rate']}% pass rate")
        with col3:
            st.metric("❌ Failed", summary['failed'])
        with col4:
            st.metric("💥 Errors", summary['errors'])
        
        # Role breakdown chart
        if summary['role_breakdown']:
            st.markdown("### 📈 Results by Role")
            role_df = pd.DataFrame([
                {
                    'Role': role,
                    'Total': stats['total'],
                    'Passed': stats['passed'],
                    'Pass Rate': stats['pass_rate']
                }
                for role, stats in summary['role_breakdown'].items()
            ])
            st.bar_chart(role_df.set_index('Role')['Pass Rate'])
        
        # Detailed results table
        st.markdown("### 🔍 Detailed Results")
        
        results_df = pd.DataFrame([r.to_dict() for r in st.session_state.test_results])
        
        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            role_filter = st.multiselect("Filter by Role", options=list(UserRole.__members__.keys()), default=[])
        with col2:
            status_filter = st.multiselect("Filter by Status", options=['PASSED', 'FAILED', 'ERROR', 'SKIPPED'], default=[])
        with col3:
            search = st.text_input("🔍 Search")
        
        # Apply filters
        filtered_df = results_df.copy()
        if role_filter:
            filtered_df = filtered_df[filtered_df['role_tested'].isin(role_filter)]
        if status_filter:
            filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
        if search:
            filtered_df = filtered_df[
                filtered_df['function_name'].str.contains(search, case=False, na=False) |
                filtered_df['test_name'].str.contains(search, case=False, na=False)
            ]
        
        # =============================================================================
        # 📊 RESULTS DISPLAY (FIXED VERSION)
        # =============================================================================
        if 'test_results' in st.session_state and st.session_state.test_results:
            st.markdown("---")
            st.markdown("## 📊 Test Results")
            
            summary = st.session_state.test_summary
            
            # Summary cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Tests", summary['total_tests'])
            with col2:
                st.metric("✅ Passed", summary['passed'], delta=f"{summary['pass_rate']}% pass rate")
            with col3:
                st.metric("❌ Failed", summary['failed'])
            with col4:
                st.metric("💥 Errors", summary['errors'])
            
            # Role breakdown chart
            if summary.get('role_breakdown'):
                st.markdown("### 📈 Results by Role")
                role_data = [
                    {
                        'Role': role,
                        'Total': stats['total'],
                        'Passed': stats['passed'],
                        'Pass Rate': stats['pass_rate']
                    }
                    for role, stats in summary['role_breakdown'].items()
                ]
                if role_data:
                    role_df = pd.DataFrame(role_data)
                    st.bar_chart(role_df.set_index('Role')['Pass Rate'])
            
            # Detailed results table - FIXED: Handle empty results and ensure columns
            st.markdown("### 🔍 Detailed Results")
            
            # Convert results to list of dicts with explicit column handling
            results_list = [r.to_dict() for r in st.session_state.test_results]
            
            if results_list:
                results_df = pd.DataFrame(results_list)
                
                # Ensure all expected columns exist (handle missing columns gracefully)
                expected_columns = [
                    'test_name', 'function_name', 'role_tested', 'status', 
                    'execution_time_ms', 'error_message'
                ]
                for col in expected_columns:
                    if col not in results_df.columns:
                        results_df[col] = None  # Add missing columns with None values
                
                # Filters
                col1, col2, col3 = st.columns(3)
                with col1:
                    available_roles = results_df['role_tested'].dropna().unique().tolist()
                    role_filter = st.multiselect("Filter by Role", options=available_roles, default=[])
                with col2:
                    available_statuses = results_df['status'].dropna().unique().tolist()
                    status_filter = st.multiselect("Filter by Status", options=available_statuses, default=[])
                with col3:
                    search = st.text_input("🔍 Search")
                
                # Apply filters
                filtered_df = results_df.copy()
                if role_filter:
                    filtered_df = filtered_df[filtered_df['role_tested'].isin(role_filter)]
                if status_filter:
                    filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
                if search:
                    mask = filtered_df['function_name'].astype(str).str.contains(search, case=False, na=False) | \
                        filtered_df['test_name'].astype(str).str.contains(search, case=False, na=False)
                    filtered_df = filtered_df[mask]
                
                # Display table with safe column selection
                display_columns = [c for c in expected_columns if c in filtered_df.columns]
                if display_columns:
                    st.dataframe(
                        filtered_df[display_columns],
                        use_container_width=True,
                        column_config={
                            'status': st.column_config.SelectboxColumn(
                                "Status",
                                options=["PASSED", "FAILED", "ERROR", "SKIPPED"],
                                disabled=True
                            ),
                            'execution_time_ms': st.column_config.NumberColumn("Time (ms)", format="%.0f"),
                        }
                    )
                else:
                    st.warning("⚠️ No columns available to display")
            else:
                st.info("📭 No test results to display. Run tests first!")
            
            # Download reports
            st.markdown("### 📥 Download Reports")
            col1, col2, col3 = st.columns(3)
            
            reports = st.session_state.get('test_reports', {})
            
            with col1:
                if 'html' in reports and os.path.exists(reports['html']):
                    with open(reports['html'], 'rb') as f:
                        st.download_button(
                            "📄 Download HTML Report",
                            data=f.read(),
                            file_name=os.path.basename(reports['html']),
                            mime="text/html",
                            use_container_width=True
                        )
            
            with col2:
                if 'json' in reports and os.path.exists(reports['json']):
                    with open(reports['json'], 'rb') as f:
                        st.download_button(
                            "📋 Download JSON Report",
                            data=f.read(),
                            file_name=os.path.basename(reports['json']),
                            mime="application/json",
                            use_container_width=True
                        )
            
            with col3:
                if 'csv' in reports and os.path.exists(reports['csv']):
                    with open(reports['csv'], 'rb') as f:
                        st.download_button(
                            "📊 Download CSV Report",
                            data=f.read(),
                            file_name=os.path.basename(reports['csv']),
                            mime="text/csv",
                            use_container_width=True
                        )
            
            # Failed tests section
            failed_results = [r for r in st.session_state.test_results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
            if failed_results:
                st.markdown("---")
                st.markdown(f"### ⚠️ {len(failed_results)} Failed/Error Tests")
                
                for result in failed_results[:10]:  # Show first 10
                    with st.expander(f"❌ {result.test_name} - {str(result.error_message)[:100] if result.error_message else 'No error message'}"):
                        st.code(f"Function: {result.function_name}\nRole: {result.role_tested.value}\nTime: {result.execution_time_ms:.0f}ms")
                        if result.debug_output:
                            st.markdown("**Debug Output:**")
                            st.code("\n".join(result.debug_output[:20]), language="text")
                
                if len(failed_results) > 10:
                    st.info(f"... and {len(failed_results) - 10} more failed tests. Download full report for details.")
        
        elif 'test_results' in st.session_state:
            # Handle empty results list
            st.info("📭 Tests completed but no results were captured. Check debug output for details.")
        
        # Download reports
        st.markdown("### 📥 Download Reports")
        col1, col2, col3 = st.columns(3)
        
        reports = st.session_state.get('test_reports', {})
        
        with col1:
            if 'html' in reports:
                with open(reports['html'], 'rb') as f:
                    st.download_button(
                        "📄 Download HTML Report",
                        data=f.read(),
                        file_name=os.path.basename(reports['html']),
                        mime="text/html"
                    )
        
        with col2:
            if 'json' in reports:
                with open(reports['json'], 'rb') as f:
                    st.download_button(
                        "📋 Download JSON Report",
                        data=f.read(),
                        file_name=os.path.basename(reports['json']),
                        mime="application/json"
                    )
        
        with col3:
            if 'csv' in reports:
                with open(reports['csv'], 'rb') as f:
                    st.download_button(
                        "📊 Download CSV Report",
                        data=f.read(),
                        file_name=os.path.basename(reports['csv']),
                        mime="text/csv"
                    )
        
        # Failed tests section
        failed_results = [r for r in st.session_state.test_results if r.status in [TestStatus.FAILED, TestStatus.ERROR]]
        if failed_results:
            st.markdown("---")
            st.markdown(f"### ⚠️ {len(failed_results)} Failed/Error Tests")
            
            for result in failed_results[:10]:  # Show first 10
                with st.expander(f"❌ {result.test_name} - {result.error_message[:100]}"):
                    st.code(f"Function: {result.function_name}\nRole: {result.role_tested.value}\nTime: {result.execution_time_ms:.0f}ms")
                    if result.debug_output:
                        st.markdown("**Debug Output:**")
                        st.code("\n".join(result.debug_output[:20]), language="text")
            
            if len(failed_results) > 10:
                st.info(f"... and {len(failed_results) - 10} more failed tests. Download full report for details.")
    
    # =============================================================================
    # ℹ️ HELP SECTION
    # =============================================================================
    with st.expander("ℹ️ How to Use This Test Runner"):
        st.markdown("""
        ### 🎯 What This Does
        - Automatically discovers testable functions in your TenderAI app
        - Runs each function with different user roles (public, free, pro, admin, etc.)
        - Captures debug output, session state, and execution metrics
        - Generates interactive HTML, JSON, and CSV reports
        
        ### 🔧 Configuration Tips
        - **Start small**: Test 1-2 roles first to verify setup
        - **Use filters**: Focus on specific functions during development
        - **Enable verbose logging**: See detailed debug output for troubleshooting
        
        ### 🐛 Troubleshooting
        - **Timeout errors**: Increase "Max time per test" for slow functions
        - **Session state issues**: Ensure `initialize_session_state()` is called before tests
        - **Import errors**: Verify all module imports work in test environment
        
        ### 📊 Interpreting Results
        - ✅ **PASSED**: Function executed without errors for that role
        - ❌ **FAILED**: Function raised an expected error (e.g., permission denied)
        - 💥 **ERROR**: Unexpected error or timeout - investigate debug output
        - ⏭️ **SKIPPED**: Test was intentionally skipped (e.g., premium feature for free user)
        """)


# =============================================================================
# 🧪 QUICK START - Run tests programmatically
# =============================================================================

def run_quick_test_suite() -> Dict:
    """
    Quick programmatic test run for CI/CD or script usage.
    Returns summary dict with pass/fail counts.
    """
    # Minimal config for quick run
    config = TestConfig(
        roles_to_test=[UserRole.PUBLIC, UserRole.PROFESSIONAL_USER, UserRole.SYSTEM_ADMIN],
        target_functions=None,  # Test all discovered
        delay_between_tests_ms=50,
        max_execution_time_per_test_sec=20,
        enable_verbose_logging=False,
        output_dir="test_reports/quick",
    )
    
    # Run tests
    executor = TestExecutor(config)
    functions = FunctionDiscoverer.discover_functions()
    results = executor.run_all_tests(functions)
    
    # Generate minimal report
    reporter = ReportGenerator(results, config)
    
    return {
        'success': reporter.summary['pass_rate'] >= 90,
        'summary': reporter.summary,
        'failed_tests': [r.to_dict() for r in results if r.status in [TestStatus.FAILED, TestStatus.ERROR]],
    }


# =============================================================================
# 🎬 ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # Run as Streamlit app: streamlit run test_automation.py
    run_automated_tests_ui()