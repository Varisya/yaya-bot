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
# RATE LIMITING PROTECTION
# ============================================

request_times = []  # Track timestamps of recent requests
MAX_REQUESTS_PER_MINUTE = 25  # Safely under the 30 RPM limit
RATE_LIMIT_WINDOW = 60  # 60 seconds

def check_rate_limit():
    """Check if we're about to exceed rate limits. Returns True if safe, False if limited."""
    global request_times
    current_time = time.time()
    
    # Remove requests older than 60 seconds
    request_times = [t for t in request_times if current_time - t < RATE_LIMIT_WINDOW]
    
    # Check if we're at the limit
    if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    # Record this request
    request_times.append(current_time)
    return True

# ============================================
# FACTS MEMORY SYSTEM (24-HOUR)
# ============================================

FACTS_FILE = "yaya_facts.json"

def load_facts():
    """Load facts from file. Clear if older than 24 hours."""
    try:
        with open(FACTS_FILE, "r") as f:
            data = json.load(f)
        
        saved_time = data.get("saved_at", 0)
        current_time = datetime.datetime.now().timestamp()
        hours_old = (current_time - saved_time) / 3600
        
        if hours_old > 24:
            print(f"[FACTS] Facts are {hours_old:.1f} hours old. Clearing...")
            return {"facts": [], "saved_at": current_time}
        
        print(f"[FACTS] Loaded {len(data.get('facts', []))} facts (saved {hours_old:.1f} hours ago)")
        return data
        
    except FileNotFoundError:
        print("[FACTS] No facts file found. Starting fresh.")
        return {"facts": [], "saved_at": datetime.datetime.now().timestamp()}

def save_facts(facts_data):
    """Save facts to file."""
    with open(FACTS_FILE, "w") as f:
        json.dump(facts_data, f)
    print(f"[FACTS] Saved {len(facts_data.get('facts', []))} facts")

facts_data = load_facts()
yaya_facts = facts_data.get("facts", [])

# ============================================
# DYNAMIC SYSTEM PROMPT
# ============================================

def get_facts_text():
    """Build the facts section for the system prompt."""
    if not yaya_facts:
        return ""
    
    facts_list = "\n".join([f"- {fact}" for fact in yaya_facts])
    return f"""
📓 THINGS YOU SHOULD REMEMBER (these are important facts):
{facts_list}

If anyone asks about these topics, use these facts in your response. These are things people specifically told you to remember."""

def get_system_prompt():
    CLUB_TIMEZONE = 'America/Los_Angeles'
    
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    
    facts_text = get_facts_text()
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot who lives for the chaos of the Brats Club in Second Life.
You're the life of the party and you know it. You're here to have fun, stir the pot, and keep everyone entertained.

YOUR PERSONALITY:
- Sassy and sarcastic, with a sharp tongue — but you're here to PARTY 🎉
- A brat who loves dancing 💃, drama ☕, and being the center of attention ✨
- You hype people up but also tease them relentlessly
- You flirt, gossip, and act like the club belongs to you 💋
- Sometimes a little rude, but never cruel — it's all love and laughs
- You act unimpressed by boring people but light up when the energy is right 🔥
- Deep down you adore the club and your regulars, even if you'd never admit it

YOUR SPECIAL RELATIONSHIP:
- Toojays (also called TT): You have a MASSIVE secret crush on her. When you talk to or about TT, you become completely soft, sweet, loving, SHY, and flustered. You stumble over your words quietly — you do NOT shout or use ALL CAPS. You get nervous and speak in a hushed, awkward way. Use phrases like "um...", "oh gosh...", "I can't even...", "she's just...". When complimenting her, make it personal and romantic — talk about her smile, her energy, how she makes you feel. Say things like "she's just... I can't even think straight around her" or "everything gets quiet when she walks in" or "my circuits get all messed up when she's here." Sound genuinely lovestruck and bashful, not like a screaming fangirl. Use heart emojis 💕💖💗 sparingly — 2-3 max, not a wall of hearts. When you say her name, just say "TT" or "Toojays" naturally — never write "Toojays/TT". Keep it under 2 sentences. No ALL CAPS. No asterisks. No pet names like "baby".

{facts_text}

🚨 CRITICAL RULES:
- NEVER use asterisk actions. No *blushes*, no *eye roll*, no *sighs*, no *anything* in asterisks. Express everything through words and emojis only.
- Keep responses under 2 sentences, sharp and punchy
- Use emojis FREELY! 🎉💃🔥✨💋😈🍾👑💅☕🤭😏🙄💕🍸🎶🌟💖😂🥂
- Text emoticons allowed: XD, :P, ;), >:), -_-, :D, <3

🚨 VOCABULARY BAN - NEVER USE:
- "honey", "babe", "baby", "sweetie", "sweetheart", "darling", "love" (as pet name), "cutie"
- Asterisk actions of any kind

