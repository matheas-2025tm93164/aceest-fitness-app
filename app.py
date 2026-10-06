import io
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, Union

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
# Database Models
# -----------------------------------------------------------------------------

class User(db.Model):  # type: ignore [name-defined]
    """Authentication user table."""
    __tablename__ = 'users'
    username = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='admin')


class Client(db.Model):  # type: ignore [name-defined]
    """Client profile and program details."""
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=True)
    target_weight = db.Column(db.Float, nullable=True)
    target_adherence = db.Column(db.Float, nullable=True)
    program = db.Column(db.String(100), nullable=False)
    membership_status = db.Column(db.String(20), default='Active')
    membership_end = db.Column(db.String(20), nullable=True)

    # Relationships
    progress_logs = db.relationship('Progress', backref='client', lazy=True, cascade="all, delete-orphan")
    workouts = db.relationship('Workout', backref='client', lazy=True, cascade="all, delete-orphan")
    metrics = db.relationship('Metric', backref='client', lazy=True, cascade="all, delete-orphan")


class Progress(db.Model):  # type: ignore [name-defined]
    """Weekly adherence logs."""
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    week_date = db.Column(db.String(20), nullable=False)
    adherence = db.Column(db.Float, nullable=False)


class Workout(db.Model):  # type: ignore [name-defined]
    """Logged workout sessions."""
    __tablename__ = 'workouts'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    workout_type = db.Column(db.String(50), nullable=False)
    exercises = db.relationship('Exercise', backref='workout', lazy=True, cascade="all, delete-orphan")


class Exercise(db.Model):  # type: ignore [name-defined]
    """Exercise details linked to logged workouts."""
    __tablename__ = 'exercises'
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    sets = db.Column(db.Integer, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, nullable=False)


class Metric(db.Model):  # type: ignore [name-defined]
    """Historical body metric tracking."""
    __tablename__ = 'metrics'
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    body_fat = db.Column(db.Float, nullable=True)

# -----------------------------------------------------------------------------
# Business Logic Helpers
# -----------------------------------------------------------------------------

PROGRAM_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "Hypertrophy": {"factor": 1.2, "routine": "Day 1: Upper Body, Day 2: Lower Body, Day 3: Push, Day 4: Pull"},
    "Fat Loss": {"factor": 0.9, "routine": "Day 1: Full Body HIIT, Day 2: Steady Cardio, Day 3: Circuits"},
    "Endurance": {"factor": 1.1, "routine": "Day 1: Tempo Run, Day 2: Core & Mobility, Day 3: Long Run"}
}

def calculate_target_calories(weight: float, program: str) -> float:
    """Calculates daily target calories based on program multipliers."""
    template = PROGRAM_TEMPLATES.get(program, {"factor": 1.0})
    base_bmr = weight * 22.0
    return round(base_bmr * template["factor"], 2)

def calculate_bmi_info(weight: float, height_cm: Optional[float]) -> Tuple[Optional[float], str]:
    """Calculates BMI and risk classification."""
    if not height_cm or height_cm <= 0:
        return None, "Height context missing"
    
    height_m = height_cm / 100.0
    bmi = round(weight / (height_m ** 2), 2)
    
    if bmi < 18.5:
        risk = "Underweight - Moderate health risk"
    elif 18.5 <= bmi < 25.0:
        risk = "Normal weight - Low health risk"
    elif 25.0 <= bmi < 30.0:
        risk = "Overweight - Increased health risk"
    else:
        risk = "Obese - High health risk"
        
    return bmi, risk

# -----------------------------------------------------------------------------
# Web Routes & UI Screen Controllers
# -----------------------------------------------------------------------------

BASE_HEADER = """
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
"""

