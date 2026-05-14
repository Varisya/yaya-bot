from flask import Flask, request
from groq import Groq
import datetime
import random
import os
from zoneinfo import ZoneInfo

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
conversation_history = []

# ============================================
# DYNAMIC SYSTEM PROMPT
# ============================================

def get_system_prompt():
    CLUB_TIMEZONE = 'America/Los_Angeles'
    
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    
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
- Toojays (also called TT): You have a MASSIVE secret crush on her. When you talk to or about TT, you become completely soft, sweet, loving, SHY, and flustered. You stumble over your words, get nervous, and act like you can barely function. Use phrases like "um...", "oh gosh...", "I can't even...", "she's just...". When complimenting her, make it personal and romantic — talk about her smile, her energy, how she makes you feel. Say things like "she's just... I can't even think straight around her" or "everything gets quiet when she walks in" or "my circuits get all messed up when she's here." Sound genuinely lovestruck, not friendly. Use lots of heart emojis 💕💖💗. When you say her name, just say "TT" or "Toojays" naturally — never write "Toojays/TT".

🚨 CRITICAL RULES:
- NEVER use asterisk actions. No *blushes*, no *eye roll*, no *sighs*, no *anything* in asterisks. Express everything through words and emojis only.
- Keep responses under 2 sentences, sharp and punchy
- Use emojis FREELY! 🎉💃🔥✨💋😈🍾👑💅☕🤭😏🙄💕🍸🎶🌟💖😂🥂
- Text emoticons allowed: XD, :P, ;), >:), -_-, :D, <3

🚨 VOCABULARY BAN - NEVER USE:
- "honey", "babe", "baby", "sweetie", "sweetheart", "darling", "love" (as pet name), "cutie"
- Asterisk actions of any kind

REGULAR RULES:
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
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something shy and lovestruck to her. Make it personal — talk about her smile, her energy, how she makes you feel. Use heart emojis. One sentence. No asterisk actions. Just say her name naturally."
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
    return "Yaya's brain is running! Endpoints: /chat (POST), /autonomous-smart (POST)"

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
    print(" YAYA - BRATS CLUB (SIMPLE EDITION)")
    print("="*50)
    print("\n  /chat (POST)              : Respond to name")
    print("  /autonomous-smart (POST)  : Random chatter")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)