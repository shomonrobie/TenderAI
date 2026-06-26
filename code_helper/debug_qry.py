# migrations/complete_schema_migrator.py
"""
Complete database schema migrator with DRY RUN option.
Reads ALL table definitions from schema.py and syncs the database.
Adds missing tables, columns, and indexes - preserves existing data.

Usage:
    python migrations/complete_schema_migrator.py          # Run migration
    python migrations/complete_schema_migrator.py --dry-run  # Preview changes only
"""

import sqlite3
import re
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CompleteSchemaMigrator:
    """Complete schema migrator - reads all tables from schema.py"""
    
    def __init__(self, db_path="data/tender_system.db", dry_run=False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.conn = None
        self.cursor = None
        self.changes = {
            'tables_to_add': [],
            'columns_to_add': [],
            'indexes_to_add': []
        }
        
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        if not self.dry_run:
            print(f"✅ Connected to database: {self.db_path}")
        else:
            print(f"🔍 DRY RUN MODE - No changes will be made")
            print(f"   Database: {self.db_path}\n")
    
    def disconnect(self):
        """Disconnect from database"""
        if self.conn and not self.dry_run:
            self.conn.commit()
            self.conn.close()
        elif self.conn:
            self.conn.close()
    
    def get_existing_tables(self):
        """Get list of all existing tables"""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        return {row[0] for row in self.cursor.fetchall()}
    
    def get_table_columns(self, table_name):
        """Get all columns for a table with their details"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1]: {'type': row[2], 'notnull': row[3], 'default': row[4], 'pk': row[5]} 
                for row in self.cursor.fetchall()}
    
    def get_existing_indexes(self):
        """Get all existing indexes"""
        self.cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        return {row[0]: row[1] for row in self.cursor.fetchall()}
    
    def parse_table_definitions(self, create_sql):
        """
        Parse CREATE TABLE SQL to extract:
        - Table name
        - Column definitions
        """
        # Extract table name
        table_match = re.search(r'CREATE TABLE IF NOT EXISTS (\w+)', create_sql)
        if not table_match:
            table_match = re.search(r'CREATE TABLE (\w+)', create_sql)
        table_name = table_match.group(1) if table_match else None
        
        if not table_name:
            return None, None
        
        # Extract all column definitions
        columns = {}
        
        # Find content between first ( and last )
        content = create_sql[create_sql.find('(')+1:create_sql.rfind(')')]
        
        # Split into lines
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip foreign key constraints and other constraints
            if line.upper().startswith(('FOREIGN KEY', 'PRIMARY KEY', 'UNIQUE', 'CONSTRAINT')):
                continue
            
            # Parse column definition
            parts = line.split()
            if len(parts) >= 2:
                col_name = parts[0]
                if col_name.upper() not in ['CONSTRAINT', 'PRIMARY', 'FOREIGN', 'UNIQUE']:
                    col_type = parts[1]
                    columns[col_name] = {
                        'type': col_type,
                        'definition': line
                    }
        
        return table_name, columns
    
    def extract_all_tables_from_schema(self):
        """
        Extract ALL CREATE TABLE statements from schema.py
        """
        schema_path = Path(__file__).parent.parent / "database" / "schema.py"
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all CREATE TABLE statements
        pattern = r'cursor\.execute\(f?"""(CREATE TABLE IF NOT EXISTS \w+.*?)"""\)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        tables = {}
        for match in matches:
            sql = match.strip()
            name_match = re.search(r'CREATE TABLE IF NOT EXISTS (\w+)', sql)
            if name_match:
                table_name = name_match.group(1)
                tables[table_name] = sql
        
        return tables
    
    def extract_all_indexes_from_schema(self):
        """
        Extract all CREATE INDEX statements from schema.py
        """
        schema_path = Path(__file__).parent.parent / "database" / "schema.py"
        with open(schema_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all CREATE INDEX statements
        pattern = r'cursor\.execute\(f?"""(CREATE INDEX IF NOT EXISTS \w+.*?)"""\)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        indexes = {}
        for match in matches:
            sql = match.strip()
            name_match = re.search(r'CREATE INDEX IF NOT EXISTS (\w+)', sql)
            if name_match:
                index_name = name_match.group(1)
                indexes[index_name] = sql
        
        return indexes
    
    def check_missing_tables(self, required_tables):
        """Check which tables are missing"""
        existing_tables = self.get_existing_tables()
        missing_tables = []
        
        for table_name in required_tables.keys():
            if table_name not in existing_tables:
                missing_tables.append(table_name)
        
        return missing_tables
    
    def check_missing_columns(self, required_tables):
        """Check which columns are missing"""
        existing_tables = self.get_existing_tables()
        missing_columns = []
        
        for table_name, create_sql in required_tables.items():
            if table_name not in existing_tables:
                continue
            
            existing_columns = self.get_table_columns(table_name)
            _, required_columns = self.parse_table_definitions(create_sql)
            
            if not required_columns:
                continue
            
            for col_name in required_columns.keys():
                if col_name not in existing_columns:
                    missing_columns.append(f"{table_name}.{col_name}")
        
        return missing_columns
    
    def check_missing_indexes(self, required_indexes):
        """Check which indexes are missing"""
        existing_indexes = self.get_existing_indexes()
        missing_indexes = []
        
        for index_name in required_indexes.keys():
            if index_name not in existing_indexes:
                missing_indexes.append(index_name)
        
        return missing_indexes
    
    def add_missing_tables(self, required_tables):
        """Add missing tables from schema"""
        existing_tables = self.get_existing_tables()
        added_tables = []
        
        for table_name, create_sql in required_tables.items():
            if table_name not in existing_tables:
                if self.dry_run:
                    added_tables.append(table_name)
                else:
                    try:
                        self.cursor.execute(create_sql)
                        added_tables.append(table_name)
                        print(f"  ✅ CREATED TABLE: {table_name}")
                    except Exception as e:
                        print(f"  ❌ Failed to create {table_name}: {e}")
        
        return added_tables
    
    def add_missing_columns(self, required_tables):
        """Add missing columns to existing tables"""
        existing_tables = self.get_existing_tables()
        added_columns = []
        
        for table_name, create_sql in required_tables.items():
            if table_name not in existing_tables:
                continue
            
            existing_columns = self.get_table_columns(table_name)
            _, required_columns = self.parse_table_definitions(create_sql)
            
            if not required_columns:
                continue
            
            for col_name, col_info in required_columns.items():
                if col_name not in existing_columns:
                    if self.dry_run:
                        added_columns.append(f"{table_name}.{col_name}")
                    else:
                        try:
                            col_def = col_info['definition']
                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
                            self.cursor.execute(alter_sql)
                            added_columns.append(f"{table_name}.{col_name}")
                            print(f"    ✅ ADDED COLUMN: {table_name}.{col_name}")
                        except Exception as e:
                            print(f"    ❌ Failed to add {col_name}: {e}")
        
        return added_columns
    
    def add_missing_indexes(self, required_indexes):
        """Add missing indexes"""
        existing_indexes = self.get_existing_indexes()
        added_indexes = []
        
        for index_name, index_sql in required_indexes.items():
            if index_name not in existing_indexes:
                if self.dry_run:
                    added_indexes.append(index_name)
                else:
                    try:
                        self.cursor.execute(index_sql)
                        added_indexes.append(index_name)
                        print(f"  ✅ CREATED INDEX: {index_name}")
                    except Exception as e:
                        print(f"  ❌ Failed to create {index_name}: {e}")
        
        return added_indexes
    
    def print_dry_run_report(self, missing_tables, missing_columns, missing_indexes, required_tables):
        """Print detailed dry run report"""
        print("\n" + "="*70)
        print("📋 DRY RUN REPORT - Changes that WILL be made")
        print("="*70)
        
        # Tables to add
        print(f"\n📌 TABLES TO CREATE ({len(missing_tables)}):")
        if missing_tables:
            for table in missing_tables:
                print(f"   - {table}")
                # Show first few columns of the table
                if table in required_tables:
                    _, columns = self.parse_table_definitions(required_tables[table])
                    if columns:
                        col_list = list(columns.keys())[:5]
                        print(f"     Columns: {', '.join(col_list)}")
                        if len(columns) > 5:
                            print(f"     ... and {len(columns) - 5} more")
        else:
            print("   No missing tables - all good!")
        
        # Columns to add
        print(f"\n📌 COLUMNS TO ADD ({len(missing_columns)}):")
        if missing_columns:
            # Group by table
            by_table = {}
            for col in missing_columns:
                table = col.split('.')[0]
                if table not in by_table:
                    by_table[table] = []
                by_table[table].append(col)
            
            for table, cols in by_table.items():
                print(f"   Table: {table}")
                for col in cols[:10]:
                    print(f"     - {col}")
                if len(cols) > 10:
                    print(f"     ... and {len(cols) - 10} more")
        else:
            print("   No missing columns - all good!")
        
        # Indexes to add
        print(f"\n📌 INDEXES TO CREATE ({len(missing_indexes)}):")
        if missing_indexes:
            for idx in missing_indexes:
                print(f"   - {idx}")
        else:
            print("   No missing indexes - all good!")
        
        print("\n" + "="*70)
        print(f"SUMMARY: Will add {len(missing_tables)} tables, {len(missing_columns)} columns, {len(missing_indexes)} indexes")
        print("="*70)
    
    def run_complete_migration(self):
        """Run complete schema migration"""
        
        print("\n" + "="*70)
        if self.dry_run:
            print("🔍 DRY RUN MODE - Previewing changes only")
        else:
            print("🔧 COMPLETE SCHEMA MIGRATION - Reading ALL tables from schema.py")
        print("="*70)
        print(f"Database: {self.db_path}\n")
        
        # Connect to database
        self.connect()
        
        # Extract all tables from schema.py
        print("📖 Reading schema.py...")
        required_tables = self.extract_all_tables_from_schema()
        print(f"   Found {len(required_tables)} table definitions")
        
        # Extract all indexes
        required_indexes = self.extract_all_indexes_from_schema()
        print(f"   Found {len(required_indexes)} index definitions")
        
        # Check what's missing
        print("\n🔍 Analyzing current database...")
        missing_tables = self.check_missing_tables(required_tables)
        missing_columns = self.check_missing_columns(required_tables)
        missing_indexes = self.check_missing_indexes(required_indexes)
        
        print(f"   Missing: {len(missing_tables)} tables, {len(missing_columns)} columns, {len(missing_indexes)} indexes")
        
        # If dry run, just show report and exit
        if self.dry_run:
            self.print_dry_run_report(missing_tables, missing_columns, missing_indexes, required_tables)
            self.disconnect()
            return {
                'dry_run': True,
                'tables_to_add': missing_tables,
                'columns_to_add': missing_columns,
                'indexes_to_add': missing_indexes
            }
        
        # Actual migration
        print("\n" + "="*70)
        print("📋 ADDING MISSING TABLES")
        print("="*70)
        added_tables = self.add_missing_tables(required_tables)
        
        print("\n" + "="*70)
        print("📋 ADDING MISSING COLUMNS")
        print("="*70)
        added_columns = self.add_missing_columns(required_tables)
        
        print("\n" + "="*70)
        print("📋 ADDING MISSING INDEXES")
        print("="*70)
        added_indexes = self.add_missing_indexes(required_indexes)
        
        # Commit all changes
        self.conn.commit()
        
        # Summary
        print("\n" + "="*70)
        print("📊 MIGRATION SUMMARY")
        print("="*70)
        print(f"  📋 Total tables in schema: {len(required_tables)}")
        print(f"  ✅ Tables added: {len(added_tables)}")
        print(f"  ✅ Columns added: {len(added_columns)}")
        print(f"  ✅ Indexes added: {len(added_indexes)}")
        
        if added_tables:
            print(f"\n  📌 New tables created:")
            for t in added_tables:
                print(f"     - {t}")
        
        if added_columns:
            print(f"\n  📌 New columns added (first 20):")
            for c in added_columns[:20]:
                print(f"     - {c}")
            if len(added_columns) > 20:
                print(f"     ... and {len(added_columns) - 20} more")
        
        # Disconnect
        self.disconnect()
        
        print("\n" + "="*70)
        print("✅ COMPLETE MIGRATION FINISHED SUCCESSFULLY!")
        print("="*70)
        
        return {
            'dry_run': False,
            'tables_added': added_tables,
            'columns_added': added_columns,
            'indexes_added': added_indexes
        }


def run_migration(dry_run=False):
    """Run the complete migration"""
    migrator = CompleteSchemaMigrator(dry_run=dry_run)
    result = migrator.run_complete_migration()
    return result


if __name__ == "__main__":
    # Check for --dry-run argument
    dry_run = '--dry-run' in sys.argv or '-d' in sys.argv
    
    if dry_run:
        print("\n🔍 DRY RUN MODE ENABLED")
        print("   Use without --dry-run to apply changes\n")
    
    result = run_migration(dry_run=dry_run)
    
    if dry_run:
        print("\n💡 To apply these changes, run:")
        print("   python migrations/complete_schema_migrator.py")