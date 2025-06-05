#!/usr/bin/env python3
"""
Climate Analyzer - Reads sensor data files and provides AI-powered climate analysis,
enhanced with BBR building data.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from openai import OpenAI
from dotenv import load_dotenv

# Importer BBR service og dataclass
# Antager at bbr_service.py er i samme mappe eller tilgængelig i PYTHONPATH
try:
    from bbr_service import BBRAddressService, BuildingData
except ImportError:
    print("🔴 FEJL: Kunne ikke importere BBRAddressService eller BuildingData.")
    print("   Sørg for, at 'bbr_service.py' er i samme mappe eller korrekt installeret.")
    # Du kan vælge at lade programmet afslutte her, eller fortsætte uden BBR funktionalitet.
    # For nu sætter vi dem til None, så programmet kan starte, men BBR-delen vil fejle.
    BBRAddressService = None
    BuildingData = None

# Load environment variables (for OpenAI API Key etc.)
load_dotenv()


@dataclass
class ClimateReading:
    """Represents a single climate reading."""
    timestamp: str
    temperature: float
    humidity: float
    unix_timestamp: float


class DataReader:
    """Handles reading current sensor data from files."""
    
    def __init__(self, data_dir: str = "sensordata"):
        self.data_dir = Path(data_dir)
        
        if not self.data_dir.exists():
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
                print(f"INFO: Datamappen '{data_dir}' fandtes ikke og blev oprettet.")
                current_file_path = self.data_dir / "current_reading.txt"
                if not current_file_path.exists():
                    print(f"ADVARSEL: '{current_file_path}' ikke fundet. Opret testdata ifølge README, hvis der ikke bruges live sensor.")

            except Exception as e:
                raise FileNotFoundError(f"Datamappen blev ikke fundet og kunne ikke oprettes: {data_dir}. Fejl: {e}")
    
    def get_current_reading(self) -> Optional[ClimateReading]:
        """
        Read the most recent sensor reading.
        """
        current_file = self.data_dir / "current_reading.txt"
        
        if not current_file.exists():
            print(f"❌ Fil med nuværende måling ikke fundet: {current_file}")
            print("💡 Sørg for, at 'sensor_logger.py' kører, eller opret testdata.")
            return None
        
        try:
            with open(current_file, 'r') as f:
                lines = f.readlines()
            
            data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    data[key.strip()] = value.strip()
            
            return ClimateReading(
                timestamp=data.get('Last Updated', ''),
                temperature=float(data.get('Temperature', '0').replace('°C', '')),
                humidity=float(data.get('Humidity', '0').replace('%', '')),
                unix_timestamp=float(data.get('Unix Timestamp', '0'))
            )
        except Exception as e:
            print(f"❌ Fejl ved læsning af nuværende data fra '{current_file}': {e}")
            return None


class ClimateAnalyzer:
    """AI-powered climate analysis using OpenAI."""
    
    def __init__(self, data_dir: str = "sensordata"):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set.")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4"
        self.data_dir = Path(data_dir)
        self.analysis_dir = self.data_dir / "analyses"
        self.analysis_dir.mkdir(exist_ok=True)
    
    def analyze_current_conditions(self, 
                                   current_reading: ClimateReading, 
                                   bbr_data: Optional[BuildingData], 
                                   address: str) -> str:
        """
        Analyze current climate conditions using sensor data and BBR data.
        """
        prompt = self._create_current_analysis_prompt(current_reading, bbr_data, address)
        return self._get_ai_response(prompt, "current_conditions_bbr")
    
    def _format_bbr_data_for_prompt(self, bbr_data: Optional[BuildingData]) -> str:
        """Formats BuildingData into a string for the AI prompt."""
        if not bbr_data:
            return "Ingen BBR data tilgængelig for denne adresse.\n"

        info_parts = []
        
        def add_info(label, value, unit=""):
            if value not in [None, "", []]:
                info_parts.append(f"{label}: {value}{unit}")

        add_info("Bygningstype", bbr_data.building_type)
        add_info("Opførelsesår", bbr_data.building_year)
        if bbr_data.renovation_year and bbr_data.renovation_year != bbr_data.building_year:
            add_info("Renoveret år", bbr_data.renovation_year)
        
        add_info("Ydervægsmateriale", bbr_data.exterior_material)
        add_info("Tagdækningsmateriale", bbr_data.roof_material)
        
        add_info("Samlet bygningsareal", bbr_data.total_building_area, " m²")
        add_info("Samlet boligareal", bbr_data.total_residential_area, " m²")
        add_info("Samlet erhvervsareal", bbr_data.total_commercial_area, " m²")
        add_info("Bebygget areal", bbr_data.built_area, " m²")
        
        add_info("Antal etager", bbr_data.floors)
        if bbr_data.deviating_floors:
             # BBR's 'byg055AfvigendeEtager' kode for kælder er ofte "10"
             # Din _translate_floor_type i bbr_service kan forbedres til at inkludere dette for klartekst
            kælder_info = "Ja" if "10" in str(bbr_data.deviating_floors) else f"Kode: {bbr_data.deviating_floors}"
            add_info("Afvigende etager (f.eks. kælder)", kælder_info)


        # Detaljeret kælder- og loftsareal fra floor_details
        if bbr_data.floor_details:
            has_basement_floor = False
            has_attic_floor = False
            for floor in bbr_data.floor_details:
                if floor.get('type_code') == '2': # Kælder
                    has_basement_floor = True
                    add_info(f"Kælder ({floor.get('designation', 'kl')}) areal", floor.get('total_area') or floor.get('basement_area'), " m²")
                elif floor.get('type_code') == '1': # Tagetage
                    has_attic_floor = True
                    add_info(f"Tagetage ({floor.get('designation', 'tag')}) areal", floor.get('total_area') or floor.get('attic_area'), " m²")
            
            if not bbr_data.basement_area and not has_basement_floor: # Hvis ikke allerede tilføjet
                 add_info("Kælderareal (direkte felt)", bbr_data.basement_area, " m²")
            if not bbr_data.attic_area and not has_attic_floor: # Hvis ikke allerede tilføjet
                 add_info("Loftsareal (direkte felt)", bbr_data.attic_area, " m²")


        add_info("Varmeinstallation", bbr_data.heating_type)
        add_info("Elevator", "Ja" if bbr_data.has_elevator else "Nej")
        add_info("Koordinater (reference)", bbr_data.coordinate)
        
        if not info_parts:
            return "BBR data fundet, men relevante felter er tomme.\n"
            
        return "\n".join(info_parts) + "\n"

    def _create_current_analysis_prompt(self, 
                                        reading: ClimateReading, 
                                        bbr_data: Optional[BuildingData], 
                                        address: str) -> str:
        """Create prompt for current conditions analysis, including BBR data."""
        
        bbr_info_string = self._format_bbr_data_for_prompt(bbr_data)

        prompt = f"""
