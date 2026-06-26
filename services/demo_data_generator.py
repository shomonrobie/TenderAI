# services/demo_data_generator.py

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class DemoDataGenerator:
    """Generate realistic demo data for new companies"""
    
    def __init__(self, db):
        self.db = db
        self.repository = None  # Will be initialized when needed
    
    def _get_repository(self):
        """Lazy load repository"""
        if self.repository is None:
            from database.tenant_rate_repository import TenantRateRepository
            self.repository = TenantRateRepository()
        return self.repository
    
    def generate_pwd_demo_book(
        self, 
        company_id: int, 
        user_id: int,
        book_name: str = "Demo PWD Rates",
        description: str = "Demo PWD rate book for testing"
    ) -> Dict[str, Any]:
        """Generate a demo PWD rate book"""
        
        repo = self._get_repository()
    
        # ✅ Check if book already exists
        existing = self._get_existing_demo_books(company_id)
        if 'PWD' in existing:
            logger.info(f"PWD demo book already exists: {existing['PWD']}")
            return {
                'success': True,
                'book_id': existing['PWD']['id'],
                'items_created': 0,
                'message': 'Book already exists',
                'skipped': True
            }
    
        
        # Create rate book - ensure is_demo = 1
        book_id = repo.create_rate_book({
            'tenant_id': company_id,
            'tenant_type': 'company',
            'name': book_name,
            'source_type': 'PWD',
            'description': description,
            'is_active': 1,
            'is_archived': 0,
            'is_demo': 1,  # ✅ CRITICAL: Mark as demo
            'environment_mode': 'DEMO',
            'data_source_type': 'DEMO',
            'created_by': user_id
        })
        
        logger.info(f"Created demo PWD book {book_id} for company {company_id}")
        
        # Create version
        version_id = repo.create_rate_version({
            'rate_book_id': book_id,
            'version_name': 'Demo Version 1.0',
            'effective_from': datetime.now().date().isoformat(),
            'is_current': 1,
            'is_demo': 1,  # ✅ Mark version as demo
            'notes': 'Automatically generated demo data',
            'created_by': user_id
        })
        
        logger.info(f"Created demo PWD version {version_id}")
        
        # Generate demo PWD items
        items = self._generate_pwd_demo_items()
        
        created_count = 0
        for item in items:
            try:
                # ✅ Check if item already exists
                existing = repo.get_connection()
                cursor = existing.cursor()
                cursor.execute("""
                    SELECT id FROM tenant_rate_items 
                    WHERE rate_book_id = ? AND item_code = ? AND is_archived = 0
                """, (book_id, item['code']))
                existing_item = cursor.fetchone()
                existing.close()
                
                if existing_item:
                    logger.info(f"Item {item['code']} already exists, skipping")
                    continue
                
                item_id = repo.create_rate_item({
                    'rate_book_id': book_id,
                    'master_reference_type': 'PWD',
                    'master_chapter_number': item.get('chapter'),
                    'item_code': item['code'],
                    'item_description': item['description'],
                    'unit': item['unit'],
                    'is_custom': 0,
                    'is_demo': 1,  # ✅ Mark item as demo
                    'created_by': user_id
                })
                
                logger.info(f"Created demo item {item['code']} with ID {item_id}")
                
                # Add pricing
                base_rate = item.get('base_rate', 1000)
                for level, discount in [('ECONOMY', 0.22), ('MARKET', 0.18), ('PREMIUM', 0.14)]:
                    price = base_rate * (1 - discount)
                    repo.update_pricing(
                        version_id=version_id,
                        item_id=item_id,
                        pricing_level=level,
                        price=round(price, 2),
                        user_id=user_id
                    )
                
                created_count += 1
                
            except Exception as e:
                logger.error(f"Could not add demo item {item.get('code')}: {e}")
        
        # Log generation
        self._log_generation(company_id, user_id, 'PWD', created_count)
        
        return {
            'success': True,
            'book_id': book_id,
            'version_id': version_id,
            'items_created': created_count,
            'message': f'Generated {created_count} demo PWD items'
        }

    
    def generate_lged_demo_book(
        self, 
        company_id: int, 
        user_id: int,
        book_name: str = "Demo LGED Rates",
        description: str = "Demo LGED rate book for testing"
    ) -> Dict[str, Any]:
        """Generate a demo LGED rate book"""
        
        repo = self._get_repository()
    
        # ✅ Check if book already exists
        existing = self._get_existing_demo_books(company_id)
        if 'CUSTOM' in existing:
            logger.info(f"Custom demo book already exists: {existing['CUSTOM']}")
            return {
                'success': True,
                'book_id': existing['CUSTOM']['id'],
                'items_created': 0,
                'message': 'Book already exists',
                'skipped': True
            }
        
        
        book_id = repo.create_rate_book({
            'tenant_id': company_id,
            'tenant_type': 'company',
            'name': book_name,
            'source_type': 'LGED',
            'description': description,
            'is_active': 1,
            'is_archived': 0,
            'created_by': user_id
        })
        
        version_id = repo.create_rate_version({
            'rate_book_id': book_id,
            'version_name': 'Demo Version 1.0',
            'effective_from': datetime.now().date().isoformat(),
            'is_current': 1,
            'notes': 'Automatically generated demo data',
            'created_by': user_id
        })
        
        items = self._generate_lged_demo_items()
        
        created_count = 0
        for item in items:
            try:
                item_id = repo.create_rate_item({
                    'rate_book_id': book_id,
                    'master_reference_type': 'LGED',
                    'master_chapter_number': item.get('chapter'),
                    'master_section_number': item.get('section'),
                    'item_code': item['code'],
                    'item_description': item['description'],
                    'unit': item['unit'],
                    'is_custom': 0,
                    'is_demo': 1,
                    'created_by': user_id
                })
                
                base_rate = item.get('base_rate', 1000)
                for level, discount in [('ECONOMY', 0.22), ('MARKET', 0.18), ('PREMIUM', 0.14)]:
                    price = base_rate * (1 - discount)
                    repo.update_pricing(
                        version_id=version_id,
                        item_id=item_id,
                        pricing_level=level,
                        price=round(price, 2),
                        user_id=user_id
                    )
                
                created_count += 1
                
            except Exception as e:
                logger.warning(f"Could not add demo item {item.get('code')}: {e}")
        
        self._log_generation(company_id, user_id, 'LGED', created_count)
        
        return {
            'success': True,
            'book_id': book_id,
            'version_id': version_id,
            'items_created': created_count,
            'message': f'Generated {created_count} demo LGED items'
        }
    
    def generate_custom_demo_book(
        self, 
        company_id: int, 
        user_id: int,
        book_name: str = "Demo Custom Rates",
        description: str = "Demo custom rate book for testing"
    ) -> Dict[str, Any]:
        """Generate a demo custom rate book"""
        
        repo = self._get_repository()
        
        book_id = repo.create_rate_book({
            'tenant_id': company_id,
            'tenant_type': 'company',
            'name': book_name,
            'source_type': 'CUSTOM',
            'description': description,
            'is_active': 1,
            'is_archived': 0,
            'created_by': user_id
        })
        
        version_id = repo.create_rate_version({
            'rate_book_id': book_id,
            'version_name': 'Demo Version 1.0',
            'effective_from': datetime.now().date().isoformat(),
            'is_current': 1,
            'notes': 'Automatically generated demo data',
            'created_by': user_id
        })
        
        items = self._generate_custom_demo_items()
        
        created_count = 0
        for item in items:
            try:
                item_id = repo.create_rate_item({
                    'rate_book_id': book_id,
                    'master_reference_type': 'CUSTOM',
                    'item_code': item['code'],
                    'item_description': item['description'],
                    'unit': item['unit'],
                    'is_custom': 1,
                    'is_demo': 1,
                    'created_by': user_id
                })
                
                base_rate = item.get('base_rate', 1000)
                for level, discount in [('ECONOMY', 0.22), ('MARKET', 0.18), ('PREMIUM', 0.14)]:
                    price = base_rate * (1 - discount)
                    repo.update_pricing(
                        version_id=version_id,
                        item_id=item_id,
                        pricing_level=level,
                        price=round(price, 2),
                        user_id=user_id
                    )
                
                created_count += 1
                
            except Exception as e:
                logger.warning(f"Could not add demo item {item.get('code')}: {e}")
        
        self._log_generation(company_id, user_id, 'CUSTOM', created_count)
        
        return {
            'success': True,
            'book_id': book_id,
            'version_id': version_id,
            'items_created': created_count,
            'message': f'Generated {created_count} demo custom items'
        }
    
    def generate_all_demo_data(
        self, 
        company_id: int, 
        user_id: int
    ) -> Dict[str, Any]:
        """Generate all demo data for a company"""
        
        results = {
            'pwd': None,
            'lged': None,
            'custom': None,
            'total_items': 0
        }
        
        # Check what already exists
        existing = self._get_existing_demo_books(company_id)
        
        # Generate PWD demo (skip if exists)
        if 'PWD' not in existing:
            pwd_result = self.generate_pwd_demo_book(company_id, user_id)
            results['pwd'] = pwd_result
            if not pwd_result.get('skipped', False):
                results['total_items'] += pwd_result.get('items_created', 0)
        else:
            logger.info("PWD demo book already exists, skipping creation")
            results['pwd'] = {'skipped': True, 'book_id': existing['PWD']['id']}
        
        # Generate LGED demo (skip if exists)
        if 'LGED' not in existing:
            lged_result = self.generate_lged_demo_book(company_id, user_id)
            results['lged'] = lged_result
            if not lged_result.get('skipped', False):
                results['total_items'] += lged_result.get('items_created', 0)
        else:
            logger.info("LGED demo book already exists, skipping creation")
            results['lged'] = {'skipped': True, 'book_id': existing['LGED']['id']}
        
        # Generate custom demo (skip if exists)
        if 'CUSTOM' not in existing:
            custom_result = self.generate_custom_demo_book(company_id, user_id)
            results['custom'] = custom_result
            if not custom_result.get('skipped', False):
                results['total_items'] += custom_result.get('items_created', 0)
        else:
            logger.info("Custom demo book already exists, skipping creation")
            results['custom'] = {'skipped': True, 'book_id': existing['CUSTOM']['id']}
        
        # Update company status if any new items were created
        if results['total_items'] > 0:
            self._update_company_status(company_id, 'DEMO')
        
        return {
            'success': True,
            'results': results,
            'total_items': results['total_items'],
            'message': f'Successfully generated {results["total_items"]} demo items'
        }

    def _generate_pwd_demo_items(self) -> List[Dict]:
        """Generate realistic PWD demo items"""
        items = []
        
        # PWD Chapters and items
        pwd_data = [
            {'chapter': '01', 'items': [
                ('01.1.1', 'Site Clearance and Preparation', 'sqm', 150),
                ('01.1.2', 'Demolition of Existing Structures', 'cum', 500),
                ('01.1.3', 'Removal of Debris', 'cum', 350),
                ('01.2.1', 'Setting Out Works', 'job', 2500),
                ('01.2.2', 'Construction of Site Office', 'sqm', 1200),
            ]},
            {'chapter': '02', 'items': [
                ('02.1.1', 'Earth Excavation in Ordinary Soil', 'cum', 450),
                ('02.1.2', 'Earth Excavation in Hard Soil', 'cum', 650),
                ('02.1.3', 'Earth Excavation in Rocky Soil', 'cum', 1200),
                ('02.2.1', 'Earth Filling and Compaction', 'cum', 300),
                ('02.2.2', 'Sand Filling', 'cum', 800),
                ('02.2.3', 'Granular Fill', 'cum', 950),
            ]},
            {'chapter': '03', 'items': [
                ('03.1.1', 'Plain Cement Concrete 1:3:6', 'cum', 5500),
                ('03.1.2', 'Plain Cement Concrete 1:2:4', 'cum', 6500),
                ('03.2.1', 'Reinforced Cement Concrete 1:1.5:3', 'cum', 8500),
                ('03.2.2', 'Reinforced Cement Concrete 1:2:4', 'cum', 7500),
                ('03.3.1', 'Formwork for Columns', 'sqm', 800),
                ('03.3.2', 'Formwork for Beams', 'sqm', 750),
                ('03.3.3', 'Formwork for Slabs', 'sqm', 700),
            ]},
            {'chapter': '04', 'items': [
                ('04.1.1', 'Mild Steel Reinforcement (Grade 40)', 'kg', 120),
                ('04.1.2', 'Mild Steel Reinforcement (Grade 60)', 'kg', 140),
                ('04.2.1', 'Structural Steel Fabrication', 'kg', 180),
                ('04.2.2', 'Structural Steel Erection', 'kg', 160),
                ('04.3.1', 'Welding Works', 'meter', 250),
            ]},
            {'chapter': '05', 'items': [
                ('05.1.1', 'Cement Plaster 1:4', 'sqm', 350),
                ('05.1.2', 'Cement Plaster 1:6', 'sqm', 300),
                ('05.2.1', 'White Cement Plaster', 'sqm', 450),
                ('05.3.1', 'Painting with Emulsion Paint', 'sqm', 200),
                ('05.3.2', 'Painting with Oil Paint', 'sqm', 250),
                ('05.4.1', 'Wall Tiling with Ceramic Tiles', 'sqm', 800),
                ('05.4.2', 'Floor Tiling with Ceramic Tiles', 'sqm', 700),
                ('05.5.1', 'False Ceiling with Gypsum Board', 'sqm', 900),
            ]},
        ]
        
        for chapter in pwd_data:
            chap_num = chapter['chapter']
            for code, desc, unit, base_rate in chapter['items']:
                items.append({
                    'code': code,
                    'description': desc,
                    'unit': unit,
                    'base_rate': base_rate,
                    'chapter': chap_num
                })
        
        return items
    
    def _generate_lged_demo_items(self) -> List[Dict]:
        """Generate realistic LGED demo items"""
        items = []
        
        # LGED Chapters and items
        lged_data = [
            {'chapter': '1', 'section': '1.01', 'items': [
                ('1.01.01', 'Site Clearance', 'sqm', 150),
                ('1.01.02', 'Survey and Setting Out', 'job', 3000),
                ('1.01.03', 'Construction of Site Facilities', 'job', 5000),
            ]},
            {'chapter': '1', 'section': '1.02', 'items': [
                ('1.02.01', 'Earth Excavation', 'cum', 500),
                ('1.02.02', 'Earth Filling and Compaction', 'cum', 350),
                ('1.02.03', 'Sand Cushion', 'cum', 850),
            ]},
            {'chapter': '2', 'section': '2.01', 'items': [
                ('2.01.01', 'Sub-Base with Granular Material', 'cum', 1200),
                ('2.01.02', 'Sub-Base with Brick Aggregate', 'cum', 1500),
                ('2.01.03', 'Sub-Base with Stone Aggregate', 'cum', 1800),
            ]},
            {'chapter': '2', 'section': '2.02', 'items': [
                ('2.02.01', 'Base Course with Stone Aggregate', 'cum', 2200),
                ('2.02.02', 'Base Course with Brick Aggregate', 'cum', 1800),
                ('2.02.03', 'Base Course with Bituminous Material', 'cum', 2800),
            ]},
            {'chapter': '3', 'section': '3.01', 'items': [
                ('3.01.01', 'Bituminous Pavement (Single Coat)', 'sqm', 600),
                ('3.01.02', 'Bituminous Pavement (Double Coat)', 'sqm', 850),
                ('3.01.03', 'Bituminous Pavement (Thick Coat)', 'sqm', 1100),
                ('3.01.04', 'RCC Pavement', 'sqm', 1500),
            ]},
            {'chapter': '3', 'section': '3.02', 'items': [
                ('3.02.01', 'RCC Drainage Works', 'meter', 800),
                ('3.02.02', 'Brick Drainage Works', 'meter', 400),
                ('3.02.03', 'Culvert Construction (Small)', 'job', 15000),
                ('3.02.04', 'Culvert Construction (Medium)', 'job', 35000),
                ('3.02.05', 'Culvert Construction (Large)', 'job', 65000),
            ]},
            {'chapter': '4', 'section': '4.01', 'items': [
                ('4.01.01', 'Bridge Construction (Short Span)', 'meter', 45000),
                ('4.01.02', 'Bridge Construction (Medium Span)', 'meter', 75000),
                ('4.01.03', 'Bridge Construction (Long Span)', 'meter', 120000),
                ('4.01.04', 'Bridge Approach Works', 'job', 25000),
            ]},
        ]
        
        for chapter in lged_data:
            chap_num = chapter['chapter']
            section = chapter['section']
            for code, desc, unit, base_rate in chapter['items']:
                items.append({
                    'code': code,
                    'description': desc,
                    'unit': unit,
                    'base_rate': base_rate,
                    'chapter': chap_num,
                    'section': section
                })
        
        return items
    
    def _generate_custom_demo_items(self) -> List[Dict]:
        """Generate realistic custom demo items"""
        
        custom_items = [
            ('CUST001', 'Specialized Equipment Rental', 'day', 2500),
            ('CUST002', 'Skilled Labor (Supervisor)', 'day', 1200),
            ('CUST003', 'Skilled Labor (Technician)', 'day', 800),
            ('CUST004', 'Unskilled Labor', 'day', 500),
            ('CUST005', 'Transportation Services', 'trip', 3000),
            ('CUST006', 'Quality Testing Services', 'test', 1500),
            ('CUST007', 'Safety Equipment and PPE', 'set', 2000),
            ('CUST008', 'Temporary Utilities Setup', 'job', 5000),
            ('CUST009', 'Design and Engineering Services', 'hour', 2000),
            ('CUST010', 'Project Management Services', 'month', 25000),
            ('CUST011', 'Environmental Compliance', 'job', 8000),
            ('CUST012', 'Public Liability Insurance', 'year', 15000),
            ('CUST013', 'Performance Bond', 'percent', 5000),
            ('CUST014', 'Contingency Fund', 'percent', 10000),
            ('CUST015', 'Tax and VAT', 'percent', 7500),
        ]
        
        items = []
        for code, desc, unit, base_rate in custom_items:
            items.append({
                'code': code,
                'description': desc,
                'unit': unit,
                'base_rate': base_rate
            })
        
        return items
    
    def _log_generation(self, company_id: int, user_id: int, gen_type: str, count: int):
        """Log demo data generation"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO demo_data_generation_log 
                (company_id, user_id, generation_type, items_generated, status, completed_at)
                VALUES (?, ?, ?, ?, 'completed', CURRENT_TIMESTAMP)
            """, (company_id, user_id, gen_type, count))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Could not log generation: {e}")
    
    def _update_company_status(self, company_id: int, mode: str):
        """Update company environment status"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE companies 
                SET environment_mode = ?, 
                    demo_data_generated_at = CURRENT_TIMESTAMP,
                    onboarding_status = 'in_progress'
                WHERE id = ?
            """, (mode, company_id))
            
            # Update onboarding status
            cursor.execute("""
                INSERT OR REPLACE INTO company_onboarding_status 
                (company_id, demo_generated, demo_generated_at, last_step_updated_at)
                VALUES (?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (company_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.warning(f"Could not update company status: {e}")
    def _get_existing_demo_books(self, company_id: int) -> Dict[str, Any]:
        """Get existing demo books for a company"""
        try:
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, source_type, is_demo
                FROM tenant_rate_books 
                WHERE tenant_id = ? AND is_demo = 1 AND is_archived = 0
            """, (company_id,))
            
            books = cursor.fetchall()
            conn.close()
            
            existing = {}
            for book in books:
                existing[book['source_type']] = {
                    'id': book['id'],
                    'name': book['name']
                }
            return existing
            
        except Exception as e:
            logger.error(f"Error checking existing demo books: {e}")
            return {}
        