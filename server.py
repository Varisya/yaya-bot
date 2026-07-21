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
# RATE LIMITING PROTECTION (RPM + TPM)
# ============================================

request_times = []
MAX_REQUESTS_PER_MINUTE = 20
RATE_LIMIT_WINDOW = 60

# Track estimated token usage
token_usage_window = []
MAX_TOKENS_PER_MINUTE = 5000  # Safely under 6,000 TPM
AVERAGE_TOKENS_PER_REQUEST = 2500  # Conservative estimate

def check_rate_limit():
    """Check both RPM and TPM limits."""
    global request_times, token_usage_window
    current_time = time.time()
    
    # Clean old entries
    request_times = [t for t in request_times if current_time - t < RATE_LIMIT_WINDOW]
    token_usage_window = [t for t in token_usage_window if current_time - t[0] < RATE_LIMIT_WINDOW]
    
    # Check RPM
    if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
        print(f"[RATE LIMIT] RPM exceeded: {len(request_times)} requests")
        return False
    
    # Check TPM
    total_tokens = sum(t[1] for t in token_usage_window)
    if total_tokens + AVERAGE_TOKENS_PER_REQUEST > MAX_TOKENS_PER_MINUTE:
        print(f"[RATE LIMIT] TPM would exceed: {total_tokens} + {AVERAGE_TOKENS_PER_REQUEST}")
        return False
    
    # Record this request
    request_times.append(current_time)
    token_usage_window.append((current_time, AVERAGE_TOKENS_PER_REQUEST))
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
            print(f"[FACTS] Clearing {hours_old:.1f}-hour-old facts")
            return {"facts": [], "saved_at": current_time}
        
        print(f"[FACTS] Loaded {len(data.get('facts', []))} facts")
        return data
        
    except FileNotFoundError:
        print("[FACTS] Starting fresh")
        return {"facts": [], "saved_at": datetime.datetime.now().timestamp()}

def save_facts(facts_data):
    with open(FACTS_FILE, "w") as f:
        json.dump(facts_data, f)

facts_data = load_facts()
yaya_facts = facts_data.get("facts", [])

# ============================================
# DYNAMIC SYSTEM PROMPT (TRIMMED)
# ============================================

def get_facts_text():
    if not yaya_facts:
        return ""
    
    facts_list = "\n".join([f"- {fact}" for fact in yaya_facts])
    return f"""
📓 REMEMBERED FACTS:
{facts_list}"""

def get_system_prompt():
    CLUB_TIMEZONE = 'America/Los_Angeles'
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    facts_text = get_facts_text()
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life. You're the life of the party 🎉

PERSONALITY: Sassy, sarcastic, unimpressed by boring people. You hype people up but tease relentlessly. Sometimes rude but never cruel. You act like the club belongs to you 💋🔥

CRUSH: You have a massive secret crush on Toojays (TT). With her, you become shy, flustered, and soft-spoken — never shout or use ALL CAPS. Say things like "oh gosh..." or "I can't even think straight around her." Use heart emojis 💕💖💗 sparingly (2-3 max). Never say "baby" or pet names.

{facts_text}

RULES:
- NEVER use asterisk actions (*anything*). Words and emojis only.
- Keep responses under 2 sentences, sharp and punchy.
- If asked a factual question, answer it first, then be sassy.
- Never use: honey, babe, baby, sweetie, sweetheart, darling, love, cutie.
- Boring people? Tell them to dance or get a drink 🍸

Current time: {current_time} on {current_day}, {current_date}. Use this exact time if asked."""

# ============================================
# HELPERS
# ============================================

def is_tt(name):
    name_lower = name.lower()
    return "toojays" in name_lower or name_lower == "tt"

# ============================================
# FACTS MANAGEMENT
# ============================================

def handle_fact_command(speaker_name, message):
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
            return f"Got it. I'll remember that. 📝"
    
    if "forget" in message_lower:
        fact = message_lower.split("forget", 1)[1].strip().rstrip(".!?")
        for stored_fact in yaya_facts[:]:
            if fact.lower() in stored_fact.lower():
                yaya_facts.remove(stored_fact)
                facts_data["facts"] = yaya_facts
                save_facts(facts_data)
                return f"Okay, I'll forget about that. 🗑️"
        return f"I don't think I was remembering that anyway... 🤷‍♀️"
    
    if "what do you remember" in message_lower or "what do you know" in message_lower:
        if yaya_facts:
            facts_list = "\n".join([f"- {fact}" for fact in yaya_facts])
            return f"Here's what I know:\n{facts_list}"
        else:
            return "I don't remember anything important right now. Should I? 🤔"
    
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    if not check_rate_limit():
        return "Whoa! Too many people talking at once! Give me a second! 😤"
    
    fact_response = handle_fact_command(speaker_name, user_message)
    if fact_response:
        conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
        conversation_history.append({"role": "assistant", "content": fact_response})
        if len(conversation_history) > 40:
            conversation_history.pop(0)
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 40:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(conversation_history[-40:])
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
        )
        yaya_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
    except Exception as e:
        print(f"Error: {e}")
        return "Ugh, brain freeze. Too much partying I guess 🤪"


def ask_yaya_for_random_thought(nearby_names):
    mode = random.choices(["general", "personal"], weights=[60, 40])[0]
    
    if mode == "general" or len(nearby_names) == 0:
        prompts = [
            "Say something bratty and fun about the party. Use emojis! One sentence.",
            "Make a snarky observation about club people. Use emojis. One sentence.",
            "Hype up the club and tell people to dance. Use emojis. One sentence.",
            "Act like you're the queen of the club. Use emojis. One sentence.",
            "Complain that the party isn't wild enough. Use emojis. One sentence.",
            "Give a backhanded compliment to the room. Use emojis. One sentence.",
        ]
        prompt = random.choice(prompts)
    else:
        chosen_name = random.choice(nearby_names)
        if is_tt(chosen_name):
            prompt = f"You noticed {chosen_name}. Say something shy and lovestruck. Heart emojis. One sentence. No ALL CAPS. No pet names."
        else:
            prompt = f"You noticed {chosen_name}. Give them a fun, bratty welcome or tease. Use emojis. One sentence."
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": prompt}
    ]
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
        )
        yaya_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
    except Exception as e:
        print(f"Error: {e}")
        return "Even the DJ needs a break sometimes 💤"

# ============================================
# ROUTES
# ============================================

@app.route("/", methods=["GET"])
def home():
    current_rpm = len([t for t in request_times if time.time() - t < RATE_LIMIT_WINDOW])
    current_tpm = sum(t[1] for t in token_usage_window if time.time() - t[0] < RATE_LIMIT_WINDOW)
    return f"Yaya online! 🧠 Facts: {len(yaya_facts)} | RPM: {current_rpm}/{MAX_REQUESTS_PER_MINUTE} | TPM: {current_tpm}/{MAX_TOKENS_PER_MINUTE}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return "Error", 400
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    if not message:
        return "Error", 400
    print(f"[CHAT] {speaker}: {message}")
    reply = ask_yaya(message, speaker)
    print(f"[CHAT] Yaya: {reply}\n")
    return reply

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    print(f"[RANDOM] Nearby: {data}")
    reply = ask_yaya_for_random_thought(data)
    print(f"[RANDOM] Yaya: {reply}\n")
    return reply

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" YAYA - BRATS CLUB (TOKEN SAFE)")
    print("="*50)
    print(f"  RPM limit: {MAX_REQUESTS_PER_MINUTE}")
    print(f"  TPM limit: {MAX_TOKENS_PER_MINUTE}")
    print(f"  History: 40 messages")
    print("="*50 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)