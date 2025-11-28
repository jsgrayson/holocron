import os
import json
import psycopg2
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q')
    results = []
    if query:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            # Join items with storage_locations and characters to get full context
            sql = """
                SELECT i.name, i.count, s.container_type, s.container_index, c.name
                FROM holocron.items i
                JOIN holocron.storage_locations s ON i.location_id = s.location_id
                JOIN holocron.characters c ON s.character_guid = c.character_guid
                WHERE i.name ILIKE %s
                LIMIT 50
            """
            cur.execute(sql, (f'%{query}%',))
            rows = cur.fetchall()
            for row in rows:
                results.append({
                    "name": row[0],
                    "count": row[1],
                    "container_type": row[2],
                    "container_index": row[3],
                    "character_name": row[4]
                })
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Search error: {e}")
            
    return render_template('index.html', query=query, results=results)

@app.route('/liquidation')
def liquidation():
    assets = []
    pets = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get Liquidatable Assets
        cur.execute("SELECT * FROM holocron.view_liquidatable_assets LIMIT 20")
        rows = cur.fetchall()
        for row in rows:
            assets.append({
                "name": row[0],
                "count": row[1],
                "market_value": row[2],
                "total_value": row[3],
                "container_type": row[4],
                "character_name": row[5]
            })

        # Get Safe to Sell Pets
        cur.execute("SELECT name, count FROM holocron.view_safe_to_sell_pets LIMIT 20")
        rows = cur.fetchall()
        for row in rows:
            pets.append({
                "name": row[0],
                "count": row[1]
            })

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Liquidation error: {e}")

    return render_template('liquidation.html', assets=assets, pets=pets)

