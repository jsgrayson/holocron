import os
import psycopg2
import json
from datetime import datetime

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL not set. SQL ingestion skipped.")
        return None
    return psycopg2.connect(db_url)

def ingest_reputations(data):
    """
    Ingest DataStore_Reputations data into SQL
    """
    conn = get_db_connection()
    if not conn: return
    
    try:
        cur = conn.cursor()
        
        # DataStore structure: global.Characters[GUID].Factions[FactionID]
        db_global = data.get("global", {})
        characters = db_global.get("Characters", {})
        
        for char_key, char_data in characters.items():
            # char_key is usually "Account.Realm.Name" or similar in DataStore
            # We need to extract a GUID or use the key as a proxy
            # DataStore often stores the real GUID inside the character data or we have to infer it
            # For now, we'll assume char_key is the identifier we use
            
            factions = char_data.get("Factions", {})
            last_update = char_data.get("lastUpdate", datetime.now())
            
            for faction_id_str, rep_data in factions.items():
                faction_id = int(faction_id_str)
                
                # Extract values
                current_rep = 0
                if isinstance(rep_data, dict):
                    current_rep = rep_data.get("earned", 0)
                elif isinstance(rep_data, list) and len(rep_data) > 1:
                    current_rep = rep_data[1]
                
                # Insert into history
                # We might want to avoid duplicates if nothing changed, but for now log everything
                cur.execute("""
                    INSERT INTO diplomat.reputation_history 
                    (character_guid, faction_id, reputation_amount, timestamp)
                    VALUES (%s, %s, %s, NOW())
                """, (char_key, faction_id, current_rep))
                
        conn.commit()
        cur.close()
        conn.close()
        print(f"✓ Ingested reputation data for {len(characters)} characters")
        
    except Exception as e:
        print(f"Error ingesting reputations: {e}")
        if conn: conn.close()

def ingest_saved_instances(data):
    """
    Ingest SavedInstances data into SQL (Pathfinder/Vault)
    """
    conn = get_db_connection()
    if not conn: return
    
    try:
        cur = conn.cursor()
        
        # SavedInstances structure: DB.Toons[Key]
        db = data.get("DB", {})
        toons = db.get("Toons", {})
        
        for toon_key, info in toons.items():
            # toon_key is "Realm - Name"
            # We need to map this to a GUID if possible, or store as is
            
            zone = info.get("Zone", "Unknown")
            level = info.get("Level", 0)
            race = info.get("Race", "")
            cls = info.get("Class", "")
            
            # Update Character Info (Upsert)
            # We need a characters table. holocron.characters?
            # Let's check schema.
            
            # For now, let's just log the location update if we have a table for it
            # Or just update the character record
            
            # Assuming holocron.characters exists
            # We'll try to update it
            
            # Extract Name and Realm from key
            if " - " in toon_key:
                realm, name = toon_key.split(" - ", 1)
            else:
                realm, name = "Unknown", toon_key
                
            # Generate a pseudo-GUID if we don't have one (SavedInstances doesn't always give GUID)
            # But we can try to match by name/realm
            
            cur.execute("""
                INSERT INTO holocron.characters (name, realm, class, level, last_seen_zone, last_updated)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (name, realm) DO UPDATE SET
                    level = EXCLUDED.level,
                    last_seen_zone = EXCLUDED.last_seen_zone,
                    last_updated = NOW()
            """, (name, realm, cls, level, zone))
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"✓ Ingested SavedInstances for {len(toons)} characters")
        
    except Exception as e:
        print(f"Error ingesting SavedInstances: {e}")
        if conn: conn.close()
