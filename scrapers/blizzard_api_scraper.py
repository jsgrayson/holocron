#!/usr/bin/env python3
"""
Blizzard API Encounter Scraper
Gets official encounter journal data from Blizzard's Game Data API
"""

import requests
import json
import time

class BlizzardAPIClient:
    """
    Client for Blizzard's WoW Game Data API
    Docs: https://develop.battle.net/documentation/world-of-warcraft/game-data-apis
    """
    
    def __init__(self, client_id, client_secret, region='us'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region
        self.token = None
        self.token_expires = 0
        
    def get_access_token(self):
        """Get OAuth access token"""
        if self.token and time.time() < self.token_expires:
            return self.token
            
        url = f"https://{self.region}.battle.net/oauth/token"
        response = requests.post(
            url,
            data={'grant_type': 'client_credentials'},
            auth=(self.client_id, self.client_secret)
        )
        response.raise_for_status()
        
        data = response.json()
        self.token = data['access_token']
        self.token_expires = time.time() + data['expires_in'] - 60  # 60s buffer
        
        return self.token
    
    def get_journal_instance(self, instance_id):
        """
        Get instance data from encounter journal
        Args:
            instance_id: e.g., 1273 for Nerub-ar Palace
        """
        token = self.get_access_token()
        url = f"https://{self.region}.api.blizzard.com/data/wow/journal-instance/{instance_id}"
        
        response = requests.get(
            url,
            params={
                'namespace': f'static-{self.region}',
                'locale': 'en_US',
                'access_token': token
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_journal_encounter(self, encounter_id):
        """
        Get encounter details
        Args:
            encounter_id: e.g., 2922 for Queen Ansurek
        """
        token = self.get_access_token()
        url = f"https://{self.region}.api.blizzard.com/data/wow/journal-encounter/{encounter_id}"
        
        response = requests.get(
            url,
            params={
                'namespace': f'static-{self.region}',
                'locale': 'en_US',
                'access_token': token
            }
        )
        response.raise_for_status()
        return response.json()

# Example usage (requires credentials)
if __name__ == "__main__":
    # You'll need to create an app at https://develop.battle.net/
    # and get your CLIENT_ID and CLIENT_SECRET
    
    CLIENT_ID = "YOUR_CLIENT_ID"
    CLIENT_SECRET = "YOUR_CLIENT_SECRET"
    
    if CLIENT_ID == "YOUR_CLIENT_ID":
        print("Please set your Blizzard API credentials first!")
        print("1. Go to https://develop.battle.net/")
        print("2. Create an application")
        print("3. Get your Client ID and Secret")
        print("4. Update this script with your credentials")
    else:
        client = BlizzardAPIClient(CLIENT_ID, CLIENT_SECRET)
        
        # Example: Get Nerub-ar Palace (instance ID 1273)
        instance = client.get_journal_instance(1273)
        print(json.dumps(instance, indent=2))
        
        # Example: Get Queen Ansurek encounter (encounter ID 2922)
        encounter = client.get_journal_encounter(2922)
        print(json.dumps(encounter, indent=2))
