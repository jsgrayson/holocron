import os
import json
import psycopg2
from collections import defaultdict
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        # Provide helpful error message if DATABASE_URL is not set
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please set it in your environment or .env file. "
            "Example: export DATABASE_URL='postgresql://user:pass@localhost/holocron'"
        )
    conn = psycopg2.connect(db_url)
    return conn

@app.route('/')
def index():
    # Redirect to dashboard as the new home page
    return dashboard()

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

def fetch_campaigns():
    """
    Load campaign definitions from the database with a light fallback.
    """
    campaigns = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT campaign_id, name, ordered_quest_ids FROM codex.campaigns")
        for row in cur.fetchall():
            quest_ids = list(row[2]) if len(row) > 2 and row[2] else []
            campaigns.append({
                "campaign_id": row[0],
                "name": row[1],
                "quest_ids": quest_ids
            })
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Codex campaign fetch error: {e}")

    # Fallback sample so the UI always renders
    if not campaigns:
        campaigns = [
            {
                "campaign_id": 1,
                "name": "Breaching the Tomb",
                "quest_ids": [47137, 47139, 46247]
            }
        ]
    return campaigns


def fetch_characters_and_history():
    """
    Fetch character roster and quest completion history.
    Returns: (characters, completion_map)
    """
    characters = []
    completions = defaultdict(set)
    used_fallback = False

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT character_guid, name, realm, class, level FROM holocron.characters")
        for row in cur.fetchall():
            if len(row) >= 2:
                characters.append({
                    "guid": str(row[0]),
                    "name": row[1],
                    "realm": row[2] if len(row) > 2 else "",
                    "class": row[3] if len(row) > 3 else "",
                    "level": row[4] if len(row) > 4 else None
                })

        cur.execute("SELECT guid, quest_id FROM codex.character_quest_history")
        for row in cur.fetchall():
            if len(row) >= 2 and isinstance(row[1], int):
                completions[str(row[0])].add(int(row[1]))

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Codex character/history fetch error: {e}")

    # Fallback sample roster
    if not characters:
        used_fallback = True
        characters = [
            {"guid": "GUID-1", "name": "MainMage", "realm": "Dornogal", "class": "Mage", "level": 80},
            {"guid": "GUID-2", "name": "AltDruid", "realm": "Dornogal", "class": "Druid", "level": 80}
        ]

    if not completions and used_fallback:
        completions["GUID-1"] = {47137, 47139}
        completions["GUID-2"] = {47137}

    return characters, completions

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


def evaluate_campaign_status(campaign, completed_ids):
    """
    Returns per-character campaign status and next action text.
    """
    quest_ids = campaign.get("quest_ids", [])
    total = len(quest_ids)
    done_count = sum(1 for q in quest_ids if q in completed_ids)
    percent = int((done_count / total) * 100) if total else 0
    next_step = next((q for q in quest_ids if q not in completed_ids), None)

    state = "not_started"
    status_text = "No quest data."
    next_quest_id = None
    next_quest_title = None

    if not quest_ids:
        status_text = "No quest steps recorded."
    elif next_step is None:
        state = "done"
        status_text = "Campaign complete."
    else:
        blocker = solve_dependency(next_step, completed_ids)
        if blocker and blocker[0] != next_step:
            state = "locked"
            next_quest_id, next_quest_title = blocker
            status_text = f"Missing prerequisite: {next_quest_title} (ID: {next_quest_id})"
        else:
            state = "in_progress" if done_count else "not_started"
            if blocker:
                next_quest_id, next_quest_title = blocker
                status_text = f"Next: {next_quest_title} (ID: {next_quest_id})"
            else:
                next_quest_id = next_step
                status_text = f"Next: Quest ID {next_step}"

    return {
        "campaign_id": campaign.get("campaign_id"),
        "name": campaign.get("name", "Unknown Campaign"),
        "percent": percent,
        "state": state,
        "status_text": status_text,
        "step_label": f"{done_count}/{total}" if total else "-",
        "next_quest_id": next_quest_id,
        "next_quest_title": next_quest_title
    }


def build_campaign_matrix(campaigns, characters, completions):
    """
    Builds the Universal Matrix: rows = characters, columns = campaign status.
    """
    matrix = []
    for char in characters:
        completed_ids = completions.get(char["guid"], set())
        entries = []
        for camp in campaigns:
            entries.append(evaluate_campaign_status(camp, completed_ids))
        matrix.append({
            "character": char,
            "campaigns": entries
        })
    return matrix


def summarize_campaigns(matrix, campaigns):
    """
    Aggregates campaign completion across the roster for the overview cards.
    """
    summaries = []
    for camp in campaigns:
        statuses = []
        for row in matrix:
            for status in row.get("campaigns", []):
                if status.get("campaign_id") == camp.get("campaign_id"):
                    statuses.append(status)

        if statuses:
            avg_percent = int(sum(s.get("percent", 0) for s in statuses) / len(statuses))
            non_done = next((s for s in statuses if s.get("state") != "done"), None)
            if non_done:
                status_text = non_done.get("status_text", "In progress")
            else:
                status_text = "Complete on all alts."
        else:
            avg_percent = 0
            status_text = "No character data."

        summaries.append({
            "campaign_id": camp.get("campaign_id"),
            "name": camp.get("name", "Campaign"),
            "progress": avg_percent,
            "status": status_text
        })
    return summaries


def fetch_completed_for_guid(guid):
    """
    Fetches completed quest IDs for a specific character GUID.
    """
    completed = set()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT quest_id FROM codex.character_quest_history WHERE guid = %s", (guid,))
        for row in cur.fetchall():
            if row and isinstance(row[0], int):
                completed.add(int(row[0]))
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Codex completion fetch error: {e}")
    return completed


