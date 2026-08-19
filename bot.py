import logging
import requests
import re
import xml.etree.ElementTree as ET
import telebot
from telebot import types

BOT_TOKEN = "8803016019:AAFO-bV1y8NaIMmEe1VAdD3pQmBLe3hY1Nk"
CHANNEL_ID = -1001657916970   # ваш числовой ID канала

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- ФУНКЦИИ ДЛЯ API (без изменений) ----------
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
    symbol = 'BTCUSDT' if coin == 'bitcoin' else 'ETHUSDT'
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        price_usd = float(data['price'])
        eur_url = "https://api.exchangerate-api.com/v4/latest/USD"
        eur_resp = requests.get(eur_url, timeout=5)
        eur_rate = eur_resp.json()['rates']['EUR']
        price_eur = price_usd * eur_rate
        return {'usd': price_usd, 'eur': price_eur}
    except:
        return None

def get_key_rate():
    url = "https://www.cbr.ru/scripts/XML_KeyRate.asp"
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.text)
        record = root.find('Record')
        if record is not None:
            date = record.get('Date')
            rate = record.text
            return {'date': date, 'rate': rate}
        return None
    except:
        try:
            url2 = "https://www.cbr.ru/hd_base/KeyRate/"
            resp2 = requests.get(url2, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            match = re.search(r'<td[^>]*>(\d{2}\.\d{2}\.\d{4})</td>\s*<td[^>]*>([\d,]+)</td>', resp2.text, re.DOTALL)
            if match:
                date = match.group(1)
                rate = match.group(2).replace(',', '.')
                return {'date': date, 'rate': rate}
            return None
        except:
            return None

def get_gold_price():
    url = "https://api.gold-api.com/price/XAU"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        price_usd = data['price']
        rates = get_cbr_rates()
        if rates and 'USD' in rates:
            rub_rate = rates['USD']
            price_rub = price_usd * rub_rate
            return {'usd': round(price_usd, 2), 'rub': round(price_rub, 2)}
        return None
    except:
        return None

def get_oil_price():
    ticker = "CL=F"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        data = resp.json()
        meta = data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        if price:
            return {'price': round(price, 2)}
        return None
    except:
        return None

def get_cny_rate():
    rates = get_cbr_rates()
    if rates and 'CNY' in rates:
        return {'value': rates['CNY']}
    return None

def get_sp500():
    ticker = "^GSPC"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        data = resp.json()
        meta = data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice')
        previous_close = meta.get('previousClose')
        if price and previous_close:
            change = ((price - previous_close) / previous_close) * 100
            return {'value': round(price, 2), 'change': round(change, 2)}
        return None
    except:
        return None

def get_news():
    url = "https://www.banki.ru/xml/news.rss"
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        if resp.status_code != 200:
            return None
        root = ET.fromstring(resp.content)
        items = root.findall('.//item')[:5]
        news = []
        for item in items:
            title = item.find('title').text
            pub_date = item.find('pubDate').text[:16]
            news.append(f"• {title} ({pub_date})")
        return news
    except:
        return None

def get_stock_quote(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        data = resp.json()
        meta = data['chart']['result'][0]['meta']
        regular_market_price = meta.get('regularMarketPrice')
        previous_close = meta.get('previousClose')
        if regular_market_price and previous_close:
            change = ((regular_market_price - previous_close) / previous_close) * 100
            currency = meta.get('currency', 'USD')
            return {
                'price': round(regular_market_price, 2),
                'change': round(change, 2),
                'currency': currency
            }
        return None
    except:
        return None

# ---------- ПРОВЕРКА ПОДПИСКИ ----------
def is_subscribed(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

# ---------- ОБРАБОТЧИКИ КОМАНД ----------
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if is_subscribed(user_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💱 Валюты", callback_data='currencies'),
            types.InlineKeyboardButton("₿ Криптовалюты", callback_data='cryptos'),
            types.InlineKeyboardButton("📊 Индексы", callback_data='indices'),
            types.InlineKeyboardButton("🏭 Сырьё", callback_data='commodities'),
            types.InlineKeyboardButton("🔑 Ключевая ставка", callback_data='keyrate'),
            types.InlineKeyboardButton("📰 Новости", callback_data='news')
        )
        bot.send_message(
            message.chat.id,
            "✅ Добро пожаловать в Финансовый Компас!\n"
            "Выберите нужный раздел или введите команду:\n"
            "/usd, /eur, /cny, /btc, /eth, /moex, /sp500, /gold, /oil, /keyrate, /news, /stock AAPL, /help",
            reply_markup=markup
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться", url="https://t.me/FinKompass"))
        markup.add(types.InlineKeyboardButton("🔄 Проверить", callback_data='check_sub'))
        bot.send_message(message.chat.id, "❌ Подпишись на канал!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == 'check_sub':
        if is_subscribed(call.from_user.id):
            bot.edit_message_text("✅ Подписка подтверждена! Нажми /start.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Ты ещё не подписан!", show_alert=True)

    # ---------- ВАЛЮТЫ (подменю) ----------
    elif call.data == 'currencies':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💵 Доллар (USD)", callback_data='currency_usd'),
            types.InlineKeyboardButton("💶 Евро (EUR)", callback_data='currency_eur'),
            types.InlineKeyboardButton("🇨🇳 Юань (CNY)", callback_data='currency_cny'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите валюту:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    # ---------- КРИПТОВАЛЮТЫ (подменю) ----------
    elif call.data == 'cryptos':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data='crypto_btc'),
            types.InlineKeyboardButton("⟠ Ethereum (ETH)", callback_data='crypto_eth'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите криптовалюту:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    # ---------- ИНДЕКСЫ (подменю) ----------
    elif call.data == 'indices':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📈 MOEX", callback_data='moex'),
            types.InlineKeyboardButton("🇺🇸 S&P 500", callback_data='sp500'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите индекс:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    # ---------- СЫРЬЁ (подменю) ----------
    elif call.data == 'commodities':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🏆 Золото", callback_data='gold'),
            types.InlineKeyboardButton("🛢 Нефть", callback_data='oil'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите товар:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)

    # ---------- ОБРАБОТЧИКИ ВАЛЮТ ----------
    elif call.data == 'currency_usd':
        rates = get_cbr_rates()
        if rates and 'USD' in rates:
            bot.send_message(call.message.chat.id, f"💵 Доллар: {rates['USD']:.2f} ₽")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса.")
        bot.answer_callback_query(call.id)

    elif call.data == 'currency_eur':
        rates = get_cbr_rates()
        if rates and 'EUR' in rates:
            bot.send_message(call.message.chat.id, f"💶 Евро: {rates['EUR']:.2f} ₽")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса.")
        bot.answer_callback_query(call.id)

    elif call.data == 'currency_cny':
        data = get_cny_rate()
        if data:
            bot.send_message(call.message.chat.id, f"🇨🇳 Юань: {data['value']:.2f} ₽")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса.")
        bot.answer_callback_query(call.id)

    # ---------- ОБРАБОТЧИКИ КРИПТЫ ----------
    elif call.data == 'crypto_btc':
        data = get_crypto('bitcoin')
        if data:
            bot.send_message(call.message.chat.id, f"₿ BTC: ${data['usd']:.0f} / €{data['eur']:.0f}")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса BTC.")
        bot.answer_callback_query(call.id)

    elif call.data == 'crypto_eth':
        data = get_crypto('ethereum')
        if data:
            bot.send_message(call.message.chat.id, f"⟠ ETH: ${data['usd']:.0f} / €{data['eur']:.0f}")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса ETH.")
        bot.answer_callback_query(call.id)

    # ---------- ИНДЕКСЫ ----------
    elif call.data == 'moex':
        data = get_moex_index()
        if data:
            sign = "+" if data['change'] >= 0 else ""
            bot.send_message(call.message.chat.id, f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка индекса.")
        bot.answer_callback_query(call.id)

    elif call.data == 'sp500':
        data = get_sp500()
        if data:
            sign = "+" if data['change'] >= 0 else ""
            bot.send_message(call.message.chat.id, f"🇺🇸 S&P 500: {data['value']} ({sign}{data['change']}%)")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка S&P 500.")
        bot.answer_callback_query(call.id)

    # ---------- СЫРЬЁ ----------
    elif call.data == 'gold':
        data = get_gold_price()
        if data:
            bot.send_message(call.message.chat.id, f"🏆 Золото: ${data['usd']} / {data['rub']} ₽ за тройскую унцию")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка цены золота.")
        bot.answer_callback_query(call.id)

    elif call.data == 'oil':
        data = get_oil_price()
        if data:
            bot.send_message(call.message.chat.id, f"🛢 Нефть Brent: ${data['price']} за баррель")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка цены нефти.")
        bot.answer_callback_query(call.id)

    # ---------- КЛЮЧЕВАЯ СТАВКА И НОВОСТИ ----------
    elif call.data == 'keyrate':
        data = get_key_rate()
        if data:
            bot.send_message(call.message.chat.id, f"🔑 Ключевая ставка: {data['rate']}%\n(на {data['date']})")
        else:
            bot.send_message(call.message.chat.id, "❌ Не удалось получить ставку.")
        bot.answer_callback_query(call.id)

    elif call.data == 'news':
        news = get_news()
        if news:
            bot.send_message(call.message.chat.id, "📰 *Свежие новости:*\n\n" + "\n".join(news), parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "❌ Новости временно недоступны.")
        bot.answer_callback_query(call.id)

    # ---------- НАЗАД В ГЛАВНОЕ МЕНЮ ----------
    elif call.data == 'back_to_menu':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💱 Валюты", callback_data='currencies'),
            types.InlineKeyboardButton("₿ Криптовалюты", callback_data='cryptos'),
            types.InlineKeyboardButton("📊 Индексы", callback_data='indices'),
            types.InlineKeyboardButton("🏭 Сырьё", callback_data='commodities'),
            types.InlineKeyboardButton("🔑 Ключевая ставка", callback_data='keyrate'),
            types.InlineKeyboardButton("📰 Новости", callback_data='news')
        )
        bot.edit_message_text(
            "✅ Главное меню:\nВыберите нужный раздел.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

# ---------- ТЕКСТОВЫЕ КОМАНДЫ (прямой ввод) ----------
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

@bot.message_handler(commands=['cny'])
def cmd_cny(message):
    data = get_cny_rate()
    if data:
        bot.reply_to(message, f"🇨🇳 Юань: {data['value']:.2f} ₽")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['btc'])
def cmd_btc(message):
    data = get_crypto('bitcoin')
    if data:
        bot.reply_to(message, f"₿ BTC: ${data['usd']:.0f} / €{data['eur']:.0f}")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['eth'])
def cmd_eth(message):
    data = get_crypto('ethereum')
    if data:
        bot.reply_to(message, f"⟠ ETH: ${data['usd']:.0f} / €{data['eur']:.0f}")
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

@bot.message_handler(commands=['sp500'])
def cmd_sp500(message):
    data = get_sp500()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        bot.reply_to(message, f"🇺🇸 S&P 500: {data['value']} ({sign}{data['change']}%)")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['gold'])
def cmd_gold(message):
    data = get_gold_price()
    if data:
        bot.reply_to(message, f"🏆 Золото: ${data['usd']} / {data['rub']} ₽ за тройскую унцию")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['oil'])
def cmd_oil(message):
    data = get_oil_price()
    if data:
        bot.reply_to(message, f"🛢 Нефть Brent: ${data['price']} за баррель")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['keyrate'])
def cmd_keyrate(message):
    data = get_key_rate()
    if data:
        bot.reply_to(message, f"🔑 Ставка: {data['rate']}% ({data['date']})")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['news'])
def cmd_news(message):
    news = get_news()
    if news:
        bot.reply_to(message, "📰 Новости:\n" + "\n".join(news))
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['stock'])
def cmd_stock(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Укажи тикер: /stock AAPL")
        return
    ticker = args[1].upper()
    data = get_stock_quote(ticker)
    if data:
        sign = "+" if data['change'] >= 0 else ""
        bot.reply_to(message, f"📊 {ticker}: {data['price']} {data['currency']} ({sign}{data['change']}%)")
    else:
        bot.reply_to(message, "❌ Не найден тикер или ошибка API.")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.reply_to(message,
        "Доступные команды:\n"
        "/usd, /eur, /cny, /btc, /eth\n"
        "/moex, /sp500, /gold, /oil, /keyrate, /news\n"
        "/stock [тикер], /help"
    )

# ---------- АВТОМАТИЧЕСКОЕ ДОБАВЛЕНИЕ КНОПКИ К ПОСТАМ ----------
@bot.channel_post_handler(func=lambda message: message.chat.id == CHANNEL_ID)
def add_button_to_post(message):
    if message.reply_markup:
        return
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("📊 Перейти в бот", url=f"https://t.me/{(bot.get_me()).username}")
    markup.add(btn)
    try:
        bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=markup
        )
        print(f"✅ Кнопка добавлена к посту {message.message_id}")
    except Exception as e:
        print(f"❌ Ошибка добавления кнопки: {e}")

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен!")
    bot.infinity_polling()
