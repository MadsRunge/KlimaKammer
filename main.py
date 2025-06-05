#!/usr/bin/env python3
"""
Enhanced Climate Monitor Application - Now with intelligent address-based BBR integration.
"""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Import our enhanced components
from climate_analyzer import EnhancedClimateAnalyzer, DataReader, ClimateReading
from bbr_service import BBRAddressService, BuildingData

# Load environment variables
load_dotenv()


class EnhancedClimateMonitorApp:
    """Enhanced climate monitoring application with intelligent BBR integration."""
    
    def __init__(self, data_dir: str = "sensordata"):
        self.data_reader = DataReader(data_dir)
        self.analyzer = EnhancedClimateAnalyzer(data_dir)
        
        # Current session data
        self.current_address = ""
        self.current_building_data = None
        
        # Check BBR service availability
        self.bbr_available = self.analyzer.bbr_service is not None
        
        print(f"🌡️ Climate Monitor startet")
        print(f"📁 Data directory: {data_dir}")
        print(f"🏠 BBR Integration: {'✅ Aktiveret' if self.bbr_available else '❌ Ikke tilgængelig'}")
    
    def set_property_address(self, address: str, force_reload: bool = False) -> bool:
        """
        Set the property address and load building data.
        
        Args:
            address: Property address to analyze
            force_reload: Force reload building data even if address is same
            
        Returns:
            True if building data was loaded successfully
        """
        if address == self.current_address and not force_reload and self.current_building_data:
            print(f"📍 Bruger eksisterende data for: {address}")
            return True
        
        print(f"🔍 Indlæser bygningsdata for: {address}")
        
        # Load building data if BBR is available
        if self.bbr_available:
            self.current_building_data = self.analyzer.bbr_service.get_building_data(address)
            
            if self.current_building_data:
                self.current_address = address
                print("✅ Bygningsdata indlæst")
                print(self.current_building_data.get_summary())
                return True
            else:
                print("⚠️  Kunne ikke hente bygningsdata - fortsætter med standard analyse")
                self.current_address = address
                self.current_building_data = None
                return False
        else:
            print("⚠️  BBR service ikke tilgængelig - bruger adresse-baseret analyse")
            self.current_address = address
            self.current_building_data = None
            return False
    
    def run_intelligent_analysis(self) -> None:
        """Run intelligent analysis with address and building data integration."""
        print("🔍 Kører intelligent klimaanalyse...")
        
        # Get current climate data
        current = self.data_reader.get_current_reading()
        if not current:
            print("❌ Ingen aktuelle klimadata tilgængelige")
            print("💡 Tip: Kør 'sensor_logger.py' først for at indsamle data")
            return
        
        # Ensure we have an address
        if not self.current_address:
            address = input("📍 Indtast ejendomsadresse: ").strip()
            if not address:
                print("❌ Adresse er påkrævet for intelligent analyse")
                return
            self.set_property_address(address)
        
        # Display current conditions
        print(f"\n📈 Aktuelle klimaforhold:")
        print(f"🌡️  Temperatur: {current.temperature:.1f}°C")
        print(f"💧 Luftfugtighed: {current.humidity:.1f}%")
        print(f"⏰ Målt: {current.timestamp}")
        
        # Run AI analysis with building integration
        print("🤖 AI analyserer klimaforhold og bygningsegenskaber...")
        
        if self.current_building_data:
            # Enhanced analysis with building data
            analysis = self.analyzer.analyze_with_address(current, self.current_address)
            analysis_type = "🏠 INTELLIGENT ANALYSE (med BBR data)"
        else:
            # Address-based analysis without detailed building data
            analysis = self.analyzer.analyze_current_conditions(current, self.current_address)
            analysis_type = "📍 ADRESSE-BASERET ANALYSE"
        
        # Display results
        self._display_analysis_results(analysis_type, analysis)
    
    def run_intelligent_trend_analysis(self, days_back: int = 1) -> None:
        """Run intelligent trend analysis with building data."""
        print(f"📊 Kører intelligent trendanalyse for {days_back} dag(e)...")
        
        # Get historical data
        all_readings = []
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_readings = self.data_reader.get_daily_data(date)
            all_readings.extend(daily_readings)
        
        if not all_readings:
            print("❌ Ingen historiske data tilgængelige")
            print("💡 Tip: Lad 'sensor_logger.py' køre et stykke tid for at samle data")
            return
        
        # Ensure we have an address
        if not self.current_address:
            address = input("📍 Indtast ejendomsadresse: ").strip()
            if not address:
                print("❌ Adresse er påkrævet for intelligent analyse")
                return
            self.set_property_address(address)
        
        # Get statistics
        stats = self.data_reader.get_statistics(all_readings)
        
        # Display data overview
        print(f"\n📊 Datagrundlag:")
        print(f"📋 Antal målinger: {len(all_readings)}")
        print(f"📅 Periode: {stats['time_range']['first']} → {stats['time_range']['last']}")
        print(f"🌡️  Temperatur: {stats['temperature']['min']:.1f}-{stats['temperature']['max']:.1f}°C")
        print(f"💧 Luftfugtighed: {stats['humidity']['min']:.1f}-{stats['humidity']['max']:.1f}%")
        
        # Run intelligent trend analysis
        print("🤖 AI analyserer trends med bygningsspecifik viden...")
        
        if self.current_building_data:
            analysis = self.analyzer.analyze_trends_with_building(
                all_readings, stats, self.current_address, self.current_building_data
            )
            analysis_type = "📈 INTELLIGENT TRENDANALYSE (med BBR data)"
        else:
            analysis = self.analyzer.analyze_trends(all_readings, stats, self.current_address)
            analysis_type = "📈 ADRESSE-BASERET TRENDANALYSE"
        
        # Display results
        self._display_analysis_results(analysis_type, analysis)
    
    def show_building_details(self) -> None:
        """Show detailed building information."""
        if not self.current_address:
            address = input("📍 Indtast ejendomsadresse: ").strip()
            if not address:
                print("❌ Adresse er påkrævet")
                return
            self.set_property_address(address)
        
        print("\n🏠 BYGNINGSDETALJER")
        print("="*50)
        
        if self.current_building_data:
            # Detailed building information
            print(self.current_building_data.get_summary())
            
            # Technical details
            data_dict = self.current_building_data.to_dict()
            print("\n📊 TEKNISKE DETALJER:")
            print(f"• Bygningsareal: {data_dict.get('total_building_area', 'Ukendt')} m²")
            print(f"• Boligareal: {data_dict.get('living_area', 'Ukendt')} m²")
            print(f"• Kælderareal: {data_dict.get('basement_area', 'Ukendt')} m²")
            print(f"• Loftareal: {data_dict.get('attic_area', 'Ukendt')} m²")
            print(f"• Antal etager: {data_dict.get('floors', 'Ukendt')}")
            print(f"• Antal værelser: {data_dict.get('rooms', 'Ukendt')}")
            print(f"• Badeværelser: {data_dict.get('bathrooms', 'Ukendt')}")
            print(f"• Toiletter: {data_dict.get('toilets', 'Ukendt')}")
            
            # Additional buildings
            if self.current_building_data.additional_buildings:
                print(f"\n🏗️ YDERLIGERE BYGNINGER ({len(self.current_building_data.additional_buildings)} stk):")
                for i, building in enumerate(self.current_building_data.additional_buildings, 1):
                    print(f"  {i}. {building.get('type', 'Ukendt')} ({building.get('area', '?')} m²)")
                    if building.get('year'):
                        print(f"     Opført: {building['year']}")
                    if building.get('material'):
                        print(f"     Materiale: {building['material']}")
            
            # Data source info
            print(f"\n📋 DATAKILDE:")
            print(f"• BBR (Bygnings- og Boligregistret)")
            print(f"• Hentet via Datafordeler API")
            print(f"• Opdateret: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        else:
            print(f"📍 Adresse: {self.current_address}")
            print("⚠️  Detaljerede bygningsdata ikke tilgængelige")
            
            if self.bbr_available:
                retry = input("\n🔄 Forsøg at hente bygningsdata igen? (j/n): ").strip().lower()
                if retry == 'j':
                    self.set_property_address(self.current_address, force_reload=True)
                    self.show_building_details()  # Recursive call with new data
            else:
                print("💡 BBR service ikke konfigureret - tjek environment variabler")
    
    def change_address(self) -> None:
        """Change the current property address."""
        print("\n📍 SKIFT EJENDOMSADRESSE")
        print("="*30)
        
        if self.current_address:
            print(f"Nuværende adresse: {self.current_address}")
        
        new_address = input("Indtast ny adresse: ").strip()
        
        if not new_address:
            print("❌ Ingen adresse indtastet")
            return
        
        if new_address == self.current_address:
            print("ℹ️  Same adresse som før")
            return
        
        # Load new building data
        success = self.set_property_address(new_address)
        
        if success:
            print(f"✅ Adresse opdateret til: {new_address}")
        else:
            print(f"⚠️  Adresse sat til: {new_address} (uden detaljerede bygningsdata)")
    
    def show_analysis_history(self) -> None:
        """Show enhanced analysis history."""
        print("📚 ANALYSE HISTORIK")
        print("="*50)
        
        analyses = self.analyzer.get_analysis_history(7)
        
        if not analyses:
            print("❌ Ingen tidligere analyser fundet")
            return
        
        print(f"📋 Seneste {len(analyses)} analyser:")
        
        # Group by type
        bbr_analyses = [a for a in analyses if a.get('bbr_enhanced', False)]
        standard_analyses = [a for a in analyses if not a.get('bbr_enhanced', False)]
        
        if bbr_analyses:
            print(f"\n🏠 BBR-FORBEDREDE ANALYSER ({len(bbr_analyses)} stk):")
            for analysis in bbr_analyses[:5]:
                type_display = analysis['type'].replace('_', ' ').title()
                print(f"  📅 {analysis['date']} {analysis['time']} - {type_display} ✅")
        
        if standard_analyses:
            print(f"\n📍 STANDARD ANALYSER ({len(standard_analyses)} stk):")
            for analysis in standard_analyses[:5]:
                type_display = analysis['type'].replace('_', ' ').title()
                print(f"  📅 {analysis['date']} {analysis['time']} - {type_display}")
        
        # Show latest analysis content
        if analyses:
            latest_file = Path(self.analyzer.analysis_dir) / "latest_analysis.txt"
            if latest_file.exists():
                print(f"\n📄 SENESTE ANALYSE:")
                print("-" * 30)
                try:
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(content)
                except Exception as e:
                    print(f"❌ Kunne ikke læse seneste analyse: {e}")
        
        print(f"\n💾 Alle analyser gemmes i: {self.analyzer.analysis_dir}")
    
    def show_data_summary(self) -> None:
        """Show summary of available climate data."""
        print("📁 KLIMADATA OVERSIGT")
        print("="*40)
        
        # Current reading
        current = self.data_reader.get_current_reading()
        if current:
            print(f"🕐 Seneste måling: {current.timestamp}")
            print(f"🌡️  {current.temperature:.1f}°C, 💧 {current.humidity:.1f}%")
        else:
            print("❌ Ingen aktuelle data")
        
        # Latest readings
        latest = self.data_reader.get_latest_readings(5)
        if latest:
            print(f"\n📋 Seneste {len(latest)} målinger:")
            for reading in latest[-5:]:
                print(f"  {reading.timestamp}: {reading.temperature:.1f}°C, {reading.humidity:.1f}%")
        
        # Daily files
        daily_dir = self.data_reader.data_dir / "daily"
        if daily_dir.exists():
            csv_files = list(daily_dir.glob("*.csv"))
            print(f"\n📅 Tilgængelige dage: {len(csv_files)}")
            for file_path in sorted(csv_files)[-7:]:  # Last 7 days
                try:
                    line_count = sum(1 for _ in open(file_path)) - 1
                    print(f"  {file_path.stem}: {line_count} målinger")
                except Exception:
                    print(f"  {file_path.stem}: fejl ved læsning")
        
        # Current address info
        if self.current_address:
            print(f"\n🏠 AKTUEL EJENDOM:")
            print(f"📍 Adresse: {self.current_address}")
            if self.current_building_data:
                print(f"🏗️  Bygningstype: {self.current_building_data.building_type}")
                print(f"📅 Byggeår: {self.current_building_data.building_year}")
                print("✅ BBR data tilgængelig")
            else:
                print("⚠️  BBR data ikke tilgængelig")
    
    def _display_analysis_results(self, analysis_type: str, analysis: str) -> None:
        """Display analysis results in a formatted way."""
        print(f"\n{'='*60}")
        print(f"📋 {analysis_type}")
        print('='*60)
        print(analysis)
        print('='*60)
        
        if self.current_building_data:
            print(f"\n💡 Analyse baseret på konkrete bygningsdata fra BBR")
        elif self.current_address:
            print(f"\n💡 Analyse baseret på adresse: {self.current_address}")
        
        print(f"⏰ Genereret: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Enhanced main application entry point."""
    print("🌡️ ENHANCED KLIMAANALYSE SYSTEM")
    print("="*50)
    print("🏠 Nu med intelligent BBR integration!")
    print("")
    
    try:
        # Initialize enhanced app
        data_dir = input("Data mappe (default: sensordata): ").strip() or "sensordata"
        app = EnhancedClimateMonitorApp(data_dir)
        
        # Initial address setup
        address = input("📍 Indtast ejendomsadresse (kan ændres senere): ").strip()
        if address:
            app.set_property_address(address)
        
        while True:
            print("\n🔧 VÆLG HANDLING:")
            print("1. 🏠 Intelligent klimaanalyse (nuværende forhold)")
            print("2. 📈 Intelligent trendanalyse (sidste dag)")
            print("3. 📊 Intelligent trendanalyse (flere dage)")
            print("4. 🏗️  Vis bygningsdetaljer")
            print("5. 📍 Skift ejendomsadresse")
            print("6. 📁 Vis klimadata oversigt")
            print("7. 📚 Vis analyse historik")
            print("8. ❌ Afslut")
            
            choice = input(f"\nVælg (1-8): ").strip()
            
            if choice == "1":
                app.run_intelligent_analysis()
                
            elif choice == "2":
                app.run_intelligent_trend_analysis(days_back=1)
                
            elif choice == "3":
                days = input("Antal dage tilbage (default: 3): ").strip()
                days = int(days) if days.isdigit() and int(days) > 0 else 3
                app.run_intelligent_trend_analysis(days_back=days)
                
            elif choice == "4":
                app.show_building_details()
                
            elif choice == "5":
                app.change_address()
                
            elif choice == "6":
                app.show_data_summary()
                
            elif choice == "7":
                app.show_analysis_history()
                
            elif choice == "8":
                print("👋 Farvel!")
                break
                
            else:
                print("❌ Ugyldigt valg")
            
            input("\nTryk Enter for at fortsætte...")
            
    except KeyboardInterrupt:
        print("\n👋 Program stoppet af bruger")
    except Exception as e:
        print(f"❌ Programfejl: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()