import io
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from flask import (
    Flask, render_template_string, request, redirect, 
    url_for, session, flash, send_file, Response
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fpdf import FPDF

# Initialize Flask application and database configuration
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aceest.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# -----------------------------------------------------------------------------
# Database Models (Schema Evolution: v2.1.2 - v3.2.4)
# -----------------------------------------------------------------------------

class User(db.Model):  # type: ignore [name-defined]
    """Authentication user table[cite: 316, 317]."""
    __tablename__ = 'users'
    username = db.Column(db.String(80), primary_key=True)[cite: 317]
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin')[cite: 316]


class Client(db.Model):  # type: ignore [name-defined]
    """Client profile and program details[cite: 311, 312, 314, 316, 317]."""
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)[cite: 311]
    age = db.Column(db.Integer, nullable=False)[cite: 311]
    weight = db.Column(db.Float, nullable=False)[cite: 311]
    height = db.Column(db.Float, nullable=True)[cite: 314]
    target_weight = db.Column(db.Float, nullable=True)[cite: 314]
    target_adherence = db.Column(db.Float, nullable=True)[cite: 314]
    program = db.Column(db.String(100), nullable=False)[cite: 311]
    membership_status = db.Column(db.String(20), default='Active')[cite: 317]
    membership_end = db.Column(db.String(20), nullable=True)[cite: 316, 317]

    # Relationships[cite: 312, 314]
    progress_logs = db.relationship('Progress', backref='client', lazy=True, cascade="all, delete-orphan")[cite: 312]
    workouts = db.relationship('Workout', backref='client', lazy=True, cascade="all, delete-orphan")[cite: 314]
    metrics = db.relationship('Metric', backref='client', lazy=True, cascade="all, delete-orphan")[cite: 314]


class Progress(db.Model):  # type: ignore [name-defined]
    """Weekly adherence logs[cite: 312]."""
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)[cite: 312]
    week_date = db.Column(db.String(20), nullable=False)[cite: 312]
    adherence = db.Column(db.Float, nullable=False)[cite: 312]


class Workout(db.Model):  # type: ignore [name-defined]
    """Logged workout sessions[cite: 314]."""
    __tablename__ = 'workouts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)[cite: 314]
    date = db.Column(db.String(20), nullable=False)[cite: 314]
    workout_type = db.Column(db.String(50), nullable=False)[cite: 314]
    exercises = db.relationship('Exercise', backref='workout', lazy=True, cascade="all, delete-orphan")[cite: 314]


class Exercise(db.Model):  # type: ignore [name-defined]
    """Exercise details linked to logged workouts[cite: 314]."""
    __tablename__ = 'exercises'
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)[cite: 314]
    name = db.Column(db.String(100), nullable=False)[cite: 314]
    sets = db.Column(db.Integer, nullable=False)[cite: 314]
    reps = db.Column(db.Integer, nullable=False)[cite: 314]
    weight = db.Column(db.Float, nullable=False)[cite: 314]


class Metric(db.Model):  # type: ignore [name-defined]
    """Historical body metric tracking[cite: 314]."""
    __tablename__ = 'metrics'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)[cite: 314]
    date = db.Column(db.String(20), nullable=False)[cite: 314]
    weight = db.Column(db.Float, nullable=False)[cite: 314]
    body_fat = db.Column(db.Float, nullable=True)[cite: 314]

# -----------------------------------------------------------------------------
# Business Logic Helpers (v1.1 - v3.2.4)
# -----------------------------------------------------------------------------

PROGRAM_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "Hypertrophy": {"factor": 1.2, "routine": "Day 1: Upper Body, Day 2: Lower Body, Day 3: Push, Day 4: Pull"},[cite: 311, 317]
    "Fat Loss": {"factor": 0.9, "routine": "Day 1: Full Body HIIT, Day 2: Steady Cardio, Day 3: Circuits"},[cite: 311, 317]
    "Endurance": {"factor": 1.1, "routine": "Day 1: Tempo Run, Day 2: Core & Mobility, Day 3: Long Run"}[cite: 311, 317]
}

def calculate_target_calories(weight: float, program: str) -> float:
    """Calculates daily target calories based on program multipliers[cite: 311]."""
    template = PROGRAM_TEMPLATES.get(program, {"factor": 1.0})[cite: 311, 317]
    base_bmr = weight * 22.0
    return round(base_bmr * template["factor"], 2)[cite: 311]

