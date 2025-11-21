import os
import io
import requests # <--- NEW IMPORT REQUIRED (pip install requests)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import yfinance as yf
from prophet import Prophet
from pydantic import BaseModel
from typing import Dict, Any, Optional

# --- NEW HELPER: Convert Name to Ticker ---
def lookup_ticker(query: str) -> Optional[Dict[str, str]]:
    """
    Uses Yahoo Finance Search API to convert a name (e.g., "Zomato") 
    into a ticker (e.g., "ZOMATO.NS").
    Prioritizes Indian stocks (.NS, .BO), then Global.
    """
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {'q': query, 'quotesCount': 5, 'newsCount': 0}

    try:
        r = requests.get(url, headers=headers, params=params, timeout=5)
        data = r.json()
        
        if 'quotes' not in data or len(data['quotes']) == 0:
            return None

        quotes = data['quotes']
        
        # 1. Look for Indian NSE (.NS) match first
        for q in quotes:
            if q.get('symbol', '').endswith('.NS'):
                return {'symbol': q['symbol'], 'name': q.get('shortname', q.get('longname', query))}
        
        # 2. Look for Indian BSE (.BO) match second
        for q in quotes:
            if q.get('symbol', '').endswith('.BO'):
                return {'symbol': q['symbol'], 'name': q.get('shortname', q.get('longname', query))}

        # 3. Default to the most relevant match (likely US/Global)
        best_match = quotes[0]
        return {'symbol': best_match['symbol'], 'name': best_match.get('shortname', best_match.get('longname', query))}

    except Exception as e:
        print(f"Search API Error: {e}")
        return None

# --- UPDATED PREDICTION FUNCTION ---
def predict_stock_price(user_query: str, days_ahead: int = 30) -> Dict[str, Any]:
    """
    1. Converts Name -> Ticker
    2. Downloads Data
    3. Runs Prophet
    4. Returns Image + Data
    """
    try:
        # STEP 1: Resolve Name to Ticker
        ticker_info = lookup_ticker(user_query)
        
        if not ticker_info:
            # Fallback: Try using the query exactly as is (in case it IS a ticker)
            search_ticker = user_query
            company_name = user_query.upper()
        else:
            search_ticker = ticker_info['symbol']
            company_name = ticker_info['name']

        print(f"🔍 Searching for: {user_query} -> Found: {search_ticker} ({company_name})")

        # STEP 2: Download Data
        df = yf.download(search_ticker, period="2y", progress=False)
        
        if df.empty:
            return None

        # Clean Data Structure
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

        if 'Date' not in df.columns or 'Close' not in df.columns: return None

        data = df[['Date', 'Close']].rename(columns={'Date': 'ds', 'Close': 'y'})
        if data['ds'].dt.tz is not None:
            data['ds'] = data['ds'].dt.tz_localize(None)

        # STEP 3: Run Prophet
        model = Prophet(daily_seasonality=True, yearly_seasonality=True)
        model.fit(data)
        future = model.make_future_dataframe(periods=days_ahead)
        forecast = model.predict(future)

        # Calculate Stats
        current_price = data['y'].iloc[-1]
        future_price = forecast['yhat'].iloc[-1]
        growth = ((future_price - current_price) / current_price) * 100
        
        forecast_data = []
        future_subset = forecast.iloc[-days_ahead:]
        for _, row in future_subset.iterrows():
            forecast_data.append({
                "date": row['ds'].strftime("%Y-%m-%d"),
                "price": round(row['yhat'], 2),
                "lower": round(row['yhat_lower'], 2),
                "upper": round(row['yhat_upper'], 2)
            })

        # STEP 4: Plotting
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

        plot_start = max(0, len(forecast) - (days_ahead + 90))
        future_forecast = forecast.iloc[plot_start:]
        
        ax.plot(future_forecast['ds'], future_forecast['yhat'], color='#10b981', label='Forecast', linewidth=2)
        ax.fill_between(future_forecast['ds'], future_forecast['yhat_lower'], future_forecast['yhat_upper'], color='#10b981', alpha=0.1)

        # Annotations
        last_date_hist = data['ds'].iloc[-1]
        ax.scatter(last_date_hist, current_price, color='white', s=50, zorder=5)
        
        target_date = future_forecast['ds'].iloc[-1]
        target_price = future_forecast['yhat'].iloc[-1]
        ax.scatter(target_date, target_price, color='#10b981', s=50, zorder=5)
        ax.annotate(f"{target_price:.0f}\n({growth:+.1f}%)", (target_date, target_price), 
                    textcoords="offset points", xytext=(10, 0), ha='left', color='#10b981', fontweight='bold', fontsize=10)

        ax.set_title(f"{company_name} ({search_ticker})", color='white', fontsize=14, fontweight='bold')
        ax.tick_params(colors='#94a3b8')
        ax.grid(True, color='#334155', linestyle='--', alpha=0.3)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#334155'); ax.spines['left'].set_visible(False)
        fig.autofmt_xdate()

        # Save Image
        output_dir = "generated_charts"
        os.makedirs(output_dir, exist_ok=True)
        safe_name = "".join([c for c in company_name if c.isalnum() or c in ('-','_')])[:20]
        plt.savefig(os.path.join(output_dir, f"{safe_name}_forecast.png"), format="png", bbox_inches='tight', transparent=True)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches='tight', transparent=True)
        plt.close(fig)
        buf.seek(0)

        return {
            "image_bytes": buf.read(),
            "forecast_values": forecast_data,
            "summary": {
                "company_name": company_name,   # <--- Sending Name back to UI
                "ticker": search_ticker,        # <--- Sending Ticker back to UI
                "current_price": round(current_price, 2),
                "predicted_price": round(future_price, 2),
                "growth_percent": round(growth, 2)
            }
        }

    except Exception as e:
        print(f"Stock Error: {e}")
        return None

class StockRequest(BaseModel):
    ticker: str # Note: This field name stays 'ticker' in API, but logically it's 'query'
    days_ahead: int = 30