def lookup_quest_id(target):
    """
    Resolves a quest identifier from ID or fuzzy title search.
    """
    if target is None:
        return None

    target_str = str(target).strip()
    if target_str.isdigit():
        return int(target_str)

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT quest_id FROM codex.quest_definitions WHERE title ILIKE %s LIMIT 1",
            (f"%{target_str}%",)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            return int(row[0])
    except Exception as e:
        print(f"Quest lookup error: {e}")
    return None


def parse_completed_list(raw):
    """
    Parses a comma-separated list of quest IDs into a set of integers.
    """
    completed = set()
    if not raw:
        return completed
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            completed.add(int(part))
    return completed

@app.route('/codex')
def codex():
    try:
        campaigns = fetch_campaigns()
        characters, completions = fetch_characters_and_history()
        matrix = build_campaign_matrix(campaigns, characters, completions)
        campaign_cards = summarize_campaigns(matrix, campaigns)
    except Exception as e:
        print(f"Codex error: {e}")
        campaigns = fetch_campaigns()
        matrix = []
        campaign_cards = []

    return render_template(
        'codex.html',
        campaigns=campaign_cards,
        matrix=matrix,
        campaign_columns=campaigns
    )


@app.route('/api/codex/blocker')
def codex_blocker():
    """
    API for the Blocker Breaker. Accepts ?quest=<id or name>&completed=1,2&guid=<character_guid>
    """
    target = request.args.get('quest')
    if not target:
        return jsonify({"error": "Missing 'quest' parameter"}), 400

    completed = parse_completed_list(request.args.get('completed'))
    guid = request.args.get('guid')
    if guid:
        completed |= fetch_completed_for_guid(guid)

    quest_id = lookup_quest_id(target)
    if quest_id is None:
        return jsonify({"error": "Quest not found"}), 404

    if quest_id in completed:
        return jsonify({
            "target_quest_id": quest_id,
            "blocking_quest_id": None,
            "blocking_title": None,
            "state": "complete",
            "message": "Quest already completed."
        })

    result = solve_dependency(quest_id, completed)
    if not result:
        return jsonify({
            "target_quest_id": quest_id,
            "blocking_quest_id": None,
            "blocking_title": None,
            "state": "unknown",
            "message": "No blockers found or quest data unavailable."
        })

    blocker_id, blocker_title = result
    state = "blocked" if blocker_id != quest_id else "ready"
    message = f"Missing prerequisite: {blocker_title} (ID: {blocker_id})" if state == "blocked" else f"Next step: {blocker_title} (ID: {blocker_id})"

    return jsonify({
        "target_quest_id": quest_id,
        "blocking_quest_id": blocker_id,
        "blocking_title": blocker_title,
        "state": state,
        "message": message
    })

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

# --- UNIFIED DASHBOARD ---

@app.route('/dashboard')
def dashboard():
    """Unified command center aggregating all module data"""
    pet_stats = {"total": 0, "unique": 0, "strategies_ready": 0, "duplicates": 0, "missing": 0}
    campaign_stats = {"avg_progress": 0, "campaigns_complete": 0, "total_campaigns": 0}
    liquidation_stats = {"item_count": 0, "total_value": 0}
    diplomat_stats = {"close_to_paragon": 0}
    campaigns = []
    activities = []
    liquidation_items = []
    last_sync = "Never"
    
    try:
        campaigns_data = fetch_campaigns()
        characters, completions = fetch_characters_and_history()
        matrix = build_campaign_matrix(campaigns_data, characters, completions)
        campaigns = summarize_campaigns(matrix, campaigns_data)
        
        if campaigns:
            campaign_stats["total_campaigns"] = len(campaigns)
            campaign_stats["campaigns_complete"] = sum(1 for c in campaigns if c.get("progress", 0) == 100)
            campaign_stats["avg_progress"] = int(sum(c.get("progress", 0) for c in campaigns) / len(campaigns))
    except Exception as e:
        print(f"Dashboard campaign error: {e}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        sql = """
            SELECT i.name, d.name, d.type, i.expansion, i.type
            FROM holocron.instance_drops d
            JOIN holocron.instance_locations i ON d.instance_id = i.instance_id
            LIMIT 10
        """
        cur.execute(sql)
        rows = cur.fetchall()
        for row in rows:
            activities.append({
                "instance_name": row[0],
                "drop_name": row[1],
                "drop_type": row[2],
                "expansion": row[3],
                "type": row[4],
                "available_count": 8
            })
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Dashboard navigator error: {e}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM holocron.view_liquidatable_assets LIMIT 10")
        rows = cur.fetchall()
        for row in rows:
            liquidation_items.append({
                "name": row[0],
                "count": row[1],
                "market_value": row[2],
                "total_value": row[3]
            })
            liquidation_stats["item_count"] += row[1]
            liquidation_stats["total_value"] += row[3]
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Dashboard liquidation error: {e}")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT faction_id, name, paragon_threshold FROM diplomat.factions")
        rows = cur.fetchall()
        for row in rows:
            current_val = 8500 if row[0] == 2600 else 2000
            percent = int((current_val / row[2]) * 100)
            if percent > 80:
                diplomat_stats["close_to_paragon"] += 1
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Dashboard diplomat error: {e}")
    
    return render_template(
        'dashboard.html',
        pet_stats=pet_stats,
        campaign_stats=campaign_stats,
        liquidation_stats=liquidation_stats,
        diplomat_stats=diplomat_stats,
        campaigns=campaigns,
        activities=activities,
        liquidation_items=liquidation_items,
        last_sync=last_sync
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
