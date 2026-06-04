import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Indigo BOM Arrivals", layout="wide", page_icon="🛫")

st.title("🛫 Indigo (6E) Arrivals Dashboard - BOM")
st.markdown("**Real-time monitoring for timely Wing Walker positioning**")

# Sidebar
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("AviationStack API Key", type="password", help="Get free key from aviationstack.com")
refresh_min = st.sidebar.slider("Refresh every (minutes)", 1, 10, 2)
alert_min = st.sidebar.slider("Alert if arriving in less than (minutes)", 15, 90, 45)

if not api_key:
    st.error("Please enter your AviationStack API Key in the sidebar.")
    st.stop()

def fetch_flights():
    url = "http://api.aviationstack.com/v1/flights"
    params = {
        'access_key': api_key,
        'arr_iata': 'BOM',
        'airline_iata': '6E',
        'limit': 100
    }
    
    try:
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        
        flights = []
        now = datetime.utcnow()
        
        for f in data.get('data', []):
            arr = f.get('arrival', {})
            dep = f.get('departure', {})
            
            eta_str = arr.get('estimated') or arr.get('scheduled')
            if eta_str:
                try:
                    eta = datetime.fromisoformat(eta_str.replace('Z', '+00:00'))
                    minutes_left = int((eta - now).total_seconds() / 60)
                except:
                    minutes_left = None
            else:
                minutes_left = None
            
            flights.append({
                "Flight": f.get('flight', {}).get('iata', 'N/A'),
                "Origin": dep.get('iata', 'N/A'),
                "Aircraft": f.get('aircraft', {}).get('iata', 'N/A'),
                "Status": f.get('flight_status', 'unknown').upper(),
                "Scheduled": arr.get('scheduled', 'N/A'),
                "Estimated": arr.get('estimated', 'N/A'),
                "Minutes Left": minutes_left,
                "Terminal": arr.get('terminal', '—'),
                "Gate": arr.get('gate', '—')
            })
        
        return pd.DataFrame(flights)
    
    except Exception as e:
        st.error(f"Failed to fetch data: {str(e)}")
        return pd.DataFrame()

# Auto-refresh
placeholder = st.empty()

while True:
    with placeholder.container():
        df = fetch_flights()
        
        if not df.empty:
            # Filters
            col1, col2 = st.columns([1, 1])
            with col1:
                status = st.selectbox("Status Filter", ['All'] + sorted(df['Status'].unique()))
            with col2:
                show_next = st.slider("Show flights arriving in next (minutes)", 30, 240, 180)
            
            filtered = df.copy()
            if status != 'All':
                filtered = filtered[filtered['Status'] == status]
            filtered = filtered[filtered['Minutes Left'] <= show_next]
            
            # Color coding
            def color_rows(row):
                if row['Minutes Left'] is not None and row['Minutes Left'] < alert_min:
                    return ['background-color: #ffe6e6'] * len(row)
                return [''] * len(row)
            
            styled = filtered.style.apply(color_rows, axis=1)
            
            st.dataframe(styled, use_container_width=True, height=650)
            
            # Urgent Alerts
            urgent = filtered[filtered['Minutes Left'] < alert_min]
            if not urgent.empty:
                st.error(f"🚨 **URGENT ALERT**: {len(urgent)} Indigo flights arriving soon!")
                st.dataframe(urgent[['Flight', 'Origin', 'Minutes Left', 'Status', 'Estimated']])
            
            st.success(f"✅ Showing {len(filtered)} incoming Indigo flights")
        else:
            st.info("No active Indigo arrivals found or API issue.")
        
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Auto-refresh every {refresh_min} min")
    
    time.sleep(refresh_min * 60)
