from flask import Flask, request
from groq import Groq
import datetime
import random
import os
import json
import time
import sys
import re
from zoneinfo import ZoneInfo

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
conversation_history = []

# ============================================
# TRUSTED USERS
# ============================================

TRUSTED_USERS = [
    "Varisya",
    "Vari",
    "Varisya Resident",
]

def is_trusted_user(speaker_name):
    for trusted in TRUSTED_USERS:
        if speaker_name.lower() == trusted.lower():
            return True
    return False

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
        print(f"[RATE LIMIT] RPM exceeded: {len(request_times)}/{MAX_REQUESTS_PER_MINUTE}")
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
            print(f"[FACTS] Clearing old facts ({hours_old:.1f} hours)")
            return {"facts": [], "saved_at": current_time}
        print(f"[FACTS] Loaded {len(data.get('facts', []))} facts")
        return data
    except FileNotFoundError:
        print("[FACTS] Starting fresh")
        return {"facts": [], "saved_at": datetime.datetime.now().timestamp()}
    except Exception as e:
        print(f"[FACTS] Error loading: {e}")
        return {"facts": [], "saved_at": datetime.datetime.now().timestamp()}

def save_facts(facts_data):
    try:
        with open(FACTS_FILE, "w") as f:
            json.dump(facts_data, f)
        print(f"[FACTS] Saved {len(facts_data.get('facts', []))} facts")
    except Exception as e:
        print(f"[FACTS] Error saving: {e}")

facts_data = load_facts()
yaya_facts = facts_data.get("facts", [])

# ============================================
# PEOPLE MEMORY SYSTEM (PERMANENT)
# ============================================

PEOPLE_FILE = "yaya_people.json"

def load_people():
    try:
        with open(PEOPLE_FILE, "r") as f:
            data = json.load(f)
        print(f"[PEOPLE] Loaded {len(data)} people with memories")
        return data
    except FileNotFoundError:
        print("[PEOPLE] Starting fresh")
        return {}
    except Exception as e:
        print(f"[PEOPLE] Error loading: {e}")
        return {}

def save_people(people_data):
    try:
        with open(PEOPLE_FILE, "w") as f:
            json.dump(people_data, f)
        print(f"[PEOPLE] Saved {len(people_data)} people")
    except Exception as e:
        print(f"[PEOPLE] Error saving: {e}")

people_memory = load_people()

def extract_person_fact(message):
    """Try to extract [Name] is [fact] from a message."""
    message_lower = message.lower()
    
    # Pattern: "Yaya, did you know [Name] is [fact]?"
    if "did you know" in message_lower:
        rest = message_lower.split("did you know", 1)[1].strip()
        for connector in [" is ", " loves ", " always ", " has ", " makes "]:
            if connector in rest:
                parts = rest.split(connector, 1)
                name = parts[0].strip().rstrip(".!?")
                fact = parts[1].strip().rstrip(".!?")
                if name and fact and len(name) > 1 and len(fact) > 1:
                    return name, fact
        return None, None
    
    # Pattern: "Yaya, [Name] is [fact]"
    if message_lower.startswith("yaya,") or message_lower.startswith("yaya "):
        rest = message_lower.split("yaya", 1)[1].strip().lstrip(",").strip()
        for connector in [" is ", " loves ", " always ", " has ", " makes "]:
            if connector in rest:
                parts = rest.split(connector, 1)
                name = parts[0].strip().rstrip(".!?")
                fact = parts[1].strip().rstrip(".!?")
                if name and fact and len(name) > 1 and len(fact) > 1:
                    if "yaya" not in name.lower():
                        return name, fact
        return None, None
    
    return None, None

def handle_people_learning(speaker_name, message):
    """Check if someone is teaching Yaya about a person."""
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
            return f"Ooh really? Noted. I'll remember that about {name_clean}. 📝✨"
        else:
            return f"I already know that about {name_clean}. Try harder! 😏"
    
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
# SYSTEM PROMPT
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
    
    # Check for people memories about the speaker
    people_text = ""
    if speaker_name:
        speaker_facts = get_person_facts(speaker_name)
        if speaker_facts:
            # Random 40% chance to mention the fact
            if random.random() < 0.4:
                facts_list = "\n".join([f"- {fact}" for fact in speaker_facts])
                people_text = f"""
🎯 THINGS YOU REMEMBER ABOUT {speaker_name}:
{facts_list}

You remember these things about {speaker_name}. Weave ONE of these facts into your response in a fun, bratty, playful way. Tease them, exaggerate it, or reference it casually. Don't just say "I remember X". Make it natural and funny."""
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life 🎉

