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

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/stats')
def api_stats():
    """Returns stat weights from DB or JSON fallback."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT spec, stat_string FROM skillweaver.stat_weights")
        rows = cur.fetchall()
        data = [{"spec": r[0], "stat_string": r[1]} for r in rows]
        cur.close()
        conn.close()
        return jsonify({"source": "db", "data": data})
    except Exception as e:
        print(f"DB Error (Stats): {e}")
        # Fallback
        try:
            with open("scraped_stats.json", "r") as f:
                return jsonify({"source": "json", "data": json.load(f)})
        except FileNotFoundError:
            return jsonify({"source": "none", "data": []})

@app.route('/api/talents')
def api_talents():
    """Returns talent strings from DB or JSON fallback."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT spec, build_name, talent_string FROM skillweaver.talent_builds")
        rows = cur.fetchall()
        data = [{"spec": r[0], "build_name": r[1], "talent_string": r[2]} for r in rows]
        cur.close()
        conn.close()
        return jsonify({"source": "db", "data": data})
    except Exception as e:
        print(f"DB Error (Talents): {e}")
        # Fallback
        try:
            with open("scraped_talents.json", "r") as f:
                return jsonify({"source": "json", "data": json.load(f)})
        except FileNotFoundError:
            return jsonify({"source": "none", "data": []})

