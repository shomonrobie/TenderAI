# Changelog

## [3.0.0] - 2026-05-25

### Added
- **Unified Report Generation**: PDF and HTML reports now use same data source
- **PPR 2025 Calculation Breakdown**: Full formula and weighted average display
- **Visual Performance Dashboard**: 
  - Competitor distribution histogram
  - Win probability curve
  - Risk radar chart
  - 4-in-1 performance dashboard
- **Individual Registration**: Separate flow for consultants/freelancers
- **Detailed AI Recommendations**: Strategic analysis with key insights
- **Competitor Statistics**: Min, max, avg, std deviation display
- **3 Decimal Precision**: All bids shown with 3 decimal places

### Changed
- Refactored report generator to single unified class
- Improved competitor bid extraction from multiple data sources
- Enhanced PDF formatting to match HTML exactly
- Upgraded UI with better visual hierarchy

### Fixed
- PDF generation now includes all visualizations
- Competitor count display (was showing incorrect numbers)
- Password strength validation in registration
- Session state persistence across page navigation

### Removed
- Deprecated `st.components.v1.html` replaced with modern alternatives

## [2.0.0] - 2026-05-20

### Added
- Three-tier analysis (Basic, Advanced, Enhanced)
- PPR 2025 compliance checking
- Competitor master list management
- Historical data analysis

### Fixed
- Database migration issues
- Subscription plan enforcement

## [1.0.0] - 2026-05-01

### Added
- Initial release
- Basic tender analysis
- User authentication
- Company registration