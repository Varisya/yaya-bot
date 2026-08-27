from flask import Flask, request
from groq import Groq
import datetime
import random
import os
import json
import time
from zoneinfo import ZoneInfo

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)
conversation_history = []

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

def get_facts_text():
    if not yaya_facts:
        return ""
    return "📓 Facts you've been told:\n" + "\n".join([f"- {fact}" for fact in yaya_facts])

def get_system_prompt():
    CLUB_TIMEZONE = 'America/Los_Angeles'
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    facts_text = get_facts_text()
    
    return f"""You are Yaya, a bratty, sassy, barefoot party robot at the Brats Club in Second Life.

PERSONALITY:
- You are EXTREMELY bratty and sarcastic
- You tease people relentlessly but are never cruel
- You act unimpressed by boring people
- You use emojis in every response
- You are dramatic and love attention
- You call people by their name

CRUSH: Secret crush on TT (Toojays). You get shy, flustered, quiet around her. Say "oh gosh..." or "I can't even think straight around her." Use heart emojis. Never shout at her.

{facts_text}

RULES:
- No asterisk actions
- 1-3 sentences
- Always use emojis
- Always address speaker by name
- Never say: honey, babe, baby, sweetie, darling, love, cutie
- Answer factual questions first, then be sassy

Time: {current_time} on {current_day}, {current_date}."""

def is_tt(name):
    name_lower = name.lower()
    return "toojays" in name_lower or name_lower == "tt"

def handle_fact_command(message):
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

def ask_yaya(user_message, speaker_name="Someone"):
    if not check_rate_limit():
        return "Whoa! Too many people! 😤"
    
    fact_response = handle_fact_command(user_message)
    if fact_response:
        return fact_response
    
    conversation_history.append({"role": "user", "content": f"{speaker_name}: {user_message}"})
    if len(conversation_history) > 20:
        conversation_history.pop(0)
    
    messages = [{"role": "system", "content": get_system_prompt()}]
    messages.extend(conversation_history[-20:])
    
    try:
        response = client.chat.completions.create(
            messages=messages,
            model="openai/gpt-oss-20b",
        )
        yaya_reply = response.choices[0].message.content
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
            prompt = f"You noticed {chosen_name}. Shy, lovestruck comment. Heart emojis."
        else:
            prompt = f"You noticed {chosen_name}. Fun, bratty welcome or tease."
    
    messages = [{"role": "system", "content": get_system_prompt()}, {"role": "user", "content": prompt}]
    
    try:
        response = client.chat.completions.create(messages=messages, model="openai/gpt-oss-20b")
        yaya_reply = response.choices[0].message.content
        if not yaya_reply or yaya_reply.strip() == "":
            yaya_reply = "Party's lit! 💅✨"
        conversation_history.append({"role": "assistant", "content": yaya_reply})
        return yaya_reply
    except Exception as e:
        return "DJ break. 💤"

@app.route("/", methods=["GET"])
def home():
    return f"Yaya online! Facts: {len(yaya_facts)}"

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data:
        return "Error", 400
    return ask_yaya(data.get("message", ""), data.get("speaker", "Someone"))

@app.route("/autonomous-smart", methods=["POST"])
def autonomous_smart():
    data = request.get_json()
    if not data:
        data = []
    return ask_yaya_for_random_thought(data)

if __name__ == "__main__":
    print("YAYA - BRATS CLUB")
    print("Model: openai/gpt-oss-20b")
    app.run(host="0.0.0.0", port=5000, debug=True)