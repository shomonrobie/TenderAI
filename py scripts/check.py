import re
import sys
print("Checking for 'if var and len(var) > 0:' patterns in main.py...")
pattern = re.compile(r'if\s+(\w+)\s+and\s+len\(\1\)\s*>\s*0\s*:')
with open('main.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        match = pattern.search(line)
        if match:
            var_name = match.group(1)
            print(f"Line {i}: {line.strip()}  ← Check type of '{var_name}'")
        
print("Check completed.")
