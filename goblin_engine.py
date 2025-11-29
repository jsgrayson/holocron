#!/usr/bin/env python3
"""
Goblin Brain - Market Prediction & Crafting Optimizer
Analyzes market data to identify profitable crafting opportunities
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import random

class ItemType(Enum):
    MATERIAL = "Material"
    CONSUMABLE = "Consumable"
    GEAR = "Gear"
    ENCHANT = "Enchant"

@dataclass
class ItemPrice:
    item_id: int
    name: str
    item_type: ItemType
    market_value: int  # Gold
    min_buyout: int    # Gold
    region_avg: int    # Gold
    sale_rate: float   # 0.0 to 1.0 (velocity)
    
@dataclass
class Recipe:
    recipe_id: int
    name: str
    output_item_id: int
    output_quantity: int
    materials: Dict[int, int]  # {item_id: quantity}
    craft_time_seconds: int

class GoblinEngine:
    """
    Economic intelligence engine for market analysis and crafting optimization
    """
    
    def __init__(self):
        self.prices = {}  # {item_id: ItemPrice}
        self.recipes = []
        
    def load_mock_data(self):
        """Load mock market and recipe data"""
        
        # 1. Define Items & Prices
        # Materials
        self.prices[1001] = ItemPrice(1001, "Draconium Ore", ItemType.MATERIAL, 45, 42, 48, 0.95)
        self.prices[1002] = ItemPrice(1002, "Khaz Algar Herb", ItemType.MATERIAL, 25, 24, 28, 0.90)
        self.prices[1003] = ItemPrice(1003, "Awakened Order", ItemType.MATERIAL, 150, 145, 160, 0.85)
        self.prices[1004] = ItemPrice(1004, "Resonant Crystal", ItemType.MATERIAL, 200, 190, 210, 0.60)
        
        # Crafted Items
        self.prices[2001] = ItemPrice(2001, "Algari Healing Potion", ItemType.CONSUMABLE, 80, 75, 85, 0.80)
        self.prices[2002] = ItemPrice(2002, "Draconium Plate Helm", ItemType.GEAR, 2500, 2400, 2600, 0.20)
        self.prices[2003] = ItemPrice(2003, "Enchant Weapon - Sophic Devotion", ItemType.ENCHANT, 1200, 1150, 1250, 0.75)
        self.prices[2004] = ItemPrice(2004, "Khaz Algar Flask", ItemType.CONSUMABLE, 400, 380, 420, 0.65)
        
        # 2. Define Recipes
        self.recipes = [
            # Potion: 2 Herbs (25g ea) -> 1 Potion (80g)
            # Cost: 50g, Value: 80g, Profit: 26g (after 5% cut)
            Recipe(5001, "Algari Healing Potion", 2001, 1, {1002: 2}, 2),
            
            # Helm: 20 Ore (45g ea) + 2 Crystal (200g ea) -> 1 Helm (2500g)
            # Cost: 900 + 400 = 1300g, Value: 2500g, Profit: 1075g
            Recipe(5002, "Draconium Plate Helm", 2002, 1, {1001: 20, 1004: 2}, 10),
            
            # Enchant: 4 Order (150g ea) + 2 Crystal (200g ea) -> 1 Enchant (1200g)
            # Cost: 600 + 400 = 1000g, Value: 1200g, Profit: 140g
            Recipe(5003, "Enchant Weapon - Sophic Devotion", 2003, 1, {1003: 4, 1004: 2}, 5),
            
            # Flask: 10 Herbs (25g ea) + 1 Order (150g ea) -> 1 Flask (400g)
            # Cost: 250 + 150 = 400g, Value: 400g, Profit: -20g (Loss!)
            Recipe(5004, "Khaz Algar Flask", 2004, 1, {1002: 10, 1003: 1}, 3),
        ]
        
        print(f"✓ Loaded {len(self.prices)} items, {len(self.recipes)} recipes")
        
    def calculate_crafting_cost(self, recipe: Recipe) -> int:
        """Calculate total material cost for a recipe"""
        total_cost = 0
        for item_id, quantity in recipe.materials.items():
            if item_id in self.prices:
                total_cost += self.prices[item_id].min_buyout * quantity
        return total_cost
    
    def analyze_market(self) -> Dict:
        """Analyze market for opportunities"""
        opportunities = []
        
        for recipe in self.recipes:
            output_item = self.prices.get(recipe.output_item_id)
            if not output_item:
                continue
                
            crafting_cost = self.calculate_crafting_cost(recipe)
            market_value = output_item.min_buyout
            
            # Calculate profit (Market Value * 0.95 for AH cut - Cost)
            ah_cut = 0.05
            net_value = market_value * (1 - ah_cut)
            profit = net_value - crafting_cost
            profit_margin = (profit / crafting_cost) * 100 if crafting_cost > 0 else 0
            
            # Score = Profit * Sale Rate (Velocity)
            # High profit items that never sell get lower priority
            score = profit * output_item.sale_rate
            
            opportunities.append({
                "recipe_name": recipe.name,
                "output_item": output_item.name,
                "type": output_item.item_type.value,
                "crafting_cost": crafting_cost,
                "market_value": market_value,
                "profit": int(profit),
                "profit_margin": int(profit_margin),
                "sale_rate": output_item.sale_rate,
                "score": int(score),
                "recommendation": self._get_recommendation(profit, output_item.sale_rate)
            })
            
        # Sort by score (best opportunities first)
        opportunities.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "opportunities": opportunities,
            "timestamp": "Now",
            "total_potential_profit": sum(o["profit"] for o in opportunities if o["profit"] > 0)
        }
    
    def _get_recommendation(self, profit: float, sale_rate: float) -> str:
        """Generate recommendation string"""
        if profit <= 0:
            return "DO NOT CRAFT (Loss)"
        
        if sale_rate >= 0.5:
            if profit > 500:
                return "CRAFT IMMEDIATELY (High Profit/High Vol)"
            elif profit > 100:
                return "Craft (Good Profit)"
            else:
                return "Craft (Low Margin)"
        else:
            if profit > 1000:
                return "Craft 1-2 (High Profit/Low Vol)"
            else:
                return "Avoid (Low Vol/Low Profit)"

    def get_sniper_list(self) -> List[Dict]:
        """Identify items posted significantly below market value"""
        # Mock sniper logic - in real app would compare live listings to DB avg
        sniper_hits = []
        
        # Simulate finding a cheap listing
        sniper_hits.append({
            "item": "Draconium Ore",
            "listed_price": 25,
            "market_value": 45,
            "potential_profit": 18, # (45*0.95) - 25
            "confidence": "High"
        })
        
        return sniper_hits

class GoldTracker:
    """Tracks gold income over time"""
    def __init__(self):
        self.history = [] # List of (date, amount)
        
    def get_benchmark(self, period: str) -> Dict:
        """Get income for a specific period"""
        # Mock data
        if period == 'day':
            return {"income": 1250, "change": "+5%"}
        elif period == 'week':
            return {"income": 15400, "change": "+12%"}
        elif period == 'month':
            return {"income": 62000, "change": "-3%"}
        return {"income": 0, "change": "0%"}
        
    def get_history(self) -> List[Dict]:
        """Get gold history for graphing"""
        # Mock 7-day history
        return [
            {"day": "Mon", "gold": 124000},
            {"day": "Tue", "gold": 128000}, # Reset day spike
            {"day": "Wed", "gold": 131000},
            {"day": "Thu", "gold": 132500},
            {"day": "Fri", "gold": 133000},
            {"day": "Sat", "gold": 138000}, # Weekend sales
            {"day": "Sun", "gold": 142000},
        ]

class InvestmentAdvisor:
    """Recommends items to buy and hold"""
    def get_bank_tab_recommendations(self) -> List[Dict]:
        """Identify items with high long-term value"""
        return [
            {
                "item": "Draconium Ore",
                "current_price": 45,
                "avg_price": 55,
                "recommendation": "BUY",
                "reason": "20% below monthly average. Reset day demand expected.",
                "confidence": "High"
            },
            {
                "item": "Awakened Order",
                "current_price": 150,
                "avg_price": 145,
                "recommendation": "HOLD",
                "reason": "Price stable. Wait for raid release spike.",
                "confidence": "Medium"
            },
            {
                "item": "Resonant Crystal",
                "current_price": 200,
                "avg_price": 250,
                "recommendation": "BUY",
                "reason": "Undervalued. crafting demand increasing.",
                "confidence": "High"
            }
        ]

# Update GoblinEngine to include new modules
class GoblinEngineExpanded(GoblinEngine):
    def __init__(self):
        super().__init__()
        self.gold_tracker = GoldTracker()
        self.investment_advisor = InvestmentAdvisor()
        
    def get_gold_benchmarks(self) -> Dict:
        return {
            "day": self.gold_tracker.get_benchmark('day'),
            "week": self.gold_tracker.get_benchmark('week'),
            "month": self.gold_tracker.get_benchmark('month'),
            "history": self.gold_tracker.get_history()
        }
        
    def get_investments(self) -> List[Dict]:
        return self.investment_advisor.get_bank_tab_recommendations()

if __name__ == "__main__":
    # Test the engine
    print("\n" + "="*70)
    print("GOBLIN BRAIN - Market Intelligence")
    print("="*70)
    
    engine = GoblinEngine()
    engine.load_mock_data()
    
    # Test 1: Market Analysis
    print("\n" + "="*70)
    print("CRAFTING OPPORTUNITIES")
    print("="*70)
    
    analysis = engine.analyze_market()
    
    for i, opp in enumerate(analysis['opportunities'], 1):
        print(f"\n  {i}. {opp['recipe_name']} ({opp['type']})")
        print(f"     Cost: {opp['crafting_cost']}g | Sell: {opp['market_value']}g")
        print(f"     Profit: {opp['profit']}g ({opp['profit_margin']}%)")
        print(f"     Sale Rate: {opp['sale_rate']} | Score: {opp['score']}")
        print(f"     Action: {opp['recommendation']}")
        
    print(f"\n  Total Potential Profit: {analysis['total_potential_profit']}g")
    
    # Test 2: Sniper
    print("\n" + "="*70)
    print("SNIPER HITS")
    print("="*70)
    
    hits = engine.get_sniper_list()
    for hit in hits:
        print(f"\n  • {hit['item']}")
        print(f"    Buy: {hit['listed_price']}g | Market: {hit['market_value']}g")
        print(f"    Flip Profit: {hit['potential_profit']}g")
    
    print("\n" + "="*70)
    print("✓ All tests complete!")
    print("="*70)
