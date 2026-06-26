import sys
sys.path.append('D:/iTender')
from database.db_manager import DatabaseManager
from datetime import datetime

db = DatabaseManager()

test_data = {
    'tender_id': 'TEST-002',
    'tender_title': 'Test Tender with Analysis Type',
    'procuring_entity': 'PWD',
    'division': 'Dhaka',
    'district': 'Dhaka',
    'thana': 'Dhaka Sadar',
    'construction_type': 'works',
    'official_estimate': 5000000,
    'recommended_bid': 4500000,
    'success_probability': 0.65,
    'risk_level': 'MEDIUM',
    'competitor_count': 5,
    'analysis_type': 'Enhanced - ML Analysis',  # This should now work
    'bid_status': 'Pending',
    'competitor_bids': [4500000, 4600000, 4400000, 4700000, 4300000],
    'risk_strategy': 'moderate',
    'confidence_score': 0.75,
    'expected_profit': 500000,
    'expected_value': 325000,
    'slt_threshold': 4000000,
    'nppi_factor': 0.92,
    'weighted_average': 4300000
}

result = db.save_analysis(1, 1, test_data)
print(f"Save result: {result}")