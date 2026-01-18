import telebot
import random
import time
from collections import defaultdict, deque
from datetime import datetime
import threading

# ================== НАСТРОЙКАЛАР ==================
TOKEN = "8452130052:AAEmgL6VpmuGNi6NAX88byrKV7q-QGxyy-o"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
ROULETTE_GIF = "https://media.giphy.com/media/3o6Zt6ML6BklcajjsA/giphy.gif"

START_BALANCE = 5000
MIN_BET = 100
admins = [7268172384]

# ================== ДАННЫЕ ==================
balances = defaultdict(lambda: START_BALANCE)
last_numbers = defaultdict(lambda: deque(maxlen=10))
history = defaultdict(lambda: deque(maxlen=50))
bets = defaultdict(lambda: defaultdict(list))
spinning = set()
last_bet = defaultdict(lambda: None)

ICONS_SLOT = ["🍒","🍋","🍇"]
ICONS_BANDIT = ["🍒","🍋","🍇","💎","7️⃣"]

# ================== ФУНКЦИИ ==================
def mention(user):
    return f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"

def record_history(user_id, action):
    now = datetime.now().strftime("%d.%m %H:%M:%S")
    history[user_id].append(f"{now} - {action}")

def roulette_spin():
    return random.choice(list(range(13)))

def roulette_multiplier(number):
    if number == 0: return 12
    multipliers = {1:12,2:6,3:4,4:3,5:2.4,6:2,7:1.71,8:1.5,9:1.33,10:1.2,11:1.09,12:1}
    return multipliers.get(number,1)

def va_bank_numbers(v):
    if v=="к": return [1,3,5,7,9,11]
    if v=="ч": return [2,4,6,8,10,12]
    if v=="ж": return [0]
    return []

# ================== SLOT / BANDIT ==================
def play_game(user, user_id, chat_id, amt, icons):
    if balances[user_id]<amt:
        bot.reply_to(user,"❌ Баланс жетишсиз")
        return
    balances[user_id]-=amt
    player = f"<b>{user.first_name}</b>"
    length = len(icons)
    msg = bot.send_message(chat_id, f"{player}\n🎰 " + " | ".join(["⬛"]*length), parse_mode="HTML")
    final = [random.choice(icons) for _ in range(length)]

    # Бир нече жолу айлантуу эффектиси
    for _ in range(6):
        temp = [random.choice(icons) for _ in range(length)]
        bot.edit_message_text(f"{player}\n🎰 " + " | ".join(temp), chat_id, msg.message_id, parse_mode="HTML")
        time.sleep(0.3)

    # Бирден ачуу
    shown = ["⬛"]*length
    for i in range(length):
        shown[i] = final[i]
        bot.edit_message_text(f"{player}\n🎰 " + " | ".join(shown), chat_id, msg.message_id, parse_mode="HTML")
        time.sleep(0.8)

    # Жеңиш текшерүү
    multiplier = 1
    counts = {x: final.count(x) for x in set(final)}
    if length==3:  # SLOT
        if len(set(final))==1: multiplier=6
        elif len(set(final))==2: multiplier=2
    else:  # BANDIT
        for v in counts.values():
            if v==3: multiplier=max(multiplier,4)
            elif v==4: multiplier=max(multiplier,8)
            elif v==5: multiplier=max(multiplier,16)

    if multiplier>1:
        win = amt*multiplier
        balances[user_id]+=win
        bot.edit_message_text(f"{player}\n🎰 " + " | ".join(final) + f"\n🔥 Уттуң! +{win}", chat_id, msg.message_id, parse_mode="HTML")
    else:
        bot.edit_message_text(f"{player}\n🎰 " + " | ".join(final) + "\n💀 Утулду", chat_id, msg.message_id, parse_mode="HTML")
    record_history(user_id,f"{'Слот' if length==3 else 'Бандит'} ойноду, ставка {amt}")

# ================== РУЛЕТКА ==================
def roulette_play(chat_id):
    if chat_id in spinning: return
    if not bets[chat_id]:
        bot.send_message(chat_id,"❌ Ставка жок")
        return
    spinning.add(chat_id)
    gif_msg = bot.send_animation(chat_id,ROULETTE_GIF)

    def finish_spin():
        try: bot.delete_message(chat_id,gif_msg.message_id)
        except: pass
        result = roulette_spin()
        last_numbers[chat_id].append(result)
        text_out = f"🎯 Выпало: {result}\n\n"
        winners=[]
        for u,bets_list in bets[chat_id].items():
            for amt,n in bets_list:
                if n in ["к","ч","ж"]:
                    nums = va_bank_numbers(n)
                    multiplier = 6 if n in ["к","ч"] else 12
                elif "-" in str(n):
                    s,e = map(int,n.split("-"))
                    nums = list(range(s,e+1))
                    multiplier = 1
                else:
                    nums=[int(n)]
                    multiplier = roulette_multiplier(int(n))
                if result in nums:
                    win = int(amt*multiplier)
                    balances[u]+=win
                    winners.append(f"{mention(bot.get_chat_member(chat_id,u).user)} выиграл {win} на {n}")
                text_out+=f"{mention(bot.get_chat_member(chat_id,u).user)} {amt} на {n}\n"
        if winners: text_out+="\n🏆 ЖЕҢДИ:\n"+ "\n".join(winners)
        else: text_out+="\n❌ Бул жолу уткан жок"
        bot.send_message(chat_id,text_out)
        bets[chat_id].clear()
        spinning.remove(chat_id)

    threading.Timer(5, finish_spin).start()

