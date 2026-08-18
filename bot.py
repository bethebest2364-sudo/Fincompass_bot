import logging
import requests
import xml.etree.ElementTree as ET
import telebot
from telebot import types

BOT_TOKEN = "8803016019:AAFO-bV1y8NaIMmEe1VAdD3pQmBLe3hY1Nk"
CHANNEL_ID = "@FinKompass"

bot = telebot.TeleBot(BOT_TOKEN)

# --- Функции для API ---
def get_cbr_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        resp = requests.get(url, timeout=10)
        resp.encoding = 'windows-1251'
        root = ET.fromstring(resp.text)
        rates = {}
        for valute in root.findall('Valute'):
            code = valute.find('CharCode').text
            value = valute.find('Value').text.replace(',', '.')
            rates[code] = float(value)
        return rates
    except:
        return None

def get_moex_index():
    url = "https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        row = data['marketdata']['data'][0]
        return {'value': row[2], 'change': row[5]}
    except:
        return None

def get_crypto(coin):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get(coin, None)
    except:
        return None

# --- Проверка подписки ---
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

# --- Обработчики команд ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("💵 Курсы валют", callback_data='rates')
        btn2 = types.InlineKeyboardButton("📈 Индекс MOEX", callback_data='moex')
        btn3 = types.InlineKeyboardButton("₿ Криптовалюты", callback_data='crypto')
        markup.add(btn1, btn2, btn3)
        bot.send_message(
            message.chat.id,
            "✅ Добро пожаловать!\n"
            "Команды: /usd, /eur, /moex, /crypto\n"
            "Или нажми кнопку.",
            reply_markup=markup
        )
    else:
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("📢 Подписаться", url="https://t.me/FinKompass")
        markup.add(btn)
        btn2 = types.InlineKeyboardButton("🔄 Проверить", callback_data='check_sub')
        markup.add(btn2)
        bot.send_message(
            message.chat.id,
            "❌ Подпишись на канал!",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'check_sub':
        if is_subscribed(call.from_user.id):
            bot.edit_message_text(
                "✅ Подписка подтверждена! Нажми /start.",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(call.id, "❌ Ты ещё не подписан!", show_alert=True)
    elif call.data == 'rates':
        rates = get_cbr_rates()
        if rates and 'USD' in rates and 'EUR' in rates:
            text = f"💵 Доллар: {rates['USD']:.2f} ₽\n💶 Евро: {rates['EUR']:.2f} ₽"
            bot.send_message(call.message.chat.id, text)
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курсов.")
        bot.answer_callback_query(call.id)
    elif call.data == 'moex':
        data = get_moex_index()
        if data:
            sign = "+" if data['change'] >= 0 else ""
            text = f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)"
            bot.send_message(call.message.chat.id, text)
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка индекса.")
        bot.answer_callback_query(call.id)
    elif call.data == 'crypto':
        btc = get_crypto('bitcoin')
        eth = get_crypto('ethereum')
        if btc and eth:
            text = f"₿ BTC: ${btc['usd']:.0f} / €{btc['eur']:.0f}\n⟠ ETH: ${eth['usd']:.0f} / €{eth['eur']:.0f}"
            bot.send_message(call.message.chat.id, text)
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка крипты.")
        bot.answer_callback_query(call.id)

@bot.message_handler(commands=['usd'])
def cmd_usd(message):
    rates = get_cbr_rates()
    if rates and 'USD' in rates:
        bot.reply_to(message, f"💵 Доллар: {rates['USD']:.2f} ₽")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['eur'])
def cmd_eur(message):
    rates = get_cbr_rates()
    if rates and 'EUR' in rates:
        bot.reply_to(message, f"💶 Евро: {rates['EUR']:.2f} ₽")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['moex'])
def cmd_moex(message):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        bot.reply_to(message, f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['crypto'])
def cmd_crypto(message):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        bot.reply_to(message, f"₿ BTC: ${btc['usd']:.0f}  ⟠ ETH: ${eth['usd']:.0f}")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.reply_to(message, "/usd, /eur, /moex, /crypto, /help")

# --- Запуск ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен!")
    bot.infinity_polling()
