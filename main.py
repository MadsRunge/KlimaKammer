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

# Import our components
from climate_analyzer import ClimateAnalyzer, DataReader, ClimateReading # Bruger ClimateAnalyzer
from bbr_service import BBRAddressService, BuildingData # Sørg for BBRAddressService er tilgængelig

# Load environment variables
load_dotenv()


class EnhancedClimateMonitorApp:
    """Enhanced climate monitoring application with intelligent BBR integration."""

    def __init__(self, data_dir: str = "sensordata"):
        self.data_reader = DataReader(data_dir)
        self.analyzer = ClimateAnalyzer(data_dir) # ClimateAnalyzer har ikke selv bbr_service

        # Initialiser BBR service her i EnhancedClimateMonitorApp
        self.bbr_service_instance = None # Ny attribut til at holde BBR service
        if BBRAddressService: # Tjek om klassen blev importeret korrekt
            try:
                bbr_username = os.getenv('DATAFORDELER_NO_CERT_USERNAME')
                bbr_password = os.getenv('DATAFORDELER_NO_CERT_PASSWORD')
                if not bbr_username or not bbr_password:
                    print("⚠️ ADVARSEL: BBR brugernavn/password ikke fundet i miljøvariabler.")
                    print("   BBR-data vil ikke blive hentet. Angiv DATAFORDELER_NO_CERT_USERNAME og DATAFORDELER_NO_CERT_PASSWORD.")
                else:
                    self.bbr_service_instance = BBRAddressService(username=bbr_username, password=bbr_password)
            except Exception as e:
                print(f"❌ Fejl ved initialisering af BBRAddressService: {e}")
                self.bbr_service_instance = None
        else:
            print("ℹ️ BBRAddressService klasse ikke fundet (mulig importfejl). Fortsætter uden BBR-integration.")

        # Tjek BBR tilgængelighed baseret på den lokalt initialiserede service
        self.bbr_available = self.bbr_service_instance is not None

        # Current session data
        self.current_address = ""
        self.current_building_data = None # Vil holde BBR BuildingData objektet

        print(f"🌡️ Climate Monitor startet")
        print(f"📁 Data directory: {data_dir}")
        print(f"🏠 BBR Integration: {'✅ Aktiveret' if self.bbr_available else '❌ Ikke tilgængelig'}")

    def set_property_address(self, address: str, force_reload: bool = False) -> bool:
        """
        Set the property address and load building data.
        """
        if address == self.current_address and not force_reload and self.current_building_data:
            print(f"📍 Bruger eksisterende data for: {address}")
            return True

        print(f"🔍 Indlæser bygningsdata for: {address}")

        # Brug den lokalt initialiserede bbr_service_instance
        if self.bbr_available and self.bbr_service_instance:
            self.current_building_data = self.bbr_service_instance.get_building_data(address) #

            if self.current_building_data:
                self.current_address = address
                print("✅ Bygningsdata indlæst")
                print(self.current_building_data.get_summary()) #
                return True
            else:
                print("⚠️  Kunne ikke hente bygningsdata - fortsætter med standard analyse")
                self.current_address = address
                self.current_building_data = None
                return False
        else:
            print("⚠️  BBR service ikke tilgængelig eller ikke initialiseret korrekt - bruger adresse-baseret analyse uden BBR data.")
            self.current_address = address
            self.current_building_data = None
            return False

    def run_intelligent_analysis(self) -> None:
        """Run intelligent analysis with address and building data integration."""
        print("🔍 Kører intelligent klimaanalyse...")

        current = self.data_reader.get_current_reading() #
        if not current:
            print("❌ Ingen aktuelle klimadata tilgængelige")
            print("💡 Tip: Kør 'sensor_logger.py' først for at indsamle data")
            return

        if not self.current_address:
            address_input = input("📍 Indtast ejendomsadresse: ").strip()
            if not address_input:
                print("❌ Adresse er påkrævet for intelligent analyse")
                return
            self.set_property_address(address_input)

        print(f"\n📈 Aktuelle klimaforhold:")
        print(f"🌡️  Temperatur: {current.temperature:.1f}°C")
        print(f"💧 Luftfugtighed: {current.humidity:.1f}%")
        print(f"⏰ Målt: {current.timestamp}")

        print("🤖 AI analyserer klimaforhold og bygningsegenskaber...")
        analysis_result = ""
        analysis_type = ""

        # self.current_building_data hentes via self.set_property_address()
        # og er enten BuildingData objekt eller None.
        # ClimateAnalyzer.analyze_current_conditions forventer bbr_data som parameter.
        analysis_result = self.analyzer.analyze_current_conditions(
            current,
            self.current_building_data, # Sender det hentede BBR data (eller None)
            self.current_address or "Ukendt adresse"
        ) #

        if self.current_building_data:
            analysis_type = "🏠 INTELLIGENT ANALYSE (med BBR data)"
        else:
            analysis_type = "📍 ADRESSE-BASERET ANALYSE (uden BBR data)"

        self._display_analysis_results(analysis_type, analysis_result)

    def run_intelligent_trend_analysis(self, days_back: int = 1) -> None:
        """Run intelligent trend analysis with building data."""
        print(f"📊 Kører intelligent trendanalyse for {days_back} dag(e)...")
        all_readings = []
        # NOTE: Manglende funktionalitet i DataReader for historiske data.
        print("NOTE: Funktionen for at hente daglige data ('get_daily_data') og statistik ('get_statistics') er ikke fuldt defineret i DataReader.")
        print("      Trendanalyse vil muligvis ikke fungere som forventet uden disse.")

        if not all_readings: # Vil være tom baseret på noten ovenfor
            print("❌ Ingen historiske data tilgængelige for trendanalyse (eller metoder mangler i DataReader).")
            return

        if not self.current_address:
            address_input = input("📍 Indtast ejendomsadresse: ").strip()
            if not address_input:
                print("❌ Adresse er påkrævet for intelligent analyse")
                return
            self.set_property_address(address_input)

        stats = {"time_range": {"first": "N/A", "last": "N/A"}, "temperature": {"min": 0, "max": 0}, "humidity": {"min": 0, "max": 0}} # Placeholder

        print(f"\n📊 Datagrundlag:")
        print(f"📋 Antal målinger: {len(all_readings)}")
        print(f"📅 Periode: {stats['time_range']['first']} → {stats['time_range']['last']}")
        print(f"🌡️  Temperatur: {stats['temperature']['min']:.1f}-{stats['temperature']['max']:.1f}°C")
        print(f"💧 Luftfugtighed: {stats['humidity']['min']:.1f}-{stats['humidity']['max']:.1f}%")

        print("🤖 AI analyserer trends med bygningsspecifik viden...")
        # NOTE: Manglende trendanalyse-metoder i ClimateAnalyzer
        print("NOTE: Metoderne for trendanalyse (f.eks. 'analyze_trends_with_building', 'analyze_trends') er ikke defineret i ClimateAnalyzer.")
        analysis_result = "Trendanalyse funktion er ikke implementeret i ClimateAnalyzer."
        analysis_type = "TRENDANALYSE STATUS"

        self._display_analysis_results(analysis_type, analysis_result)


    def show_building_details(self) -> None:
        """Show detailed building information."""
        if not self.current_address:
            address_input = input("📍 Indtast ejendomsadresse: ").strip()
            if not address_input:
                print("❌ Adresse er påkrævet")
                return
            if not self.set_property_address(address_input): # Opdaterer også current_building_data
                 print("ℹ️ Kunne ikke indlæse bygningsdetaljer for den angivne adresse.")
                 # Fortsæt evt. med at vise hvad der er, eller returner helt
                 # return

        print("\n🏠 BYGNINGSDETALJER")
        print("="*50)

        if self.current_building_data:
            print(self.current_building_data.get_summary()) #
            data_dict = self.current_building_data.to_dict() #
            print("\n📊 TEKNISKE DETALJER:")
            for key, value in data_dict.items():
                 if value is not None and value != "" and value != []: # Vis kun felter med værdi
                     print(f"• {key.replace('_', ' ').capitalize()}: {value}")

            if self.current_building_data.additional_buildings:
                print(f"\n🏗️ YDERLIGERE BYGNINGER ({len(self.current_building_data.additional_buildings)} stk):")
                for i, building in enumerate(self.current_building_data.additional_buildings, 1):
                    print(f"  {i}. {building.get('type', 'Ukendt')} ({building.get('area', '?')} m²)")
                    if building.get('year'): print(f"     Opført: {building['year']}")
                    if building.get('material'): print(f"     Materiale: {building['material']}")
            print(f"\n📋 DATAKILDE Opdateret: {self.current_building_data.last_updated or 'Ukendt'}")
        else:
            print(f"📍 Adresse: {self.current_address}")
            print("⚠️  Detaljerede bygningsdata ikke tilgængelige for denne adresse.")
            if self.bbr_available and self.current_address: # Tilføjet current_address check
                retry = input("\n🔄 Forsøg at hente bygningsdata igen? (j/n): ").strip().lower()
                if retry == 'j':
                    self.set_property_address(self.current_address, force_reload=True)
                    self.show_building_details()
            elif not self.bbr_available:
                 print("💡 BBR service er ikke konfigureret - tjek environment variabler.")


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
            print("ℹ️  Samme adresse som før")
            return
        if self.set_property_address(new_address):
            print(f"✅ Adresse opdateret til: {new_address}")
        else:
            print(f"⚠️  Adresse sat til: {new_address}, men BBR-data kunne ikke hentes.")


    def show_analysis_history(self) -> None:
        """Show enhanced analysis history."""
        print("📚 ANALYSE HISTORIK")
        print("="*50)
        # NOTE: Manglende funktionalitet i ClimateAnalyzer
        print("NOTE: Metoden 'get_analysis_history' er ikke defineret i ClimateAnalyzer.")
        analyses = [] # Placeholder
        if not analyses:
            print("❌ Ingen tidligere analyser fundet (eller metode mangler).")
            return
        # ... (resten af logikken forudsætter at 'analyses' fyldes)


    def show_data_summary(self) -> None:
        """Show summary of available climate data."""
        print("📁 KLIMADATA OVERSIGT")
        print("="*40)
        current = self.data_reader.get_current_reading() #
        if current:
            print(f"🕐 Seneste måling: {current.timestamp} - 🌡️ {current.temperature:.1f}°C, 💧 {current.humidity:.1f}%")
        else:
            print("❌ Ingen aktuelle data")

        # NOTE: Manglende funktionalitet i DataReader
        print("NOTE: Metoden 'get_latest_readings' for DataReader er ikke defineret i de viste filer.")

        daily_dir = self.data_reader.data_dir / "daily" #
        if daily_dir.exists():
            csv_files = sorted(list(daily_dir.glob("*.csv")), reverse=True)
            print(f"\n📅 Tilgængelige dage (seneste 7 vist): {len(csv_files)}")
            for file_path in csv_files[:7]:
                try:
                    line_count = sum(1 for _ in open(file_path, encoding='utf-8')) -1
                    print(f"  {file_path.stem}: {line_count} målinger")
                except Exception: print(f"  {file_path.stem}: fejl ved læsning")
        if self.current_address:
            print(f"\n🏠 AKTUEL EJENDOM: {self.current_address}")
            if self.current_building_data: print(f"🏗️  {self.current_building_data.building_type}, Opført: {self.current_building_data.building_year} (BBR data ✅)")
            else: print("⚠️  BBR data ikke tilgængelig for adressen.")


    def _display_analysis_results(self, analysis_type: str, analysis_content: str) -> None:
        """Display analysis results in a formatted way."""
        print(f"\n{'='*60}\n📋 {analysis_type}\n{'='*60}\n{analysis_content}\n{'='*60}")
        if self.current_building_data and "(med BBR data)" in analysis_type:
            print(f"\n💡 Analyse baseret på konkrete bygningsdata fra BBR for {self.current_address}")
        elif self.current_address:
            print(f"\n💡 Analyse baseret på adresse: {self.current_address}")
        print(f"⏰ Genereret: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Enhanced main application entry point."""
    print("🌡️ ENHANCED KLIMAANALYSE SYSTEM")
    print("="*50 + "\n🏠 Nu med intelligent BBR integration!\n")
    try:
        data_dir_input = input("Data mappe (default: sensordata): ").strip() or "sensordata"
        app = EnhancedClimateMonitorApp(data_dir_input)
        address_input_main = input("📍 Indtast ejendomsadresse (kan ændres senere, Enter for ingen): ").strip()
        if address_input_main:
            app.set_property_address(address_input_main)

        while True:
            print("\n🔧 VÆLG HANDLING:")
            print("1. 🏠 Intelligent klimaanalyse (nuværende forhold)")
            print("2. 📈 Intelligent trendanalyse (sidste dag) [Kræver implementering]")
            print("3. 📊 Intelligent trendanalyse (flere dage) [Kræver implementering]")
            print("4. 🏗️  Vis bygningsdetaljer")
            print("5. 📍 Skift ejendomsadresse")
            print("6. 📁 Vis klimadata oversigt")
            print("7. 📚 Vis analyse historik [Kræver implementering]")
            print("8. ❌ Afslut")
            choice = input(f"\nVælg (1-8): ").strip()

            if choice == "1": app.run_intelligent_analysis()
            elif choice == "2": app.run_intelligent_trend_analysis(days_back=1)
            elif choice == "3":
                days_input = input("Antal dage tilbage (default: 3): ").strip()
                days_to_check = int(days_input) if days_input.isdigit() and int(days_input) > 0 else 3
                app.run_intelligent_trend_analysis(days_back=days_to_check)
            elif choice == "4": app.show_building_details()
            elif choice == "5": app.change_address()
            elif choice == "6": app.show_data_summary()
            elif choice == "7": app.show_analysis_history()
            elif choice == "8": print("👋 Farvel!"); break
            else: print("❌ Ugyldigt valg")
            input("\nTryk Enter for at fortsætte...")
    except KeyboardInterrupt: print("\n👋 Program stoppet af bruger")
    except Exception as e:
        print(f"❌ Programfejl: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()