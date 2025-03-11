import os
from typing import List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('alerts.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AlertSystem')

# Load environment variables
load_dotenv()

class AlertSystem:
    def __init__(self):
        self.sender_email = os.getenv('EMAIL_SENDER')
        self.sender_password = os.getenv('EMAIL_PASSWORD')
        self.recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
        self.threshold = float(os.getenv('DISCREPANCY_THRESHOLD', '0.5'))
        self.alert_history = pd.DataFrame(
            columns=['Timestamp', 'Symbol', 'Discrepancy', 'Alert Sent', 'Alert Type']
        )
        self.last_alert_time = {}  # Track last alert time per symbol
        self.alert_cooldown = timedelta(minutes=5)  # Minimum time between alerts for same symbol
        
        if not all([self.sender_email, self.sender_password, self.recipients]):
            raise ValueError('Email configuration not found in environment variables')
            
    def _validate_alert_conditions(self, symbol: str, price_difference: float) -> tuple[bool, str]:
        """Validate if an alert should be sent based on various conditions."""
        current_time = datetime.now()
        
        # Check alert cooldown
        if symbol in self.last_alert_time:
            time_since_last_alert = current_time - self.last_alert_time[symbol]
            if time_since_last_alert < self.alert_cooldown:
                logger.info(f'Alert for {symbol} skipped: cooldown period active')
                return False, "cooldown"
        
        # Check if the difference is significant enough
        if abs(price_difference) <= self.threshold:
            return False, "below_threshold"
            
        # Check for repeated alerts
        recent_alerts = self.alert_history[
            (self.alert_history['Symbol'] == symbol) & 
            (self.alert_history['Timestamp'] > current_time - timedelta(hours=1))
        ]
        
        if len(recent_alerts) >= 5:
            logger.warning(f'Too many alerts for {symbol} in the last hour')
            return False, "rate_limit"
            
        return True, "valid"
    
    def should_send_alert(self, price_difference: float) -> bool:
        """Check if the price difference exceeds the threshold."""
        return abs(price_difference) > self.threshold
    
    def send_alert(self, symbol: str, alpha_price: float, yahoo_price: float, difference_percentage: float) -> bool:
        """Send email alert when price discrepancy exceeds threshold."""
        should_alert, reason = self._validate_alert_conditions(symbol, difference_percentage)
        
        if not should_alert:
            logger.info(f'Alert validation failed for {symbol}: {reason}')
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = f'Price Discrepancy Alert - {symbol}'
            
            current_time = datetime.now()
            body = f"""Price Discrepancy Alert for {symbol}:
            
Alpha Vantage Price: ${alpha_price:.2f}
Yahoo Finance Price: ${yahoo_price:.2f}
Price Difference: {difference_percentage:.2f}%

This difference exceeds the configured threshold of {self.threshold}%.

Time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}

Alert Analysis:
- Threshold: {self.threshold}%
- Current Discrepancy: {difference_percentage:.2f}%
- Percentage Above Threshold: {(difference_percentage - self.threshold):.2f}%
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            # Update alert history and tracking
            self.last_alert_time[symbol] = current_time
            self.alert_history = pd.concat([
                self.alert_history,
                pd.DataFrame([{
                    'Timestamp': current_time,
                    'Symbol': symbol,
                    'Discrepancy': difference_percentage,
                    'Alert Sent': True,
                    'Alert Type': 'threshold_exceeded'
                }])
            ], ignore_index=True)
            
            logger.info(f'Alert sent successfully for {symbol} with {difference_percentage:.2f}% discrepancy')
            return True
            
        except Exception as e:
            logger.error(f'Error sending alert for {symbol}: {str(e)}')
            return False
    
    def get_alert_history(self) -> pd.DataFrame:
        """Get historical alert data."""
        return self.alert_history
        
    def get_alert_stats(self) -> dict:
        """Get statistics about alerts sent."""
        if self.alert_history.empty:
            return {
                'total_alerts': 0,
                'unique_symbols': 0,
                'avg_discrepancy': 0,
                'max_discrepancy': 0
            }
            
        stats = {
            'total_alerts': len(self.alert_history),
            'unique_symbols': self.alert_history['Symbol'].nunique(),
            'avg_discrepancy': self.alert_history['Discrepancy'].mean(),
            'max_discrepancy': self.alert_history['Discrepancy'].max()
        }
        
        return stats