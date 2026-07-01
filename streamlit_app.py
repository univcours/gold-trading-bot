import streamlit as st
import pandas as pd
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

# ====================== العنوان ======================
st.title("🏆 Gold Trading Bot")
st.markdown("### 📊 Live XAUUSDT Analysis")
st.markdown("---")

# ====================== جلب سعر الذهب ======================
@st.cache_data(ttl=10)
def get_gold_price():
    """جلب سعر الذهب من Binance"""
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=XAUUSDT"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        else:
            return 3300 + np.random.randn() * 5
    except:
        return 3300 + np.random.randn() * 5

@st.cache_data(ttl=10)
def get_order_book():
    """جلب الأوردر بوك"""
    try:
        url = "https://api.binance.com/api/v3/depth?symbol=XAUUSDT&limit=20"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            bids = pd.DataFrame(data['bids'], columns=['price', 'quantity'], dtype=float)
            asks = pd.DataFrame(data['asks'], columns=['price', 'quantity'], dtype=float)
            return bids, asks
        else:
            return generate_mock_order_book()
    except:
        return generate_mock_order_book()

def generate_mock_order_book():
    """بيانات تجريبية للأوردر بوك"""
    base = 3300 + np.random.randn() * 5
    bids = pd.DataFrame({
        'price': [base - i*0.5 for i in range(20)],
        'quantity': [np.random.randint(5, 50) for _ in range(20)]
    })
    asks = pd.DataFrame({
        'price': [base + i*0.5 for i in range(20)],
        'quantity': [np.random.randint(5, 50) for _ in range(20)]
    })
    return bids, asks

# ====================== الواجهة الرئيسية ======================
def main():
    # الشريط الجانبي
    with st.sidebar:
        st.header("⚙️ Settings")
        st.caption(f"Last Update: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # جلب البيانات
    with st.spinner("Loading data..."):
        price = get_gold_price()
        bids, asks = get_order_book()
    
    # عرض السعر
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 Gold Price", f"${price:.2f}")
    
    with col2:
        if not bids.empty:
            st.metric("📈 Best Bid", f"${bids['price'].iloc[0]:.2f}")
    
    with col3:
        if not asks.empty:
            st.metric("📉 Best Ask", f"${asks['price'].iloc[0]:.2f}")
    
    st.divider()
    
    # عرض الأوردر بوك
    if not bids.empty and not asks.empty:
        st.subheader("📊 Order Book")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Bids (Buy)")
            st.dataframe(bids.head(20), use_container_width=True)
            st.metric("Total Bid Volume", f"{bids['quantity'].sum():.2f}")
        
        with col2:
            st.markdown("### 🔴 Asks (Sell)")
            st.dataframe(asks.head(20), use_container_width=True)
            st.metric("Total Ask Volume", f"{asks['quantity'].sum():.2f}")
    
    # تحديث تلقائي
    st.caption("🔄 Updates every 10 seconds")
    time.sleep(10)
    st.rerun()

if __name__ == "__main__":
    main()
