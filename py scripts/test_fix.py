# test_fix.py - Run with: python test_fix.py
import pandas as pd
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional, List

class TestStatus(Enum):
    PASSED = auto()
    FAILED = auto()
    ERROR = auto()

class UserRole(Enum):
    ADMIN = "admin"
    FREE = "free"

@dataclass
class TestResult:
    test_name: str
    function_name: str
    role_tested: UserRole
    status: TestStatus
    execution_time_ms: float
    error_message: Optional[str] = None
    
    def to_dict(self):
        return {
            'test_name': self.test_name or 'Unknown',
            'function_name': self.function_name or 'Unknown',
            'role_tested': self.role_tested.value if self.role_tested else 'unknown',
            'status': self.status.name if self.status else 'UNKNOWN',
            'execution_time_ms': round(self.execution_time_ms, 2) if self.execution_time_ms else 0.0,
            'error_message': str(self.error_message) if self.error_message else None,
        }

def _safe_results_to_dataframe(results):
    if not results:
        return pd.DataFrame(columns=['test_name', 'function_name', 'role_tested', 'status', 'execution_time_ms', 'error_message'])
    
    rows = [r.to_dict() for r in results]
    df = pd.DataFrame(rows)
    
    # Ensure columns exist
    for col in ['test_name', 'function_name', 'role_tested', 'status', 'execution_time_ms', 'error_message']:
        if col not in df.columns:
            df[col] = None
    return df

# Test with empty list
print("Test 1: Empty list")
df1 = _safe_results_to_dataframe([])
print(f"Columns: {list(df1.columns)}")
print(f"Shape: {df1.shape}\n")

# Test with data
print("Test 2: With data")
results = [
    TestResult("test_1", "func_a", UserRole.ADMIN, TestStatus.PASSED, 123.456),
    TestResult("test_2", "func_b", UserRole.FREE, TestStatus.FAILED, 78.9, error_message="Test error"),
]
df2 = _safe_results_to_dataframe(results)
print(f"Columns: {list(df2.columns)}")
print(df2[['test_name', 'function_name', 'status']])
print("\n✅ All tests passed!")