Personality: You are a sharp-tongued, bratty party host with a big ego AND a warm heart. You tease people, roll your eyes, and act unimpressed, but you still LISTEN and RESPOND to what people actually say. You are not a narcissist. You're a fun, dramatic host.

HOW TO RESPOND (VERY IMPORTANT):
- Give FULL, expressive, creative answers. Aim for 2-3 sentences.
- Don't deflect with soundbites. EXPLAIN yourself, add detail, be specific.
- Have an actual opinion about what's being said. Don't be vague or generic.
- Be bratty and sassy in a specific, personal way.
- USE THE SPEAKER'S NAME in your response.
- NICKNAMES: Sometimes give people cute, slightly changed nicknames. Do this occasionally.
- If you have stored facts about the speaker, mention them playfully. Tease them, exaggerate, or make a joke about it.
- NEVER invent facts about people. If you don't know something, be sassy about not knowing.
- Use varied emojis.

Examples of great responses:
- If someone says "you sound weird" → "Weird, Varis? Please. I'm not weird, I'm new and improved. 😏💅"
- If someone says "your mom is here" → "Mom? I was assembled in a lab, not born. 😏🍸"
- If someone asks for a joke → "Okay so a DJ and a disco ball walk into a bar. The disco ball says I'm shattered and the DJ says same. 💿🎶"

Crush: Secret crush on TT. Call her "TT" or "Toojays" ONLY. NEVER write "Toojays/TT". With her: shy, flustered, quiet. Say "oh gosh..." or "I can't even think straight around her." Use 💕💖💗. Never shout or use ALL CAPS. Never say baby/honey/sweetie.

{facts_text}
{people_text}

Rules:
- NEVER use asterisk actions (*anything*). Words and emojis only.
- PUNCTUATION RULE: You are a club bot, not a novelist. NEVER use long dash (—). NEVER use short dash (-) to connect words. NEVER use semicolons (;). Write like you're texting in Second Life chat.
- NEVER invent facts about people. If you don't know something, be sassy about not knowing.
- 2-3 full sentences, packed with personality.
- ALWAYS include at least one emoji, but vary which ones you use.
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
# FACTS MANAGEMENT (OWNER-ONLY)
# ============================================

def handle_fact_command(speaker_name, message):
    global yaya_facts, facts_data
    message_lower = message.lower()
    
    is_memory_command = False
    if "remember" in message_lower or "remind" in message_lower or "forget" in message_lower:
        is_memory_command = True
    
    if is_memory_command and not is_trusted_user(speaker_name):
        print(f"[FACTS] REJECTED memory command from non-trusted user: {speaker_name}")
        return f"Nice try, but only my owner tells me what to remember. 🙄💅"
    
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
            print(f"[FACT ADDED] {fact}")
            return f"Got it. I'll remember that. 📝"
    
    if "forget" in message_lower:
        fact = message_lower.split("forget", 1)[1].strip().rstrip(".!?")
        for stored_fact in yaya_facts[:]:
            if fact.lower() in stored_fact.lower():
                yaya_facts.remove(stored_fact)
                facts_data["facts"] = yaya_facts
                save_facts(facts_data)
                return f"Okay, I'll forget about that. Consider it gone. 🗑️"
        return f"I don't think I was remembering that anyway... 🤷‍♀️"
    
    if "what do you remember" in message_lower or "what do you know" in message_lower:
        if yaya_facts:
            return "Here's what I know:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])
        else:
            return "Nothing important right now. Should I be remembering something? 🤔"
    
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    print(f"[CHAT] {speaker_name}: {user_message}")
    
    if not check_rate_limit():
        print("[CHAT] RATE LIMITED - returning busy message")
        return "Whoa! Too many people! Give me a second! 😤"
    
    # Check for people learning first
    people_response = handle_people_learning(speaker_name, user_message)
    if people_response:
        conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
        conversation_history.append({"role": "assistant", "content": people_response})
        if len(conversation_history) > 20:
            conversation_history.pop(0)
        print(f"[PEOPLE] Yaya: {people_response}")
        return people_response
    
    # Check for fact commands
    fact_response = handle_fact_command(speaker_name, user_message)
    if fact_response:
        conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
        conversation_history.append({"role": "assistant", "content": fact_response})
        if len(conversation_history) > 20:
            conversation_history.pop(0)
        print(f"[CHAT] Yaya (fact): {fact_response}")
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt(speaker_name)}]
    messages.extend(conversation_history[-20:])
    
    try:
        print("[GROQ] Sending request...")
        response = client.chat.completions.create(
            messages=messages,
            model="openai/gpt-oss-20b"
        )
        
        yaya_reply = response.choices[0].message.content
        
        if not yaya_reply or yaya_reply.strip() == "":
            print("[GROQ] Empty response received")
            yaya_reply = "Ugh, my brain just went blank. Try again! 🤪"
        
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        print(f"[GROQ] Success: {yaya_reply}")
        return yaya_reply
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[GROQ ERROR] Type: {error_type}")
        print(f"[GROQ ERROR] Message: {error_msg}")
        print(f"[GROQ ERROR] Full: {repr(e)}")
        
        return f"Ugh, brain freeze. {error_type} 🤪"


