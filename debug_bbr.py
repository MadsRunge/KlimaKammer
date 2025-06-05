#!/usr/bin/env python3
"""
BBR Debug Script - Comprehensive debugging of BBR API issues
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_bbr_connection():
    """Comprehensive BBR API debugging."""
    
    username = os.getenv('DATAFORDELER_NO_CERT_USERNAME')
    password = os.getenv('DATAFORDELER_NO_CERT_PASSWORD')
    
    print("🔧 BBR API DEBUGGING")
    print("=" * 50)
    
    if not username or not password:
        print("❌ Missing credentials in .env file")
        print("Need: DATAFORDELER_NO_CERT_USERNAME and DATAFORDELER_NO_CERT_PASSWORD")
        return
    
    print(f"🔑 Username: {username[:10]}...")
    print(f"🔑 Password: {'*' * len(password)}")
    
    session = requests.Session()
    session.timeout = 30
    
    # Test husnummer ID from previous run
    husnummer_id = "0a3f507b-2321-32b8-e044-0003ba298018"
    base_url = "https://services.datafordeler.dk"
    
    # Test different BBR endpoints
    endpoints = {
        'grund': f"{base_url}/BBR/BBRPublic/1/rest/grund",
        'bygning': f"{base_url}/BBR/BBRPublic/1/rest/bygning", 
        'enhed': f"{base_url}/BBR/BBRPublic/1/rest/enhed",
        'technical': f"{base_url}/BBR/BBRPublic/1/rest/tekniskanlæg"
    }
    
    for name, url in endpoints.items():
        print(f"\n🔍 Testing {name.upper()} endpoint...")
        print(f"URL: {url}")
        
        # Try different parameter combinations
        param_variations = [
            {'Husnummer': husnummer_id},
            {'HusnummerIdList': husnummer_id},
            {'Id': husnummer_id},
            {'AdgangsadresseId': husnummer_id}
        ]
        
        for i, base_params in enumerate(param_variations):
            params = {
                **base_params,
                'username': username,
                'password': password,
                'Format': 'JSON'
            }
            
            try:
                print(f"  Variation {i+1}: {list(base_params.keys())[0]}")
                response = session.get(url, params=params)
                
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"    ✅ JSON response received")
                        print(f"    Type: {type(data)}")
                        
                        if isinstance(data, list):
                            print(f"    Length: {len(data)}")
                            if len(data) > 0:
                                print(f"    🎯 SUCCESS! Found data in {name}")
                                print(f"    Sample keys: {list(data[0].keys())[:5]}")
                                return True
                        elif isinstance(data, dict):
                            print(f"    Keys: {list(data.keys())[:5]}")
                            if data:
                                print(f"    🎯 SUCCESS! Found data in {name}")
                                return True
                        else:
                            print(f"    Unexpected data type: {type(data)}")
                            
                    except json.JSONDecodeError:
                        print(f"    ❌ Invalid JSON response")
                        print(f"    Response: {response.text[:200]}...")
                        
                elif response.status_code == 401:
                    print(f"    ❌ Authentication failed - check credentials")
                elif response.status_code == 403:
                    print(f"    ❌ Access forbidden - check permissions")
                elif response.status_code == 404:
                    print(f"    ⚠️  Endpoint not found")
                else:
                    print(f"    ❌ HTTP Error: {response.text[:200]}...")
                    
            except requests.exceptions.RequestException as e:
                print(f"    ❌ Request failed: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 CREDENTIAL VERIFICATION")
    
    # Test simple authentication
    auth_test_url = f"{base_url}/BBR/BBRPublic/1/rest/grund"
    params = {
        'username': username,
        'password': password,
        'Format': 'JSON',
        'Husnummer': husnummer_id
    }
    
    try:
        response = session.get(auth_test_url, params=params)
        print(f"Auth test status: {response.status_code}")
        print(f"Auth test headers: {dict(response.headers)}")
        
        if response.status_code == 401:
            print("❌ CREDENTIALS INVALID - Check your Datafordeler account")
        elif response.status_code == 403:
            print("❌ ACCOUNT LACKS BBR PERMISSIONS - Contact Datafordeler support")
        elif response.status_code == 200:
            print("✅ CREDENTIALS OK - Issue is with data availability")
        
    except Exception as e:
        print(f"❌ Auth test failed: {e}")
    
    return False

def test_alternative_apis():
    """Test alternative data sources."""
    print("\n🔄 TESTING ALTERNATIVE APPROACHES")
    print("=" * 50)
    
    # Test DAWA building endpoint
    print("🏠 Testing DAWA buildings...")
    try:
        dawa_url = "https://api.dataforsyningen.dk/bygninger"
        params = {
            'husnummer': "0a3f507b-2321-32b8-e044-0003ba298018",
            'format': 'json'
        }
        
        response = requests.get(dawa_url, params=params)
        print(f"DAWA buildings status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"DAWA buildings found: {len(data)}")
            if data:
                print("✅ DAWA has building data - can use as fallback")
                return True
        
    except Exception as e:
        print(f"DAWA test failed: {e}")
    
    return False

if __name__ == "__main__":
    success = test_bbr_connection()
    if not success:
        test_alternative_apis()
    
    print("\n💡 NEXT STEPS:")
    if not success:
        print("1. Verify your Datafordeler credentials")
        print("2. Check if your account has BBR access permissions") 
        print("3. Consider using DAWA buildings as fallback")
        print("4. Contact Datafordeler support if needed")
    else:
        print("✅ BBR connection works - update your code with working parameters")