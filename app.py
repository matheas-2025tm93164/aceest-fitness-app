from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

# Program Specification Data Store extracted from Aceestver-1.0.py
PROGRAMS = {
    "fat_loss": {
        "id": "fat_loss",
        "title": "Fat Loss (FL)",
        "workout": "Mon: 5x5 Back Squat + AMRAP\nTue: EMOM 20min Assault Bike\nWed: Bench Press + 21-15-9\nThu: 10RFT Deadlifts/Box Jumps\nFri: 30min Active Recovery",
        "diet": "B: 3 Egg Whites + Oats Idli\nL: Grilled Chicken + Brown Rice\nD: Fish Curry + Millet Roti\nTarget: 2,000 kcal",
        "color": "#e74c3c"
    },
    "muscle_gain": {
        "id": "muscle_gain",
        "title": "Muscle Gain (MG)",
        "workout": "Mon: Squat 5x5\nTue: Bench 5x5\nWed: Deadlift 4x6\nThu: Front Squat 4x8\nFri: Incline Press 4x10\nSat: Barbell Rows 4x10",
        "diet": "B: 4 Eggs + PB Oats\nL: Chicken Biryani (250g Chicken)\nD: Mutton Curry + Jeera Rice\nTarget: 3,200 kcal",
        "color": "#2ecc71"
    },
    "beginner": {
        "id": "beginner",
        "title": "Beginner (BG)",
        "workout": "Circuit Training: Air Squats, Ring Rows, Push-ups.\nFocus: Technique Mastery & Form (90% Threshold)",
        "diet": "Balanced Tamil Meals: Idli-Sambar, Rice-Dal, Chapati.\nProtein: 120g/day",
        "color": "#3498db"
    }
}

SITE_METRICS = {
    "capacity": "150 Users",
    "area": "10,000 sq ft",
    "break_even": "250 Members"
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ACEest Fitness & Gym</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a1a; color: white; margin: 0; padding: 20px; }
        .header { background-color: #d4af37; color: black; padding: 20px; text-align: center; font-size: 24px; font-weight: bold; }
        .container { display: flex; margin-top: 20px; }
        .sidebar { width: 30%; background-color: #2a2a2a; padding: 20px; border-radius: 5px; }
        .content { width: 70%; padding-left: 20px; }
        .card { background-color: #333; padding: 15px; border-radius: 5px; margin-bottom: 15px; }
        .metrics { background-color: #444; padding: 10px; font-family: monospace; }
        a { color: #d4af37; text-decoration: none; }
    </style>
</head>
<body>
    <div class="header">ACEest FUNCTIONAL FITNESS</div>
    <div class="container">
        <div class="sidebar">
            <h3>Client Programs</h3>
            <ul>
                <li><a href="/api/programs/fat_loss">Fat Loss (FL)</a></li>
                <li><a href="/api/programs/muscle_gain">Muscle Gain (MG)</a></li>
                <li><a href="/api/programs/beginner">Beginner (BG)</a></li>
            </ul>
            <h3>Site Metrics</h3>
            <div class="metrics">
                CAPACITY: {{ metrics.capacity }}<br>
                AREA: {{ metrics.area }}<br>
                BREAK-EVEN: {{ metrics.break_even }}
            </div>
        </div>
        <div class="content">
            <div class="card">
                <h2>Welcome to ACEest Fitness API Service</h2>
                <p>Use <code>/api/programs</code> or <code>/api/metrics</code> endpoints to fetch JSON data.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE, metrics=SITE_METRICS)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Healthy", "app": "ACEest Fitness & Gym"}), 200

@app.route('/api/programs', methods=['GET'])
def get_all_programs():
    return jsonify(PROGRAMS), 200

@app.route('/api/programs/<program_id>', methods=['GET'])
def get_program(program_id):
    program = PROGRAMS.get(program_id.lower())
    if not program:
        return jsonify({"error": "Program not found"}), 404
    return jsonify(program), 200

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    return jsonify(SITE_METRICS), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
