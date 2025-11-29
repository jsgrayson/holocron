#!/usr/bin/env python3
"""
The Diplomat - Reputation & World Quest Optimizer
Recommends most efficient WQs for factions close to Paragon rewards
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class Faction:
    faction_id: int
    name: str
    expansion: str
    paragon_threshold: int = 10000
    
@dataclass
class ReputationStatus:
    faction_id: int
    current_value: int
    is_paragon: bool = True
    
    @property
    def progress_percent(self) -> int:
        return int((self.current_value / 10000) * 100)
    
    @property
    def remaining(self) -> int:
        return 10000 - self.current_value
    
    @property
    def is_opportunity(self) -> bool:
        """Faction is >80% to next Paragon reward"""
        return self.progress_percent >= 80

@dataclass
class WorldQuest:
    quest_id: int
    title: str
    zone_id: int
    zone_name: str
    faction_id: int
    rep_reward: int
    estimated_time_seconds: int
    gold_reward: int = 0
    expires_at: Optional[datetime] = None
    
    @property
    def efficiency(self) -> float:
        """Rep per minute"""
        if self.estimated_time_seconds == 0:
            return 0
        return (self.rep_reward / self.estimated_time_seconds) * 60
    
    @property
    def efficiency_score(self) -> str:
        if self.efficiency >= 400:
            return "Excellent"
        elif self.efficiency >= 200:
            return "Good"
        elif self.efficiency >= 100:
            return "Average"
        else:
            return "Poor"

class DiplomatEngine:
    """
    Reputation optimizer that identifies Paragon opportunities
    and recommends most efficient World Quests
    """
    
    def __init__(self):
        self.factions = {}
        self.reputation_status = {}
        self.active_wqs = []
        
    def load_mock_data(self):
        """Load mock data for testing (no database needed)"""
        
        # TWW Factions
        self.factions = {
            2600: Faction(2600, "Council of Dornogal", "TWW"),
            2601: Faction(2601, "The Assembly of the Deeps", "TWW"),
            2602: Faction(2602, "Hallowfall Arathi", "TWW"),
            2603: Faction(2603, "The Severed Threads", "TWW"),
        }
        
        # Mock reputation (Council of Dornogal is close to Paragon)
        self.reputation_status = {
            2600: ReputationStatus(2600, 8500),  # 85% - OPPORTUNITY!
            2601: ReputationStatus(2601, 4200),  # 42%
            2602: ReputationStatus(2602, 9100),  # 91% - OPPORTUNITY!
            2603: ReputationStatus(2603, 2000),  # 20%
        }
        
        # Mock active World Quests
        now = datetime.now()
        self.active_wqs = [
            # Council of Dornogal quests (faction 2600)
            WorldQuest(70001, "Protect the Core", 2248, "Isle of Dorn", 
                      2600, 250, 30, 150, now + timedelta(hours=6)),  # 500 rep/min - EXCELLENT
            WorldQuest(70002, "Gather Minerals", 2248, "Isle of Dorn",
                      2600, 150, 120, 100, now + timedelta(hours=4)),  # 75 rep/min - Poor
            WorldQuest(70003, "Kill Rare Elite", 2248, "Isle of Dorn",
                      2600, 300, 60, 200, now + timedelta(hours=8)),   # 300 rep/min - Good
            
            # Hallowfall Arathi quests (faction 2602)
            WorldQuest(70004, "Defend the Lighthouse", 2215, "Hallowfall",
                      2602, 350, 90, 175, now + timedelta(hours=5)),   # 233 rep/min - Good
            WorldQuest(70005, "Clear Undead", 2215, "Hallowfall",
                      2602, 250, 45, 125, now + timedelta(hours=7)),   # 333 rep/min - Good
            
            # Assembly of the Deeps (faction 2601)
            WorldQuest(70006, "Mine Ore", 2024, "The Azure Span",
                      2601, 200, 180, 150, now + timedelta(hours=3)),  # 67 rep/min - Poor
        ]
        
        print(f"✓ Loaded {len(self.factions)} factions, {len(self.active_wqs)} active WQs")
    
    def find_paragon_opportunities(self) -> List[Dict]:
        """Find factions close to Paragon rewards (>80%)"""
        opportunities = []
        
        for faction_id, status in self.reputation_status.items():
            if status.is_opportunity:
                faction = self.factions.get(faction_id)
                if faction:
                    opportunities.append({
                        "faction_id": faction_id,
                        "faction_name": faction.name,
                        "current": status.current_value,
                        "max": faction.paragon_threshold,
                        "remaining": status.remaining,
                        "percent": status.progress_percent,
                        "priority": "HIGH" if status.progress_percent >= 90 else "MEDIUM"
                    })
        
        return sorted(opportunities, key=lambda x: x["percent"], reverse=True)
    
    def get_recommended_quests(self, faction_id: int, limit: int = 5) -> List[Dict]:
        """Get best WQs for a faction, sorted by efficiency"""
        quests = [wq for wq in self.active_wqs if wq.faction_id == faction_id]
        
        # Sort by efficiency (rep/min)
        quests.sort(key=lambda q: q.efficiency, reverse=True)
        
        results = []
        for wq in quests[:limit]:
            results.append({
                "quest_id": wq.quest_id,
                "title": wq.title,
                "zone": wq.zone_name,
                "rep_reward": wq.rep_reward,
                "time_seconds": wq.estimated_time_seconds,
                "efficiency": round(wq.efficiency, 1),
                "efficiency_score": wq.efficiency_score,
                "gold": wq.gold_reward,
                "expires_hours": (wq.expires_at - datetime.now()).total_seconds() / 3600 if wq.expires_at else None
            })
        
        return results
    
    def generate_recommendations(self) -> Dict:
        """
        Generate complete Diplomat recommendations
        Returns: {opportunities: [], all_quests: []}
        """
        opportunities = self.find_paragon_opportunities()
        
        # For each opportunity, add recommended WQs
        for opp in opportunities:
            opp["recommended_quests"] = self.get_recommended_quests(opp["faction_id"])
        
        # All WQs sorted by efficiency
        all_wqs = []
        for wq in self.active_wqs:
            faction = self.factions.get(wq.faction_id)
            all_wqs.append({
                "quest_id": wq.quest_id,
                "title": wq.title,
                "faction": faction.name if faction else "Unknown",
                "zone": wq.zone_name,
                "rep_reward": wq.rep_reward,
                "efficiency": round(wq.efficiency, 1),
                "efficiency_score": wq.efficiency_score
            })
        
        all_wqs.sort(key=lambda x: x["efficiency"], reverse=True)
        
        return {
            "opportunities": opportunities,
            "all_quests": all_wqs,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Test the engine
    print("\n" + "="*70)
    print("THE DIPLOMAT - Reputation Optimizer")
    print("="*70)
    
    engine = DiplomatEngine()
    engine.load_mock_data()
    
    # Test 1: Find Paragon opportunities
    print("\n" + "="*70)
    print("PARAGON OPPORTUNITIES (>80% to reward)")
    print("="*70)
    
    opportunities = engine.find_paragon_opportunities()
    for opp in opportunities:
        print(f"\n  {opp['faction_name']}")
        print(f"    Progress: {opp['current']:,}/{opp['max']:,} ({opp['percent']}%)")
        print(f"    Remaining: {opp['remaining']:,} rep")
        print(f"    Priority: {opp['priority']}")
    
    # Test 2: Get recommended WQs for Council of Dornogal
    print("\n" + "="*70)
    print("RECOMMENDED WQs - Council of Dornogal")
    print("="*70)
    
    quests = engine.get_recommended_quests(2600)
    for i, quest in enumerate(quests, 1):
        print(f"\n  {i}. {quest['title']}")
        print(f"     Zone: {quest['zone']}")
        print(f"     Rep: {quest['rep_reward']} | Time: {quest['time_seconds']}s")
        print(f"     Efficiency: {quest['efficiency']} rep/min ({quest['efficiency_score']})")
        print(f"     Gold: {quest['gold']} | Expires: {quest['expires_hours']:.1f}h")
    
    # Test 3: Full recommendations
    print("\n" + "="*70)
    print("COMPLETE RECOMMENDATIONS")
    print("="*70)
    
    recommendations = engine.generate_recommendations()
    print(f"\n  Found {len(recommendations['opportunities'])} opportunities")
    print(f"  Total active WQs: {len(recommendations['all_quests'])}")
    
    print("\n  Top 3 Most Efficient WQs (any faction):")
    for i, wq in enumerate(recommendations['all_quests'][:3], 1):
        print(f"    {i}. {wq['title']} - {wq['efficiency']} rep/min ({wq['faction']})")
    
    print("\n" + "="*70)
    print("✓ All tests complete!")
    print("="*70)
