import requests
import time
import json
import os
from datetime import datetime

BOT_TOKEN = "7523737381:AAFVKjy-YkvhW5H8QDQFJxYKhk4O6bUT2Rk"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
CHANNEL_USERNAME = "zetzero"
BOT_LINK = "https://t.me/zetzero_customsms_bot"

ADMIN_ID = 6333041510
DATA_FILE = "data.json"
BANNED_USERS_FILE = "banned_users.json"

# ===========================
# Load / Save User Data
# ===========================

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
                # Ensure all users have sms_history field
                for user_id in data:
                    if "sms_history" not in data[user_id]:
                        data[user_id]["sms_history"] = []
                return data
            except json.JSONDecodeError:
                return {}
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

users = load_data()

# ===========================
# Banned Users Functions
# ===========================

def load_banned_users():
    if os.path.exists(BANNED_USERS_FILE):
        with open(BANNED_USERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_banned_users(banned_users):
    with open(BANNED_USERS_FILE, "w") as f:
        json.dump(banned_users, f, indent=4)

banned_users = load_banned_users()

# ===========================
# Telegram Functions
# ===========================

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        r = requests.post(f"{BASE_URL}/sendMessage", json=data).json()
        return r.get("result", {}).get("message_id")
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")
        return None

def delete_message(chat_id, message_id):
    try:
        requests.post(f"{BASE_URL}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
    except Exception as e:
        print(f"Error deleting message {message_id} from {chat_id}: {e}")

def is_user_joined(user_id):
    url = f"{BASE_URL}/getChatMember?chat_id=@{CHANNEL_USERNAME}&user_id={user_id}"
    try:
        resp = requests.get(url).json()
        status = resp.get("result", {}).get("status", "")
        return status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Error checking channel membership for {user_id}: {e}")
        return False

# ===========================
# Keyboards
# ===========================

def main_buttons():
    return {
        "keyboard": [
            ["✉️ Send Custom SMS", "🔄 Update"],
            ["👤 Account", "👥 Invite"],
            ["🎁 Daily Bonus", "💰 Buy Coin"],
            ["🔙 Back"]
        ],
        "resize_keyboard": True
    }

def joined_button():
    return {"keyboard": [["✅ JOINED"]], "resize_keyboard": True}

def invite_buttons():
    return {"keyboard": [["👀 View Referrals"], ["🔙 Back"]], "resize_keyboard": True}

# ===========================
# Handle Update
# ===========================

def handle_update(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    username = message["from"].get("first_name", "User")
    text = message.get("text", "")

    if str(user_id) in banned_users:
        send_message(chat_id, "🚫 আপনি আমাদের বটের সকল রুলস মেনে চলেন নি, তাই আপনাকে ব্যান করা হয়েছে।", reply_markup={"remove_keyboard": True})
        return

    if str(user_id) not in users:
        users[str(user_id)] = {
            "coins": 5,
            "referred_by": None,
            "action": None,
            "target": None,
            "refers": 0,
            "referrals": [],
            "join_msg_id": None,
            "last_bonus_time": 0,
            "sms_history": []
        }
        save_data()

    user = users[str(user_id)]
    
    # Check if user is a member of the channel
    if not is_user_joined(user_id):
        send_message(chat_id, 
            "⚠️ আপনি আমাদের চ্যানেল থেকে রিমুভ হয়ে গেছেন। অনুগ্রহ করে আবার জয়েন করুন:\n\n"
            f"🔗 @{CHANNEL_USERNAME}", 
            reply_markup=joined_button()
        )
        return

    # ✅ Start Command
    if text.startswith("/start"):
        msg_id = send_message(
            chat_id,
            "ℹ️ আমাদের চ্যানেল এ জয়েন করুন এবং পরিচয় দিন\n\n"
            f"🔗 @{CHANNEL_USERNAME}\n\n"
            "✅ Join করার পর JOINED বাটনে ক্লিক করুন ✅",
            reply_markup=joined_button()
        )
        user["join_msg_id"] = msg_id

        # referral handle
        if len(text.split()) > 1:
            ref_id = text.split()[1].replace("Bot", "")
            if ref_id.isdigit():
                ref_id = str(ref_id)
                if ref_id != str(user_id) and user["referred_by"] is None:
                    if str(user_id) not in [str(r["id"]) for r in users.get(ref_id, {}).get("referrals", [])]:
                        user["referred_by"] = ref_id
                        save_data()
        return

    # ✅ Update Button
    if text == "🔄 Update":
        handle_update({
            "message": {
                "chat": {"id": chat_id},
                "from": {"id": user_id, "first_name": username},
                "text": "/start"
            }
        })
        return

    # ✅ Admin Commands
    if user_id == ADMIN_ID:
        if text == "/admin":
            send_message(chat_id, "✅ Admin login successful!", reply_markup=main_buttons())
            return
        
        # NEW: /admincmd
        if text == "/admincmd":
            admin_commands = (
                "<b>Admin Commands:</b>\n"
                "কমান্ডগুলোর কাজ সম্পর্কে জানতে টাইপ করুন:\n\n"
                "<code>/info {uid}</code> - একটি নির্দিষ্ট ইউজার সম্পর্কে বিস্তারিত তথ্য দেখুন।\n"
                "<code>/add {uid}-{amount}</code> - একটি ইউজারকে নির্দিষ্ট পরিমাণ কয়েন দিন।\n"
                "<code>/removecoin {uid}-{amount}</code> - একটি ইউজার থেকে নির্দিষ্ট পরিমাণ কয়েন নিন।\n"
                "<code>/alluser</code> - বটের সকল ইউজারের তালিকা দেখুন।\n"
                "<code>/alluserinfo</code> - সকল ইউজারের বিস্তারিত তথ্য এবং SMS হিস্টোরি দেখুন।\n"
                "<code>/sms {uid} - {message}</code> - একটি নির্দিষ্ট ইউজারকে ব্যক্তিগত মেসেজ পাঠান।\n"
                "<code>/ban {uid}</code> - একটি ইউজারকে বট ব্যবহার থেকে ব্যান করুন।\n"
                "<code>/unban {uid}</code> - ব্যান হওয়া ইউজারকে আনব্যান করুন।\n"
                "<code>/broadcast {message}</code> - সকল ইউজারকে একটি মেসেজ পাঠান।"
            )
            send_message(chat_id, admin_commands)
            return

        # Add coins
        if text.startswith("/add"):
            try:
                cmd = text.split()[1]
                uid, amount = cmd.split("-")
                uid = str(uid)
                amount = int(amount)
                if uid in users:
                    users[uid]["coins"] += amount
                    save_data()
                    send_message(chat_id, f"✅ Added {amount} coins to {users[uid]['coins']} total (UID {uid})")
                    send_message(uid, f"🎁 <b>{amount} coins added to your account by Admin!</b>")
                else:
                    send_message(chat_id, f"❌ User {uid} not found.")
            except Exception as e:
                send_message(chat_id, f"🚫 Error: {e}\nUsage: /add uid-amount")
            return

        # Remove coins
        if text.startswith("/removecoin"):
            try:
                cmd_parts = text.split()
                if len(cmd_parts) < 2:
                    send_message(chat_id, "🚫 Usage: /removecoin uid-amount or /removecoin -all")
                    return
                
                target = cmd_parts[1]
                if target == "-all":
                    for uid in users.keys():
                        users[uid]["coins"] = 0
                    save_data()
                    send_message(chat_id, "✅ Removed all coins from all users.")
                else:
                    uid, amount = target.split("-")
                    uid = str(uid)
                    amount = int(amount)
                    if uid in users:
                        if users[uid]["coins"] >= amount:
                            users[uid]["coins"] -= amount
                            save_data()
                            send_message(chat_id, f"✅ Removed {amount} coins from UID {uid}. Remaining: {users[uid]['coins']}")
                            send_message(uid, f"🚫 Admin removed {amount} coins from your account.")
                        else:
                            send_message(chat_id, f"❌ User has only {users[uid]['coins']} coins. Cannot remove {amount}.")
                    else:
                        send_message(chat_id, f"❌ User {uid} not found.")
            except Exception as e:
                send_message(chat_id, f"🚫 Error: {e}")
            return

        # /alluser
        if text == "/alluser":
            user_list = []
            for uid, data in users.items():
                try:
                    user_info = requests.get(f"{BASE_URL}/getChatMember?chat_id={uid}&user_id={uid}").json().get("result", {})
                    name = user_info.get("user", {}).get("first_name", "User")
                    user_list.append(f"<a href='tg://user?id={uid}'>{name}</a> - {uid} - {data['coins']} coins")
                except:
                    user_list.append(f"User - {uid} - {data['coins']} coins")
            response_text = "All Users:\n" + "\n".join(user_list)
            send_message(chat_id, response_text)
            return

        # /sms {uid} - {message}
        if text.startswith("/sms"):
            try:
                parts = text.split(" ", 2)
                uid = parts[1]
                message_to_send = parts[2]
                if uid in users:
                    send_message(uid, f"📢 Admin Message: {message_to_send}")
                    send_message(chat_id, f"✅ Message sent to UID {uid}.")
                else:
                    send_message(chat_id, f"❌ User {uid} not found.")
            except Exception as e:
                send_message(chat_id, f"🚫 Usage: /sms {{uid}} - {{message}}")
            return

        # /ban {uid}
        if text.startswith("/ban"):
            try:
                uid = text.split(" ")[1]
                if uid not in banned_users:
                    banned_users.append(uid)
                    save_banned_users(banned_users)
                    send_message(chat_id, f"✅ User {uid} has been banned.")
                    send_message(uid, "🚫 আপনি আমাদের বটের সকল রুলস মেনে চলেন নি, তাই আপনাকে ব্যান করা হয়েছে।", reply_markup={"remove_keyboard": True})
                else:
                    send_message(chat_id, f"❌ User {uid} is already banned.")
            except:
                send_message(chat_id, "🚫 Usage: /ban {uid}")
            return
        
        # /unban {uid}
        if text.startswith("/unban"):
            try:
                uid = text.split(" ")[1]
                if uid in banned_users:
                    banned_users.remove(uid)
                    save_banned_users(banned_users)
                    send_message(chat_id, f"✅ User {uid} has been unbanned.")
                    send_message(uid, "🎉 আপনি এখন আনব্যান হয়েছেন।")
                else:
                    send_message(chat_id, f"❌ User {uid} is not banned.")
            except:
                send_message(chat_id, "🚫 Usage: /unban {uid}")
            return
        
        # /alluserinfo
        if text == "/alluserinfo":
            info_list = []
            for uid, data in users.items():
                try:
                    user_info = requests.get(f"{BASE_URL}/getChatMember?chat_id={uid}&user_id={uid}").json().get("result", {})
                    name = user_info.get("user", {}).get("first_name", "User")
                    
                    sms_history_text = ""
                    if data.get("sms_history"):
                        sms_history_text = "\n" + "\n".join(
                            [f"  - Number: {h['target']}, Message: {h['message']}, Time: {h['time']}" for h in data["sms_history"]]
                        )
                    
                    info_list.append(
                        f"----------------------------------\n"
                        f"👤 Name: <a href='tg://user?id={uid}'>{name}</a>\n"
                        f"🆔 UID: {uid}\n"
                        f"🪙 Coins: {data['coins']}\n"
                        f"👥 Total Refers: {data['refers']}\n"
                        f"💬 SMS History: {sms_history_text if sms_history_text else 'No SMS sent.'}"
                    )
                except:
                    info_list.append(f"----------------------------------\nUser: {uid} (Info not available)")
            
            response_text = "\n".join(info_list)
            send_message(chat_id, response_text)
            return

        # /info {uid}
        if text.startswith("/info"):
            try:
                uid = text.split(" ")[1]
                if uid in users:
                    u = users[uid]
                    user_profile_link = f"tg://user?id={uid}"
                    
                    user_info = requests.get(f"{BASE_URL}/getChatMember?chat_id={uid}&user_id={uid}").json().get("result", {})
                    name = user_info.get("user", {}).get("first_name", "User")

                    sms_history_text = "No SMS sent."
                    if u.get("sms_history"):
                        sms_history_text = "\n" + "\n".join(
                            [f"  - Number: {h['target']}, Message: {h['message']}, Time: {h['time']}" for h in u["sms_history"]]
                        )

                    send_message(chat_id,
                        f"👤 User Info for <a href='tg://user?id={uid}'>{name}</a>\n"
                        f"🆔 UID: {uid}\n"
                        f"🪙 Coins: {u['coins']}\n"
                        f"👥 Total Refers: {u['refers']}\n"
                        f"💬 SMS History: {sms_history_text}",
                        reply_markup={
                            "inline_keyboard": [
                                [{"text": f"👤 {name}'s Profile", "url": user_profile_link}]
                            ]
                        }
                    )
                else:
                    send_message(chat_id, f"❌ User {uid} not found.")
            except:
                send_message(chat_id, "🚫 Usage: /info {uid}")
            return

        # /user UID command (renamed to /user)
        if text.startswith("/user"):
            try:
                uid = text.split()[1]
                if uid in users:
                    u = users[uid]
                    send_message(chat_id,
                        f"👤 User Info (UID {uid})\n"
                        f"Coins: {u['coins']}\n"
                        f"Total Refers: {u['refers']}"
                    )
                else:
                    send_message(chat_id, f"❌ User {uid} not found.")
            except:
                send_message(chat_id, "🚫 Usage: /user UID")
            return

        # /broadcast message
        if text.startswith("/broadcast"):
            try:
                msg = text.split(" ", 1)[1]
                for uid in users.keys():
                    try:
                        send_message(uid, f"📣 {msg}")
                    except:
                        pass
                send_message(chat_id, "✅ Broadcast sent to all users.")
            except:
                send_message(chat_id, "🚫 Usage: /broadcast your_message")
            return

    # ✅ JOINED Button
    if text == "✅ JOINED":
        if is_user_joined(user_id):
            if user["join_msg_id"]:
                delete_message(chat_id, user["join_msg_id"])
                user["join_msg_id"] = None
            
            ref_id = user.get("referred_by")
            if ref_id and ref_id in users:
                users[ref_id]["coins"] += 2
                users[ref_id]["refers"] += 1
                users[ref_id]["referrals"].append({"id": user_id, "name": username})
                send_message(ref_id, f"👥 New referral joined! +2 coins\nCurrent Coins: {users[ref_id]['coins']}")
                user["referred_by"] = None
            
            send_message(chat_id, f"স্বাগতম <a href='tg://user?id={user_id}'>{username}</a>, আপনাকে আমাদের বটে স্বাগতম। আমাদের বটের সকল রুলস মেনে চলবেন। ধন্যবাদ!", reply_markup=main_buttons())
        else:
            send_message(chat_id, "❌ Please join the channel first!", reply_markup=joined_button())
        save_data()
        return

    # ✅ Daily Bonus
    if text == "🎁 Daily Bonus":
        now = int(time.time())
        last_time = user.get("last_bonus_time", 0)
        if now - last_time >= 86400:
            user["coins"] += 5
            user["last_bonus_time"] = now
            save_data()
            send_message(chat_id, "🎁 You claimed your Daily Bonus +5 coins!", reply_markup=main_buttons())
        else:
            wait = 86400 - (now - last_time)
            hours = wait // 3600
            mins = (wait % 3600) // 60
            send_message(chat_id, f"⏳ You can claim again in {hours}h {mins}m.", reply_markup=main_buttons())
        return

    # ✅ Buy Coin
    if text == "💰 Buy Coin":
        send_message(
            chat_id,
            "🛍️ To buy coins contact 👤",
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📞 Contact", "url": "https://t.me/binmamun"}]
                ]
            }
        )
        return

    # ✅ Other Buttons
    if text == "✉️ Send Custom SMS":
        send_message(chat_id, "❯ Enter Target Number", reply_markup={"keyboard": [["🔙 Back"]], "resize_keyboard": True})
        user["action"] = "await_number"
        save_data()
        return

    if text == "👤 Account":
        send_message(chat_id, f"👤 {username}\n\n🪙 Coins: {user['coins']}\n👥 Total Invites: {user['refers']}", reply_markup=main_buttons())
        return

    if text == "👥 Invite":
        link = f"{BOT_LINK}?start=Bot{user_id}"
        msg = (
            f"👥🔥 Total Referrals = {user['refers']} User(s)\n\n"
            f"👥🔥 Your Referral Link = {link}\n\n"
            "➕ প্রতিটি রেফারেলে 2 Coins করে পাবেন"
        )
        send_message(chat_id, msg, reply_markup=invite_buttons())
        return

    if text == "👀 View Referrals":
        if not user["referrals"]:
            ref_text = "❌ No users referred yet."
        else:
            ref_text = "👀 Your Referrals:\n" + "\n".join(
                [f"➡️ <a href='tg://user?id={r['id']}'>{r['name']}</a>" for r in user["referrals"]]
            )
        send_message(chat_id, ref_text, reply_markup=invite_buttons())
        return

    if text == "🔙 Back":
        user["action"] = None
        user["target"] = None
        send_message(chat_id, "Select Option:", reply_markup=main_buttons())
        save_data()
        return

    # ✅ Custom SMS Flow
    action = user.get("action")
    if action == "await_number":
        user["target"] = text
        user["action"] = "await_message"
        send_message(chat_id, "❯ Enter Your Message", reply_markup={"keyboard": [["🔙 Back"]], "resize_keyboard": True})
        save_data()
        return

    if action == "await_message":
        if user["coins"] < 2:
            send_message(chat_id, "ℹ️ You don't have enough coins to send SMS.", reply_markup=main_buttons())
            user["action"] = None
            save_data()
            return
        
        target = user["target"]
        msg = text
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sms_data = {"target": target, "message": msg, "time": timestamp, "status": "Failed"}
        
        try:
            response = requests.get(
                f"https://hl-hadi.mooo.com/csms/api.php?key=45656448fbe25448ce6ae7180e0e607c&number={target}&msg={msg}"
            )
            print("STATUS:", response.status_code)
            print("RESPONSE:", response.text)

            if response.status_code == 200 and "success" in response.text.lower():
                user["coins"] -= 2
                send_message(chat_id, "📨 CUSTOM SMS SENT SUCCESSFULLY", reply_markup=main_buttons())
                sms_data["status"] = "Success"
            else:
                send_message(chat_id, "🚫 Failed to send SMS.", reply_markup=main_buttons())
            
        except Exception as e:
            print("ERROR:", str(e))
            send_message(chat_id, "🚫 Failed to send SMS.", reply_markup=main_buttons())
        
        user["sms_history"].append(sms_data)
        user["action"] = None
        user["target"] = None
        save_data()
        return

# ===========================
# Run Bot
# ===========================

def run_bot():
    last_update_id = 0
    while True:
        try:
            params = {"timeout": 50, "offset": last_update_id}
            resp = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=60).json()
            result = resp.get("result", [])
            for update in result:
                last_update_id = update["update_id"] + 1
                handle_update(update)
        except Exception as e:
            print("Error:", e)
        time.sleep(1)

if __name__ == "__main__":
    run_bot()