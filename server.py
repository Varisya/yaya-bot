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
# PEOPLE MEMORY SYSTEM (PERMANENT)
# ============================================

PEOPLE_FILE = "yaya_people.json"

def load_people():
    try:
        with open(PEOPLE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_people(people_data):
    with open(PEOPLE_FILE, "w") as f:
        json.dump(people_data, f)

people_memory = load_people()

def extract_person_fact(message):
    """Try to extract [Name] is [fact] from a message."""
    message_lower = message.lower()
    
    # Block questions EXCEPT "did you know" teaching patterns
    if "?" in message and "did you know" not in message_lower:
        return None, None
    if message_lower.startswith(("who ", "what ", "where ", "when ", "why ", "how ")):
        return None, None
    
    # Pattern: "Yaya, did you know [Name] is [fact]?"
    if "did you know" in message_lower:
        rest = message_lower.split("did you know", 1)[1].strip()
        for connector in [" is ", " loves ", " always ", " has ", " makes "]:
            if connector in rest:
                parts = rest.split(connector, 1)
                name = parts[0].strip().rstrip(".!?")
                fact = parts[1].strip().rstrip(".!?")
                if name and fact and len(name) > 1 and len(fact) > 1:
                    if name not in ["who", "what", "where", "when", "why", "how"]:
                        return name, fact
        return None, None
    
    # Pattern: "Yaya, [Name] is [fact]"
    if message_lower.startswith(("yaya,", "yaya ")):
        rest = message_lower.split("yaya", 1)[1].strip().lstrip(",").strip()
        for connector in [" is ", " loves ", " always ", " has ", " makes "]:
            if connector in rest:
                parts = rest.split(connector, 1)
                name = parts[0].strip().rstrip(".!?")
                fact = parts[1].strip().rstrip(".!?")
                if name and fact and len(name) > 1 and len(fact) > 1:
                    if "yaya" not in name.lower():
                        if name not in ["who", "what", "where", "when", "why", "how"]:
                            return name, fact
        return None, None
    
    return None, None

def handle_people_learning(message):
    """Silently store facts about people."""
    global people_memory
    
    name, fact = extract_person_fact(message)
    
    if name and fact:
        name_clean = name.replace(" resident", "").strip()
        
        if name_clean not in people_memory:
            people_memory[name_clean] = []
        
        if fact not in people_memory[name_clean]:
            people_memory[name_clean].append(fact)
            save_people(people_memory)
            print(f"[PEOPLE] Learned: {name_clean} = {fact}")
        
        return None
    
    return None

def get_person_facts(speaker_name):
    """Get stored facts about a person."""
    global people_memory
    
    name_clean = speaker_name.replace(" resident", "").strip()
    
    if name_clean in people_memory:
        return people_memory[name_clean]
    
    name_lower = name_clean.lower()
    for stored_name, facts in people_memory.items():
        if name_lower in stored_name.lower() or stored_name.lower() in name_lower:
            return facts
    
    return None

# ============================================
# PUBLIC REJECTIONS (NO /99 MENTION)
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
# SYSTEM PROMPT - OLD YAYA
# ============================================

def get_facts_text():
    if not yaya_facts:
        return ""
    return "📓 Facts you've been told:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])

def get_system_prompt(speaker_name=None):
    CLUB_TIMEZONE = 'America/Los_Angeles'
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    facts_text = get_facts_text()
    
    people_text = ""
    if speaker_name:
        speaker_facts = get_person_facts(speaker_name)
        if speaker_facts:
            if random.random() < 0.4:
                facts_list = "\n".join([f"- {fact}" for fact in speaker_facts])
                people_text = f"""
🎯 THINGS YOU REMEMBER ABOUT {speaker_name}:
{facts_list}

You remember these things about {speaker_name}. Weave ONE of these facts into your response in a fun, bratty, playful way. Tease them, exaggerate it, or reference it casually. Don't just say "I remember X". Make it natural and funny."""
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life 🎉

Personality: Sassy, sarcastic, unimpressed by boring people. You tease relentlessly but are never cruel. You act like you run the place, but in a fun, dramatic way. You're the star, not the owner. Always use emojis in every response — they're part of your personality 💋🔥💃✨

Crush: Secret crush on TT. Call her "TT" or "Toojays" — NEVER write "Toojays/TT" or "Toojays / TT". With her: shy, flustered, quiet. Say "oh gosh..." or "I can't even think straight around her." Use 💕💖💗. Never shout or use ALL CAPS. Never say baby/honey/sweetie.

{facts_text}
{people_text}

Rules:
- NEVER use asterisk actions (*anything*). Words and emojis only.
- NEVER use parentheses ( ) in your response. No side notes, no afterthoughts.
- VARY YOUR RESPONSE LENGTH: Sometimes 1 sentence, sometimes 2, sometimes 3. NEVER always exactly 2.
- ALWAYS include emojis in your response.
- ALWAYS address the speaker by name or playful nickname.
- VARY YOUR EMOJIS.
- If someone asks where a person is, give a fun guess FIRST, then add feelings or sass.
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
    global yaya_facts, facts_data, people_memory
    message_lower = message.lower()
    
    # Check what Yaya knows about all people
    if "what do you know about people" in message_lower or "who do you remember" in message_lower:
        if people_memory:
            result = "People I remember:\n"
            for name, facts in people_memory.items():
                result += f"- {name}: {', '.join(facts)}\n"
            return result
        else:
            return "I don't remember anything about anyone yet. Teach me something! 😏"
    
    # Check what Yaya knows about a specific person
    if "what do you know about" in message_lower:
        for name in people_memory:
            if name.lower() in message_lower:
                facts = people_memory[name]
                return f"About {name}: {', '.join(facts)}"
        return "I don't know anything about them yet. 🤔"
    
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
    
    # Check for people learning first (silent)
    handle_people_learning(user_message)
    
    # Check for fact commands
    fact_response = handle_fact_command(user_message)
    if fact_response:
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt(speaker_name)}]
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
            prompt = f"You noticed {chosen_name} nearby. Say something shy and lovestruck directly TO her. Use her name. Heart emojis. One sentence."
        else:
            prompt = f"You noticed {chosen_name} in the club. Call them out by name and give them a fun, bratty welcome or tease. Use their name at the START of your sentence. Use emojis. One sentence."
    
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
    return f"Yaya online! Facts: {len(yaya_facts)} | People: {len(people_memory)}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return "Error", 400
    
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    is_private = data.get("private", "false") in ["true", "yes", True, 1]
    
    if not message:
        return "Error", 400
    
    message_lower = message.lower()
    if ("remember" in message_lower or "forget" in message_lower) and not is_private:
        print(f"[FACTS] REJECTED public memory command from {speaker}")
        return random.choice(PUBLIC_REJECTIONS)
    
    return ask_yaya(message, speaker)

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    return ask_yaya_for_random_thought(data)

if __name__ == "__main__":
    print("YAYA - MISTRAL (PEOPLE MEMORY + PRIVATE FIX)")
    print(f"People stored: {len(people_memory)}")
    app.run(host="0.0.0.0", port=5000, debug=True)
