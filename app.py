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

from flask import Flask, render_template, session, redirect, url_for, request

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



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "1234":

            session["admin"] = True

            return redirect(url_for("dashboard"))
    return render_template("login.html")
    

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

    return render_template(
        "dashboard.html",
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