# ================== ХАНДЛЕР ==================
@bot.message_handler(func=lambda m: True)
def handler(message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id
    text = message.text.lower().strip()

    # ---------- БАЛАНС ----------
    if text=="б":
        bot.reply_to(message,f"💰 Эсебин: {balances[user_id]}")
        return

    # ---------- ЛОГ ----------
    if text=="лог":
        if not last_numbers[chat_id]:
            bot.reply_to(message,"📜 Лог бош")
        else:
            nums = " ".join(map(str,last_numbers[chat_id]))
            bot.reply_to(message,f"📜 Акыркы ойногон сандар:\n{nums}")
        return

    # ---------- ИСТОРИЯ ----------
    if text=="история":
        if not history[user_id]:
            bot.reply_to(message,"📜 История бош")
            return
        bot.reply_to(message,"\n".join(history[user_id]))
        return

    # ---------- ПОВТОРИТЬ / УДВОИТЬ ----------
    if text in ["повторить","удвоить"]:
        if last_bet[user_id] is None:
            bot.reply_to(message,"❌ Акыркы ставка жок")
            return
        amount,target = last_bet[user_id]
        if text=="удвоить": amount*=2
        if amount>balances[user_id]:
            bot.reply_to(message,"❌ Баланс жетишсиз")
            return
        balances[user_id]-=amount
        bets[chat_id][user_id].append((amount,target))
        bot.send_message(chat_id,f"{mention(user)} ставка койду: {amount} на {target} ✅")
        last_bet[user_id]=(amount,target)
        record_history(user_id,f"Ставка {'повторить' if text=='повторить' else 'удвоить'} {amount} на {target}")
        return

    # ---------- СТАВКА РУЛЕТКА ----------
    parts = text.split()
    if len(parts)==2:
        try:
            amount=int(parts[0])
            target=parts[1]
        except: return
        if amount>balances[user_id]:
            bot.reply_to(message,"❌ Баланс жетишсиз")
            return
        balances[user_id]-=amount
        bets[chat_id][user_id].append((amount,target))
        last_bet[user_id]=(amount,target)
        bot.send_message(chat_id,f"{mention(user)} ставка койду: {amount} на {target} ✅")
        record_history(user_id,f"Ставка {amount} на {target}")
        return

    # ---------- РУЛЕТКА ----------
    if text in ["го","айлантыр","айда","бол"]:
        roulette_play(chat_id)
        return

    # ---------- СЛОТ ----------
    if text.startswith("слот"):
        try:
            amt = int(text.split()[1])
            threading.Thread(target=play_game,args=(user,user_id,chat_id,amt,ICONS_SLOT)).start()
        except:
            bot.reply_to(message,"❌ Команда туура эмес")
        return

    # ---------- БАНДИТ ----------
    if text.startswith("бандит"):
        try:
            amt = int(text.split()[1])
            threading.Thread(target=play_game,args=(user,user_id,chat_id,amt,ICONS_BANDIT)).start()
        except:
            bot.reply_to(message,"❌ Команда туура эмес")
        return

    # ---------- АДМИН ФУНКЦИИ ----------
    if user_id in admins:
        if text.startswith("/донат"):
            try:
                parts = text.split()
                target_id = int(parts[1])
                amount = int(parts[2])
                balances[target_id]+=amount
                bot.reply_to(message,f"{mention(user)} донат жасады {amount} монета {target_id}ге")
                record_history(user_id,f"Донат {amount} -> {target_id}")
            except: return
        if text.startswith("/бан"):
            try:
                target_id=int(text.split()[1])
                bot.kick_chat_member(chat_id,target_id)
                bot.reply_to(message,f"{mention(user)} забанил {target_id}")
                record_history(user_id,f"Бан {target_id}")
            except: return
        if text.startswith("/кик"):
            try:
                target_id=int(text.split()[1])
                bot.kick_chat_member(chat_id,target_id)
                bot.unban_chat_member(chat_id,target_id)
                bot.reply_to(message,f"{mention(user)} кикнул {target_id}")
                record_history(user_id,f"Кик {target_id}")
            except: return
        if text.startswith("/мут"):
            try:
                target_id=int(text.split()[1])
                bot.restrict_chat_member(chat_id,target_id,until_date=int(time.time()+3600))
                bot.reply_to(message,f"{mention(user)} замутил {target_id} на 1ч")
                record_history(user_id,f"Мут {target_id} 1ч")
            except: return

bot.infinity_polling()
