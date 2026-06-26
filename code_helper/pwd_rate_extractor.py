
## Key Features of the Validation Approach:

### 1. **CSV Export for Manual Review**:
- Exports all extracted data to `pwd_rates_validation.csv`
- Creates a summary CSV with statistics
- Easy to open in Excel for visual inspection

### 2. **Comprehensive Validation Checks**:
- **Format validation**: Item number format, description quality
- **Rate validation**: Missing rates, negative values, invalid formats
- **Consistency checks**: Duplicate items, rate variations across regions
- **Unit validation**: Unknown units, missing units

### 3. **Validation Report**:
- JSON report with detailed statistics
- Category distribution
- Rate statistics by region
- Warning and error logs

### 4. **Interactive Process**:
- Shows validation results before database insertion
- Asks for confirmation before creating database
- Allows you to review CSV files first

### 5. **Quality Metrics**:
- Percentage of valid items
- Rate range analysis
- Variation detection (>20% differences flagged)

## To Run:

```bash
python pwd_rate_extractor.py