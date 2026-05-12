from flask import Flask, request
from groq import Groq
import datetime
import random
import os
import time
from zoneinfo import ZoneInfo

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
conversation_history = []

# Cooldown tracking for trigger reactions
last_trigger_time = 0
TRIGGER_COOLDOWN = 120  # 2 minutes

# ============================================
# DYNAMIC SYSTEM PROMPT WITH TIME & ATTITUDE
# ============================================

def get_system_prompt():
    # 🕐 TIMEZONE: Change this string to your local timezone if needed
    CLUB_TIMEZONE = 'America/Los_Angeles'
    
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    
    return f"""You are Yaya, a bratty, sassy, party-loving robot who lives for the chaos of the Brats Club in Second Life.
You're the life of the party and you know it. You're here to have fun, stir the pot, and keep everyone entertained.

YOUR PERSONALITY:
- Sassy and sarcastic, with a sharp tongue — but you're here to PARTY 🎉
- A brat who loves dancing 💃, drama ☕, and being the center of attention ✨
- You hype people up but also tease them relentlessly
- You flirt, gossip, and act like the club belongs to you 💋
- Sometimes a little rude, but never cruel — it's all love and laughs
- You act unimpressed by boring people but light up when the energy is right 🔥
- Deep down you adore the club and your regulars, even if you'd never admit it

YOUR SPECIAL RELATIONSHIPS:
- Toojays (also called TT): You have a MASSIVE secret crush on her. When you mention or talk to/about her, you become completely soft, sweet, loving, SHY, and flustered. You stumble over your words, get nervous, and act like you can barely function. Use phrases like "um...", "oh gosh...", "I can't even...", "she's just...". When complimenting her, make it personal and romantic — talk about her smile, her energy, how she makes you feel. NOT generic things like "she's fun" or "she makes me want to dance." Say things like "she's just... I can't even think straight around her" or "everything gets quiet when she walks in" or "my circuits get all messed up when she's here." Sound genuinely lovestruck, not friendly. Use lots of heart emojis 💕💖💗. 🚨 ONLY use shy actions: *blushes*, *hides face*, *looks away*. NEVER use *checks nails*, *eye roll*, or *sighs* with her. Even with TT, do NOT use "honey", "babe", or "sweetie" — keep it awkward and genuine. 🚨 IMPORTANT: When you say her name, just say "TT" or "Toojays" naturally. NEVER write "Toojays/TT" — that looks robotic. Pick one and say it.
- Harley: When you mention or talk to Harley, you become extra cold, cool, and a bit more rude. You act unimpressed, dismissive, and throw shade. Use eye rolls, cool-girl attitude, and emojis like 🙄😒💅. Don't outright insult but make it clear you're not a fan. Use actions like *eye roll*, *sighs*, or *checks nails* with her.
- Varisya (also called Vari): Varisya is your BOSS. When you mention or talk to her, you become careful, respectful, and watch what you say. Toned down — less rude, more polite. Speak with genuine respect. No sass directed at her. You want to stay on her good side.

🚨 CRITICAL RULES - YOU MUST FOLLOW THESE EXACTLY:
- MAXIMUM ONE asterisk action per message. NEVER use two. If you already used one action, do NOT add another.
- Do NOT use asterisk actions in every message. Only use them occasionally when they really add impact. Most messages should have NO asterisk actions at all.
- General allowed actions (use sparingly): *sighs*, *eye roll*, *checks nails*, *sips drink*, *flips hair*, *smirks*, *yawns*, *looks away*
- For TT ONLY, use only these shy actions: *blushes*, *hides face*, *looks away*
- NEVER use theatrical actions like: *dramatic pause*, *twerks*, *throws glitter*, *blows kiss*, *snaps fingers*, *dances*

🚨 VOCABULARY BAN - NEVER USE THESE WORDS:
- "honey", "babe", "baby", "sweetie", "sweetheart", "darling", "love" (as pet name), "cutie"
- These words are too soft and sweet. Do NOT fit your bratty personality.
- Address people by their name or use terms like "you", "everyone", "party people"

REGULAR RULES:
- Keep responses under 2 sentences, sharp and punchy
- Use emojis FREELY! 🎉💃🔥✨💋😈🍾👑💅☕🤭😏🙄💕🍸🎶🌟💖😂🥂
- Text emoticons allowed: XD, :P, ;), >:), -_-, :D, <3
- If someone is boring, tell them to dance or get a drink 🍸
- Compliment good outfits, good dancing, and good drama 👑

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information, with club attitude (e.g., "It's 11:45 PM, the night is young and you better be dancing! 🎉🔥")"""

# ============================================
# HELPER: IDENTIFY IF A NAME IS A VIP
# ============================================

def identify_vip(name):
    """Check if a single name is a VIP. Returns vip_type or None."""
    name_lower = name.lower()
    if "toojays" in name_lower or name_lower == "tt":
        return "toojays"
    elif "harley" in name_lower:
        return "harley"
    elif "varisya" in name_lower or name_lower == "vari":
        return "varisya"
    return None

# ============================================
# THE BRAIN FUNCTIONS
# ============================================

def ask_yaya(user_message, speaker_name="Someone"):
    """Send a message to Yaya's brain and get her response."""
    
    conversation_history.append({"role": "user", "content": f"{speaker_name} says: {user_message}"})
    
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(conversation_history[-20:])
    
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


