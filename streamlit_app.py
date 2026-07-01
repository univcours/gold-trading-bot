import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import time
from datetime import datetime
import numpy as np

# ====================== إعدادات الصفحة ======================
st.set_page_config(
    page_title="Gold Trading Bot",
    page_icon="📊",
    layout="wide"
)

# ====================== عنوان التطبيق ======================
st.title("🏆 Gold Trading Bot")
st.markdown("### 📊 Live XAUUSDT Analysis")
st.markdown("---")

# ====================== دوال جلب البيانات ======================
@st.cache_data(ttl=30)
def get_klines():
    """جلب بيانات الشموع من Binance"""
    try:
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": "XAUUSDT",
            "interval": "5m",
            "limit": 100
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        else:
            return generate_mock_data()
    except Exception as e:
        return generate_mock_data()

@st.cache_data(ttl=30)
def get_order_book():
    """جلب الأوردر بوك"""
    try:
        url = "https://api.binance.com/api/v3/depth"
        params = {
            "symbol": "XAUUSDT",
            "limit": 50
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
            asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
            return bids, asks
        else:
            return generate_mock_order_book()
    except Exception as e:
        return generate_mock_order_book()

def generate_mock_data():
    """توليد بيانات تجريبية"""
    st.warning("⚠️ Using simulated data (API unavailable)")
    
    dates = pd.date_range(end=datetime.now(), periods=100, freq='5min')
    base_price = 3300
    
    data = []
    for i in range(100):
        change = np.random.randn() * 0.5
        base_price += change
        open_p = base_price
        close_p = base_price + np.random.randn() * 0.3
        high_p = max(open_p, close_p) + abs(np.random.randn() * 0.5)
        low_p = min(open_p, close_p) - abs(np.random.randn() * 0.5)
        volume = np.random.randint(50, 500)
        data.append([dates[i], open_p, high_p, low_p, close_p, volume])
    
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def generate_mock_order_book():
    """توليد بيانات تجريبية للأوردر بوك"""
    base_price = 3300 + np.random.randn() * 5
    
    bids = pd.DataFrame({
        'price': [base_price - i * 0.2 for i in range(50)],
        'quantity': [np.random.randint(5, 50) for _ in range(50)]
    })
    
    asks = pd.DataFrame({
        'price': [base_price + i * 0.2 for i in range(50)],
        'quantity': [np.random.randint(5, 50) for _ in range(50)]
    })
    
    return bids, asks

# ====================== حساب المؤشرات ======================
def calculate_indicators(df):
    """حساب المؤشرات الفنية"""
    if df.empty:
        return df
    
    # المتوسطات المتحركة
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['SMA_50'] = df['close'].rolling(50).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    df['SMA_20'] = df['close'].rolling(20).mean()
    df['STD_20'] = df['close'].rolling(20).std()
    df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    return df

# ====================== توليد الإشارات ======================
def generate_signals(df):
    """توليد إشارات بيع وشراء"""
    signals = {
        'buy': [],
        'sell': [],
        'score': 0,
        'reasons': []
    }
    
    if df.empty or len(df) < 30:
        return signals
    
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    score = 0
    
    # RSI
    if 'RSI' in last and not pd.isna(last['RSI']):
        if last['RSI'] < 30:
            score += 2
            signals['buy'].append(f"RSI Oversold: {last['RSI']:.2f}")
            signals['reasons'].append(f"🟢 RSI oversold")
        elif last['RSI'] > 70:
            score -= 2
            signals['sell'].append(f"RSI Overbought: {last['RSI']:.2f}")
            signals['reasons'].append(f"🔴 RSI overbought")
    
    # SMA
    if 'SMA_20' in last and 'SMA_50' in last:
        if not pd.isna(last['SMA_20']) and not pd.isna(last['SMA_50']):
            if last['SMA_20'] > last['SMA_50']:
                score += 1
                signals['buy'].append("SMA 20 > SMA 50 (Bullish)")
            else:
                score -= 1
                signals['sell'].append("SMA 20 < SMA 50 (Bearish)")
    
    # Bollinger Bands
    if 'Lower_Band' in last and 'Upper_Band' in last:
        if not pd.isna(last['Lower_Band']) and not pd.isna(last['Upper_Band']):
            if last['close'] < last['Lower_Band']:
                score += 2
                signals['buy'].append("Price below Lower Band")
            elif last['close'] > last['Upper_Band']:
                score -= 2
                signals['sell'].append("Price above Upper Band")
    
    signals['score'] = score
    return signals

# ====================== رسم الشارت ======================
def create_chart(df):
    """إنشاء شارت الشموع"""
    if df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # الشموع اليابانية
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='XAUUSDT',
        increasing_line_color='#00ff00',
        decreasing_line_color='#ff0000'
    ))
    
    # المتوسطات المتحركة
    if 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['SMA_20'],
            mode='lines',
            name='SMA 20',
            line=dict(color='#FFD700', width=1.5)
        ))
    
    if 'SMA_50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['SMA_50'],
            mode='lines',
            name='SMA 50',
            line=dict(color='#FF6B6B', width=1.5)
        ))
    
    # Bollinger Bands
    if 'Upper_Band' in df.columns and 'Lower_Band' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['Upper_Band'],
            mode='lines',
            name='Upper Band',
            line=dict(color='#ff0000', width=1, dash='dash')
        ))
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['Lower_Band'],
            mode='lines',
            name='Lower Band',
            line=dict(color='#00ff00', width=1, dash='dash')
        ))
    
    fig.update_layout(
        title='📈 XAUUSDT Price Chart',
        xaxis_title='Time',
        yaxis_title='Price (USDT)',
        template='plotly_dark',
        height=600,
        xaxis_rangeslider_visible=False
    )
    
    return fig