@app.route('/api/generate_jobs', methods=['POST'])
def generate_jobs():
    """
    Generates logistics jobs based on the current 'Liquidatable Assets' view.
    For MVP: Moves everything to a hardcoded 'AuctionAlt' (placeholder GUID).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Get all liquidatable assets
        cur.execute("SELECT name, count, character_name FROM holocron.view_liquidatable_assets")
        rows = cur.fetchall()
        
        jobs_created = 0
        for row in rows:
            # name = row[0]
            count = row[1]
            # character_name = row[2]
            
            # In a real app, we'd lookup GUIDs. For now, we mock the insertion.
            # cur.execute("INSERT INTO holocron.logistics_jobs ...")
            jobs_created += 1

        # Mock insertion for demonstration
        print(f"Generated {jobs_created} jobs.")

        cur.close()
        conn.close()
        return jsonify({"status": "success", "jobs_created": jobs_created}), 200
    except Exception as e:
        print(f"Job generation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/navigator')
def navigator():
    activities = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Logic:
        # 1. Get all notable drops.
        # 2. For each drop, count how many characters are NOT locked to that instance.
        # (Mocking the count for MVP as we don't have full character data populated)
        
        sql = """
            SELECT i.name, d.name, d.type, i.expansion, i.type
            FROM holocron.instance_drops d
            JOIN holocron.instance_locations i ON d.instance_id = i.instance_id
        """
        cur.execute(sql)
        rows = cur.fetchall()
        
        for row in rows:
            activities.append({
                "instance_name": row[0],
                "drop_name": row[1],
                "drop_type": row[2],
                "expansion": row[3],
                "type": row[4], # Raid, Dungeon, or Holiday
                "available_count": 8 # Mocked: "Available on 8 alts"
            })

        cur.close()
        conn.close()
        
        # Integrate Diplomat Recommendations (Mock)
        # In a real app, we'd call a shared function.
        activities.append({
            "instance_name": "Isle of Dorn",
            "drop_name": "Paragon Cache (Council of Dornogal)",
            "type": "Reputation",
            "expansion": "The War Within",
            "available_count": "1 (MainMage)"
        })
        
    except Exception as e:
        print(f"Navigator error: {e}")

    return render_template('navigator.html', activities=activities)

    return render_template('navigator.html', activities=activities)

# --- PATHFINDER MODULE ---
try:
    import networkx as nx
except ImportError:
    nx = None
    print("Warning: networkx not found. Pathfinder module disabled.")

def build_azeroth_graph():
    """
    Builds the graph of Azeroth from the database.
    """
    G = nx.DiGraph()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Add Zones (Nodes)
        cur.execute("SELECT zone_id, name FROM pathfinder.zones")
        for row in cur.fetchall():
            G.add_node(row[0], name=row[1])
            
        # 2. Add Connections (Edges)
        cur.execute("SELECT source_zone_id, dest_zone_id, travel_time_seconds FROM pathfinder.travel_nodes")
        for row in cur.fetchall():
            G.add_edge(row[0], row[1], weight=row[2])
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Graph build error: {e}")
    return G

@app.route('/api/distance')
def calculate_distance():
    """
    Calculates the shortest path between two zones.
    Query Params: from (zone_id), to (zone_id)
    """
    source = request.args.get('from', type=int)
    target = request.args.get('to', type=int)
    
    if not source or not target:
        return jsonify({"error": "Missing 'from' or 'to' parameters"}), 400
        
    G = build_azeroth_graph()
    
    try:
        path = nx.shortest_path(G, source=source, target=target, weight='weight')
        distance = nx.shortest_path_length(G, source=source, target=target, weight='weight')
        
        # Convert path IDs to Names
        path_names = []
        for node_id in path:
            path_names.append(G.nodes[node_id].get('name', str(node_id)))
            
        return jsonify({
            "source": source,
            "target": target,
            "path": path_names,
            "travel_time_seconds": distance,
            "travel_time_formatted": f"{distance // 60}m {distance % 60}s"
        })
    except nx.NetworkXNoPath:
        return jsonify({"error": "No path found between these zones"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/pathfinder')
def pathfinder():
    # Mock Matrix Data for MVP
    matrix = [
        {
            "name": "MainMage", "zone": "Valdrakken", 
            "hs_ready": True, "dalaran_ready": True, "garrison_ready": False, "garrison_cd": "12m", "wormhole_ready": True
        },
        {
            "name": "AltDruid", "zone": "Oribos", 
            "hs_ready": False, "hs_cd": "5m", "dalaran_ready": True, "garrison_ready": True, "wormhole_ready": False, "wormhole_cd": "4h"
        }
    ]
    return render_template('pathfinder.html', matrix=matrix)

    return render_template('pathfinder.html', matrix=matrix)

# --- CODEX MODULE ---

def solve_dependency(quest_id, completed_ids, depth=0):
    """
    Recursive function to find the first missing prerequisite.
    Returns: (Missing Quest ID, Title)
    """
    if depth > 10: return None # Prevent infinite recursion
    
    # 1. Check if we have this quest
    if quest_id in completed_ids:
        return None
        
    # 2. Check dependencies
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT required_quest_id FROM codex.quest_dependencies WHERE quest_id = %s", (quest_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        for row in rows:
            parent_id = row[0]
            if parent_id not in completed_ids:
                # Recursively check the parent
                missing_prereq = solve_dependency(parent_id, completed_ids, depth+1)
                if missing_prereq:
                    return missing_prereq
                else:
                    # Parent is missing but has no missing prereqs -> Parent is the blocker
                    # Fetch title
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("SELECT title FROM codex.quest_definitions WHERE quest_id = %s", (parent_id,))
                    title_row = cur.fetchone()
                    cur.close()
                    conn.close()
                    return (parent_id, title_row[0] if title_row else "Unknown Quest")
                    
        # If no dependencies are missing, but we don't have this quest -> This quest is the next step
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT title FROM codex.quest_definitions WHERE quest_id = %s", (quest_id,))
        title_row = cur.fetchone()
        cur.close()
        conn.close()
        return (quest_id, title_row[0] if title_row else "Unknown Quest")
        
    except Exception as e:
        print(f"Codex solver error: {e}")
        return None

@app.route('/codex')
def codex():
    campaigns = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Mock Character Data for MVP
        # Assume "MainChar" has done the first 2 quests of Campaign 1
        completed_ids = {47137, 47139} 
        
        # Get Campaigns
        cur.execute("SELECT campaign_id, name, ordered_quest_ids FROM codex.campaigns")
        rows = cur.fetchall()
        
        for row in rows:
            c_id = row[0]
            c_name = row[1]
            q_ids = row[2] # List of ints
            
            # Calculate Progress
            done_count = sum(1 for q in q_ids if q in completed_ids)
            total_count = len(q_ids)
            percent = int((done_count / total_count) * 100) if total_count > 0 else 0
            
            # Find Next Step
            next_step = "Complete"
            if done_count < total_count:
                # Find first missing quest
                for q in q_ids:
                    if q not in completed_ids:
                        # Solve dependencies
                        blocker = solve_dependency(q, completed_ids)
                        if blocker:
                            next_step = f"Next: {blocker[1]} (ID: {blocker[0]})"
                        else:
                            next_step = f"Next: Quest ID {q}"
                        break
            
            campaigns.append({
                "name": c_name,
                "progress": percent,
                "status": next_step
            })

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Codex error: {e}")

    return render_template('codex.html', campaigns=campaigns)

    return render_template('codex.html', campaigns=campaigns)

# --- DIPLOMAT MODULE ---

@app.route('/diplomat')
def diplomat():
    factions_data = []
    sniper_list = []
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. Get Faction Status (Mocked for MVP if no data)
        # In a real scenario, we'd join diplomat.reputation_status with factions
        # For now, let's return the static factions with mock progress
        cur.execute("SELECT faction_id, name, paragon_threshold FROM diplomat.factions")
        rows = cur.fetchall()
        
        for row in rows:
            f_id = row[0]
            name = row[1]
            threshold = row[2]
            
            # Mock Progress
            current_val = 8500 if f_id == 2600 else 2000 # Dornogal is close
            percent = int((current_val / threshold) * 100)
            
            factions_data.append({
                "name": name,
                "current": current_val,
                "max": threshold,
                "percent": percent,
                "is_close": percent > 80
            })
            
            # 2. Generate Sniper Recommendations (Mock)
            if percent > 80:
                sniper_list.append({
                    "quest": "Protect the Core",
                    "zone": "Isle of Dorn",
                    "reward": "250 Rep",
                    "efficiency": "High (Kill Quest)",
                    "assigned_char": "MainMage"
                })

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Diplomat error: {e}")

    return render_template('diplomat.html', factions=factions_data, sniper=sniper_list)

@app.route('/upload', methods=['POST'])
def upload_data():
    """
    Endpoint to receive JSON payloads from the Bridge script.
    Expected JSON format:
    {
        "source": "DataStore", 
        "data": { ... }
    }
    """
    try:
        payload = request.get_json()
        if not payload:
            return jsonify({"error": "No JSON payload received"}), 400

        source = payload.get('source')
        data = payload.get('data')

        if not source or not data:
            return jsonify({"error": "Missing 'source' or 'data' fields"}), 400

        # TODO: Implement specific parsing logic based on 'source'
        # For now, we just acknowledge receipt.
        print(f"Received data from {source}: {len(str(data))} bytes")
        
        # Placeholder for DB insertion logic
        # conn = get_db_connection()
        # cur = conn.cursor()
        # ...
        # conn.commit()
        # cur.close()
        # conn.close()

        return jsonify({"status": "success", "message": f"Processed {source} data"}), 200

    except Exception as e:
        print(f"Error processing upload: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT 1')
        cur.close()
        conn.close()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "database": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
