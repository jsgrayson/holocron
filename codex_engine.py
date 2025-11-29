#!/usr/bin/env python3
"""
The Codex - Encounter Guide Engine
Provides raid and dungeon strategies, loot tables, and ability breakdowns
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class Role(Enum):
    TANK = "Tank"
    HEALER = "Healer"
    DPS = "DPS"
    EVERYONE = "Everyone"

class Difficulty(Enum):
    LFR = "LFR"
    NORMAL = "Normal"
    HEROIC = "Heroic"
    MYTHIC = "Mythic"

@dataclass
class Ability:
    name: str
    description: str
    role: Role
    importance: str  # "Critical", "High", "Medium", "Low"
    phase: int = 1

@dataclass
class LootItem:
    name: str
    slot: str
    item_level: int
    type: str  # "Plate", "Trinket", "Weapon", etc.

@dataclass
class Encounter:
    id: int
    name: str
    description: str
    abilities: List[Ability]
    loot: List[LootItem]

@dataclass
class Instance:
    id: int
    name: str
    type: str  # "Raid", "Dungeon"
    encounters: List[Encounter]

class CodexEngine:
    """
    Engine for The Codex encounter guide
    """
    
    def __init__(self):
        self.instances = {}
        
    def load_mock_data(self):
        """Load mock data for Nerub-ar Palace"""
        
        # 1. Queen Ansurek (Final Boss)
        ansurek_abilities = [
            Ability("Venom Nova", "Massive AoE damage. Healers must use cooldowns.", Role.HEALER, "Critical", 1),
            Ability("Silken Tomb", "Players are webbed. DPS must switch targets immediately.", Role.DPS, "High", 1),
            Ability("Royal Slash", "Tank buster. Swap every 2 stacks.", Role.TANK, "Critical", 1),
            Ability("Phase 2 Transition", "Boss ascends. Avoid falling debris.", Role.EVERYONE, "High", 2),
            Ability("Web Blades", "Dodge swirling blades on platform.", Role.EVERYONE, "Medium", 2),
            Ability("Devour", "Boss eats an add to heal. Interrupt/Kill add.", Role.DPS, "High", 3)
        ]
        
        ansurek_loot = [
            LootItem("Void-Touched Curio", "Trinket", 619, "Trinket"),
            LootItem("Crown of the Spider Queen", "Head", 619, "Cloth"),
            LootItem("Ansurek's Royal Scepter", "Main Hand", 619, "Mace"),
            LootItem("Reins of the Ascendant Skyrazor", "Mount", 0, "Mount")
        ]
        
        ansurek = Encounter(2922, "Queen Ansurek", "The final confrontation with the Spider Queen.", ansurek_abilities, ansurek_loot)
        
        # 2. Ulgrax the Devourer (First Boss)
        ulgrax_abilities = [
            Ability("Carnivorous Contest", "Pull players in. Run away.", Role.EVERYONE, "High", 1),
            Ability("Digestive Acid", "DoT on random players. Dispel.", Role.HEALER, "Medium", 1),
            Ability("Hungering Jaw", "Tank hit. Active mitigation required.", Role.TANK, "High", 1)
        ]
        
        ulgrax_loot = [
            LootItem("Devourer's Mandible", "One-Hand", 606, "Dagger"),
            LootItem("Chitinous Plate Greaves", "Feet", 606, "Plate")
        ]
        
        ulgrax = Encounter(2900, "Ulgrax the Devourer", "A massive beast consumed by hunger.", ulgrax_abilities, ulgrax_loot)
        
        # Create Instance
        nerubar = Instance(1273, "Nerub-ar Palace", "Raid", [ulgrax, ansurek])
        self.instances[1273] = nerubar
        
        print(f"✓ Loaded {len(self.instances)} instances with {sum(len(i.encounters) for i in self.instances.values())} encounters")
        
    def get_instance(self, instance_id: int) -> Optional[Dict]:
        """Get instance details"""
        instance = self.instances.get(instance_id)
        if not instance:
            return None
            
        return {
            "id": instance.id,
            "name": instance.name,
            "type": instance.type,
            "encounters": [
                {"id": e.id, "name": e.name, "description": e.description}
                for e in instance.encounters
            ]
        }
        
    def get_encounter(self, encounter_id: int) -> Optional[Dict]:
        """Get encounter details with abilities and loot"""
        for instance in self.instances.values():
            for encounter in instance.encounters:
                if encounter.id == encounter_id:
                    return {
                        "id": encounter.id,
                        "name": encounter.name,
                        "description": encounter.description,
                        "instance": instance.name,
                        "abilities": [
                            {
                                "name": a.name,
                                "description": a.description,
                                "role": a.role.value,
                                "importance": a.importance,
                                "phase": a.phase
                            }
                            for a in encounter.abilities
                        ],
                        "loot": [
                            {
                                "name": l.name,
                                "slot": l.slot,
                                "ilvl": l.item_level,
                                "type": l.type
                            }
                            for l in encounter.loot
                        ]
                    }
        return None

if __name__ == "__main__":
    # Test the engine
    print("\n" + "="*70)
    print("THE CODEX - Encounter Guide")
    print("="*70)
    
    engine = CodexEngine()
    engine.load_mock_data()
    
    # Test 1: Get Instance
    print("\n" + "="*70)
    print("INSTANCE: Nerub-ar Palace")
    print("="*70)
    
    instance = engine.get_instance(1273)
    if instance:
        print(f"\nName: {instance['name']} ({instance['type']})")
        print(f"Encounters: {len(instance['encounters'])}")
        for enc in instance['encounters']:
            print(f"  - {enc['name']}")
            
    # Test 2: Get Encounter (Queen Ansurek)
    print("\n" + "="*70)
    print("ENCOUNTER: Queen Ansurek")
    print("="*70)
    
    boss = engine.get_encounter(2922)
    if boss:
        print(f"\nBoss: {boss['name']}")
        print(f"Description: {boss['description']}")
        
        print("\nAbilities:")
        for ab in boss['abilities']:
            print(f"  [{ab['role']}] {ab['name']} ({ab['importance']})")
            print(f"    {ab['description']}")
            
        print("\nLoot Table:")
        for item in boss['loot']:
            print(f"  • {item['name']} ({item['slot']} - {item['ilvl']})")
            
    print("\n" + "="*70)
    print("✓ All tests complete!")
    print("="*70)
