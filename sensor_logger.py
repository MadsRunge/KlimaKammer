#!/usr/bin/env python3
"""
Sensor Logger - Continuously reads climate sensor data and saves to text files.
"""

import os
import serial
import time
import json
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class SensorReading:
    """Data class for a single sensor reading."""
    timestamp: str
    temperature: float
    humidity: float
    unix_timestamp: float
    
    def to_csv_line(self) -> str:
        """Convert to CSV format line."""
        return f"{self.timestamp},{self.temperature},{self.humidity},{self.unix_timestamp}\n"
    
    def to_json_line(self) -> str:
        """Convert to JSON lines format."""
        return json.dumps(asdict(self)) + "\n"


class SensorLogger:
    """Handles continuous sensor data collection and file storage."""
    
    def __init__(self, 
                 port: str = "/dev/cu.usbserial-0001", 
                 baudrate: int = 115200,
                 data_dir: str = "sensordata"):
        self.port = port
        self.baudrate = baudrate
        self.timeout = 5
        self.data_dir = Path(data_dir)
        
        # Create data directory if it doesn't exist
        self.data_dir.mkdir(exist_ok=True)
        
        # Setup file paths
        self.setup_files()
    
    def setup_files(self) -> None:
        """Initialize data files and directories."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Create subdirectories
        (self.data_dir / "daily").mkdir(exist_ok=True)
        (self.data_dir / "monthly").mkdir(exist_ok=True)
        
        # File paths
        self.current_file = self.data_dir / "current_reading.txt"
        self.daily_csv = self.data_dir / "daily" / f"{today}.csv"
        self.daily_json = self.data_dir / "daily" / f"{today}.jsonl"
        self.latest_file = self.data_dir / "latest_readings.txt"
        
        # Create CSV header if file doesn't exist
        if not self.daily_csv.exists():
            with open(self.daily_csv, 'w') as f:
                f.write("timestamp,temperature,humidity,unix_timestamp\n")
    
    def read_sensor_data(self) -> Optional[SensorReading]:
        """
        Read single measurement from sensor.
        
        Returns:
            SensorReading object or None if reading failed
        """
        try:
            with serial.Serial(self.port, self.baudrate, timeout=self.timeout) as ser:
                # Wait for stable connection
                time.sleep(1)
                
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if not line or ',' not in line:
                    print(f"⚠️  Invalid data format: {line}")
                    return None
                
                # Parse temperature and humidity
                temp_str, humidity_str = line.split(',', 1)
                temperature = float(temp_str)
                humidity = float(humidity_str)
                
                # Validate ranges
                if not (-50 <= temperature <= 80):
                    print(f"⚠️  Temperature out of range: {temperature}°C")
                    return None
                    
                if not (0 <= humidity <= 100):
                    print(f"⚠️  Humidity out of range: {humidity}%")
                    return None
                
                # Create reading object
                now = time.time()
                timestamp = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
                
                return SensorReading(
                    timestamp=timestamp,
                    temperature=temperature,
                    humidity=humidity,
                    unix_timestamp=now
                )
                
        except serial.SerialException as e:
            print(f"❌ Serial connection error: {e}")
            return None
        except ValueError as e:
            print(f"❌ Data parsing error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def save_reading(self, reading: SensorReading) -> None:
        """
        Save reading to all relevant files.
        
        Args:
            reading: SensorReading object to save
        """
        try:
            # Save current reading (single latest value)
            with open(self.current_file, 'w') as f:
                f.write(f"Last Updated: {reading.timestamp}\n")
                f.write(f"Temperature: {reading.temperature:.2f}°C\n")
                f.write(f"Humidity: {reading.humidity:.2f}%\n")
                f.write(f"Unix Timestamp: {reading.unix_timestamp}\n")
            
            # Append to daily CSV
            with open(self.daily_csv, 'a') as f:
                f.write(reading.to_csv_line())
            
            # Append to daily JSON lines
            with open(self.daily_json, 'a') as f:
                f.write(reading.to_json_line())
            
            # Maintain latest N readings (last 100)
            self.update_latest_readings(reading)
            
        except Exception as e:
            print(f"❌ Error saving data: {e}")
    
    def update_latest_readings(self, new_reading: SensorReading, max_readings: int = 100) -> None:
        """
        Maintain a file with the latest N readings.
        
        Args:
            new_reading: New reading to add
            max_readings: Maximum number of readings to keep
        """
        readings = []
        
        # Read existing readings
        if self.latest_file.exists():
            try:
                with open(self.latest_file, 'r') as f:
                    for line in f:
                        if line.strip() and not line.startswith('#'):
                            readings.append(line.strip())
            except Exception:
                pass  # Start fresh if file is corrupted
        
        # Add new reading
        new_line = f"{new_reading.timestamp},{new_reading.temperature},{new_reading.humidity}"
        readings.append(new_line)
        
        # Keep only latest readings
        readings = readings[-max_readings:]
        
        # Write back to file
        with open(self.latest_file, 'w') as f:
            f.write("# Latest sensor readings (timestamp,temperature,humidity)\n")
            f.write("# Updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
            for reading_line in readings:
                f.write(reading_line + "\n")
    
    def run_continuous_logging(self, interval_seconds: int = 60) -> None:
        """
        Run continuous sensor data logging.
        
        Args:
            interval_seconds: Time between readings in seconds
        """
        print(f"🚀 Starting sensor logging (every {interval_seconds} seconds)")
        print(f"📁 Data directory: {self.data_dir.absolute()}")
        print("Press Ctrl+C to stop\n")
        
        reading_count = 0
        error_count = 0
        
        try:
            while True:
                reading = self.read_sensor_data()
                
                if reading:
                    self.save_reading(reading)
                    reading_count += 1
                    print(f"✅ Reading #{reading_count}: "
                          f"{reading.temperature:.1f}°C, {reading.humidity:.1f}% "
                          f"at {reading.timestamp}")
                else:
                    error_count += 1
                    print(f"❌ Failed reading #{error_count}")
                
                # Check if new day (rotate files)
                current_date = datetime.now().strftime("%Y-%m-%d")
                if current_date not in str(self.daily_csv):
                    self.setup_files()
                    print(f"📅 New day detected - created new files for {current_date}")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Logging stopped by user")
            print(f"📊 Total readings: {reading_count}, Errors: {error_count}")
    
    def get_stats(self) -> Dict:
        """Get statistics about collected data."""
        stats = {
            "data_directory": str(self.data_dir.absolute()),
            "files": {
                "current_reading": self.current_file.exists(),
                "latest_readings": self.latest_file.exists(),
            },
            "daily_files": []
        }
        
        # Count daily files
        daily_dir = self.data_dir / "daily"
        if daily_dir.exists():
            for file_path in daily_dir.glob("*.csv"):
                try:
                    line_count = sum(1 for _ in open(file_path)) - 1  # Subtract header
                    stats["daily_files"].append({
                        "date": file_path.stem,
                        "readings": line_count
                    })
                except Exception:
                    continue
        
        return stats


def main():
    """Main function for sensor logging."""
    print("🌡️  Climate Sensor Logger")
    print("=" * 40)
    
    # Configuration
    port = input("Enter serial port (default: /dev/cu.usbserial-0001): ").strip()
    if not port:
        port = "/dev/cu.usbserial-0001"
    
    data_dir = input("Enter data directory (default: sensordata): ").strip()
    if not data_dir:
        data_dir = "sensordata"
    
    interval = input("Enter logging interval in seconds (default: 60): ").strip()
    interval = int(interval) if interval.isdigit() else 60
    
    try:
        # Initialize logger
        logger = SensorLogger(port=port, data_dir=data_dir)
        
        # Show current stats
        stats = logger.get_stats()
        print(f"\n📁 Data will be saved to: {stats['data_directory']}")
        
        # Ask for action
        action = input("\nChoose action:\n1. Start logging\n2. Single reading\n3. Show stats\nEnter choice (1-3): ").strip()
        
        if action == "2":
            # Single reading
            print("\n🔍 Taking single reading...")
            reading = logger.read_sensor_data()
            if reading:
                logger.save_reading(reading)
                print(f"✅ Reading saved: {reading.temperature:.1f}°C, {reading.humidity:.1f}%")
            else:
                print("❌ Failed to get reading")
                
        elif action == "3":
            # Show stats
            stats = logger.get_stats()
            print(f"\n📊 Statistics:")
            print(f"Data directory: {stats['data_directory']}")
            print(f"Daily files: {len(stats['daily_files'])}")
            for day_stats in stats['daily_files']:
                print(f"  {day_stats['date']}: {day_stats['readings']} readings")
        else:
            # Start continuous logging
            logger.run_continuous_logging(interval)
            
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Application error: {e}")


if __name__ == "__main__":
    main()