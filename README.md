# Financial Data Accuracy Dashboard

A real-time monitoring system that compares stock prices from multiple data sources (Alpha Vantage and Yahoo Finance) to detect and alert on price discrepancies.

## Features

- Real-time price comparison between Alpha Vantage and Yahoo Finance
- Email alerts for significant price discrepancies
- Interactive dashboard with real-time visualization
- Historical price comparison and trend analysis
- Performance monitoring and error tracking
- Data export functionality (CSV, JSON, Excel)
- Comprehensive logging system

## Prerequisites

- Python 3.11 or higher
- Alpha Vantage API key
- Gmail account with App Password for email alerts

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd financial-data-accuracy-dashboard
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
Copy `.env.example` to `.env` and update with your credentials:
```
ALPHA_VANTAGE_API_KEY=your_api_key
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENTS=recipient1@email.com,recipient2@email.com
DISCREPANCY_THRESHOLD=0.5
REFRESH_INTERVAL=300
```

## Usage

1. Start the dashboard:
```bash
streamlit run src/dashboard.py
```

2. Access the dashboard in your browser at `http://localhost:8501`

3. Enter a stock symbol in the sidebar to start monitoring

## Features in Detail

### Real-time Price Monitoring
- Fetches prices from Alpha Vantage and Yahoo Finance APIs
- Calculates price discrepancies in real-time
- Displays current prices and differences

### Alert System
- Configurable threshold for price discrepancies
- Email alerts when discrepancies exceed threshold
- Alert cooldown to prevent spam
- Historical alert tracking

### Data Visualization
- Real-time price comparison charts
- Historical price trends
- Discrepancy distribution analysis
- 24-hour trend analysis

### System Monitoring
- API response time tracking
- Error rate monitoring
- System performance metrics
- Comprehensive logging

### Data Export
- Export historical data in CSV format
- Export in JSON format
- Export in Excel format with formatting

## File Structure

```
├── src/
│   ├── dashboard.py        # Main Streamlit dashboard
│   ├── data_fetcher.py     # Data fetching from APIs
│   ├── alert_system.py     # Alert system implementation
│   └── app.py             # Flask app (if needed)
├── .env                    # Environment variables
├── .env.example           # Example environment variables
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Error Handling

The system includes comprehensive error handling:
- API rate limiting
- Connection errors
- Data validation
- Alert throttling
- Memory management

## Logging

Logs are stored in three files:
- `dashboard.log`: Dashboard operations
- `price_monitor.log`: Price fetching operations
- `alerts.log`: Alert system operations

## Performance Considerations

- Caches API responses to reduce calls
- Implements rate limiting for APIs
- Manages memory usage for historical data
- Optimizes chart rendering

## Security

- Uses environment variables for sensitive data
- Implements API rate limiting
- Uses Gmail App Passwords instead of account passwords
- Validates all input data

## License



## Support

For support, please open an issue in the repository or contact [your contact information]