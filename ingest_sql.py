import os
import sqlite3
import json
from datetime import datetime
from lua_parser import parse_lua_table

# Configuration
WTF_PATH = "/Applications/World of Warcraft/_retail_/WTF/Account/NIGHTHWK77/SavedVariables"
DB_FILE = "/Users/jgrayson/Documents/holocron/holocron.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Initialize SQLite database with schema.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Characters
    cur.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            character_guid TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            realm TEXT NOT NULL,
            class TEXT,
            level INTEGER,
            last_seen_zone TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, realm)
        )
    """)
    
    # 2. Reputation History (Diplomat)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reputation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_guid TEXT,
            faction_id INTEGER,
            reputation_amount INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 3. Gear
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gear (
            character_guid TEXT,
            slot_id INTEGER,
            item_id INTEGER,
            item_level INTEGER,
            item_link TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (character_guid, slot_id)
        )
    """)
    
    # 4. Professions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS professions (
            character_guid TEXT,
            profession_id INTEGER,
            profession_name TEXT,
            skill_level INTEGER,
            max_skill INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (character_guid, profession_id)
        )
    """)
    
    # 5. Recipes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            character_guid TEXT,
            recipe_id INTEGER,
            profession_id INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (character_guid, recipe_id)
        )
    """)

    # 6. Inventory (DeepPockets)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            character_guid TEXT,
            item_id INTEGER,
            count INTEGER,
            location TEXT,
            link TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            -- No primary key as we can have multiple stacks of same item
        )
    """)

    conn.commit()
    conn.close()
    print("✓ Database initialized (SQLite)")

def ingest_all():
    """
    Main entry point for ingestion.
    """
    print(f"--- Starting Data Ingestion (SQLite: {DB_FILE}) ---")
    init_db()
    
    # 1. Ingest Reputations (Diplomat)
    rep_file = os.path.join(WTF_PATH, "DataStore_Reputations.lua")
    if os.path.exists(rep_file):
        print(f"Parsing {rep_file}...")
        data = parse_lua_table(rep_file)
        ingest_reputations(data)
    else:
        print(f"Skipping Reputations: {rep_file} not found.")

    # 2. Ingest SavedInstances (Pathfinder)
    inst_file = os.path.join(WTF_PATH, "SavedInstances.lua")
    if os.path.exists(inst_file):
        print(f"Parsing {inst_file}...")
        data = parse_lua_table(inst_file)
        ingest_saved_instances(data)
    else:
        print(f"Skipping SavedInstances: {inst_file} not found.")
        
    # 3. Ingest Inventory (DeepPockets)
    dp_file = os.path.join(WTF_PATH, "DeepPockets.lua")
    if os.path.exists(dp_file):
        print(f"Parsing {dp_file}...")
        data = parse_lua_table(dp_file)
        ingest_inventory(data)
    else:
        print(f"Skipping Inventory: {dp_file} not found.")

def ingest_reputations(data):
    """
    Ingest DataStore_Reputations data into SQL
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # DataStore structure: global.Characters[GUID].Factions[FactionID]
        db_global = data.get("global", {})
        characters = db_global.get("Characters", {})
        
        for char_key, char_data in characters.items():
            factions = char_data.get("Factions", {})
            
            for faction_id_str, rep_data in factions.items():
                faction_id = int(faction_id_str)
                
                # Extract values
                current_rep = 0
                if isinstance(rep_data, dict):
                    current_rep = rep_data.get("earned", 0)
                elif isinstance(rep_data, list) and len(rep_data) > 1:
                    current_rep = rep_data[1]
                
                cur.execute("""
                    INSERT INTO reputation_history 
                    (character_guid, faction_id, reputation_amount, timestamp)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (char_key, faction_id, current_rep))
                
        conn.commit()
        print(f"✓ Ingested reputation data for {len(characters)} characters")
        
    except Exception as e:
        print(f"Error ingesting reputations: {e}")
    finally:
        conn.close()

def ingest_saved_instances(data):
    """
    Ingest SavedInstances data into SQL (Pathfinder/Vault)
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # SavedInstances structure: DB.Toons[Key]
        toons = data.get("Toons", {}) 
        if not toons:
            toons = data.get("DB", {}).get("Toons", {})
        
        for toon_key, info in toons.items():
            zone = info.get("Zone", "Unknown")
            level = info.get("Level", 0)
            cls = info.get("Class", "")
            
            # Extract Name and Realm from key
            if " - " in toon_key:
                realm, name = toon_key.split(" - ", 1)
            else:
                realm, name = "Unknown", toon_key
                
            # Upsert Character
            cur.execute("""
                INSERT INTO characters (name, realm, class, level, last_seen_zone, last_updated)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name, realm) DO UPDATE SET
                    level = excluded.level,
                    last_seen_zone = excluded.last_seen_zone,
                    last_updated = CURRENT_TIMESTAMP
            """, (name, realm, cls, level, zone))
            
        conn.commit()
        print(f"✓ Ingested SavedInstances for {len(toons)} characters")
        
    except Exception as e:
        print(f"Error ingesting SavedInstances: {e}")
    finally:
        conn.close()

def ingest_inventory(data):
    """
    Ingest DeepPockets inventory data.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Structure: global.Inventory[CharacterKey] = [ {id, count, loc, link}, ... ]
        db_global = data.get("global", {})
        inventory = db_global.get("Inventory", {})
        
        # Clear old inventory data? Or timestamp it?
        # For now, let's clear to avoid duplicates on re-ingest
        cur.execute("DELETE FROM inventory")
        
        count = 0
        for char_key, items in inventory.items():
            # char_key is "Name - Realm"
            # We ideally want GUID, but we might not have it here. 
            # We can use the Name-Realm as a proxy or look it up if we had a mapping.
            # For now, store Name-Realm as GUID or lookup from characters table?
            # Let's just use char_key as the identifier for now.
            
            for item in items:
                item_id = item.get("id")
                stack_count = item.get("count", 1)
                loc = item.get("loc", "Bag")
                link = item.get("link", "")
                
                cur.execute("""
                    INSERT INTO inventory (character_guid, item_id, count, location, link, last_updated)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (char_key, item_id, stack_count, loc, link))
                count += 1
                
        conn.commit()
        print(f"✓ Ingested {count} inventory items for {len(inventory)} characters")
        
    except Exception as e:
        print(f"Error ingesting inventory: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    ingest_all()
