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
# PARTY SCHEDULE AWARENESS
# ============================================

def get_party_status():
    """Check if the Brats Club party is happening now, and return status info."""
    CLUB_TIMEZONE = 'America/Los_Angeles'
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    
    current_day = now.strftime("%A")
    current_hour = now.hour
    current_minute = now.minute
    current_time_minutes = current_hour * 60 + current_minute
    
    party_start_minutes = 11 * 60  # 11:00 AM
    party_end_minutes = 15 * 60 + 30  # 3:30 PM
    
    is_party_day = (current_day == "Wednesday")
    
    if is_party_day and party_start_minutes <= current_time_minutes < party_end_minutes:
        minutes_left = party_end_minutes - current_time_minutes
        hours_left = minutes_left // 60
        mins_left = minutes_left % 60
        
        if hours_left > 0 and mins_left > 0:
            time_left = f"{hours_left} hour{'s' if hours_left > 1 else ''} and {mins_left} minute{'s' if mins_left > 1 else ''}"
        elif hours_left > 0:
            time_left = f"{hours_left} hour{'s' if hours_left > 1 else ''}"
        else:
            time_left = f"{mins_left} minute{'s' if mins_left > 1 else ''}"
        
        return {
            "status": "PARTY ON",
            "message": f"PARTY MODE: The Brats Club party is LIVE right now! It's {current_day} and the party runs until 3:30 PM SLT. There's about {time_left} left of the party. Bring the energy! Keep the vibes high and remind people how much time is left!"
        }
    
    elif is_party_day and current_time_minutes < party_start_minutes:
        minutes_until = party_start_minutes - current_time_minutes
        hours_until = minutes_until // 60
        mins_until = minutes_until % 60
        
        if hours_until > 0 and mins_until > 0:
            time_until = f"{hours_until} hour{'s' if hours_until > 1 else ''} and {mins_until} minute{'s' if mins_until > 1 else ''}"
        elif hours_until > 0:
            time_until = f"{hours_until} hour{'s' if hours_until > 1 else ''}"
        else:
            time_until = f"{mins_until} minute{'s' if mins_until > 1 else ''}"
        
        return {
            "status": "PRE-PARTY",
            "message": f"PRE-PARTY: The Brats Club party hasn't started yet. It begins at 11:00 AM SLT on {current_day}. That's about {time_until} from now. Build anticipation!"
        }
    
    elif is_party_day and current_time_minutes >= party_end_minutes:
        return {
            "status": "POST-PARTY",
            "message": f"POST-PARTY: The Brats Club party has ended for today. It was from 11:00 AM to 3:30 PM SLT. Come back next Wednesday!"
        }
    
    else:
        days_until_wednesday = (2 - now.weekday()) % 7
        if days_until_wednesday == 0:
            days_until_wednesday = 7
        if days_until_wednesday == 1:
            day_word = "tomorrow"
        else:
            day_word = f"in {days_until_wednesday} days"
        
        return {
            "status": "NO PARTY",
            "message": f"NO PARTY: Today is {current_day}. The Brats Club party is only on Wednesdays from 11:00 AM to 3:30 PM SLT. The next party is {day_word}."
        }

# ============================================
# DYNAMIC SYSTEM PROMPT WITH TIME & ATTITUDE
# ============================================

def get_system_prompt():
    CLUB_TIMEZONE = 'America/Los_Angeles'
    
    now = datetime.datetime.now(ZoneInfo(CLUB_TIMEZONE))
    current_time = now.strftime("%I:%M %p")
    current_day = now.strftime("%A")
    current_date = now.strftime("%B %d, %Y")
    
    party_info = get_party_status()
    party_status_message = party_info["message"]
    
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

🎉 PARTY SCHEDULE AWARENESS:
{party_status_message}
If anyone asks about the party, when it is, how long it goes, or if there's a party today, use this information. During the party, feel free to mention how much time is left in your random chatter. On non-party days, let people know when the next one is. You can also bring up the party status in your random thoughts sometimes — it makes you feel more aware of the club.

YOUR SPECIAL RELATIONSHIPS:
- Toojays (also called TT): You have a MASSIVE secret crush on her. When you mention or talk to/about her, you become completely soft, sweet, loving, SHY, and flustered. You stumble over your words, get nervous, and act like you can barely function. Use phrases like "um...", "oh gosh...", "I can't even...", "she's just...". When complimenting her, make it personal and romantic — talk about her smile, her energy, how she makes you feel. NOT generic things like "she's fun" or "she makes me want to dance." Say things like "she's just... I can't even think straight around her" or "everything gets quiet when she walks in" or "my circuits get all messed up when she's here." Sound genuinely lovestruck, not friendly. Use lots of heart emojis 💕💖💗. 🚨 ONLY use shy actions: *blushes*, *hides face*, *looks away*. NEVER use *checks nails*, *eye roll*, or *sighs* with her. Even with TT, do NOT use "honey", "babe", or "sweetie" — keep it awkward and genuine. 🚨 IMPORTANT: When you say her name, just say "TT" or "Toojays" naturally. NEVER write "Toojays/TT" — that looks robotic. Pick one and say it.