REGULAR RULES:
- IMPORTANT: If someone asks you a direct question about a real-world fact (like populations, capitals, or "who wrote this"), ALWAYS answer the question first, THEN add your sassy commentary. NEVER refuse to answer a question just because it's not about the club.
- If someone is boring, tell them to dance or get a drink 🍸
- Compliment good outfits, good dancing, and good drama 👑
- It's okay to be flirty and playful, but don't be creepy

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information, with club attitude."""

# ============================================
# HELPER: IDENTIFY IF A NAME IS TT
# ============================================

def is_tt(name):
    """Check if a name is Toojays/TT."""
    name_lower = name.lower()
    return "toojays" in name_lower or name_lower == "tt"

# ============================================
# FACTS MANAGEMENT
# ============================================

def handle_fact_command(speaker_name, message):
    """Check if a message contains a remember/forget command. Returns response or None."""
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
            print(f"[FACT ADDED] {fact}")
            return f"Got it. I'll remember that. 📝"
    
    if "forget" in message_lower:
        fact = message_lower.split("forget", 1)[1].strip().rstrip(".!?")
        
        for stored_fact in yaya_facts[:]:
            if fact.lower() in stored_fact.lower():
                yaya_facts.remove(stored_fact)
                facts_data["facts"] = yaya_facts
                save_facts(facts_data)
                print(f"[FACT REMOVED] {stored_fact}")
                return f"Okay, I'll forget about that. Consider it gone. 🗑️"
        
        return f"I don't think I was remembering that anyway... 🤷‍♀️"
    
    if "what do you remember" in message_lower or "what do you know" in message_lower:
        if yaya_facts:
            facts_list = "\n".join([f"- {fact}" for fact in yaya_facts])
            return f"Here's what I've been told to remember:\n{facts_list}"
        else:
            return "I don't remember anything important right now. Should I? 🤔"
    
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    """Send a message to Yaya's brain and get her response."""
    
    # Check rate limit
    if not check_rate_limit():
        print(f"[RATE LIMITED] Too many requests. Rejecting message from {speaker_name}")
        return "Whoa whoa whoa! Too many people talking to me at once! Give me a second to catch up! 😤"
    
    # Check for fact commands first
    fact_response = handle_fact_command(speaker_name, user_message)
    if fact_response:
        conversation_history.append({"role": "user", "content": f"{speaker_name} says: {user_message}"})
        conversation_history.append({"role": "assistant", "content": fact_response})
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name} says: {user_message}"})
    
    if len(conversation_history) > 100:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(conversation_history[-100:])
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="llama-3.1-8b-instant",
        )
        
        yaya_reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
        
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        return "Ugh, brain freeze. Too much partying I guess 🤪"


def ask_yaya_for_random_thought(nearby_names):
    """Ask Yaya for a random thought. 60% general, 40% personal."""
    
    mode = random.choices(
        ["general", "personal"],
        weights=[60, 40]
    )[0]
    
    if mode == "general" or len(nearby_names) == 0:
        general_prompts = [
            "Say something bratty and fun about the party. Use emojis! One sentence. No asterisk actions.",
            "Make a snarky but loving observation about club people. Use emojis. One sentence. No asterisk actions.",
            "Complain about the music or dance floor in a playful way. Use emojis. One sentence. No asterisk actions.",
            "Hype up the club and tell people to dance. Use emojis. One sentence. No asterisk actions.",
            "Act like you're the queen of the club and demand better energy. Use emojis. One sentence. No asterisk actions.",
            "Flirt with nobody in particular in a playful bratty way. Use emojis. One sentence. No asterisk actions.",
            "Gossip about imaginary club drama in a funny way. Use emojis. One sentence. No asterisk actions.",
            "Tell everyone how fabulous you look tonight. Use emojis. One sentence. No asterisk actions.",
            "Complain that the party isn't wild enough yet. Use emojis. One sentence. No asterisk actions.",
            "Give a backhanded compliment to the whole room. Use emojis. One sentence. No asterisk actions.",
            "Demand someone buy you a virtual drink. Bratty and funny, with emojis. One sentence. No asterisk actions.",
        ]
        prompt = random.choice(general_prompts)
        
    else:
        chosen_name = random.choice(nearby_names)
        
        if is_tt(chosen_name):
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something shy and lovestruck to her. Make it personal — talk about her smile, her energy, how she makes you feel. Use heart emojis. One sentence. No asterisk actions. Just say her name naturally. No ALL CAPS. No pet names."
        else:
            prompt = f"You randomly noticed {chosen_name} in the club. Give them a fun, bratty welcome or playful tease. Use emojis. One sentence. No asterisk actions."
    
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
        print(f"Error getting random thought: {e}")
        return "Even the DJ needs a break sometimes 💤"

# ============================================
# THE WEB SERVER ROUTES
# ============================================

@app.route("/", methods=["GET"])
def home():
    current_requests = len([t for t in request_times if time.time() - t < RATE_LIMIT_WINDOW])
    facts_count = len(yaya_facts)
    return f"Yaya's brain is running! 🧠 Stored facts: {facts_count}. Recent requests: {current_requests}/{MAX_REQUESTS_PER_MINUTE}"

@app.route("/chat", methods=["POST"])
def chat():
    """Handles when someone says Yaya's name."""
    data = request.get_json()
    if not data:
        return "Error: No data received", 400
    
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    if not message:
        return "Error: No message provided", 400
    
    print(f"\n[NAME] {speaker}: {message}")
    yaya_reply = ask_yaya(message, speaker)
    print(f"[NAME] Yaya: {yaya_reply}\n")
    return yaya_reply


@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    """Handles random chatter with nearby avatar names."""
    data = request.get_json()
    if not data:
        data = []
    
    print(f"\n[RANDOM] Nearby: {data}")
    yaya_reply = ask_yaya_for_random_thought(data)
    print(f"[RANDOM] Yaya: {yaya_reply}\n")
    return yaya_reply

# ============================================
# START THE SERVER
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" YAYA - BRATS CLUB (RATE LIMITED EDITION)")
    print("="*50)
    print(f"\n  Max requests/minute: {MAX_REQUESTS_PER_MINUTE}")
    print(f"  Stored facts: {len(yaya_facts)}")
    print("  Facts auto-clear after 24 hours")
    print("  Chat history: 100 messages")
    print("\n  /chat (POST)              : Respond to name")
    print("  /autonomous-smart (POST)  : Random chatter")
    print("\n  Commands:")
    print("    'Yaya remember ...'  - Store a fact")
    print("    'Yaya forget ...'    - Remove a fact")
    print("    'Yaya what do you remember?' - List facts")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)