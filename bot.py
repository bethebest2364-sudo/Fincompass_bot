import logging
import requests
import xml.etree.ElementTree as ET
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

BOT_TOKEN = "8803016019:AAFO-bV1y8NaIMmEe1VAdD3pQmBLe3hY1Nk"
CHANNEL_ID = "@FinKompass"

# Функции для API
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

# Проверка подписки (синхронная версия)
def is_subscribed(user_id, bot):
    try:
        member = bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

# Команда /start
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if is_subscribed(user_id, context.bot):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💵 Курсы валют", callback_data='rates'),
             InlineKeyboardButton("📈 Индекс MOEX", callback_data='moex')],
            [InlineKeyboardButton("₿ Криптовалюты", callback_data='crypto')]
        ])
        update.message.reply_text(
            "✅ Добро пожаловать!\n"
            "Команды: /usd, /eur, /moex, /crypto\n"
            "Или нажми кнопку.",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Подписаться", url="https://t.me/FinKompass")],
            [InlineKeyboardButton("🔄 Проверить", callback_data='check_sub')]
        ])
        update.message.reply_text("❌ Подпишись на канал!", reply_markup=keyboard)

def check_subscription(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    if is_subscribed(user_id, context.bot):
        query.edit_message_text("✅ Подписка подтверждена! Нажми /start.")
    else:
        query.answer("❌ Ты ещё не подписан!", show_alert=True)

def button_rates(update: Update, context: CallbackContext):
    rates = get_cbr_rates()
    if rates and 'USD' in rates and 'EUR' in rates:
        text = f"💵 Доллар: {rates['USD']:.2f} ₽\n💶 Евро: {rates['EUR']:.2f} ₽"
        update.callback_query.message.reply_text(text)
    else:
        update.callback_query.message.reply_text("❌ Ошибка курсов.")
    update.callback_query.answer()

def button_moex(update: Update, context: CallbackContext):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        text = f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)"
        update.callback_query.message.reply_text(text)
    else:
        update.callback_query.message.reply_text("❌ Ошибка индекса.")
    update.callback_query.answer()

def button_crypto(update: Update, context: CallbackContext):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        text = f"₿ BTC: ${btc['usd']:.0f} / €{btc['eur']:.0f}\n⟠ ETH: ${eth['usd']:.0f} / €{eth['eur']:.0f}"
        update.callback_query.message.reply_text(text)
    else:
        update.callback_query.message.reply_text("❌ Ошибка крипты.")
    update.callback_query.answer()

def cmd_usd(update: Update, context: CallbackContext):
    rates = get_cbr_rates()
    if rates and 'USD' in rates:
        update.message.reply_text(f"💵 Доллар: {rates['USD']:.2f} ₽")
    else:
        update.message.reply_text("❌ Ошибка")

def cmd_eur(update: Update, context: CallbackContext):
    rates = get_cbr_rates()
    if rates and 'EUR' in rates:
        update.message.reply_text(f"💶 Евро: {rates['EUR']:.2f} ₽")
    else:
        update.message.reply_text("❌ Ошибка")

def cmd_moex(update: Update, context: CallbackContext):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        update.message.reply_text(f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
    else:
        update.message.reply_text("❌ Ошибка")

def cmd_crypto(update: Update, context: CallbackContext):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        update.message.reply_text(f"₿ BTC: ${btc['usd']:.0f}  ⟠ ETH: ${eth['usd']:.0f}")
    else:
        update.message.reply_text("❌ Ошибка")

def cmd_help(update: Update, context: CallbackContext):
    update.message.reply_text("/usd, /eur, /moex, /crypto, /help")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("usd", cmd_usd))
    dp.add_handler(CommandHandler("eur", cmd_eur))
    dp.add_handler(CommandHandler("moex", cmd_moex))
    dp.add_handler(CommandHandler("crypto", cmd_crypto))
    dp.add_handler(CommandHandler("help", cmd_help))
    dp.add_handler(CallbackQueryHandler(check_subscription, pattern='check_sub'))
    dp.add_handler(CallbackQueryHandler(button_rates, pattern='rates'))
    dp.add_handler(CallbackQueryHandler(button_moex, pattern='moex'))
    dp.add_handler(CallbackQueryHandler(button_crypto, pattern='crypto'))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен!")
    main()