def calculate_bmi_info(weight: float, height_cm: Optional[float]) -> Tuple[Optional[float], str]:
    """Calculates BMI and risk classification[cite: 314]."""
    if not height_cm or height_cm <= 0:
        return None, "Height context missing"[cite: 314]
    
    height_m = height_cm / 100.0
    bmi = round(weight / (height_m ** 2), 2)[cite: 314]
    
    if bmi < 18.5:
        risk = "Underweight - Moderate health risk"[cite: 314]
    elif 18.5 <= bmi < 25.0:
        risk = "Normal weight - Low health risk"[cite: 314]
    elif 25.0 <= bmi < 30.0:
        risk = "Overweight - Increased health risk"[cite: 314]
    else:
        risk = "Obese - High health risk"[cite: 314]
        
    return bmi, risk

# -----------------------------------------------------------------------------
# Web Routes & UI Screen Controllers (v3.1.2 - v3.2.4 Frame-based equivalence)
# -----------------------------------------------------------------------------

BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ACEest Fitness Portal</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #121212; color: #E0E0E0; margin: 0; padding: 20px; }
        .container { max-width: 1100px; margin: 0 auto; background: #1E1E1E; padding: 25px; border-radius: 8px; border: 1px solid #D4AF37; }
        h1, h2, h3 { color: #D4AF37; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #333; padding: 10px; text-align: left; }
        th { background-color: #2A2A2A; color: #D4AF37; }
        .btn { background: #D4AF37; color: #121212; padding: 8px 16px; border: none; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; border-radius: 4px; }
        .btn-danger { background: #A93226; color: white; }
        .card { background: #2A2A2A; padding: 15px; margin-bottom: 20px; border-radius: 6px; }
        .form-group { margin-bottom: 12px; }
        label { display: block; margin-bottom: 4px; }
        input, select { width: 100%; padding: 8px; box-sizing: border-box; background: #121212; color: white; border: 1px solid #444; }
        .grid { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; }
        .nav { margin-bottom: 20px; text-align: right; }
    </style>
</head>
<body>
    <div class="container">
        <div class="nav">
            {% if session.get('user') %}
                <span>Logged in as: <strong>{{ session['user'] }}</strong></span> | 
                <a href="{{ url_for('logout') }}" class="btn btn-danger">Logout</a>
            {% endif %}
        </div>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for msg in messages %}
              <div style="background: #333; color: #D4AF37; padding: 10px; margin-bottom: 15px; border-left: 4px solid #D4AF37;">{{ msg }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login() -> Response | str:
    """Authentication view supporting role logins[cite: 316, 317]."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.get(username)[cite: 316, 317]
        if user and check_password_hash(user.password_hash, password):
            session['user'] = user.username[cite: 316]
            session['role'] = user.role[cite: 316]
            return redirect(url_for('dashboard'))[cite: 317]
        
        flash("Invalid credentials.")
    
    login_html = BASE_TEMPLATE + """
    {% block content %}
    <h2>System Login</h2>
    <form method="POST" style="max-width: 400px;">
        <div class="form-group">
            <label>Username</label>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>Password</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn">Login</button>
    </form>
    {% endblock %}
    """
    return render_template_string(login_html)

@app.route('/logout')
def logout() -> Response:
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
def dashboard() -> Response | str:
    """Main management dashboard[cite: 311, 314, 317]."""
    if 'user' not in session:
        return redirect(url_for('login'))[cite: 316, 317]
        
    clients = Client.query.all()[cite: 312]
    selected_id = request.args.get('client_id', type=int)
    
    selected_client = Client.query.get(selected_id) if selected_id else (clients[0] if clients else None)
    
    target_calories = 0.0
    bmi_info = (None, "N/A")
    if selected_client:
        target_calories = calculate_target_calories(selected_client.weight, selected_client.program)[cite: 311]
        bmi_info = calculate_bmi_info(selected_client.weight, selected_client.height)[cite: 314]

    dashboard_html = BASE_TEMPLATE + """
    {% block content %}
    <h1>ACEest Fitness Management Portal</h1>
    <div class="grid">
        <!-- Left Panel: Client Profile Entry & Management[cite: 311, 314] -->
        <div>
            <div class="card">
                <h3>Add / Update Client Profile</h3>
                <form action="{{ url_for('save_client') }}" method="POST">
                    <input type="hidden" name="client_id" value="{{ selected_client.id if selected_client else '' }}">
                    <div class="form-group">
                        <label>Client Name</label>
                        <input type="text" name="name" value="{{ selected_client.name if selected_client else '' }}" required>
                    </div>
                    <div class="form-group">
                        <label>Age</label>
                        <input type="number" name="age" value="{{ selected_client.age if selected_client else '' }}" required>
                    </div>
                    <div class="form-group">
                        <label>Weight (kg)</label>
                        <input type="number" step="0.1" name="weight" value="{{ selected_client.weight if selected_client else '' }}" required>
                    </div>
                    <div class="form-group">
                        <label>Height (cm)</label>
                        <input type="number" step="0.1" name="height" value="{{ selected_client.height if selected_client else '' }}">
                    </div>
                    <div class="form-group">
                        <label>Target Weight (kg)</label>
                        <input type="number" step="0.1" name="target_weight" value="{{ selected_client.target_weight if selected_client else '' }}">
                    </div>
                    <div class="form-group">
                        <label>Target Adherence (%)</label>
                        <input type="number" step="0.1" name="target_adherence" value="{{ selected_client.target_adherence if selected_client else '' }}">
                    </div>
                    <div class="form-group">
                        <label>Program</label>
                        <select name="program">
                            <option value="Hypertrophy" {% if selected_client and selected_client.program == 'Hypertrophy' %}selected{% endif %}>Hypertrophy</option>
                            <option value="Fat Loss" {% if selected_client and selected_client.program == 'Fat Loss' %}selected{% endif %}>Fat Loss</option>
                            <option value="Endurance" {% if selected_client and selected_client.program == 'Endurance' %}selected{% endif %}>Endurance</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">Save Client Profile</button>
                </form>
            </div>
        </div>

        <!-- Right Panel: Dynamic Details & Client Notebook[cite: 311, 314] -->
        <div>
            <div class="card">
                <h3>Select Active Client</h3>
                <form method="GET" action="{{ url_for('dashboard') }}">
                    <select name="client_id" onchange="this.form.submit()">
                        <option value="">-- Select Client --</option>
                        {% for c in clients %}
                            <option value="{{ c.id }}" {% if selected_client and c.id == selected_client.id %}selected{% endif %}>{{ c.name }}</option>
                        {% endfor %}
                    </select>
                </form>
            </div>

            {% if selected_client %}
            <div class="card">
                <h2>Client Details: {{ selected_client.name }}</h2>
                <p><strong>Membership Status:</strong> {{ selected_client.membership_status }} (Expires: {{ selected_client.membership_end or 'N/A' }})</p>[cite: 316, 317]
                <p><strong>Target Daily Intake:</strong> {{ target_calories }} kcal/day</p>[cite: 311]
                <p><strong>BMI Index:</strong> {{ bmi_info[0] if bmi_info[0] else 'N/A' }} ({{ bmi_info[1] }})</p>[cite: 314]
                
                <hr style="border-color: #444;">
                <h3>Management Actions</h3>
                <a href="{{ url_for('export_pdf', client_id=selected_client.id) }}" class="btn">Export PDF Summary</a>[cite: 316]
                <a href="{{ url_for('generate_ai_program', client_id=selected_client.id) }}" class="btn">Generate AI Routine</a>[cite: 316, 317]
            </div>

            <!-- Tabular View / Action Cards[cite: 314] -->
            <div class="card">
                <h3>Log Progress & Analytics</h3>
                <form action="{{ url_for('log_adherence', client_id=selected_client.id) }}" method="POST" style="margin-bottom: 15px;">
                    <h4>Log Adherence Progress</h4>
                    <input type="number" step="0.1" name="adherence" placeholder="Adherence %" required>
                    <button type="submit" class="btn" style="margin-top: 5px;">Log Weekly Adherence</button>
                </form>

                <h4>Progress Visualizations</h4>
                <img src="{{ url_for('progress_chart', client_id=selected_client.id) }}" alt="Adherence Trend" style="width: 100%; border-radius: 4px; margin-top: 10px;">[cite: 313, 316]
            </div>
            {% endif %}
        </div>
    </div>
    {% endblock %}
    """
    return render_template_string(dashboard_html, clients=clients, selected_client=selected_client, target_calories=target_calories, bmi_info=bmi_info)

@app.route('/clients/save', methods=['POST'])
def save_client() -> Response:
    """Save or update client records in SQLite database[cite: 312, 314]."""
    if 'user' not in session:
        return redirect(url_for('login'))
        
    client_id = request.form.get('client_id')
    name = request.form['name']
    age = int(request.form['age'])
    weight = float(request.form['weight'])
    height = float(request.form['height']) if request.form.get('height') else None
    target_weight = float(request.form['target_weight']) if request.form.get('target_weight') else None
    target_adherence = float(request.form['target_adherence']) if request.form.get('target_adherence') else None
    program = request.form['program']

    if client_id:
        client = Client.query.get(client_id)
        if client:
            client.name = name
            client.age = age
            client.weight = weight
            client.height = height
            client.target_weight = target_weight
            client.target_adherence = target_adherence
            client.program = program
    else:
        client = Client(
            name=name, age=age, weight=weight, height=height,
            target_weight=target_weight, target_adherence=target_adherence,
            program=program, membership_status='Active',
            membership_end=datetime.now().strftime('%Y-%12-31')
        )
        db.session.add(client)
        
    db.session.commit()
    flash(f"Client record saved successfully.")
    return redirect(url_for('dashboard', client_id=client.id))

@app.route('/clients/<int:client_id>/log-adherence', methods=['POST'])
def log_adherence(client_id: int) -> Response:
    """Log weekly adherence progress[cite: 312]."""
    adherence = float(request.form['adherence'])
    week_date = datetime.now().strftime('Week %U (%Y-%m-%d)')[cite: 312]
    
    log = Progress(client_id=client_id, week_date=week_date, adherence=adherence)[cite: 312]
    db.session.add(log)
    db.session.commit()
    
    flash("Adherence progress logged successfully.")[cite: 312]
    return redirect(url_for('dashboard', client_id=client_id))

@app.route('/clients/<int:client_id>/ai-generate')
def generate_ai_program(client_id: int) -> Response:
    """Generates automated workout routine based on program template[cite: 316, 317]."""
    client = Client.query.get_or_404(client_id)
    template = PROGRAM_TEMPLATES.get(client.program, {"routine": "General Fitness Routine"})[cite: 317]
    
    # Store dynamic structure in client workout history[cite: 314, 316, 317]
    new_workout = Workout(
        client_id=client.id, 
        date=datetime.now().strftime('%Y-%m-%d'), 
        workout_type=f"AI Routine ({client.program})"[cite: 316, 317]
    )
    db.session.add(new_workout)
    db.session.commit()
    
    flash(f"AI Template Applied: {template['routine']}")[cite: 316, 317]
    return redirect(url_for('dashboard', client_id=client.id))

@app.route('/clients/<int:client_id>/progress-chart.png')
def progress_chart(client_id: int) -> Response:
    """Renders Matplotlib adherence graph dynamically to PNG buffer[cite: 313, 316]."""
    logs = Progress.query.filter_by(client_id=client_id).all()[cite: 312, 313]
    
    x = [p.week_date for p in logs] if logs else ["Initial"]
    y = [p.adherence for p in logs] if logs else [0.0]

    fig, ax = plt.subplots(figsize=(6, 3))
    fig.patch.set_facecolor('#2A2A2A')
    ax.set_facecolor('#1E1E1E')
    
    ax.plot(x, y, marker='o', color='#D4AF37', linewidth=2)[cite: 313]
    ax.set_title("Weekly Adherence Progress (%)", color='#D4AF37')[cite: 313]
    ax.tick_params(colors='white')
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white')
    ax.spines['left'].set_color('white')
    ax.spines['right'].set_color('white')
    plt.xticks(rotation=15, fontsize=8)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor())
    buf.seek(0)
    plt.close(fig)
    
    return Response(buf.getvalue(), mimetype='image/png')

@app.route('/clients/<int:client_id>/export-pdf')
def export_pdf(client_id: int) -> Response:
    """Generates PDF summary document using FPDF library[cite: 316]."""
    client = Client.query.get_or_404(client_id)
    calories = calculate_target_calories(client.weight, client.program)[cite: 311]

    pdf = FPDF()[cite: 316]
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Client Report: {client.name}", ln=True, align='C')[cite: 316]
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Age: {client.age}", ln=True)[cite: 316]
    pdf.cell(0, 8, f"Weight: {client.weight} kg", ln=True)[cite: 316]
    pdf.cell(0, 8, f"Height: {client.height or 'N/A'} cm", ln=True)[cite: 316]
    pdf.cell(0, 8, f"Active Program: {client.program}", ln=True)[cite: 316]
    pdf.cell(0, 8, f"Target Daily Intake: {calories} kcal", ln=True)[cite: 316]
    pdf.cell(0, 8, f"Membership Expiration: {client.membership_end or 'N/A'}", ln=True)[cite: 316]

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Report_{client.name.replace(' ', '_')}.pdf"
    )

# -----------------------------------------------------------------------------
# Database Setup & Application Startup
# -----------------------------------------------------------------------------

def init_db() -> None:
    """Initializes tables and seeds default admin account[cite: 312, 316, 317]."""
    with app.app_context():
        db.create_all()[cite: 312, 314]
        if not User.query.get('admin'):[cite: 316]
            admin = User(
                username='admin', 
                password_hash=generate_password_hash('admin'), 
                role='admin'
            )[cite: 316]
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()[cite: 312, 317]
    app.run(debug=True, port=5000)
