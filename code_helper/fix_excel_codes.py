def fix_excel_codes(input_path, output_path):
    """Fix Excel file where item codes are being interpreted as dates"""
    import pandas as pd
    
    # Read as string to preserve formatting
    df = pd.read_excel(input_path, sheet_name=0, dtype=str)
    
    # Fix the first column
    col_name = df.columns[0]
    
    def fix_code(val):
        if pd.isna(val):
            return val
        val_str = str(val)
        # If it looks like a date (contains hyphens or slashes)
        if '-' in val_str or '/' in val_str:
            # Try to reconstruct the code
            parts = val_str.replace('-', '.').replace('/', '.').split('.')
            if len(parts) >= 3:
                return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return val_str
    
    df[col_name] = df[col_name].apply(fix_code)
    
    # Save with formatting preserved
    df.to_excel(output_path, index=False)
    print(f"Fixed file saved to: {output_path}")

# Usage
# fix_excel_codes('lged-2.xlsx', 'lged-2-fixed.xlsx')