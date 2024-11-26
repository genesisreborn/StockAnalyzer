import pandas as pd
import yfinance as yf
from bs4 import BeautifulSoup
import requests
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

class StockDataFetcher:
    def __init__(self):
        self.sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
    def get_sp500_symbols(self):
        """Fetch S&P 500 symbols from Wikipedia"""
        response = requests.get(self.sp500_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'class': 'wikitable'})
        
        symbols = []
        for row in table.findAll('tr')[1:]:
            symbol = row.findAll('td')[0].text.strip()
            # Fix special symbols
            symbol = symbol.replace('.','-')
            symbols.append(symbol)
        
        return symbols
    
    def fetch_stock_data(self, symbol, period='6mo'):
        """Fetch stock data using yfinance"""
        try:
            stock = yf.Ticker(symbol)
            df = stock.history(period=period)
            if not df.empty:
                return df
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
        return None

    def get_stock_financials(self, symbol):
        """Get detailed financial information"""
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            
            # Get financial statements
            balance_sheet = stock.balance_sheet
            income_stmt = stock.income_stmt
            cash_flow = stock.cashflow
            
            # Calculate key metrics
            financial_data = {
                'General': {
                    'Market Cap': info.get('marketCap'),
                    'Enterprise Value': info.get('enterpriseValue'),
                    'P/E Ratio': info.get('forwardPE'),
                    'PEG Ratio': info.get('pegRatio'),
                    'Dividend Yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                },
                'Trading': {
                    'Beta': info.get('beta'),
                    '52W High': info.get('fiftyTwoWeekHigh'),
                    '52W Low': info.get('fiftyTwoWeekLow'),
                    'Avg Volume': info.get('averageVolume'),
                },
                'Fundamentals': {
                    'ROE': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
                    'Profit Margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
                    'Operating Margin': info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else 0,
                    'Current Ratio': info.get('currentRatio'),
                },
                'Growth': {
                    'Revenue Growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
                    'Earnings Growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0,
                }
            }
            
            # Get institutional holders
            holders = stock.institutional_holders
            
            return financial_data, holders, balance_sheet, income_stmt, cash_flow
            
        except Exception as e:
            print(f"Error fetching financial data for {symbol}: {e}")
            return None, None, None, None, None

    def calculate_indicators(self, df, ema_period, sma_period):
        """Calculate EMA and SMA with adjustable periods"""
        if df is None or df.empty:
            return None
        
        df[f'EMA{ema_period}'] = df['Close'].ewm(span=ema_period, adjust=False).mean()
        df[f'SMA{sma_period}'] = df['Close'].rolling(window=sma_period).mean()
        
        # Calculate crossover
        df['Crossover'] = np.where(
            (df[f'EMA{ema_period}'] > df[f'SMA{sma_period}']) & (df[f'EMA{ema_period}'].shift(1) <= df[f'SMA{sma_period}'].shift(1)),
            'GOLDEN',
            np.where(
                (df[f'EMA{ema_period}'] < df[f'SMA{sma_period}']) & (df[f'EMA{ema_period}'].shift(1) >= df[f'SMA{sma_period}'].shift(1)),
                'DEATH',
                'NONE'
            )
        )
        
        return df 