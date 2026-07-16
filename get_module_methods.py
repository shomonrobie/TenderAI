# scripts/get_module_methods.py

"""
Script to extract and list all methods from a Python module
Usage: python get_module_methods.py <module_path>
Example: python get_module_methods.py database/crud_operations.py
"""

import ast
import sys
import os
import importlib.util
from typing import List, Dict, Set


def get_methods_from_file(filepath: str) -> Dict[str, List[str]]:
    """
    Extract all method names from a Python file using AST parsing.
    This works even if the file has syntax errors (as long as AST can parse it).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        result = {
            'classes': {},
            'functions': [],
            'all_methods': []
        }
        
        for node in ast.walk(tree):
            # Class definitions
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_name = item.name
                        # Skip private methods if needed
                        if not method_name.startswith('_'):
                            methods.append(method_name)
                            result['all_methods'].append(f"{class_name}.{method_name}")
                if methods:
                    result['classes'][class_name] = methods
            
            # Top-level functions
            elif isinstance(node, ast.FunctionDef):
                func_name = node.name
                if not func_name.startswith('_'):
                    result['functions'].append(func_name)
                    result['all_methods'].append(func_name)
        
        return result
        
    except SyntaxError as e:
        print(f"⚠️ Syntax error in file: {e}")
        print("   Trying to parse with error recovery...")
        
        # Try to read and parse line by line for basic method extraction
        return get_methods_line_by_line(filepath)


def get_methods_line_by_line(filepath: str) -> Dict[str, List[str]]:
    """
    Fallback method: extract method names by scanning lines.
    This is less accurate but works even with syntax errors.
    """
    result = {
        'classes': {},
        'functions': [],
        'all_methods': []
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_class = None
        in_class = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check for class definition
            if stripped.startswith('class '):
                match = stripped.split('class ')[1].split('(')[0].strip()
                if match:
                    current_class = match
                    in_class = True
                    if current_class not in result['classes']:
                        result['classes'][current_class] = []
                continue
            
            # Check for method definition inside class
            if in_class and stripped.startswith('def '):
                # Check if it's a method (indented)
                if line.startswith(('    ', '\t')):
                    method_name = stripped.split('def ')[1].split('(')[0].strip()
                    if not method_name.startswith('_'):
                        result['classes'][current_class].append(method_name)
                        result['all_methods'].append(f"{current_class}.{method_name}")
            
            # Check for top-level function (not indented)
            elif not in_class and stripped.startswith('def '):
                func_name = stripped.split('def ')[1].split('(')[0].strip()
                if not func_name.startswith('_'):
                    result['functions'].append(func_name)
                    result['all_methods'].append(func_name)
            
            # Reset class tracking when out of indentation
            elif in_class and stripped and not line.startswith(('    ', '\t', '    ', 'def ')):
                # Check if it's a class method or property
                if not stripped.startswith('@') and not stripped.startswith('#'):
                    in_class = False
                    current_class = None
        
        # Remove duplicates
        for class_name in result['classes']:
            result['classes'][class_name] = list(set(result['classes'][class_name]))
        
        result['functions'] = list(set(result['functions']))
        result['all_methods'] = list(set(result['all_methods']))
        
    except Exception as e:
        print(f"❌ Error in line-by-line parsing: {e}")
    
    return result


def get_methods_by_import(module_path: str, module_name: str = None) -> Dict[str, List[str]]:
    """
    Import a module and extract all methods from it.
    """
    if module_name is None:
        module_name = os.path.splitext(os.path.basename(module_path))[0]
    
    try:
        # Try to import the module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            raise ImportError(f"Could not load spec for {module_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        result = {
            'classes': {},
            'functions': [],
            'all_methods': []
        }
        
        # Get all attributes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            
            # Skip private attributes
            if attr_name.startswith('_'):
                continue
            
            # Check if it's a class
            if isinstance(attr, type):
                methods = []
                for method_name in dir(attr):
                    if method_name.startswith('_'):
                        continue
                    method = getattr(attr, method_name)
                    if callable(method):
                        methods.append(method_name)
                        result['all_methods'].append(f"{attr_name}.{method_name}")
                if methods:
                    result['classes'][attr_name] = methods
            
            # Check if it's a function
            elif callable(attr):
                result['functions'].append(attr_name)
                result['all_methods'].append(attr_name)
        
        return result
        
    except SyntaxError as e:
        print(f"⚠️ Syntax error in file: {e}")
        print("   Falling back to AST parsing...")
        return get_methods_from_file(module_path)
        
    except Exception as e:
        print(f"⚠️ Error importing module: {e}")
        print("   Falling back to AST parsing...")
        return get_methods_from_file(module_path)


def print_methods(results: Dict, module_name: str = None):
    """Pretty print the extracted methods"""
    
    if module_name:
        print(f"\n{'='*60}")
        print(f"📦 Module: {module_name}")
        print(f"{'='*60}\n")
    
    # Print classes and their methods
    if results.get('classes'):
        print("📚 CLASSES:")
        print("-" * 40)
        for class_name, methods in sorted(results['classes'].items()):
            print(f"\n  🏷️ {class_name}")
            print(f"     Methods ({len(methods)}):")
            for method in sorted(methods):
                print(f"       ✅ {method}()")
    
    # Print top-level functions
    if results.get('functions'):
        print("\n📋 TOP-LEVEL FUNCTIONS:")
        print("-" * 40)
        for func in sorted(results['functions']):
            print(f"  ✅ {func}()")
    
    # Summary
    total_methods = len(results.get('all_methods', []))
    total_classes = len(results.get('classes', {}))
    total_functions = len(results.get('functions', []))
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY:")
    print(f"  Total Classes: {total_classes}")
    print(f"  Total Functions: {total_functions}")
    print(f"  Total Methods: {total_methods}")
    print(f"{'='*60}\n")


def export_to_csv(results: Dict, filename: str = "methods_export.csv"):
    """Export methods to CSV file"""
    import csv
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Type', 'Class', 'Method'])
        
        # Class methods
        for class_name, methods in results.get('classes', {}).items():
            for method in methods:
                writer.writerow(['method', class_name, method])
        
        # Top-level functions
        for func in results.get('functions', []):
            writer.writerow(['function', '', func])
    
    print(f"✅ Exported to {filename}")


def main():
    """Main entry point"""
    
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python get_module_methods.py <module_path> [options]")
        print("\nOptions:")
        print("  --csv <filename>  Export to CSV file")
        print("  --ast             Use AST parsing (static analysis)")
        print("  --help            Show this help")
        sys.exit(1)
    
    module_path = sys.argv[1]
    use_ast = '--ast' in sys.argv
    csv_file = None
    
    # Check for CSV option
    for i, arg in enumerate(sys.argv):
        if arg == '--csv' and i + 1 < len(sys.argv):
            csv_file = sys.argv[i + 1]
    
    if not os.path.exists(module_path):
        print(f"❌ File not found: {module_path}")
        sys.exit(1)
    
    module_name = os.path.splitext(os.path.basename(module_path))[0]
    
    print(f"🔍 Analyzing: {module_path}")
    print(f"   Module name: {module_name}")
    print(f"   Method: {'AST parsing' if use_ast else 'Dynamic import'}")
    print()
    
    # Extract methods
    if use_ast:
        results = get_methods_from_file(module_path)
    else:
        results = get_methods_by_import(module_path, module_name)
    
    # Print results
    print_methods(results, module_name)
    
    # Export to CSV if requested
    if csv_file:
        export_to_csv(results, csv_file)
    
    # Return results for programmatic use
    return results


if __name__ == "__main__":
    main()