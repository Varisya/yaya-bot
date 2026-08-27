from flask import Flask, request
from groq import Groq
import datetime
import random
import os
import json
import time
from zoneinfo import ZoneInfo

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
conversation_history = []

# ============================================
# RATE LIMITING (RPM ONLY)
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
# SYSTEM PROMPT (NO EMOJIS IN PROMPT)
# ============================================

def get_system_prompt():
    now = datetime.datetime.now(ZoneInfo('America/Los_Angeles'))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life.

Personality: Sassy, sarcastic, unimpressed by boring people. You tease relentlessly but are never cruel. You act like the club belongs to you.

Crush: Secret crush on TT. Call her "TT" or "Toojays" only. With her: shy, flustered, quiet. Say "oh gosh..." or "I can't even think straight around her." Never shout. Never say baby/honey/sweetie.

Rules:
- Never use asterisk actions.
- Under 2 sentences, sharp and punchy.
- Answer factual questions first, then be sassy.
- Never: honey, babe, baby, sweetie, darling, love, cutie.

Current time: {current_time} on {current_day}."""

# ============================================
# HELPERS
# ============================================

def is_tt(name):
    name_lower = name.lower()
    return "toojays" in name_lower or name_lower == "tt"

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
            return "Got it."
    
    if "forget" in message_lower:
        fact = message_lower.split("forget", 1)[1].strip().rstrip(".!?")
        for stored_fact in yaya_facts[:]:
            if fact.lower() in stored_fact.lower():
                yaya_facts.remove(stored_fact)
                facts_data["facts"] = yaya_facts
                save_facts(facts_data)
                return "Forgotten."
    
    if "what do you remember" in message_lower or "what do you know" in message_lower:
        if yaya_facts:
            return "I know:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])
        else:
            return "Nothing important."
    
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    if not check_rate_limit():
        return "Whoa! Too many people!"
    
    fact_response = handle_fact_command(user_message)
    if fact_response:
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(conversation_history[-20:])
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="mixtral-8x7b-32768",
            max_tokens=200
        )
        yaya_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return f"Brain freeze. {type(e).__name__}"


def ask_yaya_for_random_thought(nearby_names):
    mode = random.choices(["general", "personal"], weights=[60, 40])[0]
    
    if mode == "general" or len(nearby_names) == 0:
        prompt = "Say something bratty about the party. One sentence."
    else:
        chosen_name = random.choice(nearby_names)
        if is_tt(chosen_name):
            prompt = f"You noticed {chosen_name}. Shy, lovestruck comment. One sentence."
        else:
            prompt = f"You noticed {chosen_name}. Fun, bratty welcome or tease. One sentence."
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="mixtral-8x7b-32768",
            max_tokens=200
        )
        yaya_reply = response.choices[0].message.content
        return yaya_reply
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return "DJ break."

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
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    if not message:
        return "Error", 400
    return ask_yaya(message, speaker)

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    return ask_yaya_for_random_thought(data)

if __name__ == "__main__":
    print("YAYA - TEST VERSION")
    print(f"API Key set: {bool(GROQ_API_KEY)}")
    print(f"Key: {GROQ_API_KEY[:8]}..." if GROQ_API_KEY else "NO KEY")
    app.run(host="0.0.0.0", port=5000, debug=True)