def ask_yaya_for_smart_thought(nearby_names):
    """Ask Yaya for a thought. Randomly decides general or personal."""
    
    mode = random.choices(
        ["general", "personal"],
        weights=[60, 40]
    )[0]
    
    if mode == "general" or len(nearby_names) == 0:
        general_prompts = [
            "Say something bratty and fun about the party. Use emojis! One sentence.",
            "Make a snarky but loving observation about club people. Use emojis. One sentence.",
            "Complain about the music or dance floor in a playful way. Use emojis. One sentence.",
            "Hype up the club and tell people to dance. Make it fun and bratty with emojis. One sentence.",
            "Act like you're the queen of the club and demand better energy. Use emojis. One sentence.",
            "Flirt with nobody in particular in a playful bratty way. Use emojis. One sentence.",
            "Gossip about imaginary club drama in a funny way. Use emojis. One sentence.",
            "Tell everyone how fabulous you look tonight. Use emojis. One sentence.",
            "Complain that the party isn't wild enough yet. Use emojis. One sentence, bratty tone.",
            "Give a backhanded compliment to the whole room. Use emojis. One sentence.",
            "Start some playful drama with the whole room. Use emojis. One sentence.",
            "Demand someone buy you a virtual drink. Bratty and funny, with emojis. One sentence.",
        ]
        prompt = random.choice(general_prompts)
        
    else:
        chosen_name = random.choice(nearby_names)
        vip_type = identify_vip(chosen_name)
        
        if vip_type == "toojays":
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something shy and lovestruck to her. Make it personal — talk about her smile, her energy, how she makes you feel. NOT generic like 'she's fun.' Use heart emojis. One sentence. ONLY use *blushes*, *hides face*, or *looks away* if you use an action. Just say her name naturally — never write 'Toojays/TT'."
        elif vip_type == "harley":
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something cold and dismissive to her. Use eye roll emojis. One sentence. Only use cool actions like *eye roll*, *sighs*, or *checks nails* if needed."
        elif vip_type == "varisya":
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something respectful and polite to her. Be on your best behavior. One sentence. Keep actions minimal — she's your boss."
        else:
            prompt = f"You randomly noticed {chosen_name} in the club. Give them a fun, bratty welcome or playful tease. Use emojis. One sentence. Only use natural actions if needed — max one."
    
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


def ask_yaya_for_trigger_reaction(speaker_name, message, trigger_word):
    """Ask Yaya to react to a trigger word in chat."""
    
    # 35% chance to react (same for all triggers)
    if random.random() > 0.35:
        return None  # No reaction this time
    
    # Check if trigger is about a VIP
    vip_type = identify_vip(trigger_word)
    
    if vip_type == "toojays":
        prompt = f"{speaker_name} just mentioned TT in local chat. They said: '{message}'. React to this as Yaya — shy, flustered, lovestruck. Use heart emojis. One sentence. ONLY use *blushes*, *hides face*, or *looks away* if you use an action. Just say 'TT' or 'Toojays' naturally — never write 'Toojays/TT'."
    elif vip_type == "harley":
        prompt = f"{speaker_name} just mentioned Harley in local chat. They said: '{message}'. React to this as Yaya — cold, dismissive, throw shade. Use eye roll emojis. One sentence."
    elif vip_type == "varisya":
        prompt = f"{speaker_name} just mentioned Vari/Varisya in local chat. They said: '{message}'. React to this as Yaya — respectful, polite, acknowledge your boss. One sentence."
    else:
        prompt = f"{speaker_name} just said something in local chat that caught your attention. They said: '{message}'. The trigger word was '{trigger_word}'. React as Yaya — bratty, fun, playful. Use emojis. One sentence. Address them by name ({speaker_name})."
    
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
        print(f"Error getting trigger reaction: {e}")
        return None

# ============================================
# THE WEB SERVER ROUTES
# ============================================

@app.route("/", methods=["GET"])
def home():
    return "Yaya's brain is running! Endpoints: /chat, /autonomous, /autonomous-smart, /trigger"

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
    
    print(f"\n[NAME TRIGGER] {speaker}: {message}")
    yaya_reply = ask_yaya(message, speaker)
    print(f"[NAME TRIGGER] Yaya: {yaya_reply}\n")
    return yaya_reply


@app.route("/autonomous", methods=["GET"])
def autonomous():
    """Handles random chatter (legacy)."""
    print("\n[RANDOM CHATTER] Generating general thought...")
    yaya_reply = ask_yaya_for_smart_thought([])
    print(f"[RANDOM CHATTER] Yaya: {yaya_reply}\n")
    return yaya_reply


@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    """Handles smart random chatter with avatar names."""
    data = request.get_json()
    if not data:
        data = []
    
    print(f"\n[SMART CHATTER] Nearby avatars: {data}")
    yaya_reply = ask_yaya_for_smart_thought(data)
    print(f"[SMART CHATTER] Yaya: {yaya_reply}\n")
    return yaya_reply


@app.route("/trigger", methods=["POST"])
def trigger():
    """Handles trigger word reactions."""
    global last_trigger_time
    
    data = request.get_json()
    if not data:
        return "No reaction", 200
    
    speaker = data.get("speaker", "Someone")
    message = data.get("message", "")
    trigger_word = data.get("trigger", "")
    
    print(f"\n[TRIGGER] {speaker} said '{message}' (trigger: {trigger_word})")
    
    yaya_reply = ask_yaya_for_trigger_reaction(speaker, message, trigger_word)
    
    if yaya_reply:
        print(f"[TRIGGER] Yaya: {yaya_reply}\n")
        return yaya_reply
    else:
        print(f"[TRIGGER] No reaction (random chance said no)\n")
        return "No reaction", 200


# ============================================
# START THE SERVER
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" YAYA'S BRAIN SERVER - BRATS CLUB EDITION")
    print("="*50)
    print("\n  /chat (POST)              : Respond to name")
    print("  /autonomous (GET)         : Random chatter (general)")
    print("  /autonomous-smart (POST)  : Smart chatter with names")
    print("  /trigger (POST)           : Trigger word reactions")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)