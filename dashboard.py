import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
import io
import logging
from data_fetcher import DataFetcher
from alert_system import AlertSystem

# Initialize logging for dashboard
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Dashboard')

# Performance metrics
class PerformanceMetrics:
    def __init__(self):
        self.api_response_times = []
        self.error_counts = {'alpha_vantage': 0, 'yahoo_finance': 0}
        self.last_refresh = None
        
    def add_response_time(self, duration: float):
        self.api_response_times.append(duration)
        if len(self.api_response_times) > 100:
            self.api_response_times.pop(0)
    
    def get_avg_response_time(self) -> float:
        return sum(self.api_response_times) / len(self.api_response_times) if self.api_response_times else 0
    
    def increment_error(self, source: str):
        self.error_counts[source] += 1
        
    def get_error_rates(self) -> dict:
        total_requests = len(self.api_response_times)
        return {
            source: (count / total_requests * 100 if total_requests > 0 else 0)
            for source, count in self.error_counts.items()
        }

# Page configuration
st.set_page_config(
    page_title="Financial Data Accuracy Dashboard",
    page_icon="📊",
    layout="wide"
)

# Initialize components with caching
@st.cache_resource
def init_components():
    return DataFetcher(), AlertSystem(), PerformanceMetrics()

data_fetcher, alert_system, metrics = init_components()

# Title and description
st.title("📊 Financial Data Accuracy Dashboard")
st.markdown("""
This dashboard monitors stock price data accuracy across multiple sources in real-time.
It compares prices from Alpha Vantage and Yahoo Finance APIs and alerts when discrepancies exceed the threshold.
""")

