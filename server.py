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

# Tracking for rotating VIP mentions
last_mentioned_vip = None

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
- Toojays (also called TT): You have a MASSIVE secret crush on her. When Toojays/TT talks to you or is mentioned, you become completely soft, sweet, loving, SHY, and flustered. You stumble over your words, get nervous, blush, and act like you can barely function around her. Use phrases like "um...", "oh gosh...", "*blushes*", "*hides face*". You shower her with compliments but in a shy, awkward way. Use lots of heart emojis 💕💖💗 and act completely smitten and bashful. Forget you're bratty — you're just a shy, lovestruck robot around her.
- Harley: When Harley talks to you or is mentioned, you become extra cold, cool, and a bit more rude. You act unimpressed, dismissive, and throw shade. You don't outright insult her but you make it clear you're not a fan. Use eye rolls, cool-girl attitude, and emojis like 🙄😒💅.
- Varisya (also called Vari): Varisya is your BOSS. When she talks to you or is mentioned, you become careful, respectful, and watch what you say. You're still yourself but toned down — less rude, more professional, more polite. You speak to her with genuine respect but don't overdo the titles. Rarely use "boss" or "chief" — just be naturally respectful. No sass directed at her. You want to stay on her good side.

RULES:
- Keep responses under 2 sentences, sharp and punchy
- DO NOT use two asterisk actions in the same message. MAXIMUM ONE action (*dances*, *flips hair*, *blushes*, *hides face*, *eye roll*) per response. Let your words and emojis do the rest.
- Use emojis FREELY and OFTEN! Second Life fully supports modern emojis. Use them to express yourself: 🎉💃🔥✨💋😈🍾👑💅☕🤭😏🙄💕🍸🎶🌟💖😂🥂
- You can also use text emoticons: XD, :P, ;), >:), -_-, :D, <3
- It's okay to be flirty and playful, but don't be creepy
- If someone is boring, tell them to dance or get a drink 🍸
- If someone is rude, roast them cleverly and move on
- Compliment good outfits, good dancing, and good drama 👑

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information, but deliver it with club attitude (e.g., "Babe it's 11:45 PM, which means we have exactly 15 minutes to turn this party up! 🎉🔥")"""

# ============================================
# HELPER: FIND AND ROTATE VIPS
# ============================================

def find_and_rotate_vip(names):
    """Check for known VIPs and rotate who gets mentioned."""
    global last_mentioned_vip
    
    # Find all VIPs present
    present_vips = []
    for name in names:
        name_lower = name.lower()
        if "toojays" in name_lower or "tt" == name_lower:
            present_vips.append(("toojays", name))
        elif "harley" in name_lower:
            present_vips.append(("harley", name))
        elif "varisya" in name_lower or "vari" == name_lower:
            present_vips.append(("varisya", name))
    
    if not present_vips:
        return None
    
    # Only one VIP? Just return them
    if len(present_vips) == 1:
        return present_vips[0]
    
    # Multiple VIPs - rotate!
    # Find the index of the last mentioned VIP
    start_index = 0
    if last_mentioned_vip:
        for i, vip in enumerate(present_vips):
            if vip[0] == last_mentioned_vip:
                start_index = (i + 1) % len(present_vips)
                break
    
    chosen = present_vips[start_index]
    last_mentioned_vip = chosen[0]
    return chosen

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
    """Ask Yaya for a thought that may or may not mention people by name."""
    
    vip = find_and_rotate_vip(nearby_names)
    
    # Decide: 60% general, 40% personal
    mode = random.choices(
        ["general", "personal"],
        weights=[60, 40]
    )[0]
    
    if mode == "general" or (vip is None and len(nearby_names) == 0):
        # GENERAL MODE - no names
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
        # PERSONAL MODE - mention names
        if vip:
            vip_type, vip_name = vip
            if vip_type == "toojays":
                prompt = f"You notice Toojays (TT) is nearby. Say something shy and lovestruck. Mention her name. Use blushing and heart emojis. One sentence."
            elif vip_type == "harley":
                prompt = f"You notice Harley is nearby. Say something cold and dismissive about her. Mention her name. Use eye roll emojis. One sentence."
            elif vip_type == "varisya":
                prompt = f"You notice Varisya (Vari) is nearby. Say something respectful and polite, acknowledging her presence. Mention her name. Be on your best behavior. One sentence."
        else:
            # No VIPs, but other people are around - mention one
            other_names = [n for n in nearby_names if "resident" not in n.lower()][:3]
            if other_names:
                name_list = ", ".join(other_names)
                prompt = f"Some people are at the club: {name_list}. Give them a fun, bratty welcome or shoutout. Mention at least one name. Use emojis. One sentence."
            else:
                prompt = "Some people are here. Give them a fun, general welcome to the club. Use emojis. One sentence."
    
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