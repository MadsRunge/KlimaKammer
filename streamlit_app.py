#!/usr/bin/env python3
"""
Climate Monitor Streamlit Frontend
Beautiful web interface for the climate monitoring system
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import threading
import os
import json
from pathlib import Path
import asyncio

# Import existing modules
from sensor_logger import SensorLogger, SensorReading
from climate_analyzer import ClimateAnalyzer, DataReader, ClimateReading
from main import EnhancedClimateMonitorApp
from bbr_service import BBRAddressService, BuildingData

# Configure Streamlit page
st.set_page_config(
    page_title="Climate Monitor Dashboard",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for beautiful styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    
    .status-active { background-color: #28a745; }
    .status-inactive { background-color: #dc3545; }
    .status-warning { background-color: #ffc107; }
    
    .sidebar-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .stAlert > div {
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sensor_logger' not in st.session_state:
    st.session_state.sensor_logger = None
if 'logging_active' not in st.session_state:
    st.session_state.logging_active = False
if 'sensor_thread' not in st.session_state:
    st.session_state.sensor_thread = None
if 'current_address' not in st.session_state:
    st.session_state.current_address = ""
if 'building_data' not in st.session_state:
    st.session_state.building_data = None
if 'climate_app' not in st.session_state:
    st.session_state.climate_app = None

def init_climate_app():
    """Initialize the climate monitoring application"""
    if st.session_state.climate_app is None:
        try:
            data_dir = st.session_state.get('data_dir', 'sensordata')
            st.session_state.climate_app = EnhancedClimateMonitorApp(data_dir)
            return True
        except Exception as e:
            st.error(f"❌ Fejl ved initialisering af klimaapp: {e}")
            return False
    return True

def sensor_logging_worker(sensor_logger, interval_seconds):
    """Background worker for continuous sensor logging"""
    reading_count = 0
    while st.session_state.logging_active:
        try:
            reading = sensor_logger.read_sensor_data()
            if reading:
                sensor_logger.save_reading(reading)
                reading_count += 1
                
                # Update session state with latest reading
                st.session_state.latest_reading = reading
                st.session_state.reading_count = reading_count
            
            time.sleep(interval_seconds)
        except Exception as e:
            st.session_state.sensor_error = str(e)
            break

def get_historical_data(days=7):
    """Get historical sensor data for visualization"""
    try:
        data_reader = DataReader()
        daily_dir = data_reader.data_dir / "daily"
        
        if not daily_dir.exists():
            return pd.DataFrame()
        
        all_data = []
        csv_files = sorted(list(daily_dir.glob("*.csv")))[-days:]
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file)
                if not df.empty and 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    all_data.append(df)
            except Exception as e:
                st.warning(f"⚠️ Kunne ikke læse {csv_file.name}: {e}")
                continue
        
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            return combined_df.sort_values('timestamp')
        
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Fejl ved hentning af historiske data: {e}")
        return pd.DataFrame()

def create_temperature_chart(df):
    """Create temperature chart"""
    if df.empty or 'temperature' not in df.columns or 'timestamp' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen temperaturdata tilgængelig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            title="🌡️ Temperatur over tid",
            template="plotly_white",
            height=400
        )
        return fig
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['temperature'],
        mode='lines',
        name='Temperatur',
        line=dict(color='#ff6b6b', width=2),
        hovertemplate='<b>%{y:.1f}°C</b><br>%{x}<extra></extra>'
    ))
    
    fig.update_layout(
        title="🌡️ Temperatur over tid",
        xaxis_title="Tid",
        yaxis_title="Temperatur (°C)",
        template="plotly_white",
        height=400,
        showlegend=False
    )
    
    return fig

def create_humidity_chart(df):
    """Create humidity chart"""
    if df.empty or 'humidity' not in df.columns or 'timestamp' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen luftfugtighedsdata tilgængelig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            title="💧 Luftfugtighed over tid",
            template="plotly_white",
            height=400
        )
        return fig
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['humidity'],
        mode='lines',
        name='Luftfugtighed',
        line=dict(color='#4ecdc4', width=2),
        hovertemplate='<b>%{y:.1f}%</b><br>%{x}<extra></extra>'
    ))
    
    fig.update_layout(
        title="💧 Luftfugtighed over tid",
        xaxis_title="Tid",
        yaxis_title="Luftfugtighed (%)",
        template="plotly_white",
        height=400,
        showlegend=False
    )
    
    return fig

def create_combined_chart(df):
    """Create combined temperature and humidity chart"""
    if df.empty or 'temperature' not in df.columns or 'humidity' not in df.columns or 'timestamp' not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Ingen klimadata tilgængelig",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False, font=dict(size=16)
        )
        fig.update_layout(
            title="📊 Kombineret klimadata",
            template="plotly_white",
            height=500
        )
        return fig
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['temperature'],
        mode='lines',
        name='Temperatur (°C)',
        line=dict(color='#ff6b6b', width=2),
        yaxis='y'
    ))
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['humidity'],
        mode='lines',
        name='Luftfugtighed (%)',
        line=dict(color='#4ecdc4', width=2),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title="📊 Kombineret klimadata",
        xaxis_title="Tid",
        template="plotly_white",
        height=500,
        yaxis=dict(
            title="Temperatur (°C)",
            side="left",
            color='#ff6b6b'
        ),
        yaxis2=dict(
            title="Luftfugtighed (%)",
            side="right",
            overlaying="y",
            color='#4ecdc4'
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def get_analysis_history():
    """Get list of previous analyses"""
    try:
        analysis_dir = Path(st.session_state.data_dir) / "analyses"
        if not analysis_dir.exists():
            return []
        
        analysis_files = []
        
        # Get all analysis files from all date directories
        for date_dir in sorted(analysis_dir.iterdir(), reverse=True):
            if date_dir.is_dir():
                for analysis_file in sorted(date_dir.glob("*.txt"), reverse=True):
                    if analysis_file.name != "latest_analysis.txt":
                        # Parse filename for better display
                        try:
                            file_parts = analysis_file.stem.split('_')
                            if len(file_parts) >= 3:
                                time_part = file_parts[0]
                                analysis_type = '_'.join(file_parts[1:])
                                display_name = f"{date_dir.name} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]} - {analysis_type}"
                            else:
                                display_name = f"{date_dir.name} - {analysis_file.stem}"
                            
                            analysis_files.append({
                                'path': analysis_file,
                                'display_name': display_name,
                                'date': date_dir.name,
                                'time': file_parts[0] if file_parts else "00-00-00"
                            })
                        except Exception:
                            # Fallback for files that don't match expected format
                            display_name = f"{date_dir.name} - {analysis_file.stem}"
                            analysis_files.append({
                                'path': analysis_file,
                                'display_name': display_name,
                                'date': date_dir.name,
                                'time': "00-00-00"
                            })
        
        return analysis_files
    except Exception as e:
        st.error(f"Fejl ved hentning af analyse historik: {e}")
        return []

def parse_analysis_content(content):
    """Parse analysis content for better display"""
    try:
        lines = content.split('\n')
        
        # Find the AI response section
        ai_response_start = -1
        for i, line in enumerate(lines):
            if "AI RESPONS:" in line or "AI Analyse" in line:
                ai_response_start = i + 1
                break
            elif line.strip().startswith("Du er en") or line.strip().startswith("Baseret på"):
                ai_response_start = i
                break
        
        if ai_response_start == -1:
            # If no clear start found, try to find content after metadata
            for i, line in enumerate(lines):
                if line.strip() and not any(keyword in line for keyword in 
                                          ["Tidspunkt:", "Model:", "PROMPT:", "="*10, "-"*10]):
                    ai_response_start = i
                    break
        
        if ai_response_start >= 0:
            # Extract metadata and content
            metadata = {}
            for line in lines[:ai_response_start]:
                if ":" in line and not line.startswith("=") and not line.startswith("-"):
                    key_value = line.split(":", 1)
                    if len(key_value) == 2:
                        key = key_value[0].strip()
                        value = key_value[1].strip()
                        metadata[key] = value
            
            # Get the main content
            content_lines = lines[ai_response_start:]
            # Remove trailing dividers
            while content_lines and (content_lines[-1].startswith("=") or content_lines[-1].strip() == ""):
                content_lines.pop()
            
            clean_content = '\n'.join(content_lines).strip()
            
            return metadata, clean_content
        else:
            return {}, content.strip()
    
    except Exception:
        return {}, content.strip()

def display_analysis_result(content, title="📋 AI Klimaanalyse"):
    """Display analysis result with beautiful formatting"""
    metadata, clean_content = parse_analysis_content(content)
    
    # Create a beautiful container for the analysis
    with st.container():
        # Header with gradient styling
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px 10px 0 0;
            color: white;
            margin-bottom: 0;
        ">
            <h3 style="margin: 0; color: white; text-align: center;">
                {title}
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Metadata section if available
        if metadata:
            st.markdown("""
            <div style="
                background: #f8f9fa;
                padding: 1rem;
                border-left: 4px solid #667eea;
                margin-bottom: 0;
            ">
            """, unsafe_allow_html=True)
            
            meta_cols = st.columns(len(metadata))
            for i, (key, value) in enumerate(metadata.items()):
                if i < len(meta_cols):
                    with meta_cols[i]:
                        st.markdown(f"**{key}:** {value}")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Main content area with beautiful styling
        st.markdown("""
        <div style="
            background: white;
            padding: 2rem;
            border-radius: 0 0 10px 10px;
            border: 1px solid #e1e5e9;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1rem;
        ">
        """, unsafe_allow_html=True)
        
        # Process and display content with better formatting
        if clean_content:
            # Split content into sections based on numbered lists or clear sections
            sections = []
            current_section = []
            
            for line in clean_content.split('\n'):
                line = line.strip()
                if not line:
                    if current_section:
                        current_section.append("")
                    continue
                    
                # Check if line starts a new section (numbered or with special markers)
                if (line.startswith(('1.', '2.', '3.', '4.', '5.')) or 
                    line.startswith(('**', '###', '##')) or
                    any(keyword in line.lower() for keyword in ['klimarisici', 'sårbarhed', 'beredskab', 'anbefal', 'handlinger'])):
                    if current_section:
                        sections.append('\n'.join(current_section))
                        current_section = []
                
                current_section.append(line)
            
            if current_section:
                sections.append('\n'.join(current_section))
            
            # Display sections with nice formatting
            if len(sections) > 1:
                for i, section in enumerate(sections):
                    if section.strip():
                        # Add section styling
                        if i > 0:
                            st.markdown("---")
                        
                        # Detect section type and add appropriate emoji
                        section_lower = section.lower()
                        if 'risici' in section_lower or 'risiko' in section_lower:
                            st.markdown("### ⚠️ Klimarisici")
                        elif 'sårbarhed' in section_lower:
                            st.markdown("### 🏠 Bygningssårbarhed")
                        elif 'beredskab' in section_lower:
                            st.markdown("### 🚨 Beredskabsplan")
                        elif 'anbefal' in section_lower or 'handling' in section_lower:
                            st.markdown("### 💡 Anbefalinger")
                        elif i == 0 and not any(keyword in section_lower for keyword in ['1.', '2.', '3.']):
                            st.markdown("### 📊 Oversigt")
                        
                        st.markdown(section)
            else:
                # Single section - display as is
                st.markdown(clean_content)
        else:
            st.warning("⚠️ Ingen analyseindhold fundet")
        
        st.markdown("</div>", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Header
    st.markdown('<h1 class="main-header">🌡️ Climate Monitor Dashboard</h1>', unsafe_allow_html=True)
    
    # Initialize climate app
    if not init_climate_app():
        st.stop()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Konfiguration")
        
        # Data directory configuration
        with st.expander("📁 Data Indstillinger"):
            data_dir = st.text_input("Data mappe", value="sensordata")
            st.session_state.data_dir = data_dir
        
        st.markdown("---")
        
        # Sensor logging section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("🔌 Sensor Logging")
        
        # Serial port configuration
        serial_port = st.text_input("Serial Port", value="/dev/cu.usbserial-0001")
        baudrate = st.selectbox("Baudrate", [9600, 19200, 38400, 57600, 115200], index=4)
        
        # Logging interval
        interval = st.slider("Logging interval (sekunder)", min_value=10, max_value=300, value=60, step=10)
        
        # Logging control buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("▶️ Start Logging", disabled=st.session_state.logging_active):
                try:
                    st.session_state.sensor_logger = SensorLogger(
                        port=serial_port,
                        baudrate=baudrate,
                        data_dir=data_dir
                    )
                    st.session_state.logging_active = True
                    
                    # Start background thread for sensor logging
                    st.session_state.sensor_thread = threading.Thread(
                        target=sensor_logging_worker,
                        args=(st.session_state.sensor_logger, interval),
                        daemon=True
                    )
                    st.session_state.sensor_thread.start()
                    st.success("✅ Sensor logging startet!")
                    
                except Exception as e:
                    st.error(f"❌ Fejl ved start af logging: {e}")
        
        with col2:
            if st.button("⏹️ Stop Logging", disabled=not st.session_state.logging_active):
                st.session_state.logging_active = False
                if st.session_state.sensor_thread:
                    st.session_state.sensor_thread.join(timeout=1)
                st.success("🛑 Sensor logging stoppet!")
        
        # Logging status indicator
        if st.session_state.logging_active:
            st.markdown(
                '<span class="status-indicator status-active"></span>Sensor logging aktiv',
                unsafe_allow_html=True
            )
            st.write(f"📊 Målinger: {st.session_state.get('reading_count', 0)}")
        else:
            st.markdown(
                '<span class="status-indicator status-inactive"></span>Sensor logging inaktiv',
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Address and BBR section
        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.subheader("🏠 Ejendom & BBR")
        
        address_input = st.text_input("📍 Ejendomsadresse", value=st.session_state.current_address)
        
        if st.button("🔍 Hent BBR Data") and address_input:
            with st.spinner("Henter bygningsdata..."):
                try:
                    if st.session_state.climate_app.set_property_address(address_input):
                        st.session_state.current_address = address_input
                        st.session_state.building_data = st.session_state.climate_app.current_building_data
                        st.success("✅ BBR data hentet!")
                    else:
                        st.warning("⚠️ Kunne ikke hente BBR data")
                except Exception as e:
                    st.error(f"❌ Fejl: {e}")
        
        if st.session_state.building_data:
            st.markdown(
                '<span class="status-indicator status-active"></span>BBR data tilgængelig',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<span class="status-indicator status-inactive"></span>Ingen BBR data',
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Data", "🏠 Bygningsinfo", "🤖 AI Analyse", "📈 Historik"])
    
    with tab1:
        st.header("📊 Live Klimadata")
        
        # Current readings
        try:
            data_reader = DataReader(st.session_state.data_dir)
            current_reading = data_reader.get_current_reading()
        except Exception as e:
            st.error(f"❌ Fejl ved læsning af data: {e}")
            current_reading = None
        
        if current_reading:
            # Display current metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="🌡️ Temperatur",
                    value=f"{current_reading.temperature:.1f}°C",
                    delta=None
                )
            
            with col2:
                st.metric(
                    label="💧 Luftfugtighed",
                    value=f"{current_reading.humidity:.1f}%",
                    delta=None
                )
            
            with col3:
                # Calculate time since last reading
                try:
                    last_time = datetime.strptime(current_reading.timestamp, "%Y-%m-%d %H:%M:%S")
                    time_diff = datetime.now() - last_time
                    minutes_ago = int(time_diff.total_seconds() / 60)
                    st.metric(
                        label="⏰ Sidst opdateret",
                        value=f"{minutes_ago} min siden",
                        delta=None
                    )
                except:
                    st.metric(
                        label="⏰ Sidst opdateret",
                        value="Ukendt",
                        delta=None
                    )
            
            with col4:
                # Comfort level indicator
                temp = current_reading.temperature
                humidity = current_reading.humidity
                
                if 20 <= temp <= 24 and 40 <= humidity <= 60:
                    comfort = "😊 Optimal"
                    comfort_color = "normal"
                elif 18 <= temp <= 26 and 30 <= humidity <= 70:
                    comfort = "😐 OK"
                    comfort_color = "normal"
                else:
                    comfort = "😰 Suboptimal"
                    comfort_color = "inverse"
                
                st.metric(
                    label="🏠 Komfort",
                    value=comfort,
                    delta=None
                )
        else:
            st.warning("⚠️ Ingen aktuelle klimadata tilgængelige")
            st.info("💡 Tip: Start sensor logging for at se live data")
        
        # Real-time charts
        st.subheader("📈 Klimadata visualisering")
        
        # Get recent data for charts
        historical_df = get_historical_data(days=1)  # Last 24 hours
        
        if not historical_df.empty:
            # Chart selection
            chart_type = st.selectbox(
                "Vælg visning:",
                ["Kombineret", "Temperatur", "Luftfugtighed"]
            )
            
            if chart_type == "Kombineret":
                fig = create_combined_chart(historical_df)
            elif chart_type == "Temperatur":
                fig = create_temperature_chart(historical_df)
            else:
                fig = create_humidity_chart(historical_df)
            
            st.plotly_chart(fig, use_container_width=True, key="live_chart_main")
            
            # Data statistics
            with st.expander("📊 Dagens statistik"):
                if len(historical_df) > 0 and 'temperature' in historical_df.columns and 'humidity' in historical_df.columns:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("🌡️ **Temperatur**")
                        st.write(f"• Gennemsnit: {historical_df['temperature'].mean():.1f}°C")
                        st.write(f"• Min: {historical_df['temperature'].min():.1f}°C")
                        st.write(f"• Max: {historical_df['temperature'].max():.1f}°C")
                        st.write(f"• Standardafvigelse: {historical_df['temperature'].std():.1f}°C")
                    
                    with col2:
                        st.write("💧 **Luftfugtighed**")
                        st.write(f"• Gennemsnit: {historical_df['humidity'].mean():.1f}%")
                        st.write(f"• Min: {historical_df['humidity'].min():.1f}%")
                        st.write(f"• Max: {historical_df['humidity'].max():.1f}%")
                        st.write(f"• Standardafvigelse: {historical_df['humidity'].std():.1f}%")
                else:
                    st.warning("⚠️ Ikke nok data tilgængelig for statistik")
        else:
            st.info("📈 Ingen historiske data tilgængelige for visualisering")
        
        # Auto-refresh option
        auto_refresh = st.checkbox("🔄 Auto-opdater hver 30 sekunder")
        if auto_refresh:
            time.sleep(30)
            st.rerun()
    
    with tab2:
        st.header("🏠 Bygningsinformation")
        
        if st.session_state.current_address:
            st.subheader(f"📍 {st.session_state.current_address}")
            
            if st.session_state.building_data:
                building_data = st.session_state.building_data
                
                # Building summary card
                with st.container():
                    st.markdown("### 🏗️ Bygningsoversigt")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("🏠 Bygningstype", building_data.building_type or "Ukendt")
                        st.metric("📅 Opførelsesår", building_data.building_year or "Ukendt")
                        if building_data.renovation_year and building_data.renovation_year != building_data.building_year:
                            st.metric("🔧 Renoveret", building_data.renovation_year)
                    
                    with col2:
                        st.metric("📏 Samlet areal", f"{building_data.total_building_area or 0} m²")
                        st.metric("🏠 Boligareal", f"{building_data.total_residential_area or 0} m²")
                        st.metric("🏢 Erhvervsareal", f"{building_data.total_commercial_area or 0} m²")
                    
                    with col3:
                        st.metric("🧱 Ydervæg", building_data.exterior_material or "Ukendt")
                        st.metric("🏘️ Tag", building_data.roof_material or "Ukendt")
                        st.metric("🔥 Varme", building_data.heating_type or "Ukendt")
                
                # Detailed information
                with st.expander("📋 Detaljerede bygningsdata"):
                    data_dict = building_data.to_dict()
                    
                    for key, value in data_dict.items():
                        if value is not None and value != "" and value != []:
                            formatted_key = key.replace('_', ' ').title()
                            st.write(f"**{formatted_key}:** {value}")
                
                # Floor details
                if building_data.floor_details:
                    with st.expander("🏢 Etagefordeling"):
                        for floor in building_data.floor_details:
                            st.write(f"**{floor.get('designation', 'Ukendt etage')}** ({floor.get('type_name', 'Ukendt type')})")
                            if floor.get('total_area'):
                                st.write(f"  • Samlet areal: {floor['total_area']} m²")
                            if floor.get('basement_area'):
                                st.write(f"  • Kælderareal: {floor['basement_area']} m²")
                            if floor.get('attic_area'):
                                st.write(f"  • Loftareal: {floor['attic_area']} m²")
                
                # Additional buildings
                if building_data.additional_buildings:
                    with st.expander(f"🏗️ Yderligere bygninger ({len(building_data.additional_buildings)})"):
                        for i, building in enumerate(building_data.additional_buildings, 1):
                            st.write(f"**Bygning {i}:**")
                            st.write(f"  • Type: {building.get('type', 'Ukendt')}")
                            st.write(f"  • Areal: {building.get('area', '?')} m²")
                            if building.get('year'):
                                st.write(f"  • Opført: {building['year']}")
                            if building.get('material'):
                                st.write(f"  • Materiale: {building['material']}")
            else:
                st.warning("⚠️ Ingen BBR data tilgængelig for denne adresse")
                st.info("💡 Brug sidebaren til at hente BBR data")
        else:
            st.info("📍 Indtast en adresse i sidebaren for at se bygningsinformation")
    
    with tab3:
        st.header("🤖 AI Klimaanalyse")
        
        # Analysis selection section
        st.markdown("### 📋 Analyser")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Get analysis history
            analysis_history = get_analysis_history()
            
            if analysis_history:
                analysis_options = ["🆕 Kør ny analyse"] + [f"📄 {item['display_name']}" for item in analysis_history]
                selected_analysis = st.selectbox(
                    "Vælg analyse:",
                    analysis_options,
                    key="analysis_selector"
                )
            else:
                st.info("📝 Ingen tidligere analyser fundet")
                selected_analysis = "🆕 Kør ny analyse"
        
        with col2:
            # New analysis button
            if st.button("🔍 Kør ny analyse", type="primary", use_container_width=True):
                if not st.session_state.current_address:
                    st.error("❌ Indtast en adresse først")
                else:
                    try:
                        data_reader = DataReader(st.session_state.data_dir)
                        current_reading = data_reader.get_current_reading()
                    except Exception as e:
                        st.error(f"❌ Fejl ved læsning af data: {e}")
                        current_reading = None
                    
                    if not current_reading:
                        st.error("❌ Ingen aktuelle klimadata tilgængelige")
                    else:
                        with st.spinner("🤖 AI analyserer klimaforhold og bygningsegenskaber..."):
                            try:
                                st.session_state.climate_app.run_intelligent_analysis()
                                
                                # Get the latest analysis file
                                analysis_dir = Path(st.session_state.data_dir) / "analyses"
                                if analysis_dir.exists():
                                    latest_file = analysis_dir / "latest_analysis.txt"
                                    if latest_file.exists():
                                        with open(latest_file, 'r', encoding='utf-8') as f:
                                            analysis_content = f.read()
                                        
                                        st.success("✅ AI analyse gennemført!")
                                        st.session_state.current_analysis = analysis_content
                                        st.session_state.analysis_title = "📋 Ny AI Klimaanalyse"
                                        # Reset selector to show new analysis
                                        st.session_state.analysis_selector = "🆕 Kør ny analyse"
                                        st.rerun()
                                    else:
                                        st.error("❌ Kunne ikke finde analyse resultat")
                                else:
                                    st.error("❌ Analyse mappe ikke fundet")
                                    
                            except Exception as e:
                                st.error(f"❌ Fejl under AI analyse: {e}")
        
        # Display selected analysis
        analysis_to_show = None
        analysis_title = "📋 AI Klimaanalyse"
        
        if 'current_analysis' in st.session_state and selected_analysis == "🆕 Kør ny analyse":
            analysis_to_show = st.session_state.current_analysis
            analysis_title = st.session_state.get('analysis_title', "📋 Ny AI Klimaanalyse")
        elif analysis_history and selected_analysis.startswith("📄"):
            # Find selected historical analysis
            selected_index = analysis_options.index(selected_analysis) - 1  # Subtract 1 for "new analysis" option
            if 0 <= selected_index < len(analysis_history):
                selected_file = analysis_history[selected_index]['path']
                try:
                    with open(selected_file, 'r', encoding='utf-8') as f:
                        analysis_to_show = f.read()
                    analysis_title = f"📄 {analysis_history[selected_index]['display_name']}"
                except Exception as e:
                    st.error(f"❌ Kunne ikke læse analyse fil: {e}")
        
        # Show analysis if available
        if analysis_to_show:
            display_analysis_result(analysis_to_show, analysis_title)
        else:
            # Show empty state with instructions
            st.markdown("""
            <div style="
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 3rem;
                border-radius: 15px;
                text-align: center;
                color: white;
                margin: 2rem 0;
            ">
                <h3 style="color: white; margin-bottom: 1rem;">🤖 Intelligent Klimaanalyse</h3>
                <p style="font-size: 1.1rem; margin-bottom: 1.5rem;">
                    Få en detaljeret analyse af dine klimaforhold baseret på bygningsdata og sensor målinger
                </p>
                <div style="background: rgba(255,255,255,0.2); padding: 1rem; border-radius: 10px; margin-top: 1rem;">
                    <strong>📝 For at køre en analyse:</strong><br>
                    1️⃣ Indtast en adresse i sidebaren<br>
                    2️⃣ Sørg for at have aktuelle sensor data<br>
                    3️⃣ Klik på "Kør ny analyse"
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Current conditions summary
        try:
            data_reader = DataReader(st.session_state.data_dir)
            current_reading = data_reader.get_current_reading()
        except Exception as e:
            current_reading = None
        
        if current_reading:
            st.markdown("### 📊 Aktuelle klimaforhold")
            
            # Create beautiful metrics cards
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #ff6b6b, #ee5a52);
                    padding: 1.5rem;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                ">
                    <h3 style="margin: 0; color: white;">🌡️</h3>
                    <h2 style="margin: 0.5rem 0; color: white;">{current_reading.temperature:.1f}°C</h2>
                    <p style="margin: 0; color: white;">Temperatur</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #4ecdc4, #44a08d);
                    padding: 1.5rem;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                ">
                    <h3 style="margin: 0; color: white;">💧</h3>
                    <h2 style="margin: 0.5rem 0; color: white;">{current_reading.humidity:.1f}%</h2>
                    <p style="margin: 0; color: white;">Luftfugtighed</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Calculate time since reading
                try:
                    last_time = datetime.strptime(current_reading.timestamp, "%Y-%m-%d %H:%M:%S")
                    time_diff = datetime.now() - last_time
                    minutes_ago = int(time_diff.total_seconds() / 60)
                    time_display = f"{minutes_ago} min siden"
                except:
                    time_display = "Ukendt"
                
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #667eea, #764ba2);
                    padding: 1.5rem;
                    border-radius: 10px;
                    color: white;
                    text-align: center;
                ">
                    <h3 style="margin: 0; color: white;">⏰</h3>
                    <h2 style="margin: 0.5rem 0; color: white; font-size: 1.3rem;">{time_display}</h2>
                    <p style="margin: 0; color: white;">Seneste måling</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ Ingen aktuelle klimadata tilgængelige")
        
        # Building context for analysis
        if st.session_state.building_data:
            st.markdown("### 🏠 Bygningskontext")
            building_data = st.session_state.building_data
            
            # Create building info cards
            building_cols = st.columns(4)
            
            with building_cols[0]:
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #28a745;">
                    <strong>🏠 Type</strong><br>
                    {building_data.building_type or 'Ukendt'}
                </div>
                """, unsafe_allow_html=True)
            
            with building_cols[1]:
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #17a2b8;">
                    <strong>📅 Opført</strong><br>
                    {building_data.building_year or 'Ukendt'}
                </div>
                """, unsafe_allow_html=True)
            
            with building_cols[2]:
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #ffc107;">
                    <strong>🧱 Materiale</strong><br>
                    {building_data.exterior_material or 'Ukendt'}
                </div>
                """, unsafe_allow_html=True)
            
            with building_cols[3]:
                st.markdown(f"""
                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #dc3545;">
                    <strong>📏 Areal</strong><br>
                    {building_data.total_building_area or 0} m²
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("ℹ️ Indtast en adresse for at se bygningskontext")
    
    with tab4:
        st.header("📈 Historisk Data")
        
        # Date range selector
        col1, col2 = st.columns(2)
        with col1:
            days_back = st.selectbox("Tidsperiode", [1, 3, 7, 14, 30], index=2, format_func=lambda x: f"Sidste {x} dag(e)")
        with col2:
            chart_resolution = st.selectbox("Opløsning", ["Alle punkter", "Time", "Dag"], index=0)
        
        # Get historical data
        historical_df = get_historical_data(days=days_back)
        
        if not historical_df.empty:
            # Resample data if requested
            if chart_resolution == "Time" and len(historical_df) > 100:
                historical_df = historical_df.set_index('timestamp').resample('H').mean().reset_index()
            elif chart_resolution == "Dag" and len(historical_df) > 50:
                historical_df = historical_df.set_index('timestamp').resample('D').mean().reset_index()
            
            # Display charts
            st.subheader("📊 Temperatur trend")
            temp_fig = create_temperature_chart(historical_df)
            st.plotly_chart(temp_fig, use_container_width=True, key="historical_temp_chart")
            
            st.subheader("💧 Luftfugtighed trend")
            humidity_fig = create_humidity_chart(historical_df)
            st.plotly_chart(humidity_fig, use_container_width=True, key="historical_humidity_chart")
            
            # Statistics table
            st.subheader("📋 Periode statistik")
            
            if len(historical_df) > 0 and 'temperature' in historical_df.columns and 'humidity' in historical_df.columns:
                stats_df = pd.DataFrame({
                    'Metrik': ['Gennemsnit', 'Minimum', 'Maksimum', 'Standardafvigelse'],
                    'Temperatur (°C)': [
                        f"{historical_df['temperature'].mean():.1f}",
                        f"{historical_df['temperature'].min():.1f}",
                        f"{historical_df['temperature'].max():.1f}",
                        f"{historical_df['temperature'].std():.1f}"
                    ],
                    'Luftfugtighed (%)': [
                        f"{historical_df['humidity'].mean():.1f}",
                        f"{historical_df['humidity'].min():.1f}",
                        f"{historical_df['humidity'].max():.1f}",
                        f"{historical_df['humidity'].std():.1f}"
                    ]
                })
                
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.warning("⚠️ Ikke nok data tilgængelig for statistik")
            
            # Data export
            with st.expander("💾 Eksporter data"):
                if len(historical_df) > 0:
                    csv_data = historical_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"klimadata_{days_back}_dage.csv",
                        mime="text/csv"
                    )
                else:
                    st.warning("⚠️ Ingen data at eksportere")
            
            # Data quality info
            st.info(f"📊 Viser {len(historical_df)} datapunkter fra de sidste {days_back} dag(e)")
        
        else:
            st.warning("❌ Ingen historiske data tilgængelige")
            st.info("💡 Start sensor logging for at indsamle data")
    
    # Footer
    st.markdown("---")
    st.markdown(
        "🌡️ **Climate Monitor Dashboard** - Udviklet med Streamlit | "
        f"Data gemt i: `{st.session_state.data_dir}` | "
        f"Status: {'🟢 Aktiv' if st.session_state.logging_active else '🔴 Inaktiv'}"
    )

if __name__ == "__main__":
    main()