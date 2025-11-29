#!/usr/bin/env python3
"""
Utility Tracker - Mount, Toy, and Spell Collection Progress
Tracks collectibles and shows completion percentages
"""

from typing import List, Dict
from dataclasses import dataclass
from enum import Enum

class CollectionType(Enum):
    MOUNT = "Mount"
    TOY = "Toy"
    SPELL = "Spell"
    PET = "Battle Pet"

@dataclass
class Collectible:
    item_id: int
    name: str
    collection_type: CollectionType
    source: str  # "Raid", "Dungeon", "Achievement", "Vendor", "Rare Drop"
    difficulty: str  # "Easy", "Medium", "Hard", "Very Hard"
    expansion: str
    
from utils.lua_parser import LuaParser
import os
import glob

class UtilityTracker:
    """Tracks mount, toy, and spell collections"""
    
    def __init__(self):
        self.all_collectibles = []
        self.owned = set()
        self.lua_parser = LuaParser()
        
    def load_real_data(self):
        """Load real collection data from DataStore_Mounts/Pets"""
        print("Loading real collection data...")
        
        # 1. Find SavedVariables path (reuse logic or config)
        possible_paths = [
            os.environ.get('WOW_SAVED_VARIABLES_PATH'),
            os.path.expanduser("~/Documents/holocron/SavedVariables"),
            "/Applications/World of Warcraft/_retail_/WTF/Account/*/SavedVariables",
            "C:/Program Files (x86)/World of Warcraft/_retail_/WTF/Account/*/SavedVariables"
        ]
        
        sv_path = None
        for path_pattern in possible_paths:
            if not path_pattern: continue
            matches = glob.glob(os.path.join(path_pattern, "DataStore_Mounts.lua"))
            if matches:
                sv_path = os.path.dirname(matches[0])
                break
                
        if not sv_path:
            print("Could not find SavedVariables. Falling back to mock data.")
            self.load_mock_data()
            return

        # 2. Load Mounts
        self._load_mounts(sv_path)
        
        # 3. Load Pets (if available)
        self._load_pets(sv_path)
        
        print(f"✓ Loaded {len(self.all_collectibles)} collectibles, {len(self.owned)} owned")
        
    def _load_mounts(self, sv_path):
        mount_file = os.path.join(sv_path, "DataStore_Mounts.lua")
        data = self.lua_parser.parse_file(mount_file, "DataStore_MountsDB")
        
        if not data: return
        
        # Structure: global.Characters[GUID].Mounts (list of IDs)
        # Or global.Account.Mounts? DataStore usually stores mounts account-wide now.
        # Let's check global.Account or iterate characters.
        
        # DataStore_Mounts usually has a global table for account-wide mounts
        # But structure varies. Let's assume we aggregate all unique IDs found.
        
        try:
            db_global = data.get("global", {})
            # Check for Account-wide mounts
            # Often in "Global" or "Account" key, or we just union all characters
            
            # For simplicity, let's look at the first character or iterate all
            characters = db_global.get("Characters", {})
            
            for char_key, char_data in characters.items():
                mounts = char_data.get("Mounts", [])
                # mounts might be a list of IDs or a bitmask/string
                # If it's a list of ints:
                if isinstance(mounts, list):
                    for m_id in mounts:
                        if isinstance(m_id, int):
                            self.owned.add(m_id)
                            # Add to all_collectibles if not present (we need metadata)
                            # Since we don't have a mount DB, we'll create generic entries for owned ones
                            # and keep the mock ones as "unowned" examples if they aren't in the list
                            self._ensure_collectible(m_id, CollectionType.MOUNT)
                            
                elif isinstance(mounts, dict):
                    for m_id in mounts:
                        self.owned.add(int(m_id))
                        self._ensure_collectible(int(m_id), CollectionType.MOUNT)
                        
        except Exception as e:
            print(f"Error loading mounts: {e}")

    def _load_pets(self, sv_path):
        pet_file = os.path.join(sv_path, "DataStore_Pets.lua")
        if not os.path.exists(pet_file): return
        
        data = self.lua_parser.parse_file(pet_file, "DataStore_PetsDB")
        if not data: return
        
        try:
            db_global = data.get("global", {})
            characters = db_global.get("Characters", {})
            
            for char_key, char_data in characters.items():
                pets = char_data.get("Pets", [])
                # Pets are usually stored as "SpeciesID|Level|..." strings or similar
                # Or just a list of IDs
                
                if isinstance(pets, list):
                    for p in pets:
                        # If string "123|1|..."
                        if isinstance(p, str) and "|" in p:
                            try:
                                species_id = int(p.split("|")[0])
                                self.owned.add(species_id)
                                self._ensure_collectible(species_id, CollectionType.PET)
                            except: pass
                        elif isinstance(p, int):
                            self.owned.add(p)
                            self._ensure_collectible(p, CollectionType.PET)
                            
        except Exception as e:
            print(f"Error loading pets: {e}")

    def _ensure_collectible(self, item_id: int, c_type: CollectionType):
        # Check if already exists
        for c in self.all_collectibles:
            if c.item_id == item_id and c.collection_type == c_type:
                return
        
        # Create generic entry since we don't have a name DB
        self.all_collectibles.append(Collectible(
            item_id, f"{c_type.value} #{item_id}", c_type, "Unknown", "Medium", "Unknown"
        ))

    def load_mock_data(self):
        """Load mock collection data"""
        
        # Mounts
        self.all_collectibles = [
            # Easy mounts
            Collectible(1, "Reins of the Bronze Drake", CollectionType.MOUNT,
                       "The Culling of Stratholme (Timed)", "Easy", "WotLK"),
            Collectible(2, "Swift White Hawkstrider", CollectionType.MOUNT,
                       "Magister's Terrace", "Easy", "TBC"),
            
            # Hard mounts
            Collectible(3, "Invincible's Reins", CollectionType.MOUNT,
                       "Icecrown Citadel (Heroic 25)", "Very Hard", "WotLK"),
            Collectible(4, "Ashes of Al'ar", CollectionType.MOUNT,
                       "Tempest Keep", "Very Hard", "TBC"),
            Collectible(5, "Flametalon of Alysrazor", CollectionType.MOUNT,
                       "Firelands", "Hard", "Cataclysm"),
            
            # Toys
            Collectible(100, "Toy Train Set", CollectionType.TOY,
                       "Vendor (Winter Veil)", "Easy", "Vanilla"),
            Collectible(101, "Faded Wizard Hat", CollectionType.TOY,
                       "Achievement: Higher Learning", "Medium", "WotLK"),
            Collectible(102, "Blazing Wings", CollectionType.TOY,
                       "Firelands Rare Drop", "Hard", "Cataclysm"),
            
            # Spells/Appearances
            Collectible(200, "Moonkin Form (Glyph)", CollectionType.SPELL,
                       "Inscription", "Easy", "Various"),
            Collectible(201, "Fandral's Seed Pouch (Druid)", CollectionType.SPELL,
                       "Firelands Questline", "Medium", "Cataclysm"),
            Collectible(202, "Hidden Artifact Appearance", CollectionType.SPELL,
                       "Secret Quest Chain", "Very Hard", "Legion"),
        ]
        
        # Mock owned items
        self.owned = {1, 2, 100, 101, 200}  # Have 5 items
        
        print(f"✓ Loaded {len(self.all_collectibles)} collectibles, {len(self.owned)} owned")
    
    def get_progress(self, collection_type: CollectionType = None) -> Dict:
        """Get collection progress statistics"""
        
        if collection_type:
            items = [c for c in self.all_collectibles if c.collection_type == collection_type]
        else:
            items = self.all_collectibles
        
        total = len(items)
        owned_count = sum(1 for c in items if c.item_id in self.owned)
        missing_count = total - owned_count
        percent = int((owned_count / total) * 100) if total > 0 else 0
        
        # Group missing by difficulty
        missing_by_difficulty = {"Easy": 0, "Medium": 0, "Hard": 0, "Very Hard": 0}
        for item in items:
            if item.item_id not in self.owned:
                missing_by_difficulty[item.difficulty] += 1
        
        return {
            "total": total,
            "owned": owned_count,
            "missing": missing_count,
            "percent": percent,
            "missing_by_difficulty": missing_by_difficulty
        }
    
    def get_missing_items(self, collection_type: CollectionType, limit: int = 10) -> List[Dict]:
        """Get missing items sorted by difficulty (easiest first)"""
        
        difficulty_order = {"Easy": 1, "Medium": 2, "Hard": 3, "Very Hard": 4}
        
        missing = [
            c for c in self.all_collectibles
            if c.collection_type == collection_type and c.item_id not in self.owned
        ]
        
        # Sort by difficulty (easiest first)
        missing.sort(key=lambda x: difficulty_order.get(x.difficulty, 99))
        
        return [{
            "id": item.item_id,
            "name": item.name,
            "source": item.source,
            "difficulty": item.difficulty,
            "expansion": item.expansion
        } for item in missing[:limit]]
    
    def get_summary(self) -> Dict:
        """Get complete collection summary"""
        
        mounts = self.get_progress(CollectionType.MOUNT)
        toys = self.get_progress(CollectionType.TOY)
        spells = self.get_progress(CollectionType.SPELL)
        
        return {
            "mounts": mounts,
            "toys": toys,
            "spells": spells,
            "overall": self.get_progress()
        }

