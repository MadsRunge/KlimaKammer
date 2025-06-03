# 🌡️ KlimaKammer - Intelligent Klimaovervågning

Et Python-baseret system der læser klimasensordata og bruger AI til at give beredskabsanbefalinger.

## 📋 Hvad gør systemet?

- **Læser data** fra klimasensorer (temperatur og luftfugtighed)
- **Gemmer målinger** i strukturerede filer
- **Analyserer data** med OpenAI's GPT-4
- **Giver beredskabsråd** baseret på klimarisici
- **Gemmer AI-analyser** for senere reference

## 🚀 Opsætning

### 1. Klon eller download projektet

```bash
mkdir KlimaKammer
cd KlimaKammer
# Kopier filerne: sensor_logger.py, climate_analyzer.py
```

### 2. Opret virtuel miljø

```bash
python -m venv venv

# Aktiver miljøet:
# På macOS/Linux:
source venv/bin/activate
# På Windows:
# venv\Scripts\activate
```

### 3. Installer dependencies

```bash
pip install openai>=1.0.0 pyserial>=3.5 python-dotenv>=1.0.0
```

### 4. Opret OpenAI API nøgle

```bash
echo "OPENAI_API_KEY=din-api-nøgle-her" > .env
```

> 💡 **Få API nøgle:** Gå til [OpenAI Platform](https://platform.openai.com/api-keys)

### 5. Test uden hardware (valgfrit)

```bash
# Opret test data
mkdir -p sensordata/daily

echo "Last Updated: 2025-06-03 14:30:00
Temperature: 23.5°C
Humidity: 65.2%
Unix Timestamp: 1717423800" > sensordata/current_reading.txt

echo "timestamp,temperature,humidity,unix_timestamp
2025-06-03 14:00:00,22.8,63.5,1717423200
2025-06-03 14:15:00,23.1,64.2,1717424100
2025-06-03 14:30:00,23.5,65.2,1717425000" > sensordata/daily/2025-06-03.csv
```

## 📊 Brug af systemet

### Dataindsamling (sensor_logger.py)

```bash
python sensor_logger.py
```

**Hvad den gør:**

- Læser fra sensor via USB/serial port
- Gemmer data kontinuerligt i `sensordata/` mappen
- Opretter daglige CSV filer
- Kører til du stopper den (Ctrl+C)

**Konfiguration:**

- Serial port (default: `/dev/cu.usbserial-0001`)
- Data mappe (default: `sensordata`)
- Logging interval (default: 60 sekunder)

### AI-analyse (climate_analyzer.py)

```bash
python climate_analyzer.py
```

**Menu muligheder:**

1. **Analyser nuværende forhold** - AI vurderer aktuelle målinger
2. **Analyser trends (sidste dag)** - Trend-analyse af seneste data
3. **Analyser trends (flere dage)** - Historisk trend-analyse
4. **Vis data oversigt** - Status på indsamlede data
5. **Vis analyse historik** - Tidligere AI-anbefalinger
6. **Afslut**

## 📁 Filstruktur

```
KlimaKammer/
├── sensor_logger.py           # Dataindsamling
├── climate_analyzer.py        # AI-analyse
├── .env                       # API nøgle
├── requirements.txt           # Dependencies
├── sensordata/                # Sensor målinger
│   ├── current_reading.txt       # Seneste måling
│   ├── latest_readings.txt       # Sidste 100 målinger
│   └── daily/
│       ├── 2025-06-03.csv        # Dagens data
│       └── 2025-06-04.csv        # Næste dag
└── analyses/                  # AI analyser
    ├── latest_analysis.txt       # Seneste analyse
    └── 2025-06-03/
        ├── 14-30-15_current_conditions.txt
        └── 2025-06-03_analyser.log
```

## 🔧 Hardware opsætning

### Understøttede sensorer

- Arduino med DHT22/DHT11 sensor
- ESP32 med klimasensor
- Enhver sensor der sender `temperatur,luftfugtighed` via serial

### Arduino eksempel

```cpp
// Send data i format: "23.5,65.2"
Serial.print(temperature);
Serial.print(",");
Serial.println(humidity);
```

### Seriel opsætning

- **Baudrate:** 115200
- **Format:** `temperatur,luftfugtighed` (f.eks. "23.5,65.2")
- **Port:** Konfigureres i programmet

## 📋 Eksempel på brug

### 1. Start dataindsamling

```bash
python sensor_logger.py
# Vælg port, data mappe og interval
# Lad den køre i baggrunden
```

### 2. Kør analyse

```bash
python climate_analyzer.py
# Indtast adresse: "København"
# Vælg "1" for aktuel analyse
```

### 3. Se resultater

AI-analysen giver:

- Risikovurdering af klimaforhold
- Forslag til bygningstype
- Beredskabsplan for fugt/skybrud/varme
- Konkrete handlinger

## ❓ Fejlfinding

### "No module named 'openai'"

```bash
pip install openai>=1.0.0
```

### "OPENAI_API_KEY environment variable not set"

```bash
echo "OPENAI_API_KEY=din-rigtige-nøgle" > .env
```

### "Serial connection error"

- Tjek at sensor er tilsluttet
- Verificer serial port navn
- Tjek at ingen andre programmer bruger porten

### "Ingen aktuelle data tilgængelige"

- Kør `sensor_logger.py` først for at samle data
- Eller opret test data som vist i opsætningen

## 🔄 Almindelig workflow

1. **Setup:** Installer dependencies og opret API nøgle
2. **Start sensor:** Kør `sensor_logger.py` for dataindsamling
3. **Analyse:** Kør `climate_analyzer.py` for AI-vurderinger
4. **Historik:** Se tidligere analyser via menu punkt 5
5. **Overvågning:** Lad sensor logger køre kontinuerligt

## 📊 Tips og tricks

- **Kontinuerlig overvågning:** Lad sensor_logger køre som baggrundsjob
- **Daglig analyse:** Kør climate_analyzer hver morgen for dagens vurdering
- **Trend-analyse:** Brug menu punkt 2-3 for at spore udvikling over tid
- **Backup:** Kopier `sensordata/` og `analyses/` mapper regelmæssigt

## 🆘 Support

- Tjek `.env` filen indeholder korrekt API nøgle
- Verificer sensor forbindelse og data format
- Se `analyses/` mappen for gemte AI-responser
- Restart programmer hvis de hænger

---

**God fornøjelse med din intelligente klimaovervågning! 🌡️🤖**
