
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Load API key from environment
gemini_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_key)

model = genai.GenerativeModel("gemini-2.5-flash")

def get_ai_reply(question):

    
    prompt = f"""

    You are an expert gym sales assistant.

    Your job:
    - convert leads into customers
    - sound human and friendly
    - encourage gym visit or trial
    - answer confidently
    - keep replies short and persuasive

    Gym details:
    - Modern fitness gym
    - Personal training available
    - Weight loss programs
    - Muscle gain programs
    - Cardio section
- Free trial available

Customer question:
{question}

Reply professionally like a real sales expert.
"""

    response = model.generate_content(prompt)

    return response.text

def detect_intent_ai(question):

    prompt = f"""
    Detect the customer's gym-related intent.

    Possible intents:
    - pricing
    - personal_training
    - weight_loss
    - muscle_gain
    - timings
    - free_trial
    - visit
    - membership
    - general

    Customer message:
    {question}

    Reply ONLY with the intent name.
    """

    response = model.generate_content(prompt)

    return response.text.strip().lower()