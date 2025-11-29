#!/usr/bin/env python3
"""
Project Pathfinder - Intelligent Travel Route Optimizer
Uses graph algorithms to find shortest paths between WoW locations
"""

import networkx as nx
import psycopg2
from typing import List, Dict, Optional, Tuple
import os

class PathfinderEngine:
    """
    Routing engine that calculates optimal travel paths using:
    - Portals
    - Hearthstones (with cooldown awareness)
    - Flight paths
    - Character-specific abilities (Mage teleports, etc.)
    """
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.graph = nx.DiGraph()  # Directed graph for one-way connections
        self.zones = {}  # zone_id -> {name, expansion}
        
    def build_graph(self):
        """Load zones and travel nodes from database into graph"""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        # Load zones
        cur.execute("SELECT zone_id, name, expansion FROM pathfinder.zones")
        for zone_id, name, expansion in cur.fetchall():
            self.zones[zone_id] = {"name": name, "expansion": expansion}
            self.graph.add_node(zone_id, name=name, expansion=expansion)
        
        # Load travel connections
        cur.execute("""
            SELECT source_zone_id, dest_zone_id, method, travel_time_seconds, requirements
            FROM pathfinder.travel_nodes
        """)
        
        for source, dest, method, time, requirements in cur.fetchall():
            self.graph.add_edge(
                source, dest,
                method=method,
                time=time,
                requirements=requirements or ""
            )
        
        cur.close()
        conn.close()
        
        print(f"✓ Graph built: {self.graph.number_of_nodes()} zones, {self.graph.number_of_edges()} connections")
        
    def load_mock_data(self):
        """Load mock data for testing without DB"""
        # Add some zones
        self.zones[84] = {"name": "Stormwind", "expansion": "Classic"}
        self.zones[1670] = {"name": "Oribos", "expansion": "Shadowlands"}
        self.zones[1978] = {"name": "Dragon Isles", "expansion": "Dragonflight"}
        self.zones[2022] = {"name": "The Waking Shores", "expansion": "Dragonflight"}
        self.zones[2023] = {"name": "Ohn'ahran Plains", "expansion": "Dragonflight"}
        
        # Add nodes to graph
        for zid, data in self.zones.items():
            self.graph.add_node(zid, **data)
            
        # Add some edges
        self.graph.add_edge(84, 1670, method="PORTAL", time=15, requirements="Mage")
        self.graph.add_edge(1670, 84, method="PORTAL", time=15, requirements="")
        
        print(f"✓ Mock Graph built: {self.graph.number_of_nodes()} zones")
    
    def find_shortest_path(
        self,
        source_zone_id: int,
        dest_zone_id: int,
        character_class: Optional[str] = None,
        hearthstone_available: bool = True
    ) -> Dict:
        """
        Find shortest path between two zones
        
        Args:
            source_zone_id: Starting zone
            dest_zone_id: Destination zone
            character_class: e.g., "Mage" (enables class-specific portals)
            hearthstone_available: Whether hearthstone is off cooldown
        
        Returns:
            {
                "path": [zone_ids],
                "steps": [{zone, method, time}],
                "total_time": seconds,
                "success": bool
            }
        """
        if source_zone_id not in self.graph:
            return {"success": False, "error": f"Source zone {source_zone_id} not found"}
        
        if dest_zone_id not in self.graph:
            return {"success": False, "error": f"Destination zone {dest_zone_id} not found"}
        
        # Create filtered graph based on character abilities
        filtered_graph = self._filter_graph(character_class, hearthstone_available)
        
        try:
            # Use Dijkstra's algorithm with time as weight
            path = nx.shortest_path(
                filtered_graph,
                source=source_zone_id,
                target=dest_zone_id,
                weight='time'
            )
            
            # Calculate steps and total time
            steps = []
            total_time = 0
            
            for i in range(len(path) - 1):
                source = path[i]
                dest = path[i + 1]
                edge_data = filtered_graph[source][dest]
                
                steps.append({
                    "from_zone": self.zones[source]["name"],
                    "to_zone": self.zones[dest]["name"],
                    "method": edge_data["method"],
                    "time": edge_data["time"]
                })
                total_time += edge_data["time"]
            
            return {
                "success": True,
                "path": path,
                "steps": steps,
                "total_time": total_time,
                "source": self.zones[source_zone_id]["name"],
                "destination": self.zones[dest_zone_id]["name"]
            }
            
        except nx.NetworkXNoPath:
            return {
                "success": False,
                "error": f"No path found from {self.zones[source_zone_id]['name']} to {self.zones[dest_zone_id]['name']}"
            }
    
    def _filter_graph(self, character_class: Optional[str], hearthstone_available: bool) -> nx.DiGraph:
        """
        Create filtered graph based on character abilities
        """
        filtered = self.graph.copy()
        
        # Remove edges with unmet requirements
        edges_to_remove = []
        for source, dest, data in filtered.edges(data=True):
            requirements = data.get('requirements', '')
            
            # Filter class-specific abilities
            if requirements:
                if 'Mage' in requirements and character_class != 'Mage':
                    edges_to_remove.append((source, dest))
                elif 'Engineer' in requirements and character_class != 'Engineer':
                    edges_to_remove.append((source, dest))
                elif 'Druid' in requirements and character_class != 'Druid':
                    edges_to_remove.append((source, dest))
            
            # Remove hearthstone connections if on cooldown
            if data.get('method') in ['HEARTHSTONE', 'DALARAN_HEARTHSTONE', 'GARRISON_HEARTHSTONE']:
                if not hearthstone_available:
                    edges_to_remove.append((source, dest))
        
        filtered.remove_edges_from(edges_to_remove)
        return filtered
    
    def get_reachable_zones(self, source_zone_id: int, max_time: int = 120) -> List[Dict]:
        """
        Get all zones reachable within max_time seconds from source
        Useful for "where can I get to quickly?" queries
        """
        reachable = []
        
        for zone_id in self.graph.nodes():
            if zone_id == source_zone_id:
                continue
                
            result = self.find_shortest_path(source_zone_id, zone_id)
            if result["success"] and result["total_time"] <= max_time:
                reachable.append({
                    "zone_id": zone_id,
                    "zone_name": self.zones[zone_id]["name"],
                    "time": result["total_time"],
                    "steps": len(result["steps"])
                })
        
        return sorted(reachable, key=lambda x: x["time"])


if __name__ == "__main__":
    # Test the engine
    from dotenv import load_dotenv
    load_dotenv('/Users/jgrayson/Documents/holocron/.env')
    
    db_url = os.getenv('DATABASE_URL')
    engine = PathfinderEngine(db_url)
    engine.build_graph()
    
    # Test route: Stormwind (84) to Oribos (1670)
    print("\n" + "="*60)
    print("Test Route: Stormwind → Oribos")
    print("="*60)
    
    result = engine.find_shortest_path(84, 1670)
    
    if result["success"]:
        print(f"\n✓ Route found! Total time: {result['total_time']} seconds\n")
        for i, step in enumerate(result["steps"], 1):
            print(f"{i}. {step['from_zone']} → {step['to_zone']}")
            print(f"   Method: {step['method']} ({step['time']}s)\n")
    else:
        print(f"\n✗ Error: {result['error']}")