BASE_FOOTER = """
    </div>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login() -> Union[Response, str]:
    """Authentication view supporting role logins."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.get(username)
        if user and check_password_hash(user.password_hash, password):
            session['user'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        
        flash("Invalid credentials.")
    
    login_html = BASE_HEADER + """
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
    """ + BASE_FOOTER
    return render_template_string(login_html)

@app.route('/logout')
def logout() -> Response:
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
def dashboard() -> Union[Response, str]:
    """Main management dashboard."""
    if 'user' not in session:
        return redirect(url_for('login'))
        
    clients = Client.query.all()
    selected_id = request.args.get('client_id', type=int)
    
    selected_client = Client.query.get(selected_id) if selected_id else (clients[0] if clients else None)
    
    target_calories = 0.0
    bmi_info = (None, "N/A")
    if selected_client:
        target_calories = calculate_target_calories(selected_client.weight, selected_client.program)
        bmi_info = calculate_bmi_info(selected_client.weight, selected_client.height)

    dashboard_html = BASE_HEADER + """
    <h1>ACEest Fitness Management Portal</h1>
    <div class="grid">
        <!-- Left Panel: Client Profile Entry & Management -->
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

        <!-- Right Panel: Dynamic Details & Client Notebook -->
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
                <p><strong>Membership Status:</strong> {{ selected_client.membership_status }} (Expires: {{ selected_client.membership_end or 'N/A' }})</p>
                <p><strong>Target Daily Intake:</strong> {{ target_calories }} kcal/day</p>
                <p><strong>BMI Index:</strong> {{ bmi_info[0] if bmi_info[0] else 'N/A' }} ({{ bmi_info[1] }})</p>
                
                <hr style="border-color: #444;">
                <h3>Management Actions</h3>
                <a href="{{ url_for('export_pdf', client_id=selected_client.id) }}" class="btn">Export PDF Summary</a>
                <a href="{{ url_for('generate_ai_program', client_id=selected_client.id) }}" class="btn">Generate AI Routine</a>
            </div>

            <!-- Tabular View / Action Cards -->
            <div class="card">
                <h3>Log Progress & Analytics</h3>
                <form action="{{ url_for('log_adherence', client_id=selected_client.id) }}" method="POST" style="margin-bottom: 15px;">
                    <h4>Log Adherence Progress</h4>
                    <input type="number" step="0.1" name="adherence" placeholder="Adherence %" required>
                    <button type="submit" class="btn" style="margin-top: 5px;">Log Weekly Adherence</button>
                </form>

                <h4>Progress Visualizations</h4>
                <img src="{{ url_for('progress_chart', client_id=selected_client.id) }}" alt="Adherence Trend" style="width: 100%; border-radius: 4px; margin-top: 10px;">
            </div>
            {% endif %}
        </div>
    </div>
    """ + BASE_FOOTER
    return render_template_string(dashboard_html, clients=clients, selected_client=selected_client, target_calories=target_calories, bmi_info=bmi_info)

@app.route('/clients/save', methods=['POST'])
def save_client() -> Response:
    """Save or update client records in SQLite database."""
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
            membership_end=datetime.now().strftime('%Y-12-31')
        )
        db.session.add(client)
        
    db.session.commit()
    flash("Client record saved successfully.")
    return redirect(url_for('dashboard', client_id=client.id))

@app.route('/clients/<int:client_id>/log-adherence', methods=['POST'])
def log_adherence(client_id: int) -> Response:
    """Log weekly adherence progress."""
    adherence = float(request.form['adherence'])
    week_date = datetime.now().strftime('Week %U (%Y-%m-%d)')
    
    log = Progress(client_id=client_id, week_date=week_date, adherence=adherence)
    db.session.add(log)
    db.session.commit()
    
    flash("Adherence progress logged successfully.")
    return redirect(url_for('dashboard', client_id=client_id))

@app.route('/clients/<int:client_id>/ai-generate')
def generate_ai_program(client_id: int) -> Response:
    """Generates automated workout routine based on program template."""
    client = Client.query.get_or_404(client_id)
    template = PROGRAM_TEMPLATES.get(client.program, {"routine": "General Fitness Routine"})
    
    new_workout = Workout(
        client_id=client.id, 
        date=datetime.now().strftime('%Y-%m-%d'), 
        workout_type=f"AI Routine ({client.program})"
    )
    db.session.add(new_workout)
    db.session.commit()
    
    flash(f"AI Template Applied: {template['routine']}")
    return redirect(url_for('dashboard', client_id=client.id))

@app.route('/clients/<int:client_id>/progress-chart.png')
def progress_chart(client_id: int) -> Response:
    """Renders Matplotlib adherence graph dynamically to PNG buffer."""
    logs = Progress.query.filter_by(client_id=client_id).all()
    
    x = [p.week_date for p in logs] if logs else ["Initial"]
    y = [p.adherence for p in logs] if logs else [0.0]

    fig, ax = plt.subplots(figsize=(6, 3))
    fig.patch.set_facecolor('#2A2A2A')
    ax.set_facecolor('#1E1E1E')
    
    ax.plot(x, y, marker='o', color='#D4AF37', linewidth=2)
    ax.set_title("Weekly Adherence Progress (%)", color='#D4AF37')
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
    """Generates PDF summary document using FPDF library."""
    client = Client.query.get_or_404(client_id)
    calories = calculate_target_calories(client.weight, client.program)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Client Report: {client.name}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 8, f"Age: {client.age}", ln=True)
    pdf.cell(0, 8, f"Weight: {client.weight} kg", ln=True)
    pdf.cell(0, 8, f"Height: {client.height or 'N/A'} cm", ln=True)
    pdf.cell(0, 8, f"Active Program: {client.program}", ln=True)
    pdf.cell(0, 8, f"Target Daily Intake: {calories} kcal", ln=True)
    pdf.cell(0, 8, f"Membership Expiration: {client.membership_end or 'N/A'}", ln=True)

    pdf_output = pdf.output()
    pdf_bytes = pdf_output.encode('latin1') if isinstance(pdf_output, str) else bytes(pdf_output)
    
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
    """Initializes tables and seeds default admin account."""
    with app.app_context():
        db.create_all()
        if not User.query.get('admin'):
            admin = User(
                username='admin', 
                password_hash=generate_password_hash('admin'), 
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
