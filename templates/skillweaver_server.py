from flask import Flask, render_template, jsonify
import os

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('skillweaver_dashboard.html')

@app.route('/talents')
def talents():
    return render_template('skillweaver_talents.html')

@app.route('/gear')
def gear():
    return render_template('skillweaver_gear.html')

@app.route('/rotations')
def rotations():
    return render_template('skillweaver_rotations.html')

@app.route('/characters')
def characters():
    return render_template('skillweaver_characters.html')

@app.route('/settings')
def settings():
    return render_template('skillweaver_settings.html')

# API Endpoints
@app.route('/api/characters')
def get_characters():
    return jsonify({
        "characters": [
            {"name": "Thunderfist", "class": "Shaman", "spec": "Enhancement", "ilvl": 489, "dps": 4250},
            {"name": "Shadowmend", "class": "Priest", "spec": "Shadow", "ilvl": 476, "dps": 3890},
            {"name": "Moonfire", "class": "Druid", "spec": "Balance", "ilvl": 492, "dps": 4380},
            {"name": "Firestorm", "class": "Mage", "spec": "Fire", "ilvl": 485, "dps": 4120}
        ]
    })

@app.route('/api/talents/<character>')
def get_talents(character):
    return jsonify({
        "character": character,
        "current_build": "Raid - ST",
        "dps": 4250,
        "optimal": 92,
        "suggestions": [
            {"row": 6, "current": "Hailstorm", "suggested": "Elemental Spirits", "gain": 85},
            {"row": 9, "current": "Fire Nova", "suggested": "Crash Lightning", "gain": 52}
        ]
    })

@app.route('/api/gear/<character>')
def get_gear(character):
    return jsonify({
        "character": character,
        "upgrades": [
            {"slot": "Main Hand", "current": "Stormshaper's Blade (493)", "upgrade": "Fyr'alath (496)", "gain": 210, "priority": "high"},
            {"slot": "Trinket 2", "current": "Iridescence (486)", "upgrade": "Smold's Compass (489)", "gain": 95, "priority": "medium"},
            {"slot": "Ring 1", "current": "Crit II", "upgrade": "Haste III", "gain": 42, "priority": "low"}
        ]
    })

if __name__ == '__main__':
    print("🚀 Starting SkillWeaver on http://127.0.0.1:5003")
    app.run(host='0.0.0.0', port=5003, debug=False)
