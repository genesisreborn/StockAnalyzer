import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import yfinance as yf
import numpy as np
from data_fetcher import StockDataFetcher
from datetime import datetime, timedelta

class StockApp:
    def __init__(self):
        self.fetcher = StockDataFetcher()
        self.symbols = self.fetcher.get_sp500_symbols()
        
    def run(self):
        # Set page config must be the first Streamlit command
        st.set_page_config(page_title="S&P 500 Stock Analysis", layout="wide")
        
        # Then add custom CSS
        st.markdown("""
            <style>
            .stButton button {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
                cursor: pointer;
            }
            .stButton button:hover {
                background-color: #45a049;
            }
            .metric-card {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            a {
                color: #4CAF50;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            </style>
        """, unsafe_allow_html=True)
        
        # Store the current page in session state
        if 'current_page' not in st.session_state:
            st.session_state.current_page = "Dashboard"
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = None
        
        # Initialize EMA and SMA values in session state if not present
        if 'ema_period' not in st.session_state:
            st.session_state.ema_period = 14
        if 'sma_period' not in st.session_state:
            st.session_state.sma_period = 50
        
        # Sidebar
        st.sidebar.title("Navigation")
        page = st.sidebar.radio("Go to", ["Dashboard", "Stocks", "Stock Details"], 
                               index=["Dashboard", "Stocks", "Stock Details"].index(st.session_state.current_page))
        
        st.session_state.current_page = page
        
        if page == "Dashboard":
            self.show_dashboard()
        elif page == "Stocks":
            self.show_stocks_list()
        else:
            self.show_stock_details()
    
    def show_dashboard(self):
        st.title("Dashboard - Recent Crossovers")
        
        # Add date filter and moving average inputs
        col1, col2, col3 = st.columns(3)
        with col1:
            days_to_look_back = st.slider("Days to look back", 1, 30, 7)
        with col2:
            st.session_state.ema_period = st.number_input("EMA Period", min_value=1, max_value=200, value=st.session_state.ema_period)
        with col3:
            st.session_state.sma_period = st.number_input("SMA Period", min_value=1, max_value=200, value=st.session_state.sma_period)
        
        # Create progress bar
        progress_bar = st.progress(0)
        crossover_data = []
        
        for i, symbol in enumerate(self.symbols):
            df = self.fetcher.fetch_stock_data(symbol)
            if df is not None:
                df = self.fetcher.calculate_indicators(df, st.session_state.ema_period, st.session_state.sma_period)
                if df is not None and not df.empty:
                    recent_data = df.tail(days_to_look_back)
                    crossovers = recent_data[recent_data['Crossover'] != 'NONE']
                    
                    for idx, row in crossovers.iterrows():
                        crossover_data.append({
                            'Symbol': symbol,
                            'Crossover': row['Crossover'],
                            'Price': row['Close'],
                            'Date': idx,
                            f'EMA{st.session_state.ema_period}': row[f'EMA{st.session_state.ema_period}'],
                            f'SMA{st.session_state.sma_period}': row[f'SMA{st.session_state.sma_period}']
                        })
            
            progress_bar.progress((i + 1) / len(self.symbols))
        
        # Display crossover data
        if crossover_data:
            df_crossover = pd.DataFrame(crossover_data)
            df_crossover = df_crossover.sort_values('Date', ascending=False)
            
            # Add filters
            col1, col2 = st.columns(2)
            with col1:
                signal_filter = st.multiselect(
                    "Filter by Signal Type",
                    options=['GOLDEN', 'DEATH'],
                    default=['GOLDEN', 'DEATH']
                )
            
            filtered_df = df_crossover[df_crossover['Crossover'].isin(signal_filter)]
            
            # Display metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Golden Crosses", len(filtered_df[filtered_df['Crossover'] == 'GOLDEN']))
            with col2:
                st.metric("Death Crosses", len(filtered_df[filtered_df['Crossover'] == 'DEATH']))
            
            # Make symbols clickable
            st.write("### Crossover Signals (Click on symbol for details)")
            
            # Convert dataframe to clickable format
            def make_clickable(symbol):
                return f'<a href="javascript:void(0);" onclick="handleClick(\'{symbol}\')">{symbol}</a>'
            
            filtered_df['Symbol'] = filtered_df['Symbol'].apply(make_clickable)
            
            # Display the dataframe with clickable symbols
            st.write(filtered_df.to_html(escape=False, index=False), unsafe_allow_html=True)
            
            # Add JavaScript to handle clicks
            st.markdown("""
            <script>
            function handleClick(symbol) {
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: symbol
                }, "*");
            }
            </script>
            """, unsafe_allow_html=True)
            
            # Handle symbol selection
            if st.session_state.selected_symbol:
                st.session_state.current_page = "Stock Details"
                st.rerun()
            
        else:
            st.write("No recent crossovers found")
    
    def show_stocks_list(self):
        st.title("S&P 500 Stocks")
        
        # Create a searchable dropdown
        selected_symbol = st.selectbox("Select a stock", self.symbols)
        
        if selected_symbol:
            df = self.fetcher.fetch_stock_data(selected_symbol)
            if df is not None:
                df = self.fetcher.calculate_indicators(df, st.session_state.ema_period, st.session_state.sma_period)
                
                # Display stock chart
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name='OHLC'
                ))
                
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df[f'EMA{st.session_state.ema_period}'],
                    name=f'EMA{st.session_state.ema_period}',
                    line=dict(color='orange')
                ))
                
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df[f'SMA{st.session_state.sma_period}'],
                    name=f'SMA{st.session_state.sma_period}',
                    line=dict(color='blue')
                ))
                
                st.plotly_chart(fig)
    
    def show_stock_details(self):
        st.title("Stock Details")
        
        # Use selected symbol from dashboard if available
        if st.session_state.selected_symbol:
            selected_symbol = st.session_state.selected_symbol
            st.session_state.selected_symbol = None  # Reset after use
        else:
            selected_symbol = st.selectbox("Select a stock", self.symbols)
        
        if selected_symbol:
            # Add a "Back to Dashboard" button
            if st.button("← Back to Dashboard"):
                st.session_state.current_page = "Dashboard"
                st.rerun()
            
            # Get detailed financial data
            financial_data, holders, balance_sheet, income_stmt, cash_flow = self.fetcher.get_stock_financials(selected_symbol)
            
            if financial_data:
                # Create tabs for different types of information
                tabs = st.tabs(["Overview", "Financials", "Charts", "Institutional Holders"])
                
                with tabs[0]:
                    st.subheader("Company Overview")
                    
                    # Display metrics in columns
                    for category, metrics in financial_data.items():
                        st.write(f"### {category}")
                        cols = st.columns(len(metrics))
                        for i, (metric, value) in enumerate(metrics.items()):
                            with cols[i]:
                                if isinstance(value, (int, float)) and value > 1000000:
                                    formatted_value = f"${value/1000000:.2f}M"
                                elif isinstance(value, float):
                                    formatted_value = f"{value:.2f}"
                                else:
                                    formatted_value = str(value)
                                st.metric(metric, formatted_value)
                
                with tabs[1]:
                    st.subheader("Financial Statements")
                    
                    # Show recent quarterly financials
                    if income_stmt is not None:
                        st.write("### Income Statement (Recent Quarters)")
                        st.dataframe(income_stmt.head().T)
                    
                    if balance_sheet is not None:
                        st.write("### Balance Sheet (Recent Quarters)")
                        st.dataframe(balance_sheet.head().T)
                
                with tabs[2]:
                    st.subheader("Analysis Charts")
                    
                    # Get historical data for charts
                    df = self.fetcher.fetch_stock_data(selected_symbol, period='1y')
                    if df is not None:
                        # Volume Chart
                        fig_volume = px.bar(df, x=df.index, y='Volume', title='Trading Volume')
                        st.plotly_chart(fig_volume)
                        
                        # Price Performance
                        df['Returns'] = df['Close'].pct_change()
                        df['Cumulative Returns'] = (1 + df['Returns']).cumprod()
                        fig_returns = px.line(df, x=df.index, y='Cumulative Returns', 
                                            title='Cumulative Returns (1 Year)')
                        st.plotly_chart(fig_returns)
                
                with tabs[3]:
                    st.subheader("Institutional Holders")
                    if holders is not None and not holders.empty:
                        # Create pie chart of top holders
                        fig_holders = px.pie(holders.head(10), 
                                           values='Shares', 
                                           names='Holder',
                                           title='Top 10 Institutional Holders')
                        st.plotly_chart(fig_holders)
                        
                        # Display full table
                        st.dataframe(holders)
            else:
                st.error("Unable to fetch detailed data for this stock")

if __name__ == "__main__":
    app = StockApp()
    app.run() 