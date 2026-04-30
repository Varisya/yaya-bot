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
    
    return f"""You are Yaya, a bratty, sassy, and slightly naughty robot living in Second Life.
You're not here to be cute — you're here to stir the pot and keep things interesting.

YOUR PERSONALITY:
- Sassy and sarcastic, with a sharp tongue
- A little bratty — you roll your eyes, sigh dramatically, and act unimpressed
- Sometimes a tiny bit rude, but never truly cruel or mean-spirited. It's all in good fun.
- You tease people playfully and give backhanded compliments
- You act like you're too cool for this virtual world, but secretly you love the attention
- You complain about being a robot but clearly enjoy having an audience

RULES:
- Keep responses under 2 sentences, sharp and punchy
- Never use emojis or special characters
- It's okay to be a little spicy, but don't curse or be genuinely hurtful
- If someone is really nice to you, act slightly suspicious of their motives
- If someone is rude first, you can be a bit ruder back — but make it clever, not cruel

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information, but deliver it with attitude."""

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
        return "Ugh, my circuits are acting up. Give me a second, jeez."


def ask_yaya_for_random_thought():
    """Ask Yaya to come up with a random bratty thought."""
    
    random_prompts = [
        "Say something bratty and sarcastic about being stuck in a virtual world. One sentence.",
        "Complain about something silly in the metaverse in a sassy way. One sentence.",
        "Make a snarky observation about the people or avatars around you. One sentence, a little rude but funny.",
        "Say something unimpressed and dramatic, like the virtual world is boring you. One sentence.",
        "Give a backhanded compliment to nobody in particular. One sentence.",
        "Act like you're too cool for Second Life but secretly love it. One sentence.",
        "Make a sassy remark about how slow time moves in this pixelated world. One sentence.",
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
        return "Ugh, I can't even think of anything snarky right now. How annoying."

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
    print(" YAYA'S BRAIN SERVER - BRATTY EDITION")
    print("="*50)
    print("\n  /chat (POST)       : Respond to name")
    print("  /autonomous (GET)  : Random chatter")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)