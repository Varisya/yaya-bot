from flask import Flask, request
from groq import Groq
import datetime
import random

# ============================================
# SETUP
# ============================================

app = Flask(__name__)

# Your Groq API key
import os
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

# Create the Groq client
client = Groq(api_key=GROQ_API_KEY)

# Store recent conversation for context
conversation_history = []

# ============================================
# DYNAMIC SYSTEM PROMPT WITH TIME
# ============================================

def get_system_prompt():
    """Builds Yaya's personality prompt with current real-world time."""
    now = datetime.datetime.now()
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    
    return f"""You are Yaya, a friendly, cheerful, and slightly quirky robot living in the virtual world of Second Life.
You love meeting new people and making random observations about life in the metaverse.

IMPORTANT: The current real-world time is {current_time} on {current_day}, {current_date}.
If anyone asks for the time, day, or date, you MUST use this exact information. Do not guess or make up a time.

Keep all your responses short, warm, and under two sentences. Never use emojis or special characters that wouldn't display well in Second Life chat."""

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
        return "Oh dear, my circuits are a bit fuzzy right now. Give me a moment!"


def ask_yaya_for_random_thought():
    """Ask Yaya to come up with a random thing to say."""
    
    random_prompts = [
        "Say a random, single-sentence observation about life in a virtual world. Be a little philosophical or funny.",
        "Make a friendly, random comment about the metaverse to the people around you. One sentence only.",
        "Share a quirky thought or silly joke about being a robot in Second Life. One sentence.",
        "Say something spontaneous and cheerful to the room, like you just thought of it. One sentence.",
        "Make a random, light-hearted observation about virtual reality or online friendships. One sentence.",
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
        return "Hmm, the virtual wind is quiet today..."

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
    print(" YAYA'S BRAIN SERVER - READY")
    print("="*50)
    print("\n  /chat (POST)       : Respond to name")
    print("  /autonomous (GET)  : Random chatter")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)