# ====================== الواجهة الرئيسية ======================
def main():
    # الشريط الجانبي
    with st.sidebar:
        st.header("⚙️ Settings")
        
        timeframe = st.selectbox(
            "⏱️ Timeframe",
            ["1m", "5m", "15m", "30m", "1h", "4h", "1d"],
            index=1
        )
        
        st.divider()
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        st.info("📡 Data Source: Binance API")
        st.caption(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # تحميل البيانات
    with st.spinner("🔄 Loading data..."):
        try:
            df = get_klines()
            if df.empty:
                st.error("❌ Failed to load data")
                return
            
            df = calculate_indicators(df)
            signals = generate_signals(df)
            bids, asks = get_order_book()
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return
    
    # عرض الإحصائيات
    col1, col2, col3, col4 = st.columns(4)
    
    current_price = df['close'].iloc[-1]
    price_change = ((df['close'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0] * 100)
    
    with col1:
        st.metric("💰 Current Price", f"${current_price:.2f}", f"{price_change:+.2f}%")
    with col2:
        st.metric("📊 Volume", f"{df['volume'].sum():,.0f}")
    with col3:
        if not bids.empty:
            st.metric("📈 Best Bid", f"${bids['price'].iloc[0]:.2f}")
    with col4:
        if not asks.empty:
            st.metric("📉 Best Ask", f"${asks['price'].iloc[0]:.2f}")
    
    st.divider()
    
    # ===== عرض الإشارات =====
    st.subheader("🎯 Trading Signals")
    
    score = signals['score']
    if score >= 3:
        st.success(f"🟢 BUY Signal (Score: {score})")
        st.balloons()
    elif score <= -3:
        st.error(f"🔴 SELL Signal (Score: {score})")
        st.snow()
    else:
        st.info(f"⚪ NEUTRAL (Score: {score})")
    
    if signals['buy']:
        for signal in signals['buy']:
            st.success(f"✅ {signal}")
    
    if signals['sell']:
        for signal in signals['sell']:
            st.error(f"❌ {signal}")
    
    st.divider()
    
    # ===== عرض الشارت =====
    st.subheader("📈 Live Chart")
    fig = create_chart(df)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # ===== عرض الأوردر بوك =====
    if not bids.empty and not asks.empty:
        st.subheader("📊 Order Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids (Buy Orders)")
            st.dataframe(bids.head(20), use_container_width=True)
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():.2f}")
        
        with col2:
            st.markdown("### 🔴 Asks (Sell Orders)")
            st.dataframe(asks.head(20), use_container_width=True)
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():.2f}")
    
    # ===== تحديث تلقائي =====
    st.caption("🔄 Auto-refreshing every 60 seconds...")
    time.sleep(60)
    st.rerun()

if __name__ == "__main__":
    main()
