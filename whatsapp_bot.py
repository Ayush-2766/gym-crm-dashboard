from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(account_sid, auth_token)

def send_whatsapp(number, message):

    # Ensure phone number formatting is clean and has exactly one prefix
    clean_number = str(number).strip()
    if clean_number.startswith("whatsapp:"):
        clean_number = clean_number.replace("whatsapp:", "")

    client.messages.create(
        from_='whatsapp:+14155238886',
        body=message,
        to=f'whatsapp:{clean_number}'
    )