Du er en intelligent klimarisikovurderingsassistent.

ADRESSE: {address}

NUVÆRENDE SENSORMÅLINGER:
🌡️ Temperatur (realtid): {reading.temperature:.1f} °C
💧 Luftfugtighed (realtid): {reading.humidity:.1f} %
⏰ Målt: {reading.timestamp}

BYGNINGSINFORMATION FRA BBR:
{bbr_info_string}
Baseret på BÅDE ovenstående SENSORMÅLINGER OG de detaljerede BYGNINGSOPLYSNINGER FRA BBR (hvis tilgængelige):
1. Hvad er de typiske klimarisici for DENNE SPECIFIKKE BYGNING (med dens type, materialer, alder, og konstruktion som beskrevet i BBR) på adressen?
2. Vurder bygningens sårbarhed over for fugt, skybrud og varme baseret på dens BBR-karakteristika (f.eks. kælder, tagmateriale, opførelsesår).
3. Giv en KONKRET beredskabsplan TILPASSET DENNE SPECIFIKKE BYGNING.
4. Anbefal konkrete handlinger – både forebyggende og ved kritisk hændelse – der tager højde for bygningens BBR-data og de aktuelle sensor målinger.
"""
        return prompt
    
    def _get_ai_response(self, prompt: str, analysis_type: str = "general") -> str:
        """Get response from OpenAI API and save to file."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Du er en ekspert i klimarisikovurdering og bygningsvedligeholdelse i Danmark. Giv konkrete, handlingsorienterede råd baseret på de fremlagte sensor- og BBR-data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000, # Øget max_tokens for potentielt længere prompts/svar
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            self._save_analysis(prompt, ai_response, analysis_type)
            return ai_response
            
        except Exception as e:
            error_msg = f"❌ Kunne ikke få AI-analyse. Fejl: {str(e)}"
            # Gemmer stadig prompten selv ved fejl, for debugging
            self_save_analysis_path = Path(self.analysis_dir) / datetime.now().strftime("%Y-%m-%d") / f"{datetime.now().strftime('%H-%M-%S')}_{analysis_type}_error_prompt.txt"
            try:
                self_save_analysis_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self_save_analysis_path, 'w', encoding='utf-8') as f_err:
                    f_err.write("Fejl under AI-kald.\nPROMPT:\n")
                    f_err.write(prompt)
            except Exception as save_e:
                print(f"⚠️ Yderligere fejl ved forsøg på at gemme fejlet prompt: {save_e}")

            return error_msg # Returnerer oprindelig fejlmeddelelse
    
    def _save_analysis(self, prompt: str, response: str, analysis_type: str) -> None:
        """Save AI analysis to structured files."""
        try:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y-%m-%d")
            time_str = timestamp.strftime("%H-%M-%S")
            
            daily_dir = self.analysis_dir / date_str
            daily_dir.mkdir(exist_ok=True)
            
            analysis_file = daily_dir / f"{time_str}_{analysis_type}.txt"
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write(f"KLIMAANALYSE - {analysis_type.upper()}\n")
                f.write("="*60 + "\n")
                f.write(f"Tidspunkt: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Model: {self.model}\n")
                f.write("\n" + "-"*60 + "\nPROMPT:\n" + "-"*60 + "\n")
                f.write(prompt + "\n")
                f.write("\n" + "-"*60 + "\nAI RESPONS:\n" + "-"*60 + "\n")
                f.write(response + "\n\n" + "="*60 + "\n")
            
            latest_file = self.analysis_dir / "latest_analysis.txt"
            with open(latest_file, 'w', encoding='utf-8') as f:
                f.write(f"Seneste AI Analyse\n")
                f.write(f"Tidspunkt: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Type: {analysis_type}\n")
                f.write("-" * 50 + "\n")
                f.write(response + "\n")
                
        except Exception as e:
            print(f"⚠️  Kunne ikke gemme analyse: {e}")


