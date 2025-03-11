import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from data_fetcher import DataFetcher
from alert_system import AlertSystem

# Initialize the data fetcher and alert system
data_fetcher = DataFetcher()
alert_system = AlertSystem()

# Set up the Streamlit page
st.set_page_config(page_title='Financial Data Accuracy Dashboard', layout='wide')
st.title('Financial Data Accuracy Dashboard')

# Sidebar for stock symbol input
st.sidebar.title('Settings')
symbol = st.sidebar.text_input('Enter Stock Symbol', value='AAPL').upper()

# Initialize session state for historical data
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = pd.DataFrame(
        columns=['Timestamp', 'Alpha Vantage Price', 'Yahoo Finance Price', 'Discrepancy %']
    )

# Main content area
col1, col2 = st.columns(2)

# Real-time price comparison
with col1:
    st.subheader('Real-Time Price Comparison')
    alpha_price, yahoo_price, discrepancy = data_fetcher.get_price_comparison(symbol)
    
    if all(x is not None for x in [alpha_price, yahoo_price, discrepancy]):
        # Add data to historical record
        new_data = pd.DataFrame([
            {
                'Timestamp': datetime.now(),
                'Alpha Vantage Price': alpha_price,
                'Yahoo Finance Price': yahoo_price,
                'Discrepancy %': discrepancy
            }
        ])
        st.session_state.historical_data = pd.concat(
            [st.session_state.historical_data, new_data],
            ignore_index=True
        )
        
        # Display current prices
        price_col1, price_col2 = st.columns(2)
        with price_col1:
            st.metric('Alpha Vantage Price', f'${alpha_price:.2f}')
        with price_col2:
            st.metric('Yahoo Finance Price', f'${yahoo_price:.2f}')
        
        # Display discrepancy
        st.metric('Price Discrepancy', f'{discrepancy:.2f}%')
        
        # Check for alerts
        if alert_system.should_alert(discrepancy):
            st.error(f'⚠️ High price discrepancy detected: {discrepancy:.2f}%')
            alert_system.send_alert(symbol, alpha_price, yahoo_price, discrepancy)
    else:
        st.error('Unable to fetch price data. Please check your API keys and internet connection.')

# Historical trend visualization
with col2:
    st.subheader('Historical Price Comparison')
    if not st.session_state.historical_data.empty:
        fig = go.Figure()
        
        # Add price lines
        fig.add_trace(go.Scatter(
            x=st.session_state.historical_data['Timestamp'],
            y=st.session_state.historical_data['Alpha Vantage Price'],
            name='Alpha Vantage',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=st.session_state.historical_data['Timestamp'],
            y=st.session_state.historical_data['Yahoo Finance Price'],
            name='Yahoo Finance',
            line=dict(color='green')
        ))
        
        fig.update_layout(
            title=f'{symbol} Price Comparison',
            xaxis_title='Time',
            yaxis_title='Price ($)',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display discrepancy trend
        st.subheader('Discrepancy Trend')
        fig_disc = go.Figure()
        fig_disc.add_trace(go.Scatter(
            x=st.session_state.historical_data['Timestamp'],
            y=st.session_state.historical_data['Discrepancy %'],
            name='Discrepancy',
            line=dict(color='red')
        ))
        
        fig_disc.update_layout(
            title='Price Discrepancy Over Time',
            xaxis_title='Time',
            yaxis_title='Discrepancy (%)',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_disc, use_container_width=True)
    else:
        st.info('Waiting for data to be collected...')

# Auto-refresh the dashboard
st.empty()
st.button('Refresh Data')