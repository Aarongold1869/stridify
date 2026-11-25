#!/usr/bin/env python
import os
import django
import requests

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stridify.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken

print("=" * 70)
print("SPOTIFY RE-AUTHENTICATION FLOW")
print("=" * 70)
print()

# Step 1: Ensure user exists
user, created = User.objects.get_or_create(
    username='user_session',
    defaults={
        'email': 'user_session@stridify.local',
        'first_name': 'Test',
    }
)

if created:
    user.set_password('password123')
    user.save()
    print("[+] Created user: user_session")
else:
    print("[+] User exists: user_session")

print()

# Step 2: Get JWT token
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)

print("[+] JWT Access Token obtained:")
print(f"    {access_token[:50]}...")
print()

# Step 3: Call Spotify login endpoint
print("Fetching Spotify auth URL...")

headers = {
    'Authorization': f'Bearer {access_token}',
    'Content-Type': 'application/json',
}

# Try both localhost and ngrok
urls = [
    'http://localhost:8000/api/v1/auth/spotify/login/',
    'https://endowment-sleep-starting.ngrok-free.dev/api/v1/auth/spotify/login/',
]

auth_url = None
for url in urls:
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        if response.status_code == 200:
            data = response.json()
            auth_url = data.get('auth_url')
            print(f"[+] Got auth URL from {url}")
            break
    except Exception as e:
        print(f"[-] Failed {url}: {e}")

if auth_url:
    print()
    print("=" * 70)
    print("NEXT STEP: Click this link to authenticate with Premium Spotify")
    print("=" * 70)
    print()
    print(auth_url)
    print()
    print("After you authorize, you'll be redirected back.")
    print("Then run this to test audio features:")
    print()
    print("""python manage.py shell << 'EOF'
from django.contrib.auth.models import User
from music.services.spotify_service import SpotifyService

user = User.objects.get(username='user_session')
auth = user.spotify_auth

service = SpotifyService(access_token=auth.access_token)
features = service.get_track_audio_features("11dFghVv5Yorp6AHgGeQiP")

if features:
    print(f"SUCCESS! Audio features: {features['bpm']} BPM")
else:
    print("FAILED: Still getting 403")
EOF""")
else:
    print("[ERROR] Could not get auth URL from any endpoint")
