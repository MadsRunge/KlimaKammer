#!/usr/bin/env python3
"""
Climate Analyzer - Reads sensor data files and provides AI-powered climate analysis.
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ClimateReading:
    """Represents a single climate reading."""
    timestamp: str
    temperature: float
    humidity: float
    unix_timestamp: float


class DataReader:
    """Handles reading sensor data from files."""
    
    def __init__(self, data_dir: str = "sensordata"):
        self.data_dir = Path(data_dir)
        
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
    
    def get_current_reading(self) -> Optional[ClimateReading]:
        """
        Read the most recent sensor reading.
        
        Returns:
            Latest ClimateReading or None if not available
        """
        current_file = self.data_dir / "current_reading.txt"
        
        if not current_file.exists():
            return None
        
        try:
            with open(current_file, 'r') as f:
                lines = f.readlines()
            
            # Parse the structured format
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
            print(f"❌ Error reading current data: {e}")
            return None
    
    def get_latest_readings(self, count: int = 10) -> List[ClimateReading]:
        """
        Get the latest N readings.
        
        Args:
            count: Number of recent readings to return
            
        Returns:
            List of ClimateReading objects
        """
        latest_file = self.data_dir / "latest_readings.txt"
        
        if not latest_file.exists():
            return []
        
        readings = []
        try:
            with open(latest_file, 'r') as f:
                lines = f.readlines()
            
            # Skip comment lines and get latest readings
            data_lines = [line.strip() for line in lines if not line.startswith('#') and line.strip()]
            
            for line in data_lines[-count:]:
                parts = line.split(',')
                if len(parts) >= 3:
                    readings.append(ClimateReading(
                        timestamp=parts[0],
                        temperature=float(parts[1]),
                        humidity=float(parts[2]),
                        unix_timestamp=0  # Not stored in this format
                    ))
            
        except Exception as e:
            print(f"❌ Error reading latest readings: {e}")
        
        return readings
    
    def get_daily_data(self, date: str = None) -> List[ClimateReading]:
        """
        Get all readings for a specific day.
        
        Args:
            date: Date in YYYY-MM-DD format, defaults to today
            
        Returns:
            List of ClimateReading objects for the day
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        daily_file = self.data_dir / "daily" / f"{date}.csv"
        
        if not daily_file.exists():
            return []
        
        readings = []
        try:
            with open(daily_file, 'r') as f:
                lines = f.readlines()[1:]  # Skip header
            
            for line in lines:
                parts = line.strip().split(',')
                if len(parts) >= 4:
                    readings.append(ClimateReading(
                        timestamp=parts[0],
                        temperature=float(parts[1]),
                        humidity=float(parts[2]),
                        unix_timestamp=float(parts[3])
                    ))
                    
        except Exception as e:
            print(f"❌ Error reading daily data: {e}")
        
        return readings
    
    def get_statistics(self, readings: List[ClimateReading]) -> Dict:
        """Calculate statistics for a list of readings."""
        if not readings:
            return {}
        
        temps = [r.temperature for r in readings]
        humidities = [r.humidity for r in readings]
        
        return {
            "count": len(readings),
            "temperature": {
                "min": min(temps),
                "max": max(temps),
                "avg": sum(temps) / len(temps),
                "current": temps[-1] if temps else 0
            },
            "humidity": {
                "min": min(humidities),
                "max": max(humidities),
                "avg": sum(humidities) / len(humidities),
                "current": humidities[-1] if humidities else 0
            },
            "time_range": {
                "first": readings[0].timestamp,
                "last": readings[-1].timestamp
            }
        }


