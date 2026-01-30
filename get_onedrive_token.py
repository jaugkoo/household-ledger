"""
OneDrive Authentication Helper
This script helps you get a refresh token for OneDrive API access.
"""

import webbrowser
from urllib.parse import urlencode, parse_qs, urlparse
import requests

print("=== OneDrive Authentication Helper ===\n")

# Step 1: Get credentials
client_id = input("Enter your Client ID: ").strip()
client_secret = input("Enter your Client Secret: ").strip()

# Step 2: Build authorization URL
auth_params = {
    'client_id': client_id,
    'response_type': 'code',
    'redirect_uri': 'http://localhost',
    'response_mode': 'query',
    'scope': 'Files.Read.All offline_access'
}

auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(auth_params)}"

print("\n1. Opening browser for authentication...")
print("2. Sign in and grant permissions")
print("3. You'll be redirected to localhost (page won't load - that's OK!)")
print("4. Copy the ENTIRE URL from your browser address bar\n")

webbrowser.open(auth_url)

# Step 3: Get authorization code
redirect_url = input("\nPaste the full redirect URL here: ").strip()

try:
    parsed = urlparse(redirect_url)
    code = parse_qs(parsed.query)['code'][0]
    print(f"\n✓ Authorization code received: {code[:20]}...")
except:
    print("\n✗ Failed to parse URL. Make sure you copied the full URL.")
    exit(1)

# Step 4: Exchange code for tokens
token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
token_data = {
    'client_id': client_id,
    'client_secret': client_secret,
    'code': code,
    'redirect_uri': 'http://localhost',
    'grant_type': 'authorization_code'
}

print("\nExchanging code for tokens...")
response = requests.post(token_url, data=token_data)

if response.status_code == 200:
    tokens = response.json()
    refresh_token = tokens.get('refresh_token')
    
    print("\n" + "="*50)
    print("SUCCESS! Add this to your .env file:")
    print("="*50)
    print(f"\nONEDRIVE_CLIENT_ID={client_id}")
    print(f"ONEDRIVE_CLIENT_SECRET={client_secret}")
    print(f"ONEDRIVE_TENANT_ID=common")
    print(f"ONEDRIVE_REFRESH_TOKEN={refresh_token}")
    print("\n" + "="*50)
else:
    print(f"\n✗ Error: {response.status_code}")
    print(response.text)