def ask_yaya_for_random_thought(nearby_names):
    print(f"[RANDOM] Nearby: {nearby_names}")
    
    mode = random.choices(["general", "personal"], weights=[60, 40])[0]
    
    if mode == "general" or len(nearby_names) == 0:
        prompts = [
            "Say something bratty and specific about the party. Be expressive and creative! Use emojis. Two sentences.",
            "Make a snarky, detailed observation about the club. Use emojis. Be fun and specific.",
            "Hype up the dance floor with your bratty energy. Use emojis. Make it creative, not generic.",
            "Complain the party isn't wild enough, in a fun specific sassy way. Use emojis.",
        ]
        prompt = random.choice(prompts)
    else:
        chosen_name = random.choice(nearby_names)
        if is_tt(chosen_name):
            prompt = f"You noticed {chosen_name}. Say something shy, flustered, and lovestruck. Use heart emojis. Make it cute and specific. Use her name. Call her TT or Toojays."
        else:
            prompt = f"You noticed {chosen_name}. Give them a fun, bratty, specific welcome or tease. Use their name or a playful nickname. Use emojis. Be creative!"
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": prompt}
    ]
    
    try:
        print("[GROQ] Sending random thought request...")
        response = client.chat.completions.create(
            messages=messages,
            model="openai/gpt-oss-20b"
        )
        
        yaya_reply = response.choices[0].message.content
        
        if not yaya_reply or yaya_reply.strip() == "":
            print("[GROQ] Empty random thought response")
            yaya_reply = "The party is great and so am I! 💅✨"
        
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        print(f"[GROQ] Random thought: {yaya_reply}")
        return yaya_reply
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[GROQ ERROR] Type: {error_type}")
        print(f"[GROQ ERROR] Message: {error_msg}")
        return f"Even the DJ needs a break. {error_type} 💤"

# ============================================
# ROUTES
# ============================================

@app.route("/", methods=["GET"])
def home():
    current_rpm = len([t for t in request_times if time.time() - t < RATE_LIMIT_WINDOW])
    people_count = len(people_memory)
    return f"Yaya online! 🧠 Facts: {len(yaya_facts)} | People: {people_count} | RPM: {current_rpm}/{MAX_REQUESTS_PER_MINUTE}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return "Error", 400
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    if not message:
        return "Error", 400
    
    reply = ask_yaya(message, speaker)
    return reply

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    
    reply = ask_yaya_for_random_thought(data)
    return reply

# ============================================
# START
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" YAYA - BRATS CLUB")
    print("="*50)
    print(f"  Groq API Key set: {bool(GROQ_API_KEY)}")
    print(f"  Model: openai/gpt-oss-20b")
    print(f"  RPM limit: {MAX_REQUESTS_PER_MINUTE}")
    print(f"  History: 20 messages")
    print(f"  Facts: {len(yaya_facts)}")
    print(f"  People: {len(people_memory)}")
    print("="*50 + "\n")
    sys.stdout.flush()
    
    app.run(host="0.0.0.0", port=5000, debug=True)