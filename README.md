# 🏗️ TenderAI - AI-Powered Tender Management System

[![Version](https://img.shields.io/badge/version-3.0.0-blue.svg)](https://github.com/yourusername/tenderai)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)](https://streamlit.io/)

## 📋 Overview

TenderAI is an enterprise-grade tender management and bid optimization platform specifically designed for the Bangladesh construction industry. It uses AI/ML to analyze competitor bids, calculate PPR 2025 compliant recommendations, and generate comprehensive reports.

## ✨ Features

### Core Features
- **Three-Tier Analysis**: Basic, Advanced (PPR 2025), and Enhanced (ML) bid optimization
- **Unified Reporting**: Identical PDF and HTML reports with visual dashboards
- **PPR 2025 Compliance**: Full calculation breakdown with SLT threshold analysis
- **Competitor Intelligence**: Track and analyze competitor bidding patterns
- **Visual Dashboards**: 
  - Competitor distribution histogram
  - Win probability curve
  - Risk radar chart
  - Performance metrics dashboard
  - **Rate Management**: Import and manage PWD/LGED rate schedules
  - **BOQ Generation**: Create Bill of Quantities from rate schedules
  - **Bid Optimization**: 3-tier AI analysis (Basic, Advanced PPR 2025, Enhanced ML)
  - **Tender Management**: Complete tender lifecycle management
  - **Competitor Tracking**: Track and analyze competitor bids
  - **Subscription Management**: Plan-based access control
  - **Role-Based Access**: Granular permissions for team members


### User Management
- Company registration (requires admin approval)
- Individual registration (instant activation for consultants)
- Role-based access control (Admin, Company Admin, Individual, User)
- Subscription plans (Free, Basic, Professional, Enterprise)

### Data Export
- PDF reports with 3-decimal precision
- CSV exports for analysis comparison
- Historical data tracking

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tenderai.git
cd tenderai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run main.py
Configuration
Create .streamlit/secrets.toml:

toml
# Database configuration
database_path = "tenderai.db"

# Admin settings
admin_email = "admin@tenderai.com"
admin_password_hash = "your_hashed_password"

# Email settings (for notifications)
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_username = "your_email@gmail.com"
smtp_password = "your_app_password"
📊 Usage
Register Account: Choose company or individual registration

Login: Access your dashboard

Create Tender: Input tender details and competitor bids

Run Analysis: Get three-tier bid optimization

Generate Report: Download PDF or CSV with visualizations

🏗️ Project Structure
text
tenderai/
D:.
├───.streamlit
├───data
├───database
│   └───__pycache__
├───modules
│   └───__pycache__
├───pages
├───py scripts
├───tests
├───test_reports
│   └───cli
├───utils
│   └───__pycache__
├───venv
│   ├───etc
│   │   └───jupyter
│   │       └───nbconfig
│   │           └───notebook.d
│   ├───Include
│   ├───Lib
│   │   └───site-packages
│   │       ├───altair
│   │       │   ├───datasets
│   │       │   │   └───_metadata
│   │       │   ├───expr
│   │       │   ├───jupyter
│   │       │   │   └───js
│   │       │   ├───typing
│   │       │   ├───utils
│   │       │   └───vegalite
│   │       │       └───v6
│   │       │           └───schema
│   │       ├───altair-6.1.0.dist-info
│   │       │   └───licenses
│   │       ├───anyio
│   │       │   ├───abc
│   │       │   ├───streams
│   │       │   ├───_backends
│   │       │   └───_core
│   │       ├───anyio-4.13.0.dist-info
│   │       │   └───licenses
│   │       ├───attr
│   │       ├───attrs
│   │       ├───attrs-26.1.0.dist-info
│   │       │   └───licenses
│   │       ├───bcrypt
│   │       ├───bcrypt-5.0.0.dist-info
│   │       ├───blinker
│   │       ├───blinker-1.9.0.dist-info
│   │       ├───cachetools
│   │       ├───cachetools-7.0.6.dist-info
│   │       │   └───licenses
│   │       ├───certifi
│   │       ├───certifi-2026.4.22.dist-info
│   │       │   └───licenses
│   │       ├───charset_normalizer
│   │       │   └───cli
│   │       ├───charset_normalizer-3.4.7.dist-info
│   │       │   └───licenses
│   │       ├───click
│   │       ├───click-8.3.3.dist-info
│   │       │   └───licenses
│   │       ├───colorama
│   │       │   └───tests
│   │       ├───colorama-0.4.6.dist-info
│   │       │   └───licenses
│   │       ├───dateutil
│   │       │   ├───parser
│   │       │   ├───tz
│   │       │   └───zoneinfo
│   │       ├───git
│   │       │   ├───index
│   │       │   ├───objects
│   │       │   │   └───submodule
│   │       │   ├───refs
│   │       │   └───repo
│   │       ├───gitdb
│   │       │   ├───db
│   │       │   ├───test
│   │       │   └───utils
│   │       ├───gitdb-4.0.12.dist-info
│   │       ├───gitpython-3.1.49.dist-info
│   │       │   └───licenses
│   │       ├───google
│   │       │   ├───protobuf
│   │       │   │   ├───compiler
│   │       │   │   ├───internal
│   │       │   │   ├───pyext
│   │       │   │   ├───testdata
│   │       │   │   └───util
│   │       │   └───_upb
│   │       ├───h11
│   │       ├───h11-0.16.0.dist-info
│   │       │   └───licenses
│   │       ├───httptools
│   │       │   └───parser
│   │       ├───httptools-0.7.1.dist-info
│   │       │   └───licenses
│   │       ├───idna
│   │       ├───idna-3.13.dist-info
│   │       │   └───licenses
│   │       ├───itsdangerous
│   │       ├───itsdangerous-2.2.0.dist-info
│   │       ├───jinja2
│   │       ├───jinja2-3.1.6.dist-info
│   │       │   └───licenses
│   │       ├───js
│   │       ├───jsonschema
│   │       │   ├───benchmarks
│   │       │   │   └───issue232
│   │       │   └───tests
│   │       │       └───typing
│   │       ├───jsonschema-4.26.0.dist-info
│   │       │   └───licenses
│   │       ├───jsonschema_specifications
│   │       │   ├───schemas
│   │       │   │   ├───draft201909
│   │       │   │   │   └───vocabularies
│   │       │   │   ├───draft202012
│   │       │   │   │   └───vocabularies
│   │       │   │   ├───draft3
│   │       │   │   ├───draft4
│   │       │   │   ├───draft6
│   │       │   │   └───draft7
│   │       │   └───tests
│   │       ├───jsonschema_specifications-2025.9.1.dist-info
│   │       │   └───licenses
│   │       ├───markupsafe
│   │       ├───markupsafe-3.0.3.dist-info
│   │       │   └───licenses
│   │       ├───multipart
│   │       ├───narwhals
│   │       │   ├───stable
│   │       │   │   ├───v1
│   │       │   │   └───v2
│   │       │   ├───testing
│   │       │   │   └───asserts
│   │       │   ├───_arrow
│   │       │   ├───_compliant
│   │       │   ├───_dask
│   │       │   ├───_duckdb
│   │       │   ├───_ibis
│   │       │   ├───_interchange
│   │       │   ├───_pandas_like
│   │       │   ├───_polars
│   │       │   ├───_spark_like
│   │       │   └───_sql
│   │       ├───narwhals-2.20.0.dist-info
│   │       │   └───licenses
│   │       ├───numpy
│   │       │   ├───char
│   │       │   ├───core
│   │       │   ├───ctypeslib
│   │       │   ├───doc
│   │       │   ├───f2py
│   │       │   │   ├───src
│   │       │   │   ├───tests
│   │       │   │   │   └───src
│   │       │   │   │       ├───abstract_interface
│   │       │   │   │       ├───array_from_pyobj
│   │       │   │   │       ├───assumed_shape
│   │       │   │   │       ├───block_docstring
│   │       │   │   │       ├───callback
│   │       │   │   │       ├───cli
│   │       │   │   │       ├───common
│   │       │   │   │       ├───crackfortran
│   │       │   │   │       ├───f2cmap
│   │       │   │   │       ├───isocintrin
│   │       │   │   │       ├───kind
│   │       │   │   │       ├───mixed
│   │       │   │   │       ├───modules
│   │       │   │   │       │   ├───gh25337
│   │       │   │   │       │   └───gh26920
│   │       │   │   │       ├───negative_bounds
│   │       │   │   │       ├───parameter
│   │       │   │   │       ├───quoted_character
│   │       │   │   │       ├───regression
│   │       │   │   │       ├───return_character
│   │       │   │   │       ├───return_complex
│   │       │   │   │       ├───return_integer
│   │       │   │   │       ├───return_logical
│   │       │   │   │       ├───return_real
│   │       │   │   │       ├───routines
│   │       │   │   │       ├───size
│   │       │   │   │       ├───string
│   │       │   │   │       └───value_attrspec
│   │       │   │   └───_backends
│   │       │   ├───fft
│   │       │   │   └───tests
│   │       │   ├───lib
│   │       │   │   └───tests
│   │       │   │       └───data
│   │       │   ├───linalg
│   │       │   │   └───tests
│   │       │   ├───ma
│   │       │   │   └───tests
│   │       │   ├───matrixlib
│   │       │   │   └───tests
│   │       │   ├───polynomial
│   │       │   │   └───tests
│   │       │   ├───random
│   │       │   │   ├───lib
│   │       │   │   ├───tests
│   │       │   │   │   └───data
│   │       │   │   └───_examples
│   │       │   │       ├───cffi
│   │       │   │       ├───cython
│   │       │   │       └───numba
│   │       │   ├───rec
│   │       │   ├───strings
│   │       │   ├───testing
│   │       │   │   ├───tests
│   │       │   │   └───_private
│   │       │   ├───tests
│   │       │   ├───typing
│   │       │   │   └───tests
│   │       │   │       └───data
│   │       │   │           ├───fail
│   │       │   │           ├───misc
│   │       │   │           ├───pass
│   │       │   │           └───reveal
│   │       │   ├───_core
│   │       │   │   ├───include
│   │       │   │   │   └───numpy
│   │       │   │   │       └───random
│   │       │   │   ├───lib
│   │       │   │   │   ├───npy-pkg-config
│   │       │   │   │   └───pkgconfig
│   │       │   │   └───tests
│   │       │   │       ├───data
│   │       │   │       └───examples
│   │       │   │           ├───cython
│   │       │   │           └───limited_api
│   │       │   ├───_pyinstaller
│   │       │   │   └───tests
│   │       │   ├───_typing
│   │       │   └───_utils
│   │       ├───numpy-2.4.4.dist-info
│   │       │   └───licenses
│   │       │       └───numpy
│   │       │           ├───fft
│   │       │           │   └───pocketfft
│   │       │           ├───linalg
│   │       │           │   └───lapack_lite
│   │       │           ├───ma
│   │       │           ├───random
│   │       │           │   └───src
│   │       │           │       ├───distributions
│   │       │           │       ├───mt19937
│   │       │           │       ├───pcg64
│   │       │           │       ├───philox
│   │       │           │       ├───sfc64
│   │       │           │       └───splitmix64
│   │       │           └───_core
│   │       │               ├───include
│   │       │               │   └───numpy
│   │       │               │       └───libdivide
│   │       │               └───src
│   │       │                   ├───common
│   │       │                   │   └───pythoncapi-compat
│   │       │                   ├───highway
│   │       │                   ├───multiarray
│   │       │                   ├───npysort
│   │       │                   │   └───x86-simd-sort
│   │       │                   └───umath
│   │       │                       └───svml
│   │       ├───numpy.libs
│   │       ├───packaging
│   │       │   └───licenses
│   │       ├───packaging-26.2.dist-info
│   │       │   └───licenses
│   │       ├───pandas
│   │       │   ├───api
│   │       │   │   ├───executors
│   │       │   │   ├───extensions
│   │       │   │   ├───indexers
│   │       │   │   ├───interchange
│   │       │   │   ├───types
│   │       │   │   └───typing
│   │       │   ├───arrays
│   │       │   ├───compat
│   │       │   │   └───numpy
│   │       │   ├───core
│   │       │   │   ├───arrays
│   │       │   │   │   ├───arrow
│   │       │   │   │   └───sparse
│   │       │   │   ├───array_algos
│   │       │   │   ├───computation
│   │       │   │   ├───dtypes
│   │       │   │   ├───groupby
│   │       │   │   ├───indexers
│   │       │   │   ├───indexes
│   │       │   │   ├───interchange
│   │       │   │   ├───internals
│   │       │   │   ├───methods
│   │       │   │   ├───ops
│   │       │   │   ├───reshape
│   │       │   │   ├───sparse
│   │       │   │   ├───strings
│   │       │   │   ├───tools
│   │       │   │   ├───util
│   │       │   │   ├───window
│   │       │   │   └───_numba
│   │       │   │       └───kernels
│   │       │   ├───errors
│   │       │   ├───io
│   │       │   │   ├───clipboard
│   │       │   │   ├───excel
│   │       │   │   ├───formats
│   │       │   │   │   └───templates
│   │       │   │   ├───json
│   │       │   │   ├───parsers
│   │       │   │   └───sas
│   │       │   ├───plotting
│   │       │   │   └───_matplotlib
│   │       │   ├───tests
│   │       │   │   ├───api
│   │       │   │   ├───apply
│   │       │   │   ├───arithmetic
│   │       │   │   ├───arrays
│   │       │   │   │   ├───boolean
│   │       │   │   │   ├───categorical
│   │       │   │   │   ├───datetimes
│   │       │   │   │   ├───floating
│   │       │   │   │   ├───integer
│   │       │   │   │   ├───interval
│   │       │   │   │   ├───masked
│   │       │   │   │   ├───numpy_
│   │       │   │   │   ├───period
│   │       │   │   │   ├───sparse
│   │       │   │   │   ├───string_
│   │       │   │   │   └───timedeltas
│   │       │   │   ├───base
│   │       │   │   ├───computation
│   │       │   │   ├───config
│   │       │   │   ├───construction
│   │       │   │   ├───copy_view
│   │       │   │   │   └───index
│   │       │   │   ├───dtypes
│   │       │   │   │   └───cast
│   │       │   │   ├───extension
│   │       │   │   │   ├───array_with_attr
│   │       │   │   │   ├───base
│   │       │   │   │   ├───date
│   │       │   │   │   ├───decimal
│   │       │   │   │   ├───json
│   │       │   │   │   ├───list
│   │       │   │   │   └───uuid
│   │       │   │   ├───frame
│   │       │   │   │   ├───constructors
│   │       │   │   │   ├───indexing
│   │       │   │   │   └───methods
│   │       │   │   ├───generic
│   │       │   │   ├───groupby
│   │       │   │   │   ├───aggregate
│   │       │   │   │   ├───methods
│   │       │   │   │   └───transform
│   │       │   │   ├───indexes
│   │       │   │   │   ├───base_class
│   │       │   │   │   ├───categorical
│   │       │   │   │   ├───datetimelike_
│   │       │   │   │   ├───datetimes
│   │       │   │   │   │   └───methods
│   │       │   │   │   ├───interval
│   │       │   │   │   ├───multi
│   │       │   │   │   ├───numeric
│   │       │   │   │   ├───object
│   │       │   │   │   ├───period
│   │       │   │   │   │   └───methods
│   │       │   │   │   ├───ranges
│   │       │   │   │   ├───string
│   │       │   │   │   └───timedeltas
│   │       │   │   │       └───methods
│   │       │   │   ├───indexing
│   │       │   │   │   ├───interval
│   │       │   │   │   └───multiindex
│   │       │   │   ├───interchange
│   │       │   │   ├───internals
│   │       │   │   ├───io
│   │       │   │   │   ├───excel
│   │       │   │   │   ├───formats
│   │       │   │   │   │   └───style
│   │       │   │   │   ├───json
│   │       │   │   │   ├───parser
│   │       │   │   │   │   ├───common
│   │       │   │   │   │   ├───dtypes
│   │       │   │   │   │   └───usecols
│   │       │   │   │   ├───pytables
│   │       │   │   │   ├───sas
│   │       │   │   │   └───xml
│   │       │   │   ├───libs
│   │       │   │   ├───plotting
│   │       │   │   │   └───frame
│   │       │   │   ├───reductions
│   │       │   │   ├───resample
│   │       │   │   ├───reshape
│   │       │   │   │   ├───concat
│   │       │   │   │   └───merge
│   │       │   │   ├───scalar
│   │       │   │   │   ├───interval
│   │       │   │   │   ├───period
│   │       │   │   │   ├───timedelta
│   │       │   │   │   │   └───methods
│   │       │   │   │   └───timestamp
│   │       │   │   │       └───methods
│   │       │   │   ├───series
│   │       │   │   │   ├───accessors
│   │       │   │   │   ├───indexing
│   │       │   │   │   └───methods
│   │       │   │   ├───strings
│   │       │   │   ├───tools
│   │       │   │   ├───tseries
│   │       │   │   │   ├───frequencies
│   │       │   │   │   ├───holiday
│   │       │   │   │   └───offsets
│   │       │   │   ├───tslibs
│   │       │   │   ├───util
│   │       │   │   └───window
│   │       │   │       └───moments
│   │       │   ├───tseries
│   │       │   ├───util
│   │       │   │   └───version
│   │       │   ├───_config
│   │       │   ├───_libs
│   │       │   │   ├───tslibs
│   │       │   │   └───window
│   │       │   └───_testing
│   │       ├───pandas-3.0.2.dist-info
│   │       ├───pandas.libs
│   │       ├───PIL
│   │       ├───pillow-12.2.0.dist-info
│   │       │   └───licenses
│   │       ├───pip
│   │       │   ├───_internal
│   │       │   │   ├───cli
│   │       │   │   ├───commands
│   │       │   │   ├───distributions
│   │       │   │   ├───index
│   │       │   │   ├───locations
│   │       │   │   ├───metadata
│   │       │   │   │   └───importlib
│   │       │   │   ├───models
│   │       │   │   ├───network
│   │       │   │   ├───operations
│   │       │   │   │   ├───build
│   │       │   │   │   └───install
│   │       │   │   ├───req
│   │       │   │   ├───resolution
│   │       │   │   │   ├───legacy
│   │       │   │   │   └───resolvelib
│   │       │   │   ├───utils
│   │       │   │   └───vcs
│   │       │   └───_vendor
│   │       │       ├───cachecontrol
│   │       │       │   └───caches
│   │       │       ├───certifi
│   │       │       ├───distlib
│   │       │       ├───distro
│   │       │       ├───idna
│   │       │       ├───msgpack
│   │       │       ├───packaging
│   │       │       │   └───licenses
│   │       │       ├───pkg_resources
│   │       │       ├───platformdirs
│   │       │       ├───pygments
│   │       │       │   ├───filters
│   │       │       │   ├───formatters
│   │       │       │   ├───lexers
│   │       │       │   └───styles
│   │       │       ├───pyproject_hooks
│   │       │       │   └───_in_process
│   │       │       ├───requests
│   │       │       ├───resolvelib
│   │       │       │   └───resolvers
│   │       │       ├───rich
│   │       │       ├───tomli
│   │       │       ├───tomli_w
│   │       │       ├───truststore
│   │       │       └───urllib3
│   │       │           ├───contrib
│   │       │           │   └───emscripten
│   │       │           ├───http2
│   │       │           └───util
│   │       ├───pip-26.1.dist-info
│   │       │   └───licenses
│   │       │       └───src
│   │       │           └───pip
│   │       │               └───_vendor
│   │       │                   ├───cachecontrol
│   │       │                   ├───certifi
│   │       │                   ├───distlib
│   │       │                   ├───distro
│   │       │                   ├───idna
│   │       │                   ├───msgpack
│   │       │                   ├───packaging
│   │       │                   ├───pkg_resources
│   │       │                   ├───platformdirs
│   │       │                   ├───pygments
│   │       │                   ├───pyproject_hooks
│   │       │                   ├───requests
│   │       │                   ├───resolvelib
│   │       │                   ├───rich
│   │       │                   ├───tomli
│   │       │                   ├───tomli_w
│   │       │                   ├───truststore
│   │       │                   └───urllib3
│   │       ├───plotly
│   │       │   ├───api
│   │       │   ├───colors
│   │       │   ├───data
│   │       │   ├───express
│   │       │   │   ├───colors
│   │       │   │   ├───data
│   │       │   │   └───trendline_functions
│   │       │   ├───figure_factory
│   │       │   ├───graph_objects
│   │       │   ├───graph_objs
│   │       │   │   ├───bar
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───barpolar
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───box
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───candlestick
│   │       │   │   │   ├───decreasing
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───increasing
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───carpet
│   │       │   │   │   ├───aaxis
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───baxis
│   │       │   │   │   │   └───title
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───choropleth
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───choroplethmap
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───choroplethmapbox
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───cone
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───contour
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───contours
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───contourcarpet
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───contours
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───densitymap
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───densitymapbox
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───funnel
│   │       │   │   │   ├───connector
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   └───marker
│   │       │   │   │       └───colorbar
│   │       │   │   │           └───title
│   │       │   │   ├───funnelarea
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   └───title
│   │       │   │   ├───heatmap
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───histogram
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───histogram2d
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───histogram2dcontour
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───contours
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───icicle
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   └───pathbar
│   │       │   │   ├───image
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───indicator
│   │       │   │   │   ├───delta
│   │       │   │   │   ├───gauge
│   │       │   │   │   │   ├───axis
│   │       │   │   │   │   ├───bar
│   │       │   │   │   │   ├───step
│   │       │   │   │   │   └───threshold
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───number
│   │       │   │   │   └───title
│   │       │   │   ├───isosurface
│   │       │   │   │   ├───caps
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   └───slices
│   │       │   │   ├───layout
│   │       │   │   │   ├───annotation
│   │       │   │   │   │   └───hoverlabel
│   │       │   │   │   ├───coloraxis
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───geo
│   │       │   │   │   │   └───projection
│   │       │   │   │   ├───grid
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legend
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───map
│   │       │   │   │   │   └───layer
│   │       │   │   │   │       └───symbol
│   │       │   │   │   ├───mapbox
│   │       │   │   │   │   └───layer
│   │       │   │   │   │       └───symbol
│   │       │   │   │   ├───newselection
│   │       │   │   │   ├───newshape
│   │       │   │   │   │   ├───label
│   │       │   │   │   │   └───legendgrouptitle
│   │       │   │   │   ├───polar
│   │       │   │   │   │   ├───angularaxis
│   │       │   │   │   │   └───radialaxis
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───scene
│   │       │   │   │   │   ├───annotation
│   │       │   │   │   │   │   └───hoverlabel
│   │       │   │   │   │   ├───camera
│   │       │   │   │   │   ├───xaxis
│   │       │   │   │   │   │   └───title
│   │       │   │   │   │   ├───yaxis
│   │       │   │   │   │   │   └───title
│   │       │   │   │   │   └───zaxis
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selection
│   │       │   │   │   ├───shape
│   │       │   │   │   │   ├───label
│   │       │   │   │   │   └───legendgrouptitle
│   │       │   │   │   ├───slider
│   │       │   │   │   │   └───currentvalue
│   │       │   │   │   ├───smith
│   │       │   │   │   │   ├───imaginaryaxis
│   │       │   │   │   │   └───realaxis
│   │       │   │   │   ├───template
│   │       │   │   │   │   └───data
│   │       │   │   │   ├───ternary
│   │       │   │   │   │   ├───aaxis
│   │       │   │   │   │   │   └───title
│   │       │   │   │   │   ├───baxis
│   │       │   │   │   │   │   └───title
│   │       │   │   │   │   └───caxis
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───title
│   │       │   │   │   │   └───subtitle
│   │       │   │   │   ├───updatemenu
│   │       │   │   │   ├───xaxis
│   │       │   │   │   │   ├───rangeselector
│   │       │   │   │   │   ├───rangeslider
│   │       │   │   │   │   └───title
│   │       │   │   │   └───yaxis
│   │       │   │   │       └───title
│   │       │   │   ├───mesh3d
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───ohlc
│   │       │   │   │   ├───decreasing
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───increasing
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───parcats
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   └───line
│   │       │   │   │       └───colorbar
│   │       │   │   │           └───title
│   │       │   │   ├───parcoords
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───line
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   └───unselected
│   │       │   │   ├───pie
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   └───title
│   │       │   │   ├───sankey
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───link
│   │       │   │   │   │   └───hoverlabel
│   │       │   │   │   └───node
│   │       │   │   │       └───hoverlabel
│   │       │   │   ├───scatter
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scatter3d
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───line
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   └───projection
│   │       │   │   ├───scattercarpet
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scattergeo
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scattergl
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scattermap
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scattermapbox
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scatterpolar
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scatterpolargl
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scattersmith
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───scatterternary
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───splom
│   │       │   │   │   ├───dimension
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───streamtube
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───sunburst
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   └───marker
│   │       │   │   │       └───colorbar
│   │       │   │   │           └───title
│   │       │   │   ├───surface
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───contours
│   │       │   │   │   │   ├───x
│   │       │   │   │   │   ├───y
│   │       │   │   │   │   └───z
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───table
│   │       │   │   │   ├───cells
│   │       │   │   │   ├───header
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   └───legendgrouptitle
│   │       │   │   ├───treemap
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   │   └───colorbar
│   │       │   │   │   │       └───title
│   │       │   │   │   └───pathbar
│   │       │   │   ├───violin
│   │       │   │   │   ├───box
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   ├───marker
│   │       │   │   │   ├───selected
│   │       │   │   │   └───unselected
│   │       │   │   ├───volume
│   │       │   │   │   ├───caps
│   │       │   │   │   ├───colorbar
│   │       │   │   │   │   └───title
│   │       │   │   │   ├───hoverlabel
│   │       │   │   │   ├───legendgrouptitle
│   │       │   │   │   └───slices
│   │       │   │   └───waterfall
│   │       │   │       ├───connector
│   │       │   │       ├───decreasing
│   │       │   │       │   └───marker
│   │       │   │       ├───hoverlabel
│   │       │   │       ├───increasing
│   │       │   │       │   └───marker
│   │       │   │       ├───legendgrouptitle
│   │       │   │       └───totals
│   │       │   │           └───marker
│   │       │   ├───io
│   │       │   ├───labextension
│   │       │   │   └───static
│   │       │   ├───matplotlylib
│   │       │   │   ├───mplexporter
│   │       │   │   │   ├───renderers
│   │       │   │   │   └───tests
│   │       │   │   └───tests
│   │       │   ├───offline
│   │       │   ├───package_data
│   │       │   │   ├───datasets
│   │       │   │   └───templates
│   │       │   └───validators
│   │       ├───plotly-6.7.0.dist-info
│   │       │   └───licenses
│   │       ├───protobuf-7.34.1.dist-info
│   │       ├───pyarrow
│   │       │   ├───include
│   │       │   │   ├───arrow
│   │       │   │   │   ├───acero
│   │       │   │   │   ├───adapters
│   │       │   │   │   │   ├───orc
│   │       │   │   │   │   └───tensorflow
│   │       │   │   │   ├───array
│   │       │   │   │   ├───c
│   │       │   │   │   ├───compute
│   │       │   │   │   │   └───row
│   │       │   │   │   ├───csv
│   │       │   │   │   ├───dataset
│   │       │   │   │   ├───engine
│   │       │   │   │   │   └───substrait
│   │       │   │   │   ├───extension
│   │       │   │   │   ├───filesystem
│   │       │   │   │   ├───flight
│   │       │   │   │   ├───io
│   │       │   │   │   ├───ipc
│   │       │   │   │   ├───json
│   │       │   │   │   ├───python
│   │       │   │   │   │   └───vendored
│   │       │   │   │   ├───telemetry
│   │       │   │   │   ├───tensor
│   │       │   │   │   ├───testing
│   │       │   │   │   ├───util
│   │       │   │   │   └───vendored
│   │       │   │   │       ├───datetime
│   │       │   │   │       ├───double-conversion
│   │       │   │   │       ├───pcg
│   │       │   │   │       ├───portable-snippets
│   │       │   │   │       ├───safeint
│   │       │   │   │       └───xxhash
│   │       │   │   └───parquet
│   │       │   │       ├───api
│   │       │   │       ├───arrow
│   │       │   │       ├───encryption
│   │       │   │       └───geospatial
│   │       │   ├───includes
│   │       │   ├───interchange
│   │       │   ├───parquet
│   │       │   ├───src
│   │       │   │   └───arrow
│   │       │   │       └───python
│   │       │   │           └───vendored
│   │       │   ├───tests
│   │       │   │   ├───data
│   │       │   │   │   ├───feather
│   │       │   │   │   ├───orc
│   │       │   │   │   └───parquet
│   │       │   │   ├───interchange
│   │       │   │   └───parquet
│   │       │   └───vendored
│   │       ├───pyarrow-24.0.0.dist-info
│   │       │   └───licenses
│   │       ├───pyarrow.libs
│   │       ├───pydeck
│   │       │   ├───bindings
│   │       │   ├───data_utils
│   │       │   ├───exceptions
│   │       │   ├───io
│   │       │   │   └───templates
│   │       │   ├───nbextension
│   │       │   │   └───static
│   │       │   ├───types
│   │       │   └───widget
│   │       ├───pydeck-0.9.2.dist-info
│   │       │   └───licenses
│   │       ├───PyPDF2
│   │       │   ├───generic
│   │       │   └───_codecs
│   │       ├───pypdf2-3.0.1.dist-info
│   │       ├───python_dateutil-2.9.0.post0.dist-info
│   │       ├───python_multipart
│   │       ├───python_multipart-0.0.27.dist-info
│   │       │   └───licenses
│   │       ├───referencing
│   │       │   └───tests
│   │       ├───referencing-0.37.0.dist-info
│   │       │   └───licenses
│   │       ├───reportlab
│   │       │   ├───fonts
│   │       │   ├───graphics
│   │       │   │   ├───barcode
│   │       │   │   ├───charts
│   │       │   │   ├───samples
│   │       │   │   └───widgets
│   │       │   ├───lib
│   │       │   ├───pdfbase
│   │       │   ├───pdfgen
│   │       │   └───platypus
│   │       ├───reportlab-4.5.0.dist-info
│   │       │   └───licenses
│   │       ├───requests
│   │       ├───requests-2.33.1.dist-info
│   │       │   └───licenses
│   │       ├───rpds
│   │       ├───rpds_py-0.30.0.dist-info
│   │       │   └───licenses
│   │       ├───scipy
│   │       │   ├───cluster
│   │       │   │   └───tests
│   │       │   ├───constants
│   │       │   │   └───tests
│   │       │   ├───datasets
│   │       │   │   └───tests
│   │       │   ├───differentiate
│   │       │   │   └───tests
│   │       │   ├───fft
│   │       │   │   ├───tests
│   │       │   │   └───_pocketfft
│   │       │   │       └───tests
│   │       │   ├───fftpack
│   │       │   │   └───tests
│   │       │   ├───integrate
│   │       │   │   ├───tests
│   │       │   │   ├───_ivp
│   │       │   │   │   └───tests
│   │       │   │   └───_rules
│   │       │   ├───interpolate
│   │       │   │   └───tests
│   │       │   │       └───data
│   │       │   ├───io
│   │       │   │   ├───arff
│   │       │   │   │   └───tests
│   │       │   │   │       └───data
│   │       │   │   ├───matlab
│   │       │   │   │   └───tests
│   │       │   │   │       └───data
│   │       │   │   ├───tests
│   │       │   │   │   └───data
│   │       │   │   ├───_fast_matrix_market
│   │       │   │   └───_harwell_boeing
│   │       │   │       └───tests
│   │       │   ├───linalg
│   │       │   │   └───tests
│   │       │   │       ├───data
│   │       │   │       └───_cython_examples
│   │       │   ├───misc
│   │       │   ├───ndimage
│   │       │   │   └───tests
│   │       │   │       └───data
│   │       │   ├───odr
│   │       │   │   └───tests
│   │       │   ├───optimize
│   │       │   │   ├───cython_optimize
│   │       │   │   ├───tests
│   │       │   │   │   └───_cython_examples
│   │       │   │   ├───_highspy
│   │       │   │   ├───_lsq
│   │       │   │   ├───_shgo_lib
│   │       │   │   ├───_trlib
│   │       │   │   └───_trustregion_constr
│   │       │   │       └───tests
│   │       │   ├───signal
│   │       │   │   ├───tests
│   │       │   │   └───windows
│   │       │   ├───sparse
│   │       │   │   ├───csgraph
│   │       │   │   │   └───tests
│   │       │   │   ├───linalg
│   │       │   │   │   ├───tests
│   │       │   │   │   ├───_dsolve
│   │       │   │   │   │   └───tests
│   │       │   │   │   ├───_eigen
│   │       │   │   │   │   ├───arpack
│   │       │   │   │   │   │   └───tests
│   │       │   │   │   │   ├───lobpcg
│   │       │   │   │   │   │   └───tests
│   │       │   │   │   │   └───tests
│   │       │   │   │   └───_isolve
│   │       │   │   │       └───tests
│   │       │   │   └───tests
│   │       │   │       └───data
│   │       │   ├───spatial
│   │       │   │   ├───qhull_src
│   │       │   │   ├───tests
│   │       │   │   │   └───data
│   │       │   │   └───transform
│   │       │   │       └───tests
│   │       │   ├───special
│   │       │   │   ├───tests
│   │       │   │   │   ├───data
│   │       │   │   │   └───_cython_examples
│   │       │   │   └───_precompute
│   │       │   ├───stats
│   │       │   │   ├───tests
│   │       │   │   │   └───data
│   │       │   │   │       ├───levy_stable
│   │       │   │   │       ├───nist_anova
│   │       │   │   │       └───nist_linregress
│   │       │   │   ├───_levy_stable
│   │       │   │   ├───_rcont
│   │       │   │   └───_unuran
│   │       │   └───_lib
│   │       │       ├───array_api_compat
│   │       │       │   ├───common
│   │       │       │   ├───cupy
│   │       │       │   ├───dask
│   │       │       │   │   └───array
│   │       │       │   ├───numpy
│   │       │       │   └───torch
│   │       │       ├───array_api_extra
│   │       │       │   └───_lib
│   │       │       │       └───_utils
│   │       │       ├───cobyqa
│   │       │       │   ├───subsolvers
│   │       │       │   └───utils
│   │       │       ├───pyprima
│   │       │       │   ├───cobyla
│   │       │       │   └───common
│   │       │       ├───tests
│   │       │       └───_uarray
│   │       ├───scipy-1.17.1.dist-info
│   │       ├───scipy.libs
│   │       ├───six-1.17.0.dist-info
│   │       ├───smmap
│   │       │   └───test
│   │       ├───smmap-5.0.3.dist-info
│   │       │   └───licenses
│   │       ├───starlette
│   │       │   └───middleware
│   │       ├───starlette-1.0.0.dist-info
│   │       │   └───licenses
│   │       ├───streamlit
│   │       │   ├───.agents
│   │       │   │   └───skills
│   │       │   │       └───developing-with-streamlit
│   │       │   │           ├───assets
│   │       │   │           │   └───templates
│   │       │   │           │       ├───apps
│   │       │   │           │       │   ├───dashboard-companies
│   │       │   │           │       │   ├───dashboard-compute
│   │       │   │           │       │   ├───dashboard-feature-usage
│   │       │   │           │       │   ├───dashboard-metrics
│   │       │   │           │       │   ├───dashboard-seattle-weather
│   │       │   │           │       │   └───dashboard-stock-peers
│   │       │   │           │       └───themes
│   │       │   │           │           └───configs
│   │       │   │           └───references
│   │       │   ├───commands
│   │       │   ├───components
│   │       │   │   ├───lib
│   │       │   │   ├───types
│   │       │   │   ├───v1
│   │       │   │   └───v2
│   │       │   │       └───bidi_component
│   │       │   ├───connections
│   │       │   ├───elements
│   │       │   │   ├───lib
│   │       │   │   └───widgets
│   │       │   ├───external
│   │       │   │   └───langchain
│   │       │   ├───hello
│   │       │   ├───navigation
│   │       │   ├───proto
│   │       │   ├───runtime
│   │       │   │   ├───caching
│   │       │   │   │   └───storage
│   │       │   │   ├───scriptrunner
│   │       │   │   ├───scriptrunner_utils
│   │       │   │   └───state
│   │       │   ├───static
│   │       │   │   └───static
│   │       │   │       ├───css
│   │       │   │       ├───js
│   │       │   │       └───media
│   │       │   ├───testing
│   │       │   │   └───v1
│   │       │   ├───vendor
│   │       │   │   └───pympler
│   │       │   ├───watcher
│   │       │   └───web
│   │       │       └───server
│   │       │           └───starlette
│   │       ├───streamlit-1.57.0.dist-info
│   │       ├───tenacity
│   │       │   └───asyncio
│   │       ├───tenacity-9.1.4.dist-info
│   │       │   └───licenses
│   │       ├───toml
│   │       ├───toml-0.10.2.dist-info
│   │       ├───typing_extensions-4.15.0.dist-info
│   │       │   └───licenses
│   │       ├───tzdata
│   │       │   └───zoneinfo
│   │       │       ├───Africa
│   │       │       ├───America
│   │       │       │   ├───Argentina
│   │       │       │   ├───Indiana
│   │       │       │   ├───Kentucky
│   │       │       │   └───North_Dakota
│   │       │       ├───Antarctica
│   │       │       ├───Arctic
│   │       │       ├───Asia
│   │       │       ├───Atlantic
│   │       │       ├───Australia
│   │       │       ├───Brazil
│   │       │       ├───Canada
│   │       │       ├───Chile
│   │       │       ├───Etc
│   │       │       ├───Europe
│   │       │       ├───Indian
│   │       │       ├───Mexico
│   │       │       ├───Pacific
│   │       │       └───US
│   │       ├───tzdata-2026.2.dist-info
│   │       │   └───licenses
│   │       │       └───licenses
│   │       ├───urllib3
│   │       │   ├───contrib
│   │       │   │   └───emscripten
│   │       │   ├───http2
│   │       │   └───util
│   │       ├───urllib3-2.6.3.dist-info
│   │       │   └───licenses
│   │       ├───uvicorn
│   │       │   ├───lifespan
│   │       │   ├───loops
│   │       │   ├───middleware
│   │       │   ├───protocols
│   │       │   │   ├───http
│   │       │   │   └───websockets
│   │       │   └───supervisors
│   │       ├───uvicorn-0.46.0.dist-info
│   │       │   └───licenses
│   │       ├───watchdog
│   │       │   ├───observers
│   │       │   ├───tricks
│   │       │   └───utils
│   │       ├───watchdog-6.0.0.dist-info
│   │       ├───websockets
│   │       │   ├───asyncio
│   │       │   ├───extensions
│   │       │   ├───legacy
│   │       │   └───sync
│   │       ├───websockets-16.0.dist-info
│   │       │   └───licenses
│   │       └───_plotly_utils
│   │           └───colors
│   ├───Scripts
│   └───share
│       └───jupyter
│           ├───labextensions
│           │   └───jupyterlab-plotly
│           │       └───static
│           └───nbextensions
│               └───pydeck
├───_pages
└───__pycache__
🔄 Version History

v2.0.1 (2026-06-08) - BOQ Management Release
Added BOQ Management System

Added PWD/LGED rate import wizards

Added 3-tier bid optimization

Added subscription management

Added role-based access control

See CHANGELOG.md for full version history.

🤝 Contributing
Fork the repository

Create a feature branch (git checkout -b feature/AmazingFeature)

Commit changes (git commit -m 'Add AmazingFeature')

Push to branch (git push origin feature/AmazingFeature)

Open a Pull Request

📝 License
Distributed under the MIT License. See LICENSE for more information.

📧 Contact
Your Shomon Robie - @shomonrobie - shomonrobie@gmail.com

Project Link: https://github.com/yourusername/tenderai

text

## 7. **Create `LICENSE`**

```txt
MIT License

Copyright (c) 2026 TenderAI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
