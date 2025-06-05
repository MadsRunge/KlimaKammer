#!/usr/bin/env python3
"""
BBR Address Service - Integrates DAWA and BBR APIs to fetch building data from addresses.
Updated with correct field mapping based on actual API response.
"""

import os
import requests
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class BuildingData:
    """Structured building data from BBR with all available fields."""
    
    # Basic info
    address: str
    building_number: Optional[int] = None
    building_year: Optional[int] = None
    renovation_year: Optional[int] = None
    building_type: str = ""
    building_type_code: str = ""
    
    # Materials
    exterior_material: str = ""
    exterior_material_code: str = ""
    roof_material: str = ""
    roof_material_code: str = ""
    material_source: str = ""
    
    # Areas (all in m²)
    total_building_area: Optional[int] = None
    total_residential_area: Optional[int] = None  # living_area equivalent
    total_commercial_area: Optional[int] = None
    built_area: Optional[int] = None
    basement_area: Optional[int] = None
    attic_area: Optional[int] = None
    basement_commercial_area: Optional[int] = None
    
    # Building details
    floors: Optional[int] = None
    deviating_floors: Optional[str] = None
    rooms: Optional[int] = None
    bathrooms: Optional[int] = None
    toilets: Optional[int] = None
    
    # Technical systems
    heating_type: str = ""
    heating_code: str = ""
    has_elevator: bool = False
    elevator_count: Optional[int] = None
    water_supply: str = ""
    sewerage: str = ""
    
    # Building structure and location
    coordinate: str = ""
    coordinate_system: str = ""
    coordinate_quality: str = ""
    
    # Administrative data
    municipality_code: str = ""
    plot_id: str = ""
    ground_id: str = ""
    revision_date: str = ""
    
    # Detailed floor and entrance information
    floor_details: List[Dict] = None
    entrances: List[Dict] = None
    access_from_addresses: List[str] = None
    
    # Multiple buildings on property
    additional_buildings: List[Dict] = None
    
    # Raw data for debugging
    raw_bbr_data: Dict = None
    
    # Data source tracking
    data_source: str = ""
    data_source_code: str = ""
    confidence_level: str = ""
    last_updated: str = ""
    
    def __post_init__(self):
        if self.additional_buildings is None:
            self.additional_buildings = []
        if self.floor_details is None:
            self.floor_details = []
        if self.entrances is None:
            self.entrances = []
        if self.access_from_addresses is None:
            self.access_from_addresses = []
    
    # Keep legacy property for backward compatibility
    @property
    def living_area(self) -> Optional[int]:
        """Legacy property - maps to total_residential_area."""
        return self.total_residential_area
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for easy serialization."""
        return {
            'address': self.address,
            'building_number': self.building_number,
            'building_year': self.building_year,
            'renovation_year': self.renovation_year,
            'building_type': self.building_type,
            'exterior_material': self.exterior_material,
            'roof_material': self.roof_material,
            'total_building_area': self.total_building_area,
            'total_residential_area': self.total_residential_area,
            'living_area': self.living_area,  # Legacy compatibility
            'total_commercial_area': self.total_commercial_area,
            'built_area': self.built_area,
            'basement_area': self.basement_area,
            'attic_area': self.attic_area,
            'floors': self.floors,
            'deviating_floors': self.deviating_floors,
            'rooms': self.rooms,
            'bathrooms': self.bathrooms,
            'toilets': self.toilets,
            'heating_type': self.heating_type,
            'has_elevator': self.has_elevator,
            'water_supply': self.water_supply,
            'sewerage': self.sewerage,
            'municipality_code': self.municipality_code,
            'coordinate': self.coordinate,
            'additional_buildings_count': len(self.additional_buildings),
            'floor_count': len(self.floor_details),
            'entrance_count': len(self.entrances)
        }
    
    def get_summary(self) -> str:
        """Get comprehensive human-readable summary."""
        summary = f"📍 {self.address}\n"
        
        # Basic building info
        if self.building_type:
            summary += f"🏠 {self.building_type}"
            if self.building_number:
                summary += f" (bygning #{self.building_number})"
            if self.building_year:
                summary += f" fra {self.building_year}"
            if self.renovation_year and self.renovation_year != self.building_year:
                summary += f" (renoveret {self.renovation_year})"
            summary += "\n"
        
        # Areas with better breakdown
        if self.total_building_area:
            summary += f"📏 Samlet bygningsareal: {self.total_building_area} m²\n"
        if self.total_residential_area:
            summary += f"🏠 Boligareal: {self.total_residential_area} m²\n"
        if self.total_commercial_area:
            summary += f"🏢 Erhvervsareal: {self.total_commercial_area} m²\n"
        if self.built_area:
            summary += f"🏗️ Bebygget areal: {self.built_area} m²\n"
        
        # Materials
        if self.exterior_material:
            summary += f"🧱 Ydervæg: {self.exterior_material}\n"
        if self.roof_material:
            summary += f"🏘️ Tag: {self.roof_material}\n"
        
        # Structure with more detail
        if self.floors:
            summary += f"🏢 Etager: {self.floors}"
            if self.deviating_floors:
                summary += f" (afvigende: {self.deviating_floors})"
            summary += "\n"
        
        # Detailed floor breakdown
        if self.floor_details:
            summary += f"📂 Etagefordeling ({len(self.floor_details)} etager):\n"
            for floor in self.floor_details:
                floor_name = floor.get('designation', 'Ukendt')
                floor_area = floor.get('total_area')
                floor_type = floor.get('type_name', '')
                
                if floor_area:
                    summary += f"  • {floor_name}: {floor_area} m² ({floor_type})\n"
                else:
                    summary += f"  • {floor_name} ({floor_type})\n"
                
                # Show special areas
                if floor.get('basement_area'):
                    summary += f"    - Kælderareal: {floor['basement_area']} m²\n"
                if floor.get('attic_area'):
                    summary += f"    - Loftareal: {floor['attic_area']} m²\n"
                if floor.get('commercial_area'):
                    summary += f"    - Erhverv: {floor['commercial_area']} m²\n"
        
        # Technical systems
        if self.heating_type:
            summary += f"🔥 Varme: {self.heating_type}\n"
        
        if self.has_elevator:
            elevator_text = f"Elevator: {self.elevator_count} stk" if self.elevator_count else "Elevator: Ja"
            summary += f"🛗 {elevator_text}\n"
        
        # Access information
        if self.access_from_addresses:
            summary += f"🚪 Adgang fra {len(self.access_from_addresses)} adresse(r)\n"
        
        # Additional buildings
        if len(self.additional_buildings) > 0:
            summary += f"🏗️ Ekstra bygninger: {len(self.additional_buildings)}\n"
            for i, building in enumerate(self.additional_buildings[:3]):  # Show max 3
                building_type = building.get('type', 'Ukendt type')
                building_area = building.get('area', '?')
                summary += f"  • {building_type} ({building_area} m²)\n"
        
        # Data source
        summary += f"📊 Datakilde: {self.data_source}"
        if self.confidence_level:
            summary += f" ({self.confidence_level} sikkerhed)"
        summary += "\n"
        
        if self.last_updated:
            try:
                # Parse ISO datetime and format nicely
                dt = datetime.fromisoformat(self.last_updated.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                summary += f"🕐 Opdateret: {formatted_date}\n"
            except:
                summary += f"🕐 Opdateret: {self.last_updated}\n"
        
        return summary


class BBRAddressService:
    """Service for looking up building data by address using DAWA + BBR APIs."""
    
    def __init__(self, username: str, password: str):
        self.bbr_username = username
        self.bbr_password = password
        self.dawa_base_url = "https://api.dataforsyningen.dk"
        self.bbr_base_url = "https://services.datafordeler.dk"
        self.session = requests.Session()
        
        # Setup default timeouts and headers
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': 'KlimaKammer/2.0 Enhanced Climate Analysis Tool'
        })
    
    def get_building_data(self, address: str) -> Optional[BuildingData]:
        """
        Main method to get building data from address.
        
        Args:
            address: Full address string (e.g., "Marievej 2, 4200 Slagelse")
            
        Returns:
            BuildingData object or None if not found
        """
        try:
            print(f"🔍 Søger bygningsdata for: {address}")
            
            # Step 1: Get husnummer ID from DAWA
            husnummer_id = self._dawa_address_lookup(address)
            if not husnummer_id:
                print("❌ Kunne ikke finde adresse i DAWA")
                return None
            
            print(f"✅ Fandt husnummer ID: {husnummer_id}")
            
            # Step 2: Get building data from BBR using husnummer
            building_data = self._bbr_building_lookup(husnummer_id, address)
            if not building_data:
                print("❌ Kunne ikke hente bygningsdata fra BBR")
                return None
            
            print(f"✅ Bygningsdata hentet succesfuldt")
            return building_data
            
        except Exception as e:
            print(f"❌ Fejl ved hentning af bygningsdata: {e}")
            return None
    
    def get_building_data_by_id(self, building_id: str, address: str = "") -> Optional[BuildingData]:
        """
        Get building data directly by BBR building ID.
        
        Args:
            building_id: BBR building ID
            address: Optional address for context
            
        Returns:
            BuildingData object or None if not found
        """
        try:
            print(f"🔍 Henter bygningsdata med ID: {building_id}")
            
            building_url = f"{self.bbr_base_url}/BBR/BBRPublic/1/rest/bygning"
            params = {
                'id': building_id,
                'username': self.bbr_username,
                'password': self.bbr_password,
                'Format': 'JSON'
            }
            
            response = self.session.get(building_url, params=params)
            response.raise_for_status()
            
            building_data = response.json()
            
            if building_data and len(building_data) > 0:
                print(f"✅ Fandt bygningsdata")
                return self._parse_building_data_enhanced(building_data, address or f"BBR ID: {building_id}")
            else:
                print("❌ Ingen bygningsdata fundet")
                return None
                
        except Exception as e:
            print(f"❌ BBR building lookup by ID failed: {e}")
            return None
    
    def _dawa_address_lookup(self, address: str) -> Optional[str]:
        """Look up address in DAWA to get husnummer ID."""
        try:
            cleaned_address = address.strip()
            
            url = f"{self.dawa_base_url}/adresser/autocomplete"
            params = {
                'q': cleaned_address,
                'type': 'adresse',
                'caretpos': len(cleaned_address),
                'fuzzy': 'true'
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            addresses = response.json()
            
            if not addresses:
                print(f"⚠️  Ingen adresser fundet for: {address}")
                return None
            
            best_match = addresses[0]
            address_id = best_match['adresse']['id']
            
            detail_url = f"{self.dawa_base_url}/adresser/{address_id}"
            detail_response = self.session.get(detail_url)
            detail_response.raise_for_status()
            
            address_details = detail_response.json()
            husnummer_id = address_details.get('adgangsadresse', {}).get('id')
            
            if husnummer_id:
                print(f"📍 Fandt adresse: {address_details.get('betegnelse', address)}")
            
            return husnummer_id
            
        except Exception as e:
            print(f"❌ DAWA API fejl: {e}")
            return None
    
    def _bbr_building_lookup(self, husnummer_id: str, original_address: str) -> Optional[BuildingData]:
        """BBR building lookup using husnummer ID."""
        try:
            print("🔍 Henter bygningsdata direkte fra BBR...")
            
            building_url = f"{self.bbr_base_url}/BBR/BBRPublic/1/rest/bygning"
            building_params = {
                'Husnummer': husnummer_id,
                'username': self.bbr_username,
                'password': self.bbr_password,
                'Format': 'JSON'
            }
            
            response = self.session.get(building_url, params=building_params)
            response.raise_for_status()
            
            building_data = response.json()
            
            if building_data and len(building_data) > 0:
                print(f"✅ Fandt {len(building_data)} bygning(er)")
                return self._parse_building_data_enhanced(building_data, original_address)
            else:
                print("❌ Ingen bygningsdata fundet")
                return None
                
        except Exception as e:
            print(f"❌ BBR building lookup failed: {e}")
            return None
    
    def _parse_building_data_enhanced(self, buildings: List[Dict], address: str) -> BuildingData:
        """
        Enhanced parser for BBR building data based on actual JSON structure.
        """
        # Take first building as primary
        primary = buildings[0] if buildings else {}
        
        building_data = BuildingData(address=address)
        
        # Basic building information using CORRECT field names from actual API
        building_data.building_number = primary.get('byg007Bygningsnummer')
        building_data.building_year = primary.get('byg026Opførelsesår')
        building_data.renovation_year = primary.get('byg027OmTilbygningsår')
        building_data.building_type_code = primary.get('byg021BygningensAnvendelse')
        building_data.building_type = self._translate_building_type(building_data.building_type_code)
        
        # Materials with codes
        building_data.exterior_material_code = primary.get('byg032YdervæggensMateriale')
        building_data.exterior_material = self._translate_material(building_data.exterior_material_code)
        building_data.roof_material_code = primary.get('byg033Tagdækningsmateriale')
        building_data.roof_material = self._translate_material(building_data.roof_material_code)
        building_data.material_source = self._translate_material_source(primary.get('byg037KildeTilBygningensMaterialer'))
        
        # Areas - using CORRECT field names
        building_data.total_building_area = primary.get('byg038SamletBygningsareal')
        building_data.total_residential_area = primary.get('byg039BygningensSamledeBoligAreal')
        building_data.total_commercial_area = primary.get('byg040BygningensSamledeErhvervsAreal')
        building_data.built_area = primary.get('byg041BebyggetAreal')
        
        # Structure
        building_data.floors = primary.get('byg054AntalEtager')
        building_data.deviating_floors = primary.get('byg055AfvigendeEtager')
        
        # Heating
        building_data.heating_code = primary.get('byg056Varmeinstallation')
        building_data.heating_type = self._translate_heating(building_data.heating_code)
        
        # Administrative data
        building_data.municipality_code = primary.get('kommunekode')
        building_data.plot_id = primary.get('jordstykke')
        building_data.ground_id = primary.get('grund')
        building_data.revision_date = primary.get('byg094Revisionsdato')
        
        # Coordinate information
        building_data.coordinate = primary.get('byg404Koordinat')
        building_data.coordinate_system = primary.get('byg406Koordinatsystem')
        
        # Data source information
        building_data.data_source_code = primary.get('byg053BygningsarealerKilde')
        building_data.data_source = "BBR (Bygnings- og Boligregistret)"
        building_data.confidence_level = "høj"
        building_data.last_updated = primary.get('datafordelerOpdateringstid', '')
        
        # Parse floor information (etageList) - this is where we get basement/attic areas
        if 'etageList' in primary and primary['etageList']:
            building_data.floor_details = self._parse_floor_details(primary['etageList'])
            
            # Extract basement and attic areas from floor details
            for floor in building_data.floor_details:
                if floor['type_code'] == '2':  # Basement
                    if floor.get('basement_area'):
                        building_data.basement_area = floor['basement_area']
                    if floor.get('commercial_area'):
                        building_data.basement_commercial_area = floor['commercial_area']
                elif floor['type_code'] == '1':  # Attic
                    if floor.get('attic_area'):
                        building_data.attic_area = floor['attic_area']
        
        # Parse entrance information (opgangList) - this gives us elevator info
        if 'opgangList' in primary and primary['opgangList']:
            building_data.entrances, building_data.access_from_addresses = self._parse_entrance_details(primary['opgangList'])
            
            # Check for elevators
            elevators = [e for e in building_data.entrances if e.get('has_elevator', False)]
            building_data.has_elevator = len(elevators) > 0
            building_data.elevator_count = len(elevators) if elevators else None
        
        # Handle additional buildings if multiple buildings found
        if len(buildings) > 1:
            for building in buildings[1:]:  # Skip first (primary) building
                additional = {
                    'building_number': building.get('byg007Bygningsnummer'),
                    'type': self._translate_building_type(building.get('byg021BygningensAnvendelse')),
                    'type_code': building.get('byg021BygningensAnvendelse'),
                    'year': building.get('byg026Opførelsesår'),
                    'area': building.get('byg038SamletBygningsareal'),
                    'material': self._translate_material(building.get('byg032YdervæggensMateriale')),
                    'material_code': building.get('byg032YdervæggensMateriale')
                }
                building_data.additional_buildings.append(additional)
        
        # Store raw data for debugging
        building_data.raw_bbr_data = {'buildings': buildings}
        
        return building_data
    
    def _parse_floor_details(self, etage_list: List[Dict]) -> List[Dict]:
        """Parse detailed floor information from etageList."""
        floors = []
        
        for etage_item in etage_list:
            if 'etage' in etage_item:
                etage = etage_item['etage']
                
                floor_info = {
                    'id': etage.get('id_lokalId'),
                    'designation': etage.get('eta006BygningensEtagebetegnelse'),
                    'type_code': etage.get('eta025Etagetype'),
                    'type_name': self._translate_floor_type(etage.get('eta025Etagetype')),
                    'total_area': etage.get('eta020SamletArealAfEtage'),
                    'attic_area': etage.get('eta021ArealAfUdnyttetDelAfTagetage'),
                    'basement_area': etage.get('eta022Kælderareal'),
                    'commercial_area': etage.get('eta026ErhvervIKælder'),
                    'last_updated': etage.get('datafordelerOpdateringstid')
                }
                
                floors.append(floor_info)
        
        return floors
    
    def _parse_entrance_details(self, opgang_list: List[Dict]) -> tuple[List[Dict], List[str]]:
        """Parse entrance information from opgangList."""
        entrances = []
        access_addresses = []
        
        for opgang_item in opgang_list:
            if 'opgang' in opgang_item:
                opgang = opgang_item['opgang']
                
                entrance_info = {
                    'id': opgang.get('id_lokalId'),
                    'access_from_address': opgang.get('adgangFraHusnummer'),
                    'has_elevator': opgang.get('opg020Elevator') == '1',
                    'last_updated': opgang.get('datafordelerOpdateringstid')
                }
                
                entrances.append(entrance_info)
                
                # Collect unique access addresses
                address_id = opgang.get('adgangFraHusnummer')
                if address_id and address_id not in access_addresses:
                    access_addresses.append(address_id)
        
        return entrances, access_addresses
    
    def _translate_building_type(self, code: Any) -> str:
        """Enhanced building type translation."""
        if not code:
            return "Ukendt bygningstype"
        
        translations = {
            '110': 'Fritliggende enfamiliehus',
            '120': 'Fritliggende enfamiliehus',
            '130': 'Dobbelthus/kædehus',
            '140': 'Rækkehus',
            '150': 'Etageboligbebyggelse',
            '160': 'Kollegium',
            '190': 'Anden bygning til helårsbeboelse',
            '210': 'Sommerhus',
            '220': 'Anden bygning til fritidsbeboelse',
            '510': 'Bygning til kontor/administration',
            '520': 'Bygning til handel/service',
            '530': 'Bygning til industri/produktion',
            '540': 'Bygning til hotel/restaurant',
            '550': 'Bygning til transport/kommunikation',
            '560': 'Bygning til undervisning/forskning',
            '570': 'Bygning til sundhed/social',
            '580': 'Bygning til kultur/fritid',
            '590': 'Anden bygning til erhverv',
            '910': 'Garage/carport',
            '920': 'Udhus',
            '930': 'Drivhus',
            '940': 'Anden bygning til landbrug',
        }
        
        code_str = str(code)
        return translations.get(code_str, f"Bygningstype {code_str}")
    
    def _translate_material(self, code: Any) -> str:
        """Enhanced material translation."""
        if not code:
            return ""
        
        translations = {
            '1': 'Mursten',
            '2': 'Kalksandsten',
            '3': 'Letbeton',
            '4': 'Gasbeton',
            '5': 'Beton',
            '6': 'Træ',
            '7': 'Metal',
            '8': 'Andet materiale',
            '9': 'Uoplyst materiale',
            '10': 'Fibercement (herunder asbest)',
            '11': 'Tagpap',
            '12': 'Betontagsten',
            '13': 'Tegl',
            '14': 'Skifer',
            '15': 'Fibercement tagplader',
            '16': 'Plastmaterialer',
            '17': 'Metal tagplader',
            '18': 'Glas',
            '19': 'Andet tagdækningsmateriale',
            '20': 'Strå/rør',
        }
        
        code_str = str(code)
        return translations.get(code_str, f"Materiale {code_str}")
    
    def _translate_heating(self, code: Any) -> str:
        """Enhanced heating translation."""
        if not code:
            return ""
        
        translations = {
            '1': 'Fjernvarme/blokvarme',
            '2': 'Centralvarme/etagevarme',
            '3': 'Ovne (til fast brændsel)',
            '4': 'Varmepumpe',
            '5': 'Elektrisk opvarmning',
            '6': 'Gasradiatorer',
            '7': 'Andet',
            '8': 'Ingen opvarmning',
            '9': 'Uoplyst',
        }
        
        code_str = str(code)
        return translations.get(code_str, f"Varme {code_str}")
    
    def _translate_floor_type(self, code: Any) -> str:
        """Translate floor type codes."""
        if not code:
            return ""
        
        translations = {
            '0': 'Normal etage',
            '1': 'Tagetage',
            '2': 'Kælder',
            '3': 'Tekniketage',
        }
        
        code_str = str(code)
        return translations.get(code_str, f"Etagetype {code_str}")
    
    def _translate_material_source(self, code: Any) -> str:
        """Translate material source codes."""
        if not code:
            return ""
        
        translations = {
            '1': 'BBR registrering',
            '2': 'Byggesagsbehandling',
            '3': 'Anden kilde',
            '4': 'Uoplyst',
        }
        
        code_str = str(code)
        return translations.get(code_str, f"Kilde {code_str}")


def test_bbr_service():
    """Test function for BBR service."""
    # Load credentials from environment
    username = os.getenv('DATAFORDELER_NO_CERT_USERNAME')
    password = os.getenv('DATAFORDELER_NO_CERT_PASSWORD')
    
    if not username or not password:
        print("❌ Mangler DATAFORDELER credentials i environment")
        return
    
    service = BBRAddressService(username, password)
    
    # Test with your known working address
    test_address = "Langebrogade 3, 1411 København K"
    
    print(f"\n{'='*60}")
    print(f"Testing Enhanced BBR Service: {test_address}")
    print('='*60)
    
    building_data = service.get_building_data(test_address)
    
    if building_data:
        print("\n" + building_data.get_summary())
        print(f"\n📊 Complete Data Dictionary:")
        data_dict = building_data.to_dict()
        for key, value in data_dict.items():
            if value is not None and value != "" and value != []:
                print(f"  {key}: {value}")
        
        # Test direct ID lookup if we have the building ID
        if building_data.raw_bbr_data and building_data.raw_bbr_data.get('buildings'):
            building_id = building_data.raw_bbr_data['buildings'][0].get('id_lokalId')
            if building_id:
                print(f"\n🔍 Testing direct ID lookup: {building_id}")
                id_result = service.get_building_data_by_id(building_id, test_address)
                if id_result:
                    print("✅ Direct ID lookup successful")
                else:
                    print("❌ Direct ID lookup failed")
    else:
        print("❌ Ingen data fundet")


if __name__ == "__main__":
    test_bbr_service()