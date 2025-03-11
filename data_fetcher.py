import os
from typing import Dict, Optional, Tuple
import requests
import yfinance as yf
from alpha_vantage.timeseries import TimeSeries
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('price_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DataFetcher')

# Load environment variables
load_dotenv()

class DataFetcher:
    def __init__(self):
        self.alpha_vantage_api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        if not self.alpha_vantage_api_key:
            raise ValueError('Alpha Vantage API key not found in environment variables')
        
        self.alpha_vantage = TimeSeries(key=self.alpha_vantage_api_key)
        self.price_history = pd.DataFrame(
            columns=['Timestamp', 'Symbol', 'Alpha Vantage Price', 'Yahoo Finance Price', 'Difference %', 'Moving Average', 'Volatility']
        )
        self.last_fetch_time = {}
        
    def _calculate_analytics(self, symbol: str) -> Dict[str, float]:
        """Calculate analytics for the price data."""
        if len(self.price_history) < 2:
            return {
                'moving_average': None,
                'volatility': None,
                'trend': None
            }
            
        symbol_data = self.price_history[self.price_history['Symbol'] == symbol]
        if len(symbol_data) < 2:
            return {
                'moving_average': None,
                'volatility': None,
                'trend': None
            }
            
        # Calculate 5-point moving average for differences
        moving_avg = symbol_data['Difference %'].rolling(window=5, min_periods=1).mean().iloc[-1]
        
        # Calculate volatility (standard deviation of differences)
        volatility = symbol_data['Difference %'].std()
        
        # Calculate trend
        recent_diffs = symbol_data['Difference %'].tail(5)
        trend = 'increasing' if recent_diffs.is_monotonic_increasing else (
            'decreasing' if recent_diffs.is_monotonic_decreasing else 'fluctuating'
        )
        
        return {
            'moving_average': moving_avg,
            'volatility': volatility,
            'trend': trend
        }
        
    def _cross_validate_prices(self, alpha_price: float, yahoo_price: float, symbol: str) -> bool:
        """Cross-validate prices between sources."""
        # Check for extreme price differences
        if abs(alpha_price - yahoo_price) / min(alpha_price, yahoo_price) > 0.2:  # 20% difference
            logger.warning(f'Large price discrepancy detected for {symbol}: AV=${alpha_price:.2f} vs YF=${yahoo_price:.2f}')
            
            # Check historical data for validation
            if not self.price_history.empty:
                recent_data = self.price_history[
                    self.price_history['Symbol'] == symbol
                ].tail(5)
                
                if not recent_data.empty:
                    avg_alpha = recent_data['Alpha Vantage Price'].mean()
                    avg_yahoo = recent_data['Yahoo Finance Price'].mean()
                    
                    # If current prices deviate significantly from recent averages
                    if (abs(alpha_price - avg_alpha) / avg_alpha > 0.1 and 
                        abs(yahoo_price - avg_yahoo) / avg_yahoo > 0.1):
                        logger.error(f'Both sources show suspicious prices for {symbol}')
                        return False
                        
                    # If one source deviates significantly while the other doesn't
                    if abs(alpha_price - avg_alpha) / avg_alpha > 0.1:
                        logger.warning(f'Alpha Vantage price suspicious for {symbol}')
                        return False
                    if abs(yahoo_price - avg_yahoo) / avg_yahoo > 0.1:
                        logger.warning(f'Yahoo Finance price suspicious for {symbol}')
                        return False
        
        return True
    
    def get_alpha_vantage_data(self, symbol: str) -> Optional[float]:
        """Fetch real-time stock price from Alpha Vantage."""
        try:
            # Rate limiting: wait at least 12 seconds between API calls
            current_time = datetime.now()
            if symbol in self.last_fetch_time:
                time_diff = (current_time - self.last_fetch_time[symbol]).total_seconds()
                if time_diff < 12:
                    logger.info(f'Using cached Alpha Vantage data for {symbol}')
                    return self.price_history['Alpha Vantage Price'].iloc[-1]
            
            data, _ = self.alpha_vantage.get_quote_endpoint(symbol)
            price = float(data['05. price'])
            
            if self._validate_price(price, 'Alpha Vantage', symbol):
                self.last_fetch_time[symbol] = current_time
                logger.info(f'Successfully fetched Alpha Vantage price for {symbol}: ${price}')
                return price
            return None
            
        except Exception as e:
            logger.error(f'Error fetching Alpha Vantage data for {symbol}: {str(e)}')
            return None
    
    def get_yahoo_finance_data(self, symbol: str) -> Optional[float]:
        """Fetch real-time stock price from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            
            if data.empty:
                logger.warning(f'No data returned from Yahoo Finance for {symbol}')
                return None
                
            price = data['Close'].iloc[-1]
            
            if self._validate_price(price, 'Yahoo Finance', symbol):
                logger.info(f'Successfully fetched Yahoo Finance price for {symbol}: ${price}')
                return price
            return None
            
        except Exception as e:
            logger.error(f'Error fetching Yahoo Finance data for {symbol}: {str(e)}')
            return None
    
    def get_price_comparison(self, symbol: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Get price comparison between Alpha Vantage and Yahoo Finance."""
        alpha_price = self.get_alpha_vantage_data(symbol)
        yahoo_price = self.get_yahoo_finance_data(symbol)
        
        if alpha_price is not None and yahoo_price is not None:
            # Cross-validate prices
            if not self._cross_validate_prices(alpha_price, yahoo_price, symbol):
                logger.warning(f'Price validation failed for {symbol}')
                return None, None, None
                
            price_diff_percentage = abs(alpha_price - yahoo_price) / alpha_price * 100
            
            # Calculate analytics
            analytics = self._calculate_analytics(symbol)
            
            # Store the comparison in history
            new_data = pd.DataFrame([{
                'Timestamp': datetime.now(),
                'Symbol': symbol,
                'Alpha Vantage Price': alpha_price,
                'Yahoo Finance Price': yahoo_price,
                'Difference %': price_diff_percentage,
                'Moving Average': analytics['moving_average'],
                'Volatility': analytics['volatility']
            }])
            
            self.price_history = pd.concat([self.price_history, new_data], ignore_index=True)
            
            # Keep only last 1000 records to manage memory
            if len(self.price_history) > 1000:
                self.price_history = self.price_history.tail(1000)
            
            logger.info(f'''Price comparison for {symbol}:
                AV=${alpha_price:.2f}, YF=${yahoo_price:.2f}
                Diff={price_diff_percentage:.2f}%
                MA={analytics["moving_average"]:.2f}%
                Vol={analytics["volatility"]:.2f}
                Trend={analytics["trend"]}''')
                
            return alpha_price, yahoo_price, price_diff_percentage
            
        return None, None, None
    
    def get_historical_comparison(self) -> pd.DataFrame:
        """Get historical price comparison data."""
        return self.price_history
        
    def get_analytics_summary(self, symbol: str) -> Dict[str, any]:
        """Get summary analytics for a symbol."""
        symbol_data = self.price_history[self.price_history['Symbol'] == symbol]
        
        if symbol_data.empty:
            return {
                'total_comparisons': 0,
                'avg_difference': None,
                'max_difference': None,
                'min_difference': None,
                'current_trend': None
            }
            
        analytics = {
            'total_comparisons': len(symbol_data),
            'avg_difference': symbol_data['Difference %'].mean(),
            'max_difference': symbol_data['Difference %'].max(),
            'min_difference': symbol_data['Difference %'].min(),
            'current_trend': self._calculate_analytics(symbol)['trend']
        }
        
        return analytics