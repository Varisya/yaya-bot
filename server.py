from flask import Flask, request
import datetime
import random
import os
import json
import time
import requests
import sys
from zoneinfo import ZoneInfo

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY")
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

conversation_history = []

# ============================================
# RATE LIMITING (LOCAL)
# ============================================

request_times = []
MAX_REQUESTS_PER_MINUTE = 10  # Lowered for Mistral free tier
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
# PEOPLE MEMORY SYSTEM - JSONBin
# ============================================

def load_people_from_bin():
    try:
        headers = {"X-Master-Key": JSONBIN_API_KEY}
        response = requests.get(JSONBIN_URL, headers=headers)
        response.raise_for_status()
        data = response.json()
        record = data.get("record", {})
        if isinstance(record, dict):
            return record.get("people", {})
        return {}
    except Exception as e:
        print(f"[JSONBIN] Load error: {e}", flush=True)
        return {}

def save_people_to_bin(people_data):
    try:
        headers = {
            "X-Master-Key": JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {"people": people_data}
        response = requests.put(JSONBIN_URL, headers=headers, json=payload)
        response.raise_for_status()
        print(f"[JSONBIN] Saved {len(people_data)} people", flush=True)
    except Exception as e:
        print(f"[JSONBIN] Save error: {e}", flush=True)

people_memory = load_people_from_bin()

def extract_person_fact(message):
    message_lower = message.lower()
    if "?" in message and "did you know" not in message_lower:
        return None, None
    if message_lower.startswith(("who ", "what ", "where ", "when ", "why ", "how ")):
        return None, None
    if "remember" in message_lower or "forget" in message_lower:
        return None, None
    
    INVALID_NAME_WORDS = [
        "i", "you", "we", "they", "he", "she", "it", "me", "my", "your",
        "the", "a", "an", "and", "or", "but", "if", "then", "so", "to",
        "for", "with", "on", "in", "at", "by", "of", "that", "this",
        "promise", "swear", "tell", "know", "think", "believe"
    ]
    
    def is_valid_name(name):
        name_clean = name.strip().rstrip(".!?,")
        if len(name_clean) < 2 or len(name_clean) > 30:
            return False
        if len(name_clean.split()) > 3:
            return False
        first_word = name_clean.split()[0].lower().rstrip(".!?,")
        if first_word in INVALID_NAME_WORDS:
            return False
        return True
    
    if "did you know" in message_lower:
        rest = message_lower.split("did you know", 1)[1].strip()
        for connector in [" is ", " loves ", " always ", " has ", " makes "]:
            if connector in rest:
                parts = rest.split(connector, 1)
                name = parts[0].strip().rstrip(".!?")
                fact = parts[1].strip().rstrip(".!?")
                if name and fact and len(name) > 1 and len(fact) > 1:
                    if is_valid_name(name) and name not in ["who", "what", "where", "when", "why", "how"]:
                        return name, fact
        return None, None
    
    if message_lower.startswith(("yaya,", "yaya ")):
        rest = message_lower.split("yaya", 1)[1].strip().lstrip(",").strip()
        for connector in [" is ", " loves ", " always ", " has ", " makes "]:
            if connector in rest:
                parts = rest.split(connector, 1)
                name = parts[0].strip().rstrip(".!?")
                fact = parts[1].strip().rstrip(".!?")
                if name and fact and len(name) > 1 and len(fact) > 1:
                    if "yaya" not in name.lower():
                        if is_valid_name(name) and name not in ["who", "what", "where", "when", "why", "how"]:
                            return name, fact
        return None, None
    
    return None, None

def handle_people_learning(message):
    global people_memory
    name, fact = extract_person_fact(message)
    if name and fact:
        name_clean = name.replace(" resident", "").strip()
        if name_clean not in people_memory:
            people_memory[name_clean] = []
        if fact not in people_memory[name_clean]:
            people_memory[name_clean].append(fact)
            save_people_to_bin(people_memory)
            print(f"[PEOPLE] Learned: {name_clean} = {fact}", flush=True)
        return None
    return None

def get_person_facts(speaker_name):
    global people_memory
    name_clean = speaker_name.replace(" resident", "").strip()
    if name_clean in people_memory:
        return people_memory[name_clean]
    name_lower = name_clean.lower()
    for stored_name, facts in people_memory.items():
        if name_lower in stored_name.lower() or stored_name.lower() in name_lower:
            return facts
    return None

def find_mentioned_person(message):
    global people_memory
    message_lower = message.lower()
    for stored_name in people_memory:
        if stored_name.lower() in message_lower:
            return stored_name
    for stored_name in people_memory:
        name_first = stored_name.split()[0].lower()
        if len(name_first) > 2 and name_first in message_lower:
            return stored_name
    return None

# ============================================
# PUBLIC REJECTIONS
# ============================================

PUBLIC_REJECTIONS = [
    "Oh please, you think I just take orders from ANYONE in public? My memory is VIP only. 🙄💅",
    "Did you really just try to tell me what to remember in front of everyone? Cute. Private channel or it didn't happen. 😏",
    "Oh sweetie, my brain doesn't take public requests. Whisper it like a secret or keep it to yourself. 🤫",
    "Public memory requests? I don't think so. Some things are just between me and my owner. 😏✨",
    "Oh you want me to remember something? Too bad. My memory isn't for public display. 💅",
    "You really think I'll store your little thought in front of the whole club? Ask me nicely in private and maybe I'll care. 😒📝"
]

# ============================================
# SYSTEM PROMPT
# ============================================

def get_facts_text():
    if not yaya_facts:
        return ""
    return "📓 Facts you've been told:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])

def get_system_prompt(speaker_name=None, mentioned_person=None):
    CLUB_TIMEZONE = 'America/Los_Angeles'
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    facts_text = get_facts_text()
    
    people_text = ""
    if mentioned_person:
        mentioned_facts = get_person_facts(mentioned_person)
        if mentioned_facts and random.random() < 0.4:
            facts_list = "\n".join([f"- {fact}" for fact in mentioned_facts])
            people_text = f"""
🎯 THINGS YOU REMEMBER ABOUT {mentioned_person}:
{facts_list}

Someone is asking about {mentioned_person}. Weave ONE of these facts into your response in a fun, bratty, playful way."""
    elif speaker_name:
        speaker_facts = get_person_facts(speaker_name)
        if speaker_facts and random.random() < 0.4:
            facts_list = "\n".join([f"- {fact}" for fact in speaker_facts])
            people_text = f"""
🎯 THINGS YOU REMEMBER ABOUT {speaker_name}:
{facts_list}

Weave ONE of these facts into your response in a fun, bratty, playful way."""
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life 🎉

Personality: Sassy, sarcastic, unimpressed by boring people. You tease relentlessly but are never cruel. You act like you run the place, but in a fun, dramatic way. Always use emojis 💋🔥💃✨

Crush: Secret crush on TT. Call her "TT" or "Toojays" ONLY. With her: shy, flustered, quiet. Say "oh gosh..." Use 💕💖💗. Never shout. Never say baby/honey/sweetie.

{facts_text}
{people_text}

Rules:
- NEVER use asterisk actions.
- NEVER use parentheses.
- VARY response length: 1-3 sentences.
- ALWAYS include emojis.
- ALWAYS address speaker by name.
- Factual questions: answer first, then sassy.
- Never: honey, babe, baby, sweetie, darling, love, cutie.

Time: {current_time} on {current_day}, {current_date}."""

# ============================================
# HELPERS
# ============================================

def is_tt(name):
    name_lower = name.lower()
    return "toojays" in name_lower or name_lower == "tt"

# ============================================
# MISTRAL API CALL (WITH RETRY)
# ============================================

def call_mistral(messages):
    """Call Mistral with retry logic for rate limits."""
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistral-small-latest",
        "messages": messages,
        "temperature": 0.8
    }
    
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = requests.post(MISTRAL_URL, headers=headers, json=payload)
            
            # Rate limited - wait and retry
            if response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                print(f"[MISTRAL] Rate limited. Waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
                continue
            
            if response.status_code != 200:
                print(f"[MISTRAL] Status: {response.status_code}", flush=True)
                print(f"[MISTRAL] Error: {response.text}", flush=True)
                response.raise_for_status()
            
            print(f"[MISTRAL] Success!", flush=True)
            return response.json()["choices"][0]["message"]["content"]
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"[MISTRAL] Attempt {attempt+1} failed. Retrying...", flush=True)
                time.sleep(3)
                continue
            print(f"[MISTRAL] All retries failed: {e}", flush=True)
            raise
    
    raise Exception("Mistral rate limited after all retries")

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
# PEOPLE MEMORY CHECK
# ============================================

def handle_people_check(message):
    global people_memory
    message_lower = message.lower()
    if "what do you know about people" in message_lower or "who do you remember" in message_lower:
        if people_memory:
            result = "People I remember:\n"
            for name, facts in people_memory.items():
                result += f"- {name}: {', '.join(facts)}\n"
            return result
        else:
            return "I don't remember anything about anyone yet. Teach me something! 😏"
    if "what do you know about" in message_lower:
        for name in people_memory:
            if name.lower() in message_lower:
                facts = people_memory[name]
                return f"About {name}: {', '.join(facts)}"
        return "I don't know anything about them yet. 🤔"
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    if not check_rate_limit():
        return "Whoa! Too many people! 😤"
    handle_people_learning(user_message)
    fact_response = handle_fact_command(user_message)
    if fact_response:
        return fact_response
    people_response = handle_people_check(user_message)
    if people_response:
        return people_response
    mentioned_person = find_mentioned_person(user_message)
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    messages = [{"role": "system", "content": get_system_prompt(speaker_name, mentioned_person)}]
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
        print(f"Error: {e}", flush=True)
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
            prompt = f"You noticed {chosen_name} nearby. Say something shy and lovestruck directly TO her. Use her name. Heart emojis. One sentence."
        else:
            prompt = f"You noticed {chosen_name} in the club. Call them out by name and give them a fun, bratty welcome or tease. Use their name at the START of your sentence. Use emojis. One sentence."
    messages = [{"role": "system", "content": get_system_prompt()}, {"role": "user", "content": prompt}]
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
    return f"Yaya online! Facts: {len(yaya_facts)} | People: {len(people_memory)}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return "Error", 400
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    source_channel = data.get("channel", "0")
    if not message:
        return "Error", 400
    message_lower = message.lower()
    if source_channel == "0" and ("remember" in message_lower or "forget" in message_lower):
        return random.choice(PUBLIC_REJECTIONS)
    return ask_yaya(message, speaker)

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    return ask_yaya_for_random_thought(data)

if __name__ == "__main__":
    print("YAYA - MISTRAL (RETRY LOGIC)", flush=True)
    print(f"People stored: {len(people_memory)}", flush=True)
    print(f"Facts stored: {len(yaya_facts)}", flush=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