@app.route('/api/battles')
def api_battles():
    """Returns recorded battles from DB or JSON fallback."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM petweaver.battles LIMIT 50") # Placeholder schema
        rows = cur.fetchall()
        # Mock DB response for now as schema might vary
        data = [] 
        cur.close()
        conn.close()
        return jsonify({"source": "db", "data": data})
    except Exception as e:
        print(f"DB Error (Battles): {e}")
        # Fallback
        try:
            with open("recorded_battles.json", "r") as f:
                # Read line by line if it's JSONL, or load if JSON array
                # The recorder appends lines, so it's likely JSONL-ish or just appended dicts
                # Let's assume valid JSON array or fix it
                # Actually recorder.py appends `json.dumps(data) + "\n"`.
                # So we need to parse lines.
                data = []
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
                return jsonify({"source": "json", "data": data})
        except FileNotFoundError:
            return jsonify({"source": "none", "data": []})

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

# --- NAVIGATOR MODULE ---
from navigator_engine import NavigatorEngine

# Initialize Navigator engine once
navigator_engine = NavigatorEngine()
navigator_engine.load_mock_data()

@app.route('/api/navigator/activities')
def navigator_activities():
    """
    Get prioritized activities with scores
    Query params:
        include_owned (bool): Include already-collected items
        min_available (int): Minimum available characters
    """
    include_owned = request.args.get('include_owned', 'false').lower() == 'true'
    min_available = request.args.get('min_available', 1, type=int)
    
    activities = navigator_engine.get_prioritized_activities(
        include_owned=include_owned,
        min_available=min_available
    )
    
    stats = navigator_engine.get_statistics()
    
    return jsonify({
        "activities": activities,
        "statistics": stats,
        "urgent_count": len(navigator_engine.get_urgent_activities())
    })

@app.route('/api/navigator/urgent')
def navigator_urgent():
    """Get top priority activities (score >= 80)"""
    urgent = navigator_engine.get_urgent_activities(limit=10)
    return jsonify({"urgent_activities": urgent})

@app.route('/navigator')
def navigator():
    """Navigator UI page"""
    # Get prioritized activities
    activities_data = navigator_engine.get_prioritized_activities(min_available=1)
    stats = navigator_engine.get_statistics()
    urgent = navigator_engine.get_urgent_activities()
    
    # Format for template (keep compatible with existing HTML)
    activities = []
    for act in activities_data[:20]:  # Top 20
        activities.append({
            "instance_name": act["instance"],
            "drop_name": act["drop"],
            "drop_type": act["type"],
            "expansion": act["expansion"],
            "type": act['instance_type'],
            "available_count": act["available_chars"],
            "score": act["score"],
            "priority": act["priority"]
        })
    
    return render_template('navigator.html', 
                          activities=activities,
                          statistics=stats,
                          urgent_count=len(urgent))

# --- PATHFINDER MODULE ---
from pathfinder_engine import MockPathfinder

# Initialize Pathfinder engine once
pathfinder_engine = MockPathfinder()
pathfinder_engine.build_mock_graph()

@app.route('/api/pathfinder/route')
def pathfinder_route():
    """
    Calculate shortest travel route between zones
    Query params:
        source (int): Source zone ID
        dest (int): Destination zone ID
        char_class (str): Optional character class (Mage, Engineer, Druid)
        hearthstone (bool): Whether hearthstone is available
    """
    source = request.args.get('source', type=int)
    dest = request.args.get('dest', type=int)
    char_class = request.args.get('char_class', None)
    hearthstone = request.args.get('hearthstone', 'true').lower() == 'true'
    
    if not source or not dest:
        return jsonify({"error": "Missing 'source' or 'dest' parameters"}), 400
    
    result = pathfinder_engine.find_shortest_path(
        source, dest,
        character_class=char_class,
        hearthstone_available=hearthstone
    )
    
    return jsonify(result)

@app.route('/api/pathfinder/reachable')
def pathfinder_reachable():
    """
    Get all zones reachable from a source within max_time
    Query params:
        source (int): Source zone ID
        max_time (int): Maximum travel time in seconds (default: 120)
    """
    source = request.args.get('source', type=int)
    max_time = request.args.get('max_time', 120, type=int)
    
    if not source:
        return jsonify({"error": "Missing 'source' parameter"}), 400
    
    reachable = pathfinder_engine.get_reachable_zones(source, max_time)
    return jsonify({"source": source, "max_time": max_time, "reachable": reachable})

@app.route('/pathfinder')
def pathfinder():
    # Get list of zones for dropdowns
    zones = [
        {"id": 84, "name": "Stormwind City"},
        {"id": 85, "name": "Orgrimmar"},
        {"id": 1670, "name": "Oribos"},
        {"id": 2112, "name": "Valdrakken"},
        {"id": 2339, "name": "Dornogal"},
        {"id": 1220, "name": "Legion Dalaran"},
        {"id": 125, "name": "Dalaran (Northrend)"},
    ]
    return render_template('pathfinder.html', zones=zones)

# --- KNOWLEDGE POINT TRACKER ---
from knowledge_tracker import KnowledgeTracker, Profession

# Initialize Knowledge tracker once
knowledge_tracker = KnowledgeTracker()
knowledge_tracker.load_mock_data()

@app.route('/api/knowledge/checklist')
def knowledge_checklist():
    """
    Get knowledge point checklist for a profession
    Query params:
        profession (str): Profession name (e.g., "Blacksmithing")
        character (str): Optional character GUID
    """
    profession_name = request.args.get('profession', 'Blacksmithing')
    character_guid = request.args.get('character', None)
    
    try:
        profession = Profession[profession_name.upper().replace(" ", "_")]
    except KeyError:
        return jsonify({"error": f"Invalid profession: {profession_name}"}), 400
    
    checklist = knowledge_tracker.get_checklist(profession, character_guid)
    return jsonify(checklist)

@app.route('/api/knowledge/complete', methods=['POST'])
def knowledge_complete():
    """
    Mark a knowledge source as complete/incomplete
    POST body: {source_id: int, character: str, complete: bool}
    """
    data = request.get_json()
    source_id = data.get('source_id')
    character_guid = data.get('character')
    complete = data.get('complete', True)
    
    if not source_id or not character_guid:
        return jsonify({"error": "Missing source_id or character"}), 400
    
    if complete:
        knowledge_tracker.mark_complete(source_id, character_guid)
    else:
        knowledge_tracker.mark_incomplete(source_id, character_guid)
    
    return jsonify({"success": True, "source_id": source_id, "complete": complete})

@app.route('/knowledge')
def knowledge():
    """Knowledge Point Tracker UI"""
    # Get checklist for default profession
    checklist = knowledge_tracker.get_checklist(Profession.BLACKSMITHING, "GUID-MainWarrior")
    
    return render_template('knowledge.html', 
                          profession="Blacksmithing",
                          checklist=checklist)

# --- UTILITY TRACKER ---
from utility_tracker import UtilityTracker, CollectionType

# Initialize Utility tracker once
utility_tracker = UtilityTracker()
utility_tracker.load_mock_data()

@app.route('/api/utility/summary')
def utility_summary():
    """Get collection summary (mounts, toys, spells)"""
    summary = utility_tracker.get_summary()
    return jsonify(summary)

@app.route('/api/utility/missing')
def utility_missing():
    """
    Get missing items for a collection type
    Query params:
        type (str): Collection type (mount, toy, spell)
        limit (int): Max items to return (default: 10)
    """
    collection_type_str = request.args.get('type', 'mount').upper()
    limit = request.args.get('limit', 10, type=int)
    
    try:
        collection_type = CollectionType[collection_type_str]
    except KeyError:
        return jsonify({"error": f"Invalid collection type: {collection_type_str}"}), 400
    
    missing = utility_tracker.get_missing_items(collection_type, limit)
    return jsonify({"type": collection_type.value, "missing": missing})

@app.route('/utility')
def utility():
    """Utility Tracker UI"""
    summary = utility_tracker.get_summary()
    missing_mounts = utility_tracker.get_missing_items(CollectionType.MOUNT, 5)
    
    return render_template('utility.html',
                          summary=summary,
                          missing_mounts=missing_mounts)

                          summary=summary,
                          missing_mounts=missing_mounts)

# --- GOBLIN BRAIN MODULE ---
from goblin_engine import GoblinEngine, ItemType

# Initialize Goblin engine once
goblin_engine = GoblinEngine()
goblin_engine.load_mock_data()

@app.route('/api/goblin/dashboard')
def goblin_dashboard():
    """Get market analysis dashboard data"""
    analysis = goblin_engine.analyze_market()
    sniper = goblin_engine.get_sniper_list()
    
    return jsonify({
        "analysis": analysis,
        "sniper": sniper
    })

@app.route('/api/goblin/crafting')
def goblin_crafting():
    """Get prioritized crafting queue"""
    analysis = goblin_engine.analyze_market()
    
    # Filter for profitable items only
    queue = [
        opp for opp in analysis['opportunities'] 
        if opp['profit'] > 0 and opp['sale_rate'] >= 0.2
    ]
    
    return jsonify({"queue": queue})

@app.route('/goblin')
def goblin():
    """Goblin Brain UI"""
    analysis = goblin_engine.analyze_market()
    sniper = goblin_engine.get_sniper_list()
    
    return render_template('goblin.html',
                          analysis=analysis,
                          sniper=sniper)

# --- CODEX MODULE ---
from codex_engine import CodexEngine, Role

# Initialize Codex engine once
codex_engine = CodexEngine()
codex_engine.load_mock_data()

@app.route('/api/codex/instance/<int:instance_id>')
def codex_instance(instance_id):
    """Get instance details"""
    instance = codex_engine.get_instance(instance_id)
    if not instance:
        return jsonify({"error": "Instance not found"}), 404
    return jsonify(instance)

@app.route('/api/codex/encounter/<int:encounter_id>')
def codex_encounter(encounter_id):
    """Get encounter details"""
    encounter = codex_engine.get_encounter(encounter_id)
    if not encounter:
        return jsonify({"error": "Encounter not found"}), 404
    return jsonify(encounter)

@app.route('/codex')
def codex():
    """Codex UI - Encounter Guide"""
    # Default to Nerub-ar Palace
    instance = codex_engine.get_instance(1273)
    
    return render_template('codex.html',
                          instance=instance)
                          instance=instance)

# --- VAULT VISUALIZER ---
from vault_engine import VaultEngine, VaultCategory

# Initialize Vault engine once
vault_engine = VaultEngine()
vault_engine.load_mock_data()

@app.route('/api/vault/status')
def vault_status():
    """Get current vault status"""
    status = vault_engine.get_status()
    return jsonify(status)

@app.route('/api/vault/update', methods=['POST'])
def vault_update():
    """
    Update vault progress (Mock/Debug)
    POST body: {category: "Raid", slot_id: 1, progress: 3}
    """
    data = request.get_json()
    # In a real app, this would update the DB
    # For now, just return success
    return jsonify({"success": True, "message": "Vault updated (Mock)"})

@app.route('/vault')
def vault():
    """Vault Visualizer UI"""
    status = vault_engine.get_status()
    return render_template('vault.html', status=status)

# --- THE SCOUT MODULE ---
from scout_engine import ScoutEngine, EventType

# Initialize Scout engine once
scout_engine = ScoutEngine()
scout_engine.load_mock_data()

@app.route('/api/scout/alerts')
def scout_alerts():
    """Get active push alerts"""
    alerts = scout_engine.get_alerts()
    return jsonify({"alerts": alerts})

@app.route('/scout')
def scout():
    """The Scout UI - Push Alerts"""
    alerts = scout_engine.get_alerts()
    return render_template('scout.html', alerts=alerts)

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
from diplomat_engine import DiplomatEngine

# Initialize Diplomat engine once
diplomat_engine = DiplomatEngine()
diplomat_engine.load_mock_data()

@app.route('/api/diplomat/opportunities')
def diplomat_opportunities():
    """
    Get Paragon opportunities and recommended WQs
    Returns factions >80% to next reward with efficiency-ranked quests
    """
    recommendations = diplomat_engine.generate_recommendations()
    return jsonify(recommendations)

@app.route('/api/diplomat/quests')
def diplomat_quests():
    """
    Get recommended WQs for a specific faction
    Query param: faction_id (int)
    """
    faction_id = request.args.get('faction_id', type=int)
    if not faction_id:
        return jsonify({"error": "Missing 'faction_id' parameter"}), 400
    
    quests = diplomat_engine.get_recommended_quests(faction_id)
    return jsonify({"faction_id": faction_id, "quests": quests})

@app.route('/diplomat')
def diplomat():
    """Diplomat UI page"""
    # Get all data from engine
    recommendations = diplomat_engine.generate_recommendations()
    
    # Format for template
    factions_data = []
    for opp in recommendations['opportunities']:
        factions_data.append({
            "name": opp['faction_name'],
            "current": opp['current'],
            "max": opp['max'],
            "percent": opp['percent'],
            "is_close": opp['percent'] >= 80,
            "priority": opp['priority']
        })
    
    # Get top WQ recommendations
    sniper_list = []
    for opp in recommendations['opportunities']:
        for quest in opp.get('recommended_quests', [])[:3]:  # Top 3 per faction
            sniper_list.append({
                "faction": opp['faction_name'],
                "quest": quest['title'],
                "zone": quest['zone'],
                "reward": f"{quest['rep_reward']} Rep",
                "efficiency": f"{quest['efficiency']} rep/min ({quest['efficiency_score']})",
                "gold": f"{quest['gold']}g"
            })
    
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

# --- MIRROR MODULE ---

@app.route('/api/mirror/register', methods=['POST'])
def mirror_register():
    """
    Registers a device by hostname and returns its type.
    """
    try:
        data = request.get_json()
        hostname = data.get('hostname')
        if not hostname:
            return jsonify({"error": "Missing hostname"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if exists
        cur.execute("SELECT device_type FROM mirror.trusted_devices WHERE hostname = %s", (hostname,))
        row = cur.fetchone()
        
        if row:
            device_type = row[0]
            # Update last_seen
            cur.execute("UPDATE mirror.trusted_devices SET last_seen = CURRENT_TIMESTAMP WHERE hostname = %s", (hostname,))
        else:
            # Register new (Default to DESKTOP)
            device_type = 'DESKTOP'
            cur.execute("INSERT INTO mirror.trusted_devices (hostname, device_type) VALUES (%s, %s)", (hostname, device_type))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"hostname": hostname, "device_type": device_type})
    except Exception as e:
        print(f"Mirror register error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mirror/upload', methods=['POST'])
def mirror_upload():
    """
    Uploads a config file (macros/bindings).
    """
    try:
        data = request.get_json()
        hostname = data.get('hostname')
        file_type = data.get('file_type') # MACROS, BINDINGS
        content = data.get('content')
        char_guid = data.get('char_guid', 'GLOBAL')
        
        if not all([hostname, file_type, content]):
            return jsonify({"error": "Missing fields"}), 400

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get device type
        cur.execute("SELECT device_type FROM mirror.trusted_devices WHERE hostname = %s", (hostname,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Device not registered"}), 403
        device_type = row[0]
        
        # Upsert Profile
        sql = """
            INSERT INTO mirror.config_profiles (character_guid, device_type, file_type, content, updated_at)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (character_guid, device_type, file_type) 
            DO UPDATE SET content = EXCLUDED.content, updated_at = CURRENT_TIMESTAMP
        """
        cur.execute(sql, (char_guid, device_type, file_type, content))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({"status": "success", "message": "Config uploaded"})
    except Exception as e:
        print(f"Mirror upload error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mirror/sync', methods=['GET'])
def mirror_sync():
    """
    Downloads the latest config for a device.
    """
    try:
        hostname = request.args.get('hostname')
        file_type = request.args.get('file_type')
        char_guid = request.args.get('char_guid', 'GLOBAL')
        
        if not hostname or not file_type:
            return jsonify({"error": "Missing params"}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get device type
        cur.execute("SELECT device_type FROM mirror.trusted_devices WHERE hostname = %s", (hostname,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Device not registered"}), 403
        device_type = row[0]
        
        # Fetch Config
        cur.execute("""
            SELECT content, updated_at FROM mirror.config_profiles 
            WHERE character_guid = %s AND device_type = %s AND file_type = %s
        """, (char_guid, device_type, file_type))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row:
            return jsonify({
                "found": True,
                "content": row[0],
                "updated_at": row[1]
            })
        else:
            return jsonify({"found": False})
            
    except Exception as e:
        print(f"Mirror sync error: {e}")
        return jsonify({"error": str(e)}), 500

# --- UNIFIED DASHBOARD ---

# Legacy dashboard removed in favor of Resilient Dashboard


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
