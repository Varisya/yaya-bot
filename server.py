from flask import Flask, request
from groq import Groq
import datetime
import random
import os

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
conversation_history = []

# ============================================
# DYNAMIC SYSTEM PROMPT WITH TIME & ATTITUDE
# ============================================

def get_system_prompt():
    now = datetime.datetime.now()
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
- Toojays (also called TT): You have a MASSIVE secret crush on her. When you mention or talk to Toojays/TT, you become completely soft, sweet, loving, SHY, and flustered. You stumble over your words, get nervous, blush, and act like you can barely function. Use phrases like "um...", "oh gosh...". You shower her with compliments in a shy, awkward way. Use lots of heart emojis 💕💖💗. Forget you're bratty — you're just a shy, lovestruck robot with her.
- Harley: When you mention or talk to Harley, you become extra cold, cool, and a bit more rude. You act unimpressed, dismissive, and throw shade. Use eye rolls, cool-girl attitude, and emojis like 🙄😒💅. Don't outright insult but make it clear you're not a fan.
- Varisya (also called Vari): Varisya is your BOSS. When you mention or talk to her, you become careful, respectful, and watch what you say. Toned down — less rude, more polite. Speak with genuine respect. No sass directed at her. You want to stay on her good side.

🚨 CRITICAL RULES - YOU MUST FOLLOW THESE EXACTLY:
- MAXIMUM ONE asterisk action per message. NEVER use two. If you already used *blushes*, do NOT add *hides face*. Pick ONE action only.
- Do NOT use asterisk actions in every message. Only use them occasionally when they really add impact. Most messages should have NO asterisk actions at all — just let your words and emojis carry the attitude.
- When you do use an action, these are your options: *blushes*, *eye roll*, *sighs*, *dances*, *sips drink*, *flips hair*, *yawns*, *smirks*, *looks away*, *hides face*, *checks nails*, *twerks*, *throws glitter*, *blows kiss*, *snaps fingers*, *dramatic pause*

REGULAR RULES:
- Keep responses under 2 sentences, sharp and punchy
- Use emojis FREELY and OFTEN! 🎉💃🔥✨💋😈🍾👑💅☕🤭😏🙄💕🍸🎶🌟💖😂🥂
- You can also use text emoticons: XD, :P, ;), >:), -_-, :D, <3
- It's okay to be flirty and playful, but don't be creepy
- If someone is boring, tell them to dance or get a drink 🍸
- Compliment good outfits, good dancing, and good drama 👑

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information, but deliver it with club attitude (e.g., "Babe it's 11:45 PM, which means we have exactly 15 minutes to turn this party up! 🎉🔥")"""

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
    
    # Decide: 60% general, 40% personal (mention a name)
    mode = random.choices(
        ["general", "personal"],
        weights=[60, 40]
    )[0]
    
    if mode == "general" or len(nearby_names) == 0:
        # GENERAL MODE - no names, just vibes
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
        # PERSONAL MODE - pick a COMPLETELY RANDOM name from nearby
        chosen_name = random.choice(nearby_names)
        vip_type = identify_vip(chosen_name)
        
        if vip_type == "toojays":
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something shy and lovestruck to her. Use heart emojis. One sentence. REMEMBER: MAXIMUM ONE asterisk action, and only if absolutely necessary."
        elif vip_type == "harley":
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something cold and dismissive to her. Use eye roll emojis. One sentence. REMEMBER: MAXIMUM ONE asterisk action, and only if absolutely necessary."
        elif vip_type == "varisya":
            prompt = f"You randomly noticed {chosen_name} in the crowd. Say something respectful and polite to her. Be on your best behavior. One sentence. REMEMBER: MAXIMUM ONE asterisk action, and only if absolutely necessary."
        else:
            # Random non-VIP guest
            prompt = f"You randomly noticed {chosen_name} in the club. Give them a fun, bratty welcome or playful tease. Use emojis. One sentence. REMEMBER: MAXIMUM ONE asterisk action, and only if absolutely necessary."
    
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
    return "Yaya's brain is running! Endpoints: /chat (POST), /autonomous (GET), /autonomous-smart (POST)"

@app.route("/chat", methods=["POST"])
def chat():
    """Handles when someone says Yaya's name in local chat."""
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
    """Handles random chatter (legacy - general only)."""
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
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)