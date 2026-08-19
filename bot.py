import logging
import requests
import re
import xml.etree.ElementTree as ET
import telebot
from telebot import types

BOT_TOKEN = "8803016019:AAFO-bV1y8NaIMmEe1VAdD3pQmBLe3hY1Nk"
CHANNEL_ID = "@FinKompass"

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- ФУНКЦИИ ДЛЯ API ----------

# 1. Курсы валют (ЦБ РФ)
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

# 2. Индекс МосБиржи (MOEX)
def get_moex_index():
    url = "https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        row = data['marketdata']['data'][0]
        return {'value': row[2], 'change': row[5]}
    except:
        return None

# 3. Криптовалюты (CoinGecko)
def get_crypto(coin):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get(coin, None)
    except:
        return None

# 4. Ключевая ставка ЦБ (через официальный XML-файл)
def get_key_rate():
    url = "https://www.cbr.ru/scripts/XML_KeyRate.asp"
    try:
        resp = requests.get(url, timeout=10)
        root = ET.fromstring(resp.text)
        record = root.find('Record')
        if record is not None:
            date = record.get('Date')
            rate = record.text
            return {'date': date, 'rate': rate}
        return None
    except:
        # Запасной вариант — парсинг HTML
        try:
            url2 = "https://www.cbr.ru/hd_base/KeyRate/"
            resp2 = requests.get(url2, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            match = re.search(r'<td class="[^"]*">(\d{2}\.\d{2}\.\d{4})</td>\s*<td[^>]*>([\d,]+)</td>', resp2.text, re.DOTALL)
            if match:
                date = match.group(1)
                rate = match.group(2).replace(',', '.')
                return {'date': date, 'rate': rate}
            return None
        except:
            return None

# 5. Инфляция (через Statbureau API)
def get_inflation():
    url = "https://www.statbureau.org/ru/russia/inflation-api"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data and len(data) > 0:
            last = data[-1]
            return {'month': last['month'], 'value': str(last['inflation']) + '%'}
        return None
    except:
        return None

# 6. Финансовые новости (Banki.ru RSS)
def get_news():
    url = "https://www.banki.ru/xml/news.rss"
    try:
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        root = ET.fromstring(resp.content)
        items = root.findall('.//item')[:5]
        news = []
        for item in items:
            title = item.find('title').text
            pub_date = item.find('pubDate').text[:16]
            news.append(f"• {title} ({pub_date})")
        return news
    except:
        # Второй запасной вариант — Finam
        try:
            url2 = "https://www.finam.ru/analysis/export/rss/analytical/"
            resp2 = requests.get(url2, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            root2 = ET.fromstring(resp2.content)
            items2 = root2.findall('.//item')[:5]
            news2 = []
            for item in items2:
                title = item.find('title').text
                pub_date = item.find('pubDate').text[:16]
                news2.append(f"• {title} ({pub_date})")
            return news2
        except:
            return None

# 7. Акции (Yahoo Finance API без библиотеки yfinance)
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
            types.InlineKeyboardButton("💵 Курсы валют", callback_data='rates'),
            types.InlineKeyboardButton("📈 Индекс MOEX", callback_data='moex'),
            types.InlineKeyboardButton("₿ Криптовалюты", callback_data='crypto'),
            types.InlineKeyboardButton("🔑 Ключевая ставка", callback_data='keyrate'),
            types.InlineKeyboardButton("📊 Инфляция", callback_data='inflation'),
            types.InlineKeyboardButton("📰 Новости", callback_data='news')
        )
        bot.send_message(
            message.chat.id,
            "✅ Добро пожаловать в Финансовый Компас!\n"
            "Доступные команды:\n"
            "/usd, /eur, /moex, /crypto, /keyrate, /inflation, /news, /stock AAPL, /help",
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
    elif call.data == 'rates':
        rates = get_cbr_rates()
        if rates and 'USD' in rates and 'EUR' in rates:
            bot.send_message(call.message.chat.id, f"💵 Доллар: {rates['USD']:.2f} ₽\n💶 Евро: {rates['EUR']:.2f} ₽")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курсов.")
        bot.answer_callback_query(call.id)
    elif call.data == 'moex':
        data = get_moex_index()
        if data:
            sign = "+" if data['change'] >= 0 else ""
            bot.send_message(call.message.chat.id, f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка индекса.")
        bot.answer_callback_query(call.id)
    elif call.data == 'crypto':
        btc = get_crypto('bitcoin')
        eth = get_crypto('ethereum')
        if btc and eth:
            bot.send_message(call.message.chat.id, f"₿ BTC: ${btc['usd']:.0f} / €{btc['eur']:.0f}\n⟠ ETH: ${eth['usd']:.0f} / €{eth['eur']:.0f}")
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка крипты.")
        bot.answer_callback_query(call.id)
    elif call.data == 'keyrate':
        data = get_key_rate()
        if data:
            bot.send_message(call.message.chat.id, f"🔑 Ключевая ставка: {data['rate']}%\n(на {data['date']})")
        else:
            bot.send_message(call.message.chat.id, "❌ Не удалось получить ставку.")
        bot.answer_callback_query(call.id)
    elif call.data == 'inflation':
        data = get_inflation()
        if data:
            bot.send_message(call.message.chat.id, f"📊 Инфляция за {data['month']}: {data['value']}")
        else:
            bot.send_message(call.message.chat.id, "❌ Данные по инфляции недоступны.")
        bot.answer_callback_query(call.id)
    elif call.data == 'news':
        news = get_news()
        if news:
            bot.send_message(call.message.chat.id, "📰 *Свежие новости:*\n\n" + "\n".join(news), parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "❌ Новости временно недоступны.")
        bot.answer_callback_query(call.id)

# ---------- ТЕКСТОВЫЕ КОМАНДЫ ----------
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

@bot.message_handler(commands=['keyrate'])
def cmd_keyrate(message):
    data = get_key_rate()
    if data:
        bot.reply_to(message, f"🔑 Ставка: {data['rate']}% ({data['date']})")
    else:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['inflation'])
def cmd_inflation(message):
    data = get_inflation()
    if data:
        bot.reply_to(message, f"📊 Инфляция: {data['value']} ({data['month']})")
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
        "/usd, /eur, /moex, /crypto\n"
        "/keyrate, /inflation, /news\n"
        "/stock [тикер], /help"
    )

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен!")
    bot.infinity_polling()
