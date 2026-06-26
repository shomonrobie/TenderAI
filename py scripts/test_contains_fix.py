# test_contains_fix.py - Run with: python test_contains_fix.py
import sys
import warnings
import os

# =============================================================================
# ⚠️ SUPPRESS STREAMLIT WARNINGS BEFORE ANY IMPORTS
# =============================================================================
warnings.filterwarnings("ignore", message=".*missing ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*Session state.*")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Now import streamlit (warnings already suppressed)
import streamlit as st

# =============================================================================
# ✅ FIXED CLI_SessionState Class (Standalone Version)
# =============================================================================
class CLI_SessionState(dict):
    """Dict subclass that mimics Streamlit's session_state interface"""
    
    def __getattr__(self, key):
        """Allow st.session_state.key access"""
        if key in self:
            return self[key]
        raise AttributeError(f"'session_state' object has no attribute '{key}'")
    
    def __setattr__(self, key, value):
        """Allow st.session_state.key = value assignment"""
        self[key] = value
    
    # ✅ CRITICAL FIX: Use super() to avoid infinite recursion
    def __contains__(self, key):
        return super().__contains__(key)  # ← Calls dict.__contains__, not self.__contains__
    
    def to_dict(self):
        return dict(self)
    
    def clear(self):
        super().clear()
    
    def pop(self, key, default=None):
        return super().pop(key, default)
    
    def get(self, key, default=None):
        return super().get(key, default)


# =============================================================================
# 🧪 RUN TESTS
# =============================================================================
def test_cli_session_state():
    """Test all CLI_SessionState methods"""
    print("🧪 Testing CLI_SessionState fix...")
    
    # Create instance
    state = CLI_SessionState()
    
    # Test 1: Basic dict operations
    state['key1'] = 'value1'
    assert state['key1'] == 'value1', "❌ Basic set/get failed"
    print("✅ Test 1: Basic set/get")
    
    # Test 2: __contains__ (THE FIX)
    assert 'key1' in state, "❌ __contains__ failed for existing key"
    assert 'missing' not in state, "❌ __contains__ failed for missing key"
    print("✅ Test 2: __contains__ (recursion fix verified)")
    
    # Test 3: Attribute-style access
    state.key2 = 'value2'
    assert state.key2 == 'value2', "❌ Attribute-style access failed"
    print("✅ Test 3: Attribute-style access")
    
    # Test 4: get() with default
    assert state.get('key1') == 'value1', "❌ get() failed for existing key"
    assert state.get('missing', 'default') == 'default', "❌ get() default failed"
    print("✅ Test 4: get() with default")
    
    # Test 5: to_dict()
    d = state.to_dict()
    assert isinstance(d, dict), "❌ to_dict() didn't return dict"
    assert d['key1'] == 'value1', "❌ to_dict() missing data"
    print("✅ Test 5: to_dict()")
    
    # Test 6: clear()
    state.clear()
    assert len(state) == 0, "❌ clear() didn't empty state"
    print("✅ Test 6: clear()")
    
    # Test 7: Simulate main.py initialize_session_state pattern
    state = CLI_SessionState()
    keys_to_init = {'logged_in': False, 'user_id': None, 'page': 'home'}
    for key, default in keys_to_init.items():
        if key not in state:  # ← This line caused recursion before fix
            state[key] = default
    assert state['logged_in'] is False, "❌ Session init pattern failed"
    print("✅ Test 7: main.py initialize_session_state pattern")
    
    print("\n🎉 All tests passed! CLI_SessionState is recursion-safe.")
    return True


if __name__ == "__main__":
    try:
        success = test_cli_session_state()
        sys.exit(0 if success else 1)
    except RecursionError as e:
        print(f"\n💥 RecursionError detected: {e}")
        print("❌ The __contains__ fix was NOT applied correctly!")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)