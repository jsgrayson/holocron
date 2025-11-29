#!/usr/bin/env python3
"""
Enhanced Dashboard Engine
Aggregates data from all Holocron modules into a unified view
"""

from typing import Dict, List, Any
import datetime

# Import all engines
from pathfinder_engine import PathfinderEngine
from diplomat_engine import DiplomatEngine
from navigator_engine import NavigatorEngine
from knowledge_tracker import KnowledgeTracker, Profession
from utility_tracker import UtilityTracker
from goblin_engine import GoblinEngine
from codex_engine import CodexEngine
from vault_engine import VaultEngine
from scout_engine import ScoutEngine

class DashboardEngine:
    """
    Central engine for the Holocron Dashboard
    Aggregates data from all sub-systems
    """
    
    def __init__(self):
        # Initialize all engines
        # Pathfinder needs a DB URL, but we're using mock data for now
        self.pathfinder = PathfinderEngine("postgresql://mock:mock@localhost/holocron")
        self.diplomat = DiplomatEngine()
        self.navigator = NavigatorEngine()
        self.knowledge = KnowledgeTracker()
        self.utility = UtilityTracker()
        self.goblin = GoblinEngine()
        self.codex = CodexEngine()
        self.vault = VaultEngine()
        self.scout = ScoutEngine()
        
        # Load mock data for all
        self._load_all_data()
        
    def _load_all_data(self):
        """Load mock data for all engines"""
        print("Loading Holocron modules...")
        self.pathfinder.load_mock_data()
        self.diplomat.load_mock_data()
        self.navigator.load_mock_data()
        self.knowledge.load_mock_data()
        self.utility.load_mock_data()
        self.goblin.load_mock_data()
        self.codex.load_mock_data()
        self.vault.load_mock_data()
        self.scout.load_mock_data()
        print("✓ All modules loaded")
        
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get high-level summary for the dashboard"""
        
        # 1. Pathfinder Status
        # Just check if graph is loaded
        pathfinder_status = {
            "status": "Ready",
            "nodes": len(self.pathfinder.graph.nodes),
            "zones": 5
        }
        
        # 2. Diplomat Opportunity
        # Get best reputation opportunity
        opps = self.diplomat.get_opportunities()
        best_opp = opps[0] if opps else None
        diplomat_status = {
            "best_opportunity": f"{best_opp['faction_name']} ({best_opp['percent']}%)" if best_opp else "None",
            "action": "Paragon Cache" if best_opp else "None"
        }
        
        # 3. Navigator Activity
        # Get top scored activity
        activities = self.navigator.get_prioritized_activities()
        top_activity = activities[0] if activities else None
        navigator_status = {
            "top_activity": top_activity['drop'] if top_activity else "None",
            "score": top_activity['score'] if top_activity else 0
        }
        
        # 4. Knowledge Progress
        # Get weekly progress for default profession
        checklist = self.knowledge.get_checklist(Profession.BLACKSMITHING)
        knowledge_status = {
            "weekly_progress": checklist['weekly']['percent'],
            "points_earned": checklist['weekly']['points_earned'],
            "reset_in": f"{checklist['reset']['days_remaining']}d {checklist['reset']['hours_remaining']}h"
        }
        
        # 5. Utility Collection
        # Get overall collection %
        summary = self.utility.get_summary()
        utility_status = {
            "overall_percent": summary['overall']['percent'],
            "mounts": f"{summary['mounts']['owned']}/{summary['mounts']['total']}",
            "missing_easy": summary['mounts']['missing_by_difficulty'].get('Easy', 0)
        }
        
        # 6. Goblin Profit
        # Get top craft
        market = self.goblin.analyze_market()
        top_craft = market['opportunities'][0] if market['opportunities'] else None
        goblin_status = {
            "top_craft": top_craft['output_item'] if top_craft else "None",
            "profit": top_craft['profit'] if top_craft else 0,
            "sniper_hits": len(self.goblin.get_sniper_list())
        }
        
        # 7. Codex Guide
        # Get current raid info
        instance = self.codex.get_instance(1273) # Nerub-ar Palace
        codex_status = {
            "current_raid": instance['name'] if instance else "Unknown",
            "bosses": len(instance['encounters']) if instance else 0
        }
        
        # 8. Vault Progress
        # Get unlocked slots
        vault_status_full = self.vault.get_status()
        vault_summary = vault_status_full['summary']
        vault_status = {
            "unlocked": f"{vault_summary['unlocked_slots']}/9",
            "max_ilvl": vault_summary['max_reward_ilvl']
        }
        
        # 9. Scout Alerts
        # Get active alerts count
        alerts = self.scout.get_alerts()
        critical_alerts = sum(1 for a in alerts if a['urgency'] == 'Critical')
        scout_status = {
            "active_alerts": len(alerts),
            "critical": critical_alerts,
            "next_alert": alerts[0]['event'] if alerts else "None"
        }
        
        return {
            "timestamp": datetime.datetime.now().strftime("%H:%M"),
            "modules": {
                "pathfinder": pathfinder_status,
                "diplomat": diplomat_status,
                "navigator": navigator_status,
                "knowledge": knowledge_status,
                "utility": utility_status,
                "goblin": goblin_status,
                "codex": codex_status,
                "vault": vault_status,
                "scout": scout_status
            }
        }

if __name__ == "__main__":
    # Test the engine
    print("\n" + "="*70)
    print("ENHANCED DASHBOARD - Holocron Unified View")
    print("="*70)
    
    engine = DashboardEngine()
    summary = engine.get_dashboard_summary()
    
    modules = summary['modules']
    
    print(f"\nTimestamp: {summary['timestamp']}")
    
    print("\n--- MODULE STATUS ---")
    print(f"🗺️  Pathfinder: {modules['pathfinder']['status']} ({modules['pathfinder']['nodes']} nodes)")
    print(f"📜 Diplomat:   {modules['diplomat']['best_opportunity']} ({modules['diplomat']['action']})")
    print(f"🧭 Navigator:  {modules['navigator']['top_activity']} (Score: {modules['navigator']['score']})")
    print(f"📚 Knowledge:  {modules['knowledge']['weekly_progress']}% Complete (Reset: {modules['knowledge']['reset_in']})")
    print(f"🎒 Utility:    {modules['utility']['overall_percent']}% Collected (Mounts: {modules['utility']['mounts']})")
    print(f"💰 Goblin:     {modules['goblin']['top_craft']} (+{modules['goblin']['profit']}g)")
    print(f"📖 Codex:      {modules['codex']['current_raid']} ({modules['codex']['bosses']} bosses)")
    print(f"🏦 Vault:      {modules['vault']['unlocked']} Unlocked (Max: {modules['vault']['max_ilvl']} ilvl)")
    print(f"🔔 Scout:      {modules['scout']['active_alerts']} Alerts ({modules['scout']['critical']} Critical)")
    
    print("\n" + "="*70)
    print("✓ All tests complete!")
    print("="*70)