class ClimateMonitorApp:
    """Main application for climate monitoring and analysis."""
    
    def __init__(self, data_dir: str = "sensordata"):
        self.data_reader = DataReader(data_dir)
        self.analyzer = ClimateAnalyzer(data_dir)
        self.bbr_service = None
        if BBRAddressService:
            try:
                bbr_username = os.getenv('DATAFORDELER_NO_CERT_USERNAME')
                bbr_password = os.getenv('DATAFORDELER_NO_CERT_PASSWORD')
                if not bbr_username or not bbr_password:
                    print("⚠️ ADVARSEL: BBR brugernavn/password ikke fundet i miljøvariabler.")
                    print("   BBR-data vil ikke blive hentet. Angiv DATAFORDELER_NO_CERT_USERNAME og DATAFORDELER_NO_CERT_PASSWORD.")
                else:
                    self.bbr_service = BBRAddressService(username=bbr_username, password=bbr_password)
            except Exception as e:
                print(f"❌ Fejl ved initialisering af BBRAddressService: {e}")
                self.bbr_service = None
        else:
            print("ℹ️ BBRAddressService ikke tilgængelig (importfejl). Fortsætter uden BBR-integration.")

    def run_current_analysis(self, address: str = "") -> None:
        """Analyze current climate conditions, including BBR data if available."""
        print("🔍 Henter nuværende klimadata...")
        current_sensor_reading = self.data_reader.get_current_reading()
        
        if not current_sensor_reading:
            print("❌ Ingen aktuelle sensordata tilgængelige.")
            return

        print(f"📈 Nuværende sensordata: {current_sensor_reading.temperature:.1f}°C, {current_sensor_reading.humidity:.1f}%")

        bbr_building_data: Optional[BuildingData] = None
        if self.bbr_service and address:
            print(f"🏘️ Henter BBR-data for adressen: {address}...")
            bbr_building_data = self.bbr_service.get_building_data(address)
            if bbr_building_data:
                print("✅ BBR-data hentet succesfuldt.")
                # print(bbr_building_data.get_summary()) # For debugging
            else:
                print("⚠️ Kunne ikke hente BBR-data for den angivne adresse.")
        elif not address and self.bbr_service:
            print("ℹ️ Ingen adresse angivet, BBR-data vil ikke blive hentet.")
        elif not self.bbr_service:
             print("ℹ️ BBR Service er ikke konfigureret, fortsætter uden BBR-data.")


        print("🤖 AI analyserer nuværende forhold...")
        analysis = self.analyzer.analyze_current_conditions(
            current_sensor_reading, 
            bbr_building_data, 
            address or "Ukendt adresse" # Sørg for at adresse altid er en streng
        )
        
        print("\n" + "="*60)
        print("📋 AKTUEL KLIMAANALYSE (med BBR-data hvis muligt)")
        print("="*60)
        print(analysis)


def main():
    """Main application entry point."""
    print("🌡️  KLIMAANALYSE SYSTEM (Udvidet med BBR)")
    print("="*50)
    
    try:
        data_dir = input("Data mappe (default: sensordata): ").strip() or "sensordata"
        app = ClimateMonitorApp(data_dir)
        
        address_input = input("📍 Indtast adresse for BBR-opslag (valgfri, tryk Enter for at springe over): ").strip()
        
        while True:
            print("\n🔧 VÆLG HANDLING:")
            print("1. Analyser nuværende forhold (inkl. BBR-data hvis adresse er angivet)")
            print("2. Afslut") 
            
            choice = input("\nVælg (1-2): ").strip()
            
            if choice == "1":
                # Hvis brugeren indtastede en ny adresse her, kunne man opdatere app.address
                # For nu bruges den adresse, der blev indtastet ved start.
                app.run_current_analysis(address_input)
                
            elif choice == "2":
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