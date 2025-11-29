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
class Item:
    id: int
    name: str
    item_type: ItemType
    market_value: int
    sale_rate: float

class Profession(Enum):
    ALCHEMY = "Alchemy"
    BLACKSMITHING = "Blacksmithing"
    ENCHANTING = "Enchanting"
    ENGINEERING = "Engineering"
    INSCRIPTION = "Inscription"
    JEWELCRAFTING = "Jewelcrafting"
    LEATHERWORKING = "Leatherworking"
    TAILORING = "Tailoring"
    MINING = "Mining"
    HERBALISM = "Herbalism"
    SKINNING = "Skinning"

@dataclass
class Recipe:
    recipe_id: int
    name: str
    profession: Profession
    reagents: Dict[int, int]  # {item_id: quantity}
    result_item_id: int
    output_quantity: int = 1

class Profession(Enum):
    ALCHEMY = "Alchemy"
    BLACKSMITHING = "Blacksmithing"
    ENCHANTING = "Enchanting"
    ENGINEERING = "Engineering"
    INSCRIPTION = "Inscription"
    JEWELCRAFTING = "Jewelcrafting"
    LEATHERWORKING = "Leatherworking"
    TAILORING = "Tailoring"
    MINING = "Mining"
    HERBALISM = "Herbalism"
    SKINNING = "Skinning"

class GoblinEngine:
    """
    Economic intelligence engine for market analysis and crafting optimization
    """
    
    def __init__(self, tsm_engine=None):
        self.tsm_engine = tsm_engine
        self.prices = {}  # {item_id: ItemPrice}
        self.recipes = []
        self.items = []
        
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
        self.recipes = []
            # Potion: 2 Herbs (25g ea) -> 1 Potion (80g)
        """Load mock recipe and item data"""
        # But we don't need to define prices here if we use TSM, 
        # though for now we'll keep them as fallback or base cost.
        
        # 1. Draconium Ore (Material)
        draconium = Item(198765, "Draconium Ore", ItemType.MATERIAL, 45, 0.95)
        
        # 2. Khaz'gorite Ore (Material)
        khazgorite = Item(198766, "Khaz'gorite Ore", ItemType.MATERIAL, 120, 0.80)
        
        # 3. Resonant Crystal (Material)
        crystal = Item(200111, "Resonant Crystal", ItemType.MATERIAL, 200, 0.50)
        
        # 4. Hochenblume (Material)
        hochenblume = Item(194820, "Hochenblume", ItemType.MATERIAL, 15, 0.90)
        
        self.items = [draconium, khazgorite, crystal, hochenblume]
        
        # Recipes
        # 1. Draconium Ingot (Smelting)
        # Requires: 2 Draconium Ore
        ingot_recipe = Recipe(
            382900, "Draconium Ingot", Profession.MINING,
            {198765: 2}, 382901, 1
        )
        
        # 2. Elemental Potion of Ultimate Power (Alchemy)
        # Requires: 2 Hochenblume, 1 Crystal
        potion_recipe = Recipe(
            370607, "Elemental Potion of Ultimate Power", Profession.ALCHEMY,
            {194820: 2, 200111: 1}, 191304
        )
        
        self.recipes = [ingot_recipe, potion_recipe]
        print(f"✓ Loaded {len(self.items)} items, {len(self.recipes)} recipes")
        
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
            # Calculate Crafting Cost
            crafting_cost = 0
            for mat_id, qty in recipe.reagents.items():
                # Use TSM price if available, else fallback to item.market_value
                mat_price = 0
                if self.tsm_engine:
                    mat_price = self.tsm_engine.get_market_value(mat_id)
                
                if mat_price == 0:
                    # Fallback to internal item list
                    mat_item = next((i for i in self.items if i.id == mat_id), None)
                    if mat_item:
                        mat_price = mat_item.market_value
                
                crafting_cost += mat_price * qty
            
            # Calculate Market Value of Result
            result_price = 0
            if self.tsm_engine:
                result_price = self.tsm_engine.get_market_value(recipe.result_item_id)
            
            # Fallback for result price (mock)
            if result_price == 0:
                 if recipe.name == "Draconium Ingot": result_price = 100
                 elif recipe.name == "Elemental Potion of Ultimate Power": result_price = 500
            
            profit = result_price - crafting_cost
            margin = (profit / crafting_cost) * 100 if crafting_cost > 0 else 0
            
            # Score = Profit * Sale Rate (Velocity)
            # High profit items that never sell get lower priority
            # For now, use a mock sale rate for the result item
            # In a real scenario, TSM would provide this for the result_item_id
            mock_sale_rate = 0.75 # Placeholder
            score = profit * mock_sale_rate
            
            # Find the output item for its type and name
            output_item_name = "Unknown"
            output_item_type = "Unknown"
            output_item_obj = next((i for i in self.items if i.id == recipe.result_item_id), None)
            if output_item_obj:
                output_item_name = output_item_obj.name
                output_item_type = output_item_obj.item_type.value

            opportunities.append({
                "recipe_name": recipe.name,
                "output_item": output_item_name,
                "type": output_item_type,
                "crafting_cost": int(crafting_cost),
                "market_value": int(result_price),
                "profit": int(profit),
                "profit_margin": int(margin),
                "sale_rate": mock_sale_rate,
                "score": int(score),
                "recommendation": self._get_recommendation(profit, mock_sale_rate)
            })
            
        # Sort by score (best opportunities first)
        opportunities.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "opportunities": opportunities,
            "timestamp": "Now",
            "total_potential_profit": sum(o["profit"] for o in opportunities if o["profit"] > 0)
        }
        
    def get_sniper_list(self) -> List[Dict]:
        """
        Identify underpriced items (Sniper)
        For mock data, we'll return a few fixed examples.
        """
        return [
            {
                "item": "Draconium Ore",
                "listed_price": 15,
                "market_value": 45,
                "potential_profit": 30
            },
            {
                "item": "Resonant Crystal",
                "listed_price": 150,
                "market_value": 200,
                "potential_profit": 50
            }
        ]
    
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
