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

    def calculate_score(self, weekly_income: int, profit_margin: int) -> Dict:
        """Calculate score based on metrics"""
        # Score components
        income_score = min(50, (weekly_income / 20000) * 50) # Cap at 20k/week for 50pts
        margin_score = min(30, profit_margin) # Cap at 30% margin for 30pts
        activity_score = 20 # Mock activity score
        
        total_score = int(income_score + margin_score + activity_score)
        total_score = min(100, total_score)
        
        return {
            "score": total_score,
            "title": self._get_title(total_score),
            "comparison": self._get_comparison(weekly_income)
        }
        
    def _get_title(self, score: int) -> str:
        current_title = "Peon"
        for threshold, title in self.TITLES:
            if score >= threshold:
                current_title = title
        return current_title
        
    def _get_comparison(self, income: int) -> str:
        trade_prince_avg = 100000
        percent = int((income / trade_prince_avg) * 100)
        return f"You are earning {percent}% of a Trade Prince's weekly average."

# Update GoblinEngine to include new modules
class GoblinEngineExpanded(GoblinEngine):
    def __init__(self):
        super().__init__()
        self.goblin_score = GoblinScore()
        
    def get_score(self) -> Dict:
        # Mock inputs for now
        return self.goblin_score.calculate_score(15400, 25)

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