class ClimateAnalyzer:
    """AI-powered climate analysis using OpenAI."""
    
    def __init__(self, data_dir: str = "sensordata"):
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4"
        self.data_dir = Path(data_dir)
        
        # Setup analysis storage
        self.analysis_dir = self.data_dir / "analyses"
        self.analysis_dir.mkdir(exist_ok=True)
    
    def analyze_current_conditions(self, current_reading: ClimateReading, address: str = "") -> str:
        """
        Analyze current climate conditions using your original prompt.
        
        Args:
            current_reading: Current sensor reading
            address: Optional address for location-specific advice
            
        Returns:
            AI analysis and recommendations
        """
        prompt = self._create_current_analysis_prompt(current_reading, address)
        
        return self._get_ai_response(prompt, "current_conditions")
    
    def analyze_trends(self, readings: List[ClimateReading], stats: Dict, address: str = "") -> str:
        """
        Analyze climate trends over time.
        
        Args:
            readings: List of recent readings
            stats: Statistical summary of the data
            address: Optional address for location-specific advice
            
        Returns:
            AI trend analysis and recommendations
        """
        prompt = self._create_trend_analysis_prompt(readings, stats, address)
        
        return self._get_ai_response(prompt, "trend_analysis")
    
    def _create_current_analysis_prompt(self, reading: ClimateReading, address: str) -> str:
        """Create prompt for current conditions analysis (your original prompt)."""
        address_line = f"📍 Adresse: {address}\n\n" if address else ""
        
        return f"""
Du er en intelligent klimarisikovurderingsassistent.

{address_line}🌡️ Temperatur (realtid): {reading.temperature:.1f} °C
💧 Luftfugtighed (realtid): {reading.humidity:.1f} %
⏰ Målt: {reading.timestamp}

Brug din viden om geografisk placering, klimazoner og bygningstyper i området.
Svar med:
1. Hvad er de typiske klimarisici ved denne adresse?
2. Hvilken bygningstype antager du det er, og hvorfor?
3. Giv en konkret beredskabsplan for fugt, skybrud eller varme
4. Anbefal konkrete handlinger – både forebyggende og ved kritisk hændelse.
"""
    
    def _create_trend_analysis_prompt(self, readings: List[ClimateReading], stats: Dict, address: str) -> str:
        """Create prompt for trend analysis."""
        address_line = f"📍 Adresse: {address}\n\n" if address else ""
        
        # Create trend description
        recent_temps = [r.temperature for r in readings[-5:]] if len(readings) >= 5 else [r.temperature for r in readings]
        recent_humidity = [r.humidity for r in readings[-5:]] if len(readings) >= 5 else [r.humidity for r in readings]
        
        temp_trend = "stigende" if len(recent_temps) > 1 and recent_temps[-1] > recent_temps[0] else "faldende"
        humidity_trend = "stigende" if len(recent_humidity) > 1 and recent_humidity[-1] > recent_humidity[0] else "faldende"
        
        return f"""
Du er en intelligent klimatrendanalyst og beredskabsrådgiver.

{address_line}📊 KLIMADATA OVERSIGT:
• Antal målinger: {stats['count']}
• Tidsperiode: {stats['time_range']['first']} til {stats['time_range']['last']}

🌡️ TEMPERATUR:
• Nuværende: {stats['temperature']['current']:.1f}°C
• Min/Max: {stats['temperature']['min']:.1f}°C / {stats['temperature']['max']:.1f}°C  
• Gennemsnit: {stats['temperature']['avg']:.1f}°C
• Trend: {temp_trend}

💧 LUFTFUGTIGHED:
• Nuværende: {stats['humidity']['current']:.1f}%
• Min/Max: {stats['humidity']['min']:.1f}% / {stats['humidity']['max']:.1f}%
• Gennemsnit: {stats['humidity']['avg']:.1f}%
• Trend: {humidity_trend}

Baseret på disse trends og data, giv:
1. Risikovurdering af de observerede mønstre
2. Langsigtede anbefalinger baseret på trends
3. Kritiske tærskler at holde øje med
4. Forebyggende handlingsplan for næste 24-48 timer
5. Sammenligning med normale danske klimaforhold
"""
    
    def _get_ai_response(self, prompt: str, analysis_type: str = "general") -> str:
        """Get response from OpenAI API and save to file."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Du er en ekspert i klimarisikovurdering og bygningsvedligeholdelse i Danmark. Giv konkrete, handlingsorienterede råd."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=700,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            
            # Save analysis to file
            self._save_analysis(prompt, ai_response, analysis_type)
            
            return ai_response
            
        except Exception as e:
            error_msg = f"❌ Kunne ikke få AI-analyse. Fejl: {str(e)}"
            self._save_analysis(prompt, error_msg, f"{analysis_type}_error")
            return error_msg
    
    def _save_analysis(self, prompt: str, response: str, analysis_type: str) -> None:
        """Save AI analysis to structured files."""
        try:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y-%m-%d")
            time_str = timestamp.strftime("%H-%M-%S")
            
            # Create daily analysis directory
            daily_dir = self.analysis_dir / date_str
            daily_dir.mkdir(exist_ok=True)
            
            # Individual analysis file
            analysis_file = daily_dir / f"{time_str}_{analysis_type}.txt"
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write(f"KLIMAANALYSE - {analysis_type.upper()}\n")
                f.write("="*60 + "\n")
                f.write(f"Tidspunkt: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Model: {self.model}\n")
                f.write("\n" + "-"*60 + "\n")
                f.write("PROMPT:\n")
                f.write("-"*60 + "\n")
                f.write(prompt + "\n")
                f.write("\n" + "-"*60 + "\n")
                f.write("AI RESPONS:\n")
                f.write("-"*60 + "\n")
                f.write(response + "\n")
                f.write("\n" + "="*60 + "\n")
            
            # Append to daily log file
            daily_log = daily_dir / f"{date_str}_analyser.log"
            
            with open(daily_log, 'a', encoding='utf-8') as f:
                f.write(f"\n[{timestamp.strftime('%H:%M:%S')}] {analysis_type.upper()}\n")
                f.write("-" * 40 + "\n")
                f.write(response + "\n")
                f.write("=" * 40 + "\n")
            
            # Update latest analysis file
            latest_file = self.analysis_dir / "latest_analysis.txt"
            
            with open(latest_file, 'w', encoding='utf-8') as f:
                f.write(f"Seneste AI Analyse\n")
                f.write(f"Tidspunkt: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Type: {analysis_type}\n")
                f.write("-" * 50 + "\n")
                f.write(response + "\n")
                
        except Exception as e:
            print(f"⚠️  Kunne ikke gemme analyse: {e}")
    
    def get_analysis_history(self, days_back: int = 7) -> List[Dict]:
        """Get history of recent analyses."""
        analyses = []
        
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_dir = self.analysis_dir / date
            
            if daily_dir.exists():
                for analysis_file in daily_dir.glob("*.txt"):
                    if not analysis_file.name.endswith("_analyser.log"):
                        try:
                            with open(analysis_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Extract info from filename
                            name_parts = analysis_file.stem.split('_', 1)
                            time_str = name_parts[0]
                            analysis_type = name_parts[1] if len(name_parts) > 1 else "unknown"
                            
                            analyses.append({
                                "date": date,
                                "time": time_str,
                                "type": analysis_type,
                                "file": str(analysis_file),
                                "size": len(content)
                            })
                        except Exception:
                            continue
        
        return sorted(analyses, key=lambda x: f"{x['date']} {x['time']}", reverse=True)


class ClimateMonitorApp:
    """Main application for climate monitoring and analysis."""
    
    def __init__(self, data_dir: str = "sensordata"):
        self.data_reader = DataReader(data_dir)
        self.analyzer = ClimateAnalyzer(data_dir)
    
    def run_current_analysis(self, address: str = "") -> None:
        """Analyze current climate conditions."""
        print("🔍 Henter nuværende klimadata...")
        
        current = self.data_reader.get_current_reading()
        if not current:
            print("❌ Ingen aktuelle data tilgængelige")
            return
        
        print(f"📈 Nuværende: {current.temperature:.1f}°C, {current.humidity:.1f}%")
        print("🤖 AI analyserer nuværende forhold...")
        
        analysis = self.analyzer.analyze_current_conditions(current, address)
        
        print("\n" + "="*60)
        print("📋 AKTUEL KLIMAANALYSE")
        print("="*60)
        print(analysis)
    
    def run_trend_analysis(self, address: str = "", days_back: int = 1) -> None:
        """Analyze climate trends over time."""
        print(f"📊 Henter klimadata for de sidste {days_back} dag(e)...")
        
        # Get data for analysis
        all_readings = []
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            daily_readings = self.data_reader.get_daily_data(date)
            all_readings.extend(daily_readings)
        
        if not all_readings:
            print("❌ Ingen historiske data tilgængelige")
            return
        
        # Get statistics
        stats = self.data_reader.get_statistics(all_readings)
        
        print(f"📈 Analyserer {len(all_readings)} målinger...")
        print(f"📊 Temperatur: {stats['temperature']['min']:.1f}-{stats['temperature']['max']:.1f}°C")
        print(f"💧 Luftfugtighed: {stats['humidity']['min']:.1f}-{stats['humidity']['max']:.1f}%")
        print("🤖 AI analyserer trends...")
        
        analysis = self.analyzer.analyze_trends(all_readings, stats, address)
        
        print("\n" + "="*60)
        print("📊 KLIMATREND ANALYSE")
        print("="*60)
        print(analysis)
    
    def show_analysis_history(self) -> None:
        """Show history of recent AI analyses."""
        print("📚 ANALYSE HISTORIK")
        print("="*50)
        
        analyses = self.analyzer.get_analysis_history(7)
        
        if not analyses:
            print("❌ Ingen tidligere analyser fundet")
            return
        
        print(f"📋 Seneste {len(analyses)} analyser:")
        
        for analysis in analyses[:10]:  # Show last 10
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
        """Show summary of available data."""
        print("📁 DATA OVERSIGT")
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


def main():
    """Main application entry point."""
    print("🌡️ KLIMAANALYSE SYSTEM")
    print("="*50)
    
    try:
        # Initialize app
        data_dir = input("Data mappe (default: sensordata): ").strip() or "sensordata"
        app = ClimateMonitorApp(data_dir)
        
        # Get address
        address = input("📍 Indtast adresse (valgfri): ").strip()
        
        while True:
            print("\n🔧 VÆLG HANDLING:")
            print("1. Analyser nuværende forhold")
            print("2. Analyser trends (sidste dag)")
            print("3. Analyser trends (flere dage)")
            print("4. Vis data oversigt")
            print("5. Vis analyse historik")
            print("6. Afslut")
            
            choice = input("\nVælg (1-6): ").strip()
            
            if choice == "1":
                app.run_current_analysis(address)
                
            elif choice == "2":
                app.run_trend_analysis(address, days_back=1)
                
            elif choice == "3":
                days = input("Antal dage tilbage (default: 3): ").strip()
                days = int(days) if days.isdigit() else 3
                app.run_trend_analysis(address, days_back=days)
                
            elif choice == "4":
                app.show_data_summary()
                
            elif choice == "5":
                app.show_analysis_history()
                
            elif choice == "6":
                print("👋 Farvel!")
                break
                
            else:
                print("❌ Ugyldigt valg")
            
            input("\nTryk Enter for at fortsætte...")
            
    except KeyboardInterrupt:
        print("\n👋 Program stoppet af bruger")
    except Exception as e:
        print(f"❌ Programfejl: {e}")


if __name__ == "__main__":
    main()