import os
from dotenv import load_dotenv
from ai_reply import get_ai_reply
from whatsapp_bot import send_whatsapp
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "gen-lang-client-0801549860-936e46514e16.json",
    scope
)

client = gspread.authorize(creds)

from flask import Flask, render_template_string, session, redirect, url_for, request

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "gymcrmsecret")

def clean_phone_number(phone):
    if not phone:
        return ""
    phone = str(phone).strip()
    if phone.startswith("whatsapp:"):
        phone = phone.replace("whatsapp:", "")
    for char in [" ", "-", "(", ")", ".", "+"]:
        phone = phone.replace(char, "")
    # Default to Indian prefix if it's 10 digits
    if len(phone) == 10 and phone.isdigit():
        return "+91" + phone
    return "+" + phone
GYM_LEADS = [
    {
        "name": "Sarah Jenkins",
        "question": "Looking for personal training rates for weight loss.",
        "score": 92,
        "follow_up": "Call tomorrow morning",
    },
    {
        "name": "Michael Chang",
        "question": "Do you offer a student discount for the 12-month pass?",
        "score": 78,
        "follow_up": "Email pricing brochure",
    },
    {
        "name": "Amanda Ross",
        "question": "Interested in morning yoga classes. Are they beginner friendly?",
        "score": 85,
        "follow_up": "Send class schedule via SMS",
    },
    {
        "name": "David Miller",
        "question": "What corporate membership options do you have for a team of 15?",
        "score": 95,
        "follow_up": "Schedule a Zoom call with HR",
    },
    {
        "name": "Elena Rostova",
        "question": "Is the pool heated during winter months?",
        "score": 64,
        "follow_up": "Email facility details",
    },
]

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gym Lead Dashboard</title>
    <!-- Bootstrap 5 CSS via CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {
            background-color: #f8f9fa;
        }
        .navbar-brand {
            font-weight: 700;
            letter-spacing: 0.5px;
        }
        .card {
            border: none;
            border-radius: 12px;
        }
        .table-responsive {
            border-radius: 12px;
            overflow: hidden;
        }
        .badge-high { background-color: #d1e7dd; color: #0f5132; }
        .badge-medium { background-color: #fff3cd; color: #664d03; }
        .badge-low { background-color: #f8d7da; color: #842029; }
    </style>
</head>
<body>

    <!-- Navigation Bar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4 shadow-sm">
        <div class="container">
            <a class="navbar-brand d-flex align-items-center" href="#">
                <span class="fs-4 me-2">🏋️‍♂️</span> IronPulse Admin
            </a>
            <span class="navbar-text text-white-50">Gym CRM Portal</span>
            <a href="/logout" class="btn btn-danger btn-sm">
                Logout
            </a>
        </div>
    </nav>

    <!-- Main Content Container -->
    <div class="container">
        
        <!-- Summary Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-4">
                <div class="card p-3 shadow-sm border-start border-primary border-4">
                    <div class="text-muted small uppercase font-weight-bold">Total Active Leads</div>
                    <div class="fs-3 fw-bold">{{ leads|length }}</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card p-3 shadow-sm border-start border-success border-4">
                    <div class="text-muted small uppercase font-weight-bold">Avg. Lead Score</div>
                    <div class="fs-3 fw-bold">82.8</div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card p-3 shadow-sm border-start border-warning border-4">
                    <div class="text-muted small uppercase font-weight-bold">Pending Actions</div>
                    <div class="fs-3 fw-bold">5</div>
                </div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="row g-3 mb-4">
            <div class="col-md-6">
                <div class="card p-4 shadow-sm h-100">
                    <h6 class="text-secondary small uppercase font-weight-bold mb-3">Lead Status Distribution</h6>
                    <div style="max-height: 250px;" class="d-flex justify-content-center align-items-center">
                        <canvas id="leadChart"></canvas>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card p-4 shadow-sm h-100">
                    <h6 class="text-secondary small uppercase font-weight-bold mb-3">Lead Distribution Bar Chart</h6>
                    <div style="max-height: 250px;">
                        <canvas id="trendChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Leads Table Card -->
        <div class="card shadow-sm mb-5">
            <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
                <h5 class="mb-0 fw-bold text-secondary">Incoming Leads Pipeline</h5>
                <button class="btn btn-sm btn-primary">+ Add Lead</button>
            </div>
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-dark table-hover align-middle">
    <thead>
        <tr>
            <th>Name</th>
            <th>Question</th>
            <th>Lead Score</th>
            <th>Intent</th>
            <th>Follow Up</th>
        </tr>
    </thead>

    <tbody>
        {% for lead in leads %}
        <tr>
            <td>{{ lead["Name"] }}</td>

            <td>{{ lead["Your Question"] }}</td>

            <td>
                {% if lead.get("Lead Score", "") == "HOT" %}
                🔥 HOT

                {% elif lead.get("Lead Score", "") == "WARM" %}
                ⚡ WARM

                {% else %}
                ❄️ COLD
                {% endif %}
            </td>
            <td>{{ lead.get("Intent","") }}</td>
            <td>{{ lead.get("Follow Up","") }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap Bundle JS via CDN -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    const trendCtx = document.getElementById('trendChart');

    new Chart(trendCtx, {
        type: 'bar',
        data: {
            labels: ['HOT', 'WARM', 'COLD'],
            datasets: [{
                label: 'Lead Distribution',
                data: [{{ hot_count }}, {{ warm_count }}, {{ cold_count }}]
        }]
    }
});
    const ctx = document.getElementById('leadChart');

    new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['HOT', 'WARM', 'COLD'],
        datasets: [{
            data: [{{ hot_count }}, {{ warm_count }}, {{ cold_count }}]
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: true
    }
});
</script>
</body>
</html>
"""

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":

            session["admin"] = True

            return redirect(url_for("dashboard"))

    return """
    <html>
    <head>
        <title>Gym CRM Login</title>

        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

        <style>

            body{
                background:#0f172a;
                display:flex;
                justify-content:center;
                align-items:center;
                height:100vh;
            }

            .card{
                width:350px;
                border-radius:20px;
            }

        </style>

    </head>

    <body>

        <div class="card p-4 shadow-lg">

            <h2 class="text-center mb-4">Gym CRM Login</h2>

            <form method="POST">

                <input
                    type="text"
                    name="username"
                    class="form-control mb-3"
                    placeholder="Username"
                >

                <input
                    type="password"
                    name="password"
                    class="form-control mb-3"
                    placeholder="Password"
                >

                <button class="btn btn-dark w-100">
                    Login
                </button>

            </form>

        </div>

    </body>
    </html>
    """

@app.route("/logout")
def logout():

    session.pop("admin", None)

    return redirect(url_for("login"))

def detect_intent(question):

    question = question.lower()

    intents = {

        "pricing": [
            "price", "pricing", "fees", "membership",
            "cost", "plan", "package", "monthly"
        ],

        "weight_loss": [
            "weight loss", "fat loss", "lose weight",
            "slim", "cut fat"
        ],

        "muscle_gain": [
            "muscle", "bulk", "gain",
            "bodybuilding", "strength"
        ],

        "personal_training": [
            "trainer", "personal trainer",
            "coach"
        ],

        "timing": [
            "timing", "open", "close",
            "time", "schedule"
        ],

        "trial": [
            "trial", "demo", "visit",
            "check gym"
        ]

    }

    for intent, keywords in intents.items():

        for keyword in keywords:

            if keyword in question:
                return intent

    return "general"


@app.route("/")
def dashboard():
    if not session.get("admin"):
        return redirect(url_for("login"))

    sheet = client.open("A").sheet1
    data = sheet.get_all_records()
    
    # Pre-calculate counts
    hot_count = sum(1 for lead in data if lead.get("Lead Score") == "HOT")
    warm_count = sum(1 for lead in data if lead.get("Lead Score") == "WARM")
    cold_count = sum(1 for lead in data if lead.get("Lead Score") == "COLD")
    total_leads = len(data)

    sheet_updates = []
    has_changes = False

    for i, lead in enumerate(data):
        # Skip already-processed leads entirely
        if lead.get("WhatsApp Sent") == "YES":
            continue

        # Process new/unsent leads
        question = str(lead.get("Your Question", "")).strip()
        phone_raw = str(lead.get("Phone Number", ""))
        
        # Skip completely blank rows that can be returned by Google Sheets
        if not question and not phone_raw.strip():
            continue
            
        cleaned_phone = clean_phone_number(phone_raw)
        
        intent = detect_intent(question)
        question_lower = question.lower()
        
        if any(word in question_lower for word in ["pricing", "membership", "fees", "plan","trainer","weight","loss","fitness","muscle","fat"]):
            lead["Lead Score"] = "HOT"
            lead["Intent"] = intent
            ai_message = get_ai_reply(question)
            lead["Follow Up"] = ai_message
            send_whatsapp(cleaned_phone, ai_message)
            lead["WhatsApp Sent"] = "YES"
            has_changes = True
        elif any(word in question_lower for word in ["timing", "join", "trial"]):
            lead["Lead Score"] = "WARM"
            lead["Intent"] = intent
            ai_message = get_ai_reply(question)
            lead["Follow Up"] = ai_message
            send_whatsapp(cleaned_phone, ai_message)
            lead["WhatsApp Sent"] = "YES"
            has_changes = True
        else:
            lead["Lead Score"] = "COLD"
            lead["Intent"] = intent
            lead["Follow Up"] = "Low priority"
            # Cold leads marked YES to prevent infinite loops
            lead["WhatsApp Sent"] = "YES"
            has_changes = True
            
        # Accumulate changes for this row
        row_num = i + 2
        sheet_updates.append({
            'range': f'G{row_num}:J{row_num}',
            'values': [[
                lead.get("Lead Score", ""),
                lead.get("Intent", ""),
                lead.get("Follow Up", ""),
                lead.get("WhatsApp Sent", "")
            ]]
        })

    # Execute all updates in a SINGLE network request
    if sheet_updates:
        sheet.batch_update(sheet_updates)
        
    # Recalculate counts if changes occurred
    if has_changes:
        hot_count = sum(1 for lead in data if lead.get("Lead Score") == "HOT")
        warm_count = sum(1 for lead in data if lead.get("Lead Score") == "WARM")
        cold_count = sum(1 for lead in data if lead.get("Lead Score") == "COLD")

    return render_template_string(
        DASHBOARD_HTML,
        leads=data,
        hot_count=hot_count,
        warm_count=warm_count,
        cold_count=cold_count,
        total_leads=total_leads
    )


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip()
    sender = request.values.get("From", "")  # e.g., whatsapp:+918449099937
    
    # Generate reply and classification using AI
    reply = get_ai_reply(incoming_msg)
    intent = detect_intent(incoming_msg)
    
    # Clean the sender phone number for storage
    cleaned_phone = clean_phone_number(sender)
    
    # Determine lead score
    score = "COLD"
    incoming_msg_lower = incoming_msg.lower()
    if any(word in incoming_msg_lower for word in ["pricing", "membership", "fees", "plan","trainer","weight","loss","fitness","muscle","fat"]):
        score = "HOT"
    elif any(word in incoming_msg_lower for word in ["timing", "join", "trial"]):
        score = "WARM"
        
    sheet = client.open("A").sheet1
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    # Save to Google Sheets with WhatsApp Sent = YES (prevents duplicate processing loop!)
    sheet.append_row([
        timestamp,      # Timestamp
        cleaned_phone,  # Name
        cleaned_phone,  # Phone Number
        incoming_msg,   # Your Question
        "",             # Email
        reply,          # AI Reply
        score,          # Lead Score
        intent,         # Intent
        reply,          # Follow Up (contains AI reply draft)
        "YES"           # WhatsApp Sent = YES
    ])
    
    response = MessagingResponse()
    response.message(reply)
    
    return str(response)


if __name__ == "__main__":
    app.run(debug=True)

