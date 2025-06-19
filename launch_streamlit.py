#!/usr/bin/env python3
"""
Climate Monitor Streamlit Launcher
Simple script to start the Streamlit dashboard
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'streamlit',
        'plotly',
        'pandas',
        'openai',
        'pyserial',
        'python-dotenv',
        'requests'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Manglende pakker fundet:")
        for package in missing_packages:
            print(f"   • {package}")
        print("\n💡 Installer manglende pakker med:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_environment():
    """Check if environment variables are set"""
    required_env_vars = [
        'OPENAI_API_KEY',
        'DATAFORDELER_NO_CERT_USERNAME',
        'DATAFORDELER_NO_CERT_PASSWORD'
    ]
    
    missing_vars = []
    
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️ Manglende miljøvariabler:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\n💡 Opret en .env fil med følgende indhold:")
        print("   OPENAI_API_KEY=your_openai_api_key")
        print("   DATAFORDELER_NO_CERT_USERNAME=your_bbr_username")
        print("   DATAFORDELER_NO_CERT_PASSWORD=your_bbr_password")
        print("\n🔧 Eller eksporter dem som miljøvariabler")
        return False
    
    return True

def main():
    """Main launcher function"""
    print("🌡️ Climate Monitor Dashboard Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    required_files = [
        'sensor_logger.py',
        'climate_analyzer.py',
        'main.py',
        'bbr_service.py'
    ]
    
    missing_files = [f for f in required_files if not (current_dir / f).exists()]
    
    if missing_files:
        print("❌ Påkrævede filer ikke fundet:")
        for file in missing_files:
            print(f"   • {file}")
        print("\n💡 Sørg for at køre scriptet fra projekt mappen")
        return
    
    # Check dependencies
    print("🔍 Tjekker afhængigheder...")
    if not check_dependencies():
        return
    
    print("✅ Alle afhængigheder er installeret")
    
    # Check environment variables
    print("🔍 Tjekker miljøvariabler...")
    if not check_environment():
        print("⚠️ Fortsætter uden alle miljøvariabler (noget funktionalitet vil være begrænset)")
    else:
        print("✅ Alle miljøvariabler er konfigureret")
    
    # Create streamlit app file if it doesn't exist
    streamlit_app_file = current_dir / "streamlit_app.py"
    if not streamlit_app_file.exists():
        print("❌ streamlit_app.py ikke fundet!")
        print("💡 Gem Streamlit koden som 'streamlit_app.py' i projekt mappen")
        return
    
    # Launch Streamlit
    print("\n🚀 Starter Climate Monitor Dashboard...")
    print("📱 Dashboard åbner i din browser på: http://localhost:8501")
    print("🛑 Tryk Ctrl+C for at stoppe serveren")
    print("=" * 50)
    
    try:
        # Launch streamlit with optimized settings
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            "streamlit_app.py",
            "--server.headless", "false",
            "--server.port", "8501",
            "--server.address", "localhost",
            "--theme.base", "light",
            "--theme.primaryColor", "#1f77b4",
            "--theme.backgroundColor", "#ffffff",
            "--theme.secondaryBackgroundColor", "#f0f2f6"
        ])
    except KeyboardInterrupt:
        print("\n\n👋 Climate Monitor Dashboard stoppet")
    except Exception as e:
        print(f"\n❌ Fejl ved start af dashboard: {e}")

if __name__ == "__main__":
    main()