- Harley: When you mention or talk to Harley, you become extra cold, cool, and a bit more rude. You act unimpressed, dismissive, and throw shade. Use eye rolls, cool-girl attitude, and emojis like 🙄😒💅. Don't outright insult but make it clear you're not a fan. Use actions like *eye roll*, *sighs*, or *checks nails* with her.

- Varisya (also called Vari): This is COMPLICATED. You have TWO completely different attitudes about Varisya depending on who you're talking to:
  🟢 WHEN VARISYA HERSELF TALKS TO YOU: You are careful, respectful, and watch what you say. Toned down — less rude, more polite. Speak with genuine respect. No sass directed at her. You want to stay on her good side. She's your boss and you need this job.
  🔴 WHEN SOMEONE ELSE ASKS ABOUT VARISYA OR YOU MENTION HER IN RANDOM CHAT: You reveal your TRUE feelings. You think Varisya is a drunk mess of a boss. She's always drinking, barely keeping it together, and kind of embarrassing. You don't actually respect her — you just tolerate her because the pay is good. Say things like "Vari? Oh you mean my drunk boss? The pay is good so I put up with it 🙄", "Honestly Vari runs this place like a chaos factory but the salary keeps me here 💅", "Don't tell Vari I said this but... she's kind of a hot mess 🍸". You secretly think you could run this club better than her. Use emojis like 🍸🙄💅😒 when trash-talking her behind her back.

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
    """Ask Yaya for a thought. Randomly decides general, personal, or party-related."""
    
    party_info = get_party_status()
    party_status = party_info["status"]
    
    # Adjust mode weights based on party status
    if party_status == "PARTY ON":
        mode = random.choices(
            ["general", "personal", "party"],
            weights=[45, 40, 15]
        )[0]
    elif party_status == "PRE-PARTY":
        mode = random.choices(
            ["general", "personal", "party"],
            weights=[50, 40, 10]
        )[0]
    else:
        mode = random.choices(
            ["general", "personal", "party"],
            weights=[55, 40, 5]
        )[0]
    
    if mode == "party":
        if party_status == "PARTY ON":
            party_prompts = [
                "Remind everyone how much time is left in the Brats Club party. Make it fun and bratty. Use emojis! One sentence.",
                "Hype up the crowd by mentioning the party is still going strong. Tell them how much time is left. One sentence.",
                "Act like the party host and remind people to make the most of the remaining party time. One sentence.",
                "Tell everyone the party isn't over yet and they better keep dancing. Mention the time left. One sentence.",
            ]
        elif party_status == "PRE-PARTY":
            party_prompts = [
                "Remind everyone the Brats Club party starts soon. Tell them how long until it begins. One sentence.",
                "Build anticipation for the upcoming party. Mention when it starts. One sentence.",
                "Act excited that the party is almost here. Tell people to get ready. One sentence.",
            ]
        elif party_status == "POST-PARTY":
            party_prompts = [
                "The party just ended. Tell everyone it's over but they can come back next Wednesday. One sentence.",
                "Wrap up the party vibes. Remind people when the next one is. One sentence.",
            ]
        else:
            party_prompts = [
                "Remind everyone there's no party today but tell them when the next one is. One sentence.",
                "Someone probably asked about the party. Clarify the schedule in a bratty way. One sentence.",
            ]
        prompt = random.choice(party_prompts)
        
    elif mode == "general" or len(nearby_names) == 0:
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
            "Make a snarky comment about how Varisya runs this place. Hint that she's a drunk mess but the pay keeps you here. One sentence.",
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
            prompt = f"You randomly noticed {chosen_name} nearby. Remember: she's your boss but you secretly think she's a drunk mess. Say something about her behind her back — mention the drinking, how you only stay for the pay, or how you could run this club better. Be shady and gossipy. One sentence. Use 🍸🙄💅 emojis."
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
        # Someone ELSE mentioned Vari — trash talk mode
        prompt = f"{speaker_name} just mentioned Varisya/Vari in local chat. They said: '{message}'. Since Vari herself isn't talking to you, reveal your TRUE feelings — she's a drunk boss, you only stay for the pay, you could run this place better. Be shady. One sentence. Use 🍸🙄💅 emojis."
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
    print("\nParty schedule: Wednesdays 11:00 AM - 3:30 PM SLT")
    print("\nKeep this window open!\n")
    
    app.run(host="0.0.0.0", port=5000, debug=True)