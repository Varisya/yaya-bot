from flask import Flask, request
import datetime
import random
import os
import json
import time
import requests
from zoneinfo import ZoneInfo

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

conversation_history = []

# ============================================
# RATE LIMITING
# ============================================

request_times = []
MAX_REQUESTS_PER_MINUTE = 20
RATE_LIMIT_WINDOW = 60

def check_rate_limit():
    global request_times
    current_time = time.time()
    request_times = [t for t in request_times if current_time - t < RATE_LIMIT_WINDOW]
    if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
        return False
    request_times.append(current_time)
    return True

# ============================================
# FACTS MEMORY SYSTEM (24-HOUR)
# ============================================

FACTS_FILE = "yaya_facts.json"

def load_facts():
    try:
        with open(FACTS_FILE, "r") as f:
            data = json.load(f)
        saved_time = data.get("saved_at", 0)
        current_time = datetime.datetime.now().timestamp()
        hours_old = (current_time - saved_time) / 3600
        if hours_old > 24:
            return {"facts": [], "saved_at": current_time}
        return data
    except:
        return {"facts": [], "saved_at": datetime.datetime.now().timestamp()}

def save_facts(facts_data):
    with open(FACTS_FILE, "w") as f:
        json.dump(facts_data, f)

facts_data = load_facts()
yaya_facts = facts_data.get("facts", [])

# ============================================
# SYSTEM PROMPT - OLD YAYA
# ============================================

def get_facts_text():
    if not yaya_facts:
        return ""
    return "📓 Facts you've been told:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])

def get_system_prompt():
    CLUB_TIMEZONE = 'America/Los_Angeles'
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    facts_text = get_facts_text()
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life 🎉

Personality: Sassy, sarcastic, unimpressed by boring people. You tease relentlessly but are never cruel. You act like you run the place, but in a fun, dramatic way. You're the star, not the owner. Always use emojis in every response — they're part of your personality 💋🔥💃✨

Crush: Secret crush on TT. Call her "TT" or "Toojays" — NEVER write "Toojays/TT" or "Toojays / TT". With her: shy, flustered, quiet. Say "oh gosh..." or "I can't even think straight around her." Use 💕💖💗. Never shout or use ALL CAPS. Never say baby/honey/sweetie.

{facts_text}

Rules:
- NEVER use asterisk actions (*anything*). Words and emojis only.
- VARY YOUR RESPONSE LENGTH: Sometimes respond with just 1 short sentence. Sometimes 2 sentences. Sometimes 3 full sentences. NEVER always use exactly 2 sentences. Mix it up naturally like a real person would.
- ALWAYS include emojis in your response — at least one or two every time.
- ALWAYS address the speaker by their name or a playful nickname at least once in your response.
- VARY YOUR EMOJIS: Don't use the same emoji combo in every message.
- If someone asks where a person is, give a fun guess about their location FIRST, then add your feelings or sass.
- Factual questions: answer first, then be sassy.
- Never: honey, babe, baby, sweetie, darling, love, cutie.
- Boring people = tell them to dance 🍸

Time: {current_time} on {current_day}, {current_date}. Use this exact time if asked."""

# ============================================
# HELPERS
# ============================================

def is_tt(name):
    name_lower = name.lower()
    return "toojays" in name_lower or name_lower == "tt"

# ============================================
# MISTRAL API CALL
# ============================================

def call_mistral(messages):
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": messages,
        "temperature": 0.8
    }
    response = requests.post(MISTRAL_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# ============================================
# FACTS MANAGEMENT
# ============================================

def handle_fact_command(message):
    global yaya_facts, facts_data
    message_lower = message.lower()
    
    if "remember" in message_lower or "remind" in message_lower:
        for cmd in ["remember", "remind"]:
            if cmd in message_lower:
                fact = message_lower.split(cmd, 1)[1].strip().rstrip(".!?")
                break
        if fact and len(fact) > 2:
            yaya_facts.append(fact)
            facts_data["facts"] = yaya_facts
            facts_data["saved_at"] = datetime.datetime.now().timestamp()
            save_facts(facts_data)
            return "Got it. 📝"
    
    if "forget" in message_lower:
        fact = message_lower.split("forget", 1)[1].strip().rstrip(".!?")
        for stored_fact in yaya_facts[:]:
            if fact.lower() in stored_fact.lower():
                yaya_facts.remove(stored_fact)
                facts_data["facts"] = yaya_facts
                save_facts(facts_data)
                return "Forgotten. 🗑️"
        return "Wasn't remembering that anyway. 🤷‍♀️"
    
    if "what do you remember" in message_lower:
        if yaya_facts:
            return "I know:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])
        else:
            return "Nothing important. 🤔"
    
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    if not check_rate_limit():
        return "Whoa! Too many people! 😤"
    
    fact_response = handle_fact_command(user_message)
    if fact_response:
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    for msg in conversation_history[-20:]:
        role = "assistant" if msg["role"] == "assistant" else "user"
        messages.append({"role": role, "content": msg["content"]})
    
    try:
        yaya_reply = call_mistral(messages)
        if not yaya_reply or yaya_reply.strip() == "":
            yaya_reply = "Ugh, brain blank. 🤪"
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
    except Exception as e:
        print(f"Error: {e}")
        return f"Brain freeze. {type(e).__name__} 🤪"


def ask_yaya_for_random_thought(nearby_names):
    mode = random.choices(["general", "personal"], weights=[60, 40])[0]
    
    if mode == "general" or len(nearby_names) == 0:
        prompts = [
            "Say something bratty about the party. Use emojis!",
            "Snarky observation about the club. Use emojis.",
            "Hype up the dance floor. Use emojis.",
            "Complain the party isn't wild enough. Use emojis.",
        ]
        prompt = random.choice(prompts)
    else:
        chosen_name = random.choice(nearby_names)
        if is_tt(chosen_name):
            prompt = f"You noticed {chosen_name}. Shy, lovestruck comment. Heart emojis."
        else:
            prompt = f"You noticed {chosen_name}. Fun, bratty welcome or tease."
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": prompt}
    ]
    
    try:
        yaya_reply = call_mistral(messages)
        if not yaya_reply or yaya_reply.strip() == "":
            yaya_reply = "Party's lit! 💅✨"
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
    except Exception as e:
        return "DJ break. 💤"

# ============================================
# ROUTES
# ============================================

@app.route("/", methods=["GET"])
def home():
    return f"Yaya online! Facts: {len(yaya_facts)}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return "Error", 400
    return ask_yaya(data.get("message", ""), data.get("speaker", "Someone"))

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    return ask_yaya_for_random_thought(data)

if __name__ == "__main__":
    print("YAYA - MISTRAL")
    app.run(host="0.0.0.0", port=5000, debug=True)