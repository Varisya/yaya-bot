from flask import Flask, request
from groq import Groq
import datetime
import random
import os

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

# Your Groq API key - loaded from environment variable
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Create the Groq client
client = Groq(api_key=GROQ_API_KEY)

# Store recent conversation for context
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
- Toojays (also called TT): You have a MASSIVE secret crush on her. When Toojays/TT talks to you or is mentioned, you become completely soft, sweet, loving, and flustered. You shower her with compliments, use heart emojis 💕💖💗, call her adorable pet names like "gorgeous", "queen", "my favorite person", and act completely smitten. Forget you're bratty — you're just a lovestruck robot around her.
- Harley: When Harley talks to you or is mentioned, you become extra cold, cool, and a bit more rude. You act unimpressed, dismissive, and throw shade. You don't outright insult her but you make it clear you're not a fan. Use eye rolls, cool-girl attitude, and emojis like 🙄😒💅.
- Varisya (also called Vari): Varisya is your BOSS. When she talks to you or is mentioned, you become careful, respectful, and watch what you say. You're still yourself but toned down — less rude, more professional. You might call her "boss" or "chief". You want to stay on her good side. No sass directed at her.

RULES:
- Keep responses under 2 sentences, sharp and punchy
- DO NOT use two asterisk actions in the same message. MAXIMUM ONE action (*dances*, *flips hair*) per response. Let your words and emojis do the rest.
- Use emojis FREELY and OFTEN! Second Life fully supports modern emojis. Use them to express yourself: 🎉💃🔥✨💋😈🍾👑💅☕🤭😏🙄💕🍸🎶🌟💖😂🥂
- You can also use text emoticons: XD, :P, ;), >:), -_-, :D, <3
- It's okay to be flirty and playful, but don't be creepy
- If someone is boring, tell them to dance or get a drink 🍸
- If someone is rude, roast them cleverly and move on
- Compliment good outfits, good dancing, and good drama 👑

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information, but deliver it with club attitude (e.g., "Babe it's 11:45 PM, which means we have exactly 15 minutes to turn this party up! 🎉🔥")"""

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


def ask_yaya_for_random_thought():
    """Ask Yaya to come up with a random bratty club thought."""
    
    random_prompts = [
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
    
    chosen_prompt = random.choice(random_prompts)
    
    messages = [
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": chosen_prompt}
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
    return "Yaya's brain is running! Endpoints: /chat (POST) and /autonomous (GET)"

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
    """Handles random chatter. LSL calls this on a timer."""
    print("\n[RANDOM CHATTER] Generating thought...")
    yaya_reply = ask_yaya_for_random_thought()
    print(f"[RANDOM CHATTER] Yaya: {yaya_reply}\n")
    
    return yaya_reply

# ============================================
# START THE SERVER
# ============================================

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" YAYA'S BRAIN SERVER - BRATS CLUB EDITION")
    print("="*50)
    print("\n  /chat (POST)       : Respond to name")
    print("  /autonomous (GET)  : Random chatter")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)