if __name__ == "__main__":
    # Test the tracker
    print("\n" + "="*70)
    print("UTILITY TRACKER - Collection Progress")
    print("="*70)
    
    tracker = UtilityTracker()
    tracker.load_mock_data()
    
    # Test 1: Overall summary
    print("\n" + "="*70)
    print("COLLECTION SUMMARY")
    print("="*70)
    
    summary = tracker.get_summary()
    
    print(f"\n  Mounts: {summary['mounts']['owned']}/{summary['mounts']['total']} ({summary['mounts']['percent']}%)")
    print(f"  Toys: {summary['toys']['owned']}/{summary['toys']['total']} ({summary['toys']['percent']}%)")
    print(f"  Spells: {summary['spells']['owned']}/{summary['spells']['total']} ({summary['spells']['percent']}%)")
    print(f"\n  Overall: {summary['overall']['owned']}/{summary['overall']['total']} ({summary['overall']['percent']}%)")
    
    # Test 2: Missing mounts
    print("\n" + "="*70)
    print("MISSING MOUNTS (Easiest First)")
    print("="*70)
    
    missing_mounts = tracker.get_missing_items(CollectionType.MOUNT)
    for i, mount in enumerate(missing_mounts, 1):
        print(f"\n  {i}. {mount['name']} ({mount['difficulty']})")
        print(f"     Source: {mount['source']}")
        print(f"     Expansion: {mount['expansion']}")
    
    # Test 3: Difficulty breakdown
    print("\n" + "="*70)
    print("MISSING MOUNTS BY DIFFICULTY")
    print("="*70)
    
    mount_progress = summary['mounts']
    print(f"\n  Total missing: {mount_progress['missing']}")
    for difficulty, count in mount_progress['missing_by_difficulty'].items():
        if count > 0:
            print(f"  - {difficulty}: {count}")
    
    print("\n" + "="*70)
    print("✓ All tests complete!")
    print("="*70)