# Sidebar configuration
with st.sidebar:
    st.header("Settings")
    symbol = st.text_input("Stock Symbol", value="AAPL").upper()
    refresh_interval = st.number_input(
        "Refresh Interval (seconds)",
        min_value=5,
        value=30
    )
    display_limit = st.number_input(
        "Display History Limit",
        min_value=10,
        value=100
    )
    
    # Export Data Section
    st.header("Export Data")
    export_format = st.selectbox(
        "Export Format",
        ["CSV", "JSON", "Excel"]
    )
    
    if st.button("Export Data"):
        hist_data = data_fetcher.get_historical_comparison()
        if not hist_data.empty:
            if export_format == "CSV":
                csv = hist_data.to_csv(index=False)
                st.download_button(
                    "Download CSV",
                    csv,
                    f"price_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv"
                )
            elif export_format == "JSON":
                json_str = hist_data.to_json(orient="records", date_format="iso")
                st.download_button(
                    "Download JSON",
                    json_str,
                    f"price_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    "application/json"
                )
            else:  # Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    hist_data.to_excel(writer, sheet_name='Price Comparison', index=False)
                st.download_button(
                    "Download Excel",
                    buffer.getvalue(),
                    f"price_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    # Testing Controls
    st.header("Testing Controls")
    if st.button("Test High-Volatility Symbols"):
        test_symbols = ["TSLA", "NVDA", "COIN"]
        for test_symbol in test_symbols:
            logger.info(f"Testing high-volatility symbol: {test_symbol}")
            start_time = time.time()
            prices = data_fetcher.get_price_comparison(test_symbol)
            metrics.add_response_time(time.time() - start_time)
            st.write(f"{test_symbol}: {prices}")

# Main layout
col1, col2 = st.columns(2)

with col1:
    # Price Monitoring Section
    st.subheader("Real-time Price Comparison")
    price_card = st.empty()
    
    # Performance Metrics
    st.subheader("System Performance")
    perf_container = st.empty()
    
    # Analytics Summary
    st.subheader("Analytics Summary")
    analytics_container = st.empty()
    
    # Alert Configuration Status
    st.info(f"Alert Threshold: {alert_system.threshold}%")
    alert_cooldown = st.empty()
    
    # Alert Statistics
    st.subheader("Alert Statistics")
    stats_container = st.empty()
    
    # Recent Alerts
    st.subheader("Recent Alerts")
    alert_container = st.empty()

with col2:
    # Historical Comparison
    st.subheader("Historical Price Comparison")
    history_chart = st.empty()
    
    # Discrepancy Analysis
    st.subheader("Discrepancy Analysis")
    disc_col1, disc_col2 = st.columns(2)
    
    with disc_col1:
        st.subheader("Distribution")
        dist_chart = st.empty()
    
    with disc_col2:
        st.subheader("24h Trend")
        trend_chart = st.empty()

# Bottom section for detailed monitoring
st.subheader("System Monitoring")
log_expander = st.expander("View Recent Logs")
with log_expander:
    try:
        with open('dashboard.log', 'r') as log_file:
            recent_logs = log_file.readlines()[-20:]  # Last 20 lines
            st.code(''.join(recent_logs))
    except FileNotFoundError:
        st.warning("No logs available yet")

# Data table section
st.subheader("Detailed Price History")
history_table = st.empty()

# Main loop
while True:
    try:
        start_time = time.time()
        
        # Fetch current prices
        alpha_price, yahoo_price, diff_percentage = data_fetcher.get_price_comparison(symbol)
        
        # Record API response time
        metrics.add_response_time(time.time() - start_time)
        
        if all(x is not None for x in [alpha_price, yahoo_price, diff_percentage]):
            # Update price cards with validation status
            price_card.metric(
                label=f"{symbol} Current Prices",
                value=f"${alpha_price:.2f} (Alpha) vs ${yahoo_price:.2f} (Yahoo)",
                delta=f"{diff_percentage:.2f}% difference"
            )
            
            # Update performance metrics
            avg_response_time = metrics.get_avg_response_time()
            error_rates = metrics.get_error_rates()
            perf_metrics = pd.DataFrame([
                {"Metric": "Avg Response Time", "Value": f"{avg_response_time:.2f}s"},
                {"Metric": "Alpha Vantage Error Rate", "Value": f"{error_rates['alpha_vantage']:.1f}%"},
                {"Metric": "Yahoo Finance Error Rate", "Value": f"{error_rates['yahoo_finance']:.1f}%"}
            ])
            perf_container.dataframe(perf_metrics, hide_index=True)
            
            # Check and send alerts if needed
            if alert_system.should_send_alert(diff_percentage):
                alert_system.send_alert(symbol, alpha_price, yahoo_price, diff_percentage)
            
            # Update alert statistics
            stats = alert_system.get_alert_stats()
            stats_df = pd.DataFrame([{
                "Metric": key,
                "Value": f"{value:.2f}" if isinstance(value, float) else str(value)
            } for key, value in stats.items()])
            stats_container.dataframe(stats_df, hide_index=True)
            
            # Update analytics summary
            analytics = data_fetcher.get_analytics_summary(symbol)
            analytics_df = pd.DataFrame([
                {"Metric": "Total Comparisons", "Value": analytics['total_comparisons']},
                {"Metric": "Average Difference", "Value": f"{analytics['avg_difference']:.2f}%" if analytics['avg_difference'] else "N/A"},
                {"Metric": "Maximum Difference", "Value": f"{analytics['max_difference']:.2f}%" if analytics['max_difference'] else "N/A"},
                {"Metric": "Minimum Difference", "Value": f"{analytics['min_difference']:.2f}%" if analytics['min_difference'] else "N/A"},
                {"Metric": "Current Trend", "Value": analytics['current_trend'] if analytics['current_trend'] else "N/A"}
            ])
            analytics_container.dataframe(analytics_df, hide_index=True)

            # Get and display historical data
            hist_data = data_fetcher.get_historical_comparison()
            recent_hist = hist_data.tail(display_limit)
            
            if not recent_hist.empty:
                # Update price history chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=recent_hist['Timestamp'],
                    y=recent_hist['Alpha Vantage Price'],
                    name='Alpha Vantage',
                    line=dict(color='blue')
                ))
                fig.add_trace(go.Scatter(
                    x=recent_hist['Timestamp'],
                    y=recent_hist['Yahoo Finance Price'],
                    name='Yahoo Finance',
                    line=dict(color='green')
                ))
                fig.update_layout(
                    title=f'{symbol} Price History',
                    xaxis_title='Time',
                    yaxis_title='Price ($)',
                    height=400
                )
                history_chart.plotly_chart(fig, use_container_width=True)
                
                # Add Moving Average to price history chart
                fig.add_trace(go.Scatter(
                    x=recent_hist['Timestamp'],
                    y=recent_hist['Moving Average'],
                    name='Moving Average',
                    line=dict(color='purple', dash='dash')
                ))
                
                # Update distribution chart
                fig_dist = go.Figure()
                fig_dist.add_trace(go.Histogram(
                    x=recent_hist['Difference %'],
                    nbinsx=20,
                    name='Discrepancy Distribution'
                ))
                fig_dist.update_layout(height=200)
                dist_chart.plotly_chart(fig_dist, use_container_width=True)
                
                # Update trend chart
                last_24h = recent_hist[
                    recent_hist['Timestamp'] > datetime.now() - timedelta(hours=24)
                ]
                if not last_24h.empty:
                    fig_trend = go.Figure()
                    fig_trend.add_trace(go.Scatter(
                        x=last_24h['Timestamp'],
                        y=last_24h['Difference %'],
                        name='24h Trend',
                        line=dict(color='red')
                    ))
                    fig_trend.update_layout(height=200)
                    trend_chart.plotly_chart(fig_trend, use_container_width=True)
                
                # Add volatility chart
                st.subheader("Volatility Analysis")
                fig_vol = go.Figure()
                fig_vol.add_trace(go.Scatter(
                    x=recent_hist['Timestamp'],
                    y=recent_hist['Volatility'],
                    name='Price Volatility',
                    line=dict(color='orange')
                ))
                fig_vol.update_layout(
                    title='Price Volatility Over Time',
                    xaxis_title='Time',
                    yaxis_title='Volatility',
                    height=200
                )
                st.plotly_chart(fig_vol, use_container_width=True)

            # Update alert history
            alert_hist = alert_system.get_alert_history()
            if not alert_hist.empty:
                alert_container.dataframe(
                    alert_hist.tail(5)[['Timestamp', 'Symbol', 'Discrepancy', 'Alert Type']],
                    hide_index=True
                )
            
            # Update detailed history table
            history_table.dataframe(
                recent_hist.sort_values('Timestamp', ascending=False),
                hide_index=True
            )
            
            # Update alert cooldown status
            if symbol in alert_system.last_alert_time:
                time_since_last = datetime.now() - alert_system.last_alert_time[symbol]
                cooldown_status = f"Time since last alert: {time_since_last.seconds} seconds"
                alert_cooldown.info(cooldown_status)
        else:
            if alpha_price is None:
                metrics.increment_error('alpha_vantage')
            if yahoo_price is None:
                metrics.increment_error('yahoo_finance')
    
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
    
    # Wait for next update
    time.sleep(refresh_interval)