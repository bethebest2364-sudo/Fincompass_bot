import logging
import requests
import re
import xml.etree.ElementTree as ET
import json
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import telebot
from telebot import types

BOT_TOKEN = "8803016019:AAGZPApeEG0jqEwua8nK49tL582f3Rftvy8"
CHANNEL_ID = -1001657916970

bot = telebot.TeleBot(BOT_TOKEN)

# ---------- КНОПКА ГЛАВНОГО МЕНЮ ----------
def main_menu_button():
    markup = types.InlineKeyboardMarkup()
    btn = types.InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_menu')
    markup.add(btn)
    return markup

# ---------- ФУНКЦИИ ДЛЯ API ----------
def get_currency_rates():
    """Получает курсы USD, EUR, CNY к рублю через Yahoo Finance"""
    symbols = {'USD': 'USDRUB=X', 'EUR': 'EURRUB=X', 'CNY': 'CNYRUB=X'}
    rates = {}
    for code, ticker in symbols.items():
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            data = resp.json()
            meta = data['chart']['result'][0]['meta']
            price = meta.get('regularMarketPrice')
            if price:
                rates[code] = price
        except:
            rates[code] = None
    if any(rates.values()):
        return rates
    else:
        return None

def get_moex_index():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/IMOEX.ME?range=1d&interval=1d"
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
    ticker = 'GC=F'
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
        resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        data = resp.json()
        meta = data['chart']['result'][0]['meta']
        price_usd = meta.get('regularMarketPrice')
        if price_usd:
            rates = get_currency_rates()
            if rates and 'USD' in rates:
                rub_rate = rates['USD']
                price_rub = price_usd * rub_rate
                return {'usd': round(price_usd, 2), 'rub': round(price_rub, 2)}
        return None
    except:
        return None

def get_oil_price():
    ticker = "CL=F"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
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
    rates = get_currency_rates()
    if rates and 'CNY' in rates:
        return {'value': rates['CNY']}
    return None

def get_sp500():
    ticker = "^GSPC"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
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
            link = item.find('link').text
            news.append({'title': title, 'pub_date': pub_date, 'link': link})
        return news
    except:
        return None

def get_stock_quote(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
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

# ---------- ГРАФИКИ ----------
def get_historical_data(asset_type, symbol, days=7):
    if asset_type == 'currency':
        if symbol == 'CNY':
            # Для CNY используем кросс-курс через Yahoo Finance
            # Получаем историю USD/RUB
            ticker_usd_rub = 'USDRUB=X'
            url_usd_rub = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_usd_rub}?range={days}d&interval=1d"
            resp_usd_rub = requests.get(url_usd_rub, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            data_usd_rub = resp_usd_rub.json()
            if 'chart' not in data_usd_rub or 'result' not in data_usd_rub['chart'] or not data_usd_rub['chart']['result']:
                return None
            timestamps_usd_rub = data_usd_rub['chart']['result'][0]['timestamp']
            close_usd_rub = data_usd_rub['chart']['result'][0]['indicators']['quote'][0]['close']
            dates_usd_rub = [datetime.fromtimestamp(t).strftime('%Y-%m-%d') for t in timestamps_usd_rub]
            valid_usd_rub = [(d, c) for d, c in zip(dates_usd_rub, close_usd_rub) if c is not None]
            if not valid_usd_rub:
                return None

            # Получаем историю USD/CNY
            ticker_usd_cny = 'USDCNY=X'
            url_usd_cny = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_usd_cny}?range={days}d&interval=1d"
            resp_usd_cny = requests.get(url_usd_cny, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            data_usd_cny = resp_usd_cny.json()
            if 'chart' not in data_usd_cny or 'result' not in data_usd_cny['chart'] or not data_usd_cny['chart']['result']:
                return None
            timestamps_usd_cny = data_usd_cny['chart']['result'][0]['timestamp']
            close_usd_cny = data_usd_cny['chart']['result'][0]['indicators']['quote'][0]['close']
            dates_usd_cny = [datetime.fromtimestamp(t).strftime('%Y-%m-%d') for t in timestamps_usd_cny]
            valid_usd_cny = [(d, c) for d, c in zip(dates_usd_cny, close_usd_cny) if c is not None]
            if not valid_usd_cny:
                return None

            # Объединяем по датам и вычисляем CNY/RUB
            dates_common = sorted(set([d for d, _ in valid_usd_rub]) & set([d for d, _ in valid_usd_cny]))
            if not dates_common:
                return None
            dict_usd_rub = {d: c for d, c in valid_usd_rub}
            dict_usd_cny = {d: c for d, c in valid_usd_cny}
            values = []
            for d in dates_common:
                usd_rub = dict_usd_rub[d]
                usd_cny = dict_usd_cny[d]
                if usd_cny != 0:
                    values.append(usd_rub / usd_cny)
                else:
                    values.append(None)
            valid_values = [(d, v) for d, v in zip(dates_common, values) if v is not None]
            if not valid_values:
                return None
            return {'dates': [d for d, _ in valid_values], 'values': [v for _, v in valid_values]}
        else:
            # Для USD и EUR используем Yahoo Finance
            symbol_map = {'USD': 'USDRUB=X', 'EUR': 'EURRUB=X'}
            if symbol not in symbol_map:
                return None
            ticker = symbol_map[symbol]
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={days}d&interval=1d"
            try:
                resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                data = resp.json()
                if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
                    return None
                timestamps = data['chart']['result'][0]['timestamp']
                close = data['chart']['result'][0]['indicators']['quote'][0]['close']
                dates = [datetime.fromtimestamp(t).strftime('%Y-%m-%d') for t in timestamps]
                valid = [(d, c) for d, c in zip(dates, close) if c is not None]
                if valid:
                    return {'dates': [v[0] for v in valid], 'values': [v[1] for v in valid]}
                return None
            except:
                return None
    elif asset_type == 'crypto':
        symbol_map = {'BTC': 'BTCUSDT', 'ETH': 'ETHUSDT'}
        if symbol not in symbol_map:
            return None
        sym = symbol_map[symbol]
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&limit={days}"
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            dates = [datetime.fromtimestamp(c[0]/1000).strftime('%Y-%m-%d') for c in data]
            values = [float(c[4]) for c in data]
            if dates and values:
                return {'dates': dates, 'values': values}
            return None
        except:
            return None
    elif asset_type == 'index':
        if symbol == 'MOEX':
            ticker = 'IMOEX.ME'
        elif symbol == 'SP500':
            ticker = '^GSPC'
        else:
            return None
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={days}d&interval=1d"
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            data = resp.json()
            if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
                return None
            timestamps = data['chart']['result'][0]['timestamp']
            close = data['chart']['result'][0]['indicators']['quote'][0]['close']
            dates = [datetime.fromtimestamp(t).strftime('%Y-%m-%d') for t in timestamps]
            valid = [(d, c) for d, c in zip(dates, close) if c is not None]
            if valid:
                return {'dates': [v[0] for v in valid], 'values': [v[1] for v in valid]}
            return None
        except:
            return None
    elif asset_type == 'commodity':
        symbol_map = {'GOLD': 'GC=F', 'OIL': 'CL=F'}
        if symbol not in symbol_map:
            return None
        sym = symbol_map[symbol]
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={days}d&interval=1d"
        try:
            resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            data = resp.json()
            if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
                return None
            timestamps = data['chart']['result'][0]['timestamp']
            close = data['chart']['result'][0]['indicators']['quote'][0]['close']
            dates = [datetime.fromtimestamp(t).strftime('%Y-%m-%d') for t in timestamps]
            valid = [(d, c) for d, c in zip(dates, close) if c is not None]
            if valid:
                return {'dates': [v[0] for v in valid], 'values': [v[1] for v in valid]}
            return None
        except:
            return None
    return None

def generate_chart(data, title, ylabel='Цена', color='blue'):
    if not data or not data['values']:
        return None
    points = min(7, len(data['values']))
    dates = data['dates'][-points:]
    values = data['values'][-points:]
    chart_config = {
        "type": "line",
        "data": {
            "labels": dates,
            "datasets": [{
                "label": title,
                "data": values,
                "borderColor": color,
                "fill": False,
                "borderWidth": 2
            }]
        },
        "options": {
            "title": {"display": True, "text": title},
            "legend": {"display": False},
            "scales": {
                "yAxes": [{"scaleLabel": {"display": True, "labelString": ylabel}}],
                "xAxes": [{"ticks": {"maxRotation": 45, "fontSize": 10}}]
            }
        }
    }
    import urllib.parse
    chart_json = urllib.parse.quote(json.dumps(chart_config))
    url = f"https://quickchart.io/chart?c={chart_json}"
    return url

# ---------- ОПОВЕЩЕНИЯ ----------
LAST_VALUES_FILE = 'last_values.json'

def load_last_values():
    if os.path.exists(LAST_VALUES_FILE):
        with open(LAST_VALUES_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_last_values(values):
    with open(LAST_VALUES_FILE, 'w') as f:
        json.dump(values, f)

def check_alerts():
    logging.info("Запуск проверки оповещений...")
    last = load_last_values()
    new_data = {}
    alerts = []

    rates = get_currency_rates()
    if rates:
        for cur in ['USD', 'EUR', 'CNY']:
            if cur in rates and rates[cur]:
                val = rates[cur]
                new_data[cur] = val
                if cur in last and last[cur] != 0:
                    change = abs(val - last[cur]) / last[cur] * 100
                    if change > 2.0:
                        alerts.append(f"💱 {cur}: изменился на {change:.1f}% (было {last[cur]:.2f}, стало {val:.2f})")

    for coin, name in [('bitcoin', 'BTC'), ('ethereum', 'ETH')]:
        data = get_crypto(coin)
        if data:
            val = data['usd']
            new_data[name] = val
            if name in last and last[name] != 0:
                change = abs(val - last[name]) / last[name] * 100
                if change > 5.0:
                    alerts.append(f"₿ {name}: изменился на {change:.1f}% (было ${last[name]:.0f}, стало ${val:.0f})")

    moex = get_moex_index()
    if moex:
        val = moex['value']
        new_data['MOEX'] = val
        if 'MOEX' in last and last['MOEX'] != 0:
            change = abs(val - last['MOEX']) / last['MOEX'] * 100
            if change > 3.0:
                alerts.append(f"📈 MOEX: изменился на {change:.1f}% (было {last['MOEX']:.2f}, стало {val:.2f})")

    sp500 = get_sp500()
    if sp500:
        val = sp500['value']
        new_data['SP500'] = val
        if 'SP500' in last and last['SP500'] != 0:
            change = abs(val - last['SP500']) / last['SP500'] * 100
            if change > 3.0:
                alerts.append(f"🇺🇸 S&P 500: изменился на {change:.1f}% (было {last['SP500']:.2f}, стало {val:.2f})")

    gold = get_gold_price()
    if gold:
        val = gold['usd']
        new_data['GOLD'] = val
        if 'GOLD' in last and last['GOLD'] != 0:
            change = abs(val - last['GOLD']) / last['GOLD'] * 100
            if change > 3.0:
                alerts.append(f"🏆 Золото: изменилось на {change:.1f}% (было ${last['GOLD']:.2f}, стало ${val:.2f})")

    oil = get_oil_price()
    if oil:
        val = oil['price']
        new_data['OIL'] = val
        if 'OIL' in last and last['OIL'] != 0:
            change = abs(val - last['OIL']) / last['OIL'] * 100
            if change > 3.0:
                alerts.append(f"🛢 Нефть: изменилась на {change:.1f}% (было ${last['OIL']:.2f}, стало ${val:.2f})")

    save_last_values(new_data)

    if alerts:
        text = "⚠️ *Внимание, сильные изменения!*\n\n" + "\n".join(alerts)
        bot.send_message(CHANNEL_ID, text, parse_mode='Markdown')
        logging.info("Оповещения отправлены.")
    else:
        logging.info("Сильных изменений не обнаружено.")

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
            "📊 *Финансовый Компас* — ваш ежедневный гид по рынкам.\n\n"
            "Мы собираем для вас главные цифры и события: курсы валют, индексы, сырьё, ключевую ставку, новости. Без воды и прогнозов — только факты и контекст.\n\n"
            "🚀 *Что вы можете сделать прямо сейчас:*\n"
            "• Узнать курс доллара, евро, юаня\n"
            "• Проверить индекс МосБиржи и S&P 500\n"
            "• Посмотреть цену золота, нефти, биткоина\n"
            "• Получить свежие новости\n"
            "• Построить график за 7 дней\n\n"
            "Выберите нужный раздел ниже или введите команду.\n\n"
            "🔹 Команды: /usd, /moex, /gold, /oil, /news, /stock AAPL и другие.\n"
            "🔹 Полный список — /help.\n\n"
            "Начните прямо сейчас 👇",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Подписаться", url="https://t.me/FinKompass"))
        markup.add(types.InlineKeyboardButton("🔄 Проверить", callback_data='check_sub'))
        bot.send_message(message.chat.id, "❌ Подпишись на канал, чтобы пользоваться ботом!", reply_markup=markup)

@bot.message_handler(commands=['help'])
def cmd_help(message):
    bot.reply_to(message,
        "Доступные команды:\n"
        "/usd, /eur, /cny, /btc, /eth\n"
        "/moex, /sp500, /gold, /oil, /keyrate, /news\n"
        "/stock [тикер], /help\n\n"
        "Используйте кнопки в меню для быстрого доступа.",
        reply_markup=main_menu_button()
    )

@bot.message_handler(commands=['usd'])
def cmd_usd(message):
    rates = get_currency_rates()
    if rates and 'USD' in rates and rates['USD']:
        bot.reply_to(message, f"💵 Доллар: {rates['USD']:.2f} ₽", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['eur'])
def cmd_eur(message):
    rates = get_currency_rates()
    if rates and 'EUR' in rates and rates['EUR']:
        bot.reply_to(message, f"💶 Евро: {rates['EUR']:.2f} ₽", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['cny'])
def cmd_cny(message):
    data = get_cny_rate()
    if data and data['value']:
        bot.reply_to(message, f"🇨🇳 Юань: {data['value']:.2f} ₽", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['btc'])
def cmd_btc(message):
    data = get_crypto('bitcoin')
    if data:
        bot.reply_to(message, f"₿ BTC: ${data['usd']:.0f} / €{data['eur']:.0f}", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['eth'])
def cmd_eth(message):
    data = get_crypto('ethereum')
    if data:
        bot.reply_to(message, f"⟠ ETH: ${data['usd']:.0f} / €{data['eur']:.0f}", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['moex'])
def cmd_moex(message):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        bot.reply_to(message, f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['sp500'])
def cmd_sp500(message):
    data = get_sp500()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        bot.reply_to(message, f"🇺🇸 S&P 500: {data['value']} ({sign}{data['change']}%)", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['gold'])
def cmd_gold(message):
    data = get_gold_price()
    if data:
        bot.reply_to(message, f"🏆 Золото: ${data['usd']} / {data['rub']} ₽ за тройскую унцию", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['oil'])
def cmd_oil(message):
    data = get_oil_price()
    if data:
        bot.reply_to(message, f"🛢 Нефть Brent: ${data['price']} за баррель", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['keyrate'])
def cmd_keyrate(message):
    data = get_key_rate()
    if data:
        bot.reply_to(message, f"🔑 Ставка: {data['rate']}% ({data['date']})", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['news'])
def cmd_news(message):
    news = get_news()
    if news:
        text = "📰 Новости:\n"
        for item in news:
            text += f"• {item['title']} ({item['pub_date']})\n🔗 {item['link']}\n\n"
        bot.reply_to(message, text, reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Ошибка", reply_markup=main_menu_button())

@bot.message_handler(commands=['stock'])
def cmd_stock(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Укажи тикер: /stock AAPL", reply_markup=main_menu_button())
        return
    ticker = args[1].upper()
    data = get_stock_quote(ticker)
    if data:
        sign = "+" if data['change'] >= 0 else ""
        bot.reply_to(message, f"📊 {ticker}: {data['price']} {data['currency']} ({sign}{data['change']}%)", reply_markup=main_menu_button())
    else:
        bot.reply_to(message, "❌ Не найден тикер или ошибка API.", reply_markup=main_menu_button())

# ---------- FALLBACK ДЛЯ ТЕКСТОВЫХ СООБЩЕНИЙ ----------
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "Используйте кнопки в меню или команды из /help. Для начала нажмите /start.")

# ---------- ЕДИНЫЙ ОБРАБОТЧИК CALLBACK ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # Проверка подписки
    if call.data == 'check_sub':
        if is_subscribed(call.from_user.id):
            bot.edit_message_text("✅ Подписка подтверждена! Нажми /start.", call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Ты ещё не подписан!", show_alert=True)
        return

    # ---------- ОСНОВНЫЕ РАЗДЕЛЫ ----------
    if call.data == 'currencies':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("💵 Доллар (USD)", callback_data='currency_usd'),
            types.InlineKeyboardButton("💶 Евро (EUR)", callback_data='currency_eur'),
            types.InlineKeyboardButton("🇨🇳 Юань (CNY)", callback_data='currency_cny'),
            types.InlineKeyboardButton("📈 График USD", callback_data='chart_currency_USD'),
            types.InlineKeyboardButton("📈 График EUR", callback_data='chart_currency_EUR'),
            types.InlineKeyboardButton("📈 График CNY", callback_data='chart_currency_CNY'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите валюту или график:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if call.data == 'cryptos':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("₿ Bitcoin (BTC)", callback_data='crypto_btc'),
            types.InlineKeyboardButton("⟠ Ethereum (ETH)", callback_data='crypto_eth'),
            types.InlineKeyboardButton("📈 График BTC", callback_data='chart_crypto_BTC'),
            types.InlineKeyboardButton("📈 График ETH", callback_data='chart_crypto_ETH'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите криптовалюту или график:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if call.data == 'indices':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📈 MOEX", callback_data='moex'),
            types.InlineKeyboardButton("🇺🇸 S&P 500", callback_data='sp500'),
            types.InlineKeyboardButton("📈 График MOEX", callback_data='chart_index_MOEX'),
            types.InlineKeyboardButton("📈 График S&P 500", callback_data='chart_index_SP500'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите индекс или график:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if call.data == 'commodities':
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🏆 Золото", callback_data='gold'),
            types.InlineKeyboardButton("🛢 Нефть", callback_data='oil'),
            types.InlineKeyboardButton("📈 График золота", callback_data='chart_commodity_GOLD'),
            types.InlineKeyboardButton("📈 График нефти", callback_data='chart_commodity_OIL'),
            types.InlineKeyboardButton("◀️ Назад", callback_data='back_to_menu')
        )
        bot.edit_message_text("Выберите товар или график:", call.message.chat.id, call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    # ---------- ОТДЕЛЬНЫЕ КОМАНДЫ ----------
    if call.data == 'currency_usd':
        rates = get_currency_rates()
        if rates and 'USD' in rates and rates['USD']:
            bot.send_message(call.message.chat.id, f"💵 Доллар: {rates['USD']:.2f} ₽", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'currency_eur':
        rates = get_currency_rates()
        if rates and 'EUR' in rates and rates['EUR']:
            bot.send_message(call.message.chat.id, f"💶 Евро: {rates['EUR']:.2f} ₽", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'currency_cny':
        data = get_cny_rate()
        if data and data['value']:
            bot.send_message(call.message.chat.id, f"🇨🇳 Юань: {data['value']:.2f} ₽", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'crypto_btc':
        data = get_crypto('bitcoin')
        if data:
            bot.send_message(call.message.chat.id, f"₿ BTC: ${data['usd']:.0f} / €{data['eur']:.0f}", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса BTC.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'crypto_eth':
        data = get_crypto('ethereum')
        if data:
            bot.send_message(call.message.chat.id, f"⟠ ETH: ${data['usd']:.0f} / €{data['eur']:.0f}", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка курса ETH.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    # ---------- ГРАФИКИ ----------
    if call.data.startswith('chart_'):
        parts = call.data.split('_')
        if len(parts) < 3:
            bot.send_message(call.message.chat.id, "❌ Ошибка параметров графика.", reply_markup=main_menu_button())
            bot.answer_callback_query(call.id)
            return
        chart_type = parts[1]
        symbol = parts[2]
        asset_map = {
            'currency': ('currency', 'Курс', '₽'),
            'crypto': ('crypto', 'Цена', '$'),
            'index': ('index', 'Значение', ''),
            'commodity': ('commodity', 'Цена', '$')
        }
        if chart_type not in asset_map:
            bot.send_message(call.message.chat.id, "❌ Неизвестный тип.", reply_markup=main_menu_button())
            bot.answer_callback_query(call.id)
            return
        atype, label, unit = asset_map[chart_type]
        data = get_historical_data(atype, symbol, days=7)
        if not data:
            bot.send_message(call.message.chat.id, f"❌ Не удалось получить исторические данные для {symbol}.", reply_markup=main_menu_button())
            bot.answer_callback_query(call.id)
            return
        title = f"{label} {symbol} за 7 дней"
        chart_url = generate_chart(data, title, unit, color='green' if chart_type=='currency' else 'blue')
        if chart_url:
            bot.send_photo(call.message.chat.id, chart_url, caption=f"📊 {title}")
            bot.send_message(call.message.chat.id, "📌 Для возврата в меню нажмите кнопку ниже:", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка генерации графика.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'moex':
        data = get_moex_index()
        if data:
            sign = "+" if data['change'] >= 0 else ""
            bot.send_message(call.message.chat.id, f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка индекса.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'sp500':
        data = get_sp500()
        if data:
            sign = "+" if data['change'] >= 0 else ""
            bot.send_message(call.message.chat.id, f"🇺🇸 S&P 500: {data['value']} ({sign}{data['change']}%)", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка S&P 500.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'gold':
        data = get_gold_price()
        if data:
            bot.send_message(call.message.chat.id, f"🏆 Золото: ${data['usd']} / {data['rub']} ₽ за тройскую унцию", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка цены золота.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'oil':
        data = get_oil_price()
        if data:
            bot.send_message(call.message.chat.id, f"🛢 Нефть Brent: ${data['price']} за баррель", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Ошибка цены нефти.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'news':
        news = get_news()
        if not news:
            bot.send_message(call.message.chat.id, "❌ Новости временно недоступны.", reply_markup=main_menu_button())
            bot.answer_callback_query(call.id)
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, item in enumerate(news):
            btn = types.InlineKeyboardButton(
                f"📖 Подробнее: {item['title'][:30]}...",
                callback_data=f'news_detail_{i}'
            )
            markup.add(btn)
        markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data='back_to_menu'))
        text = "📰 *Свежие новости:*\n\n"
        for i, item in enumerate(news):
            text += f"{i+1}. {item['title']} ({item['pub_date']})\n"
        bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=markup)
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith('news_detail_'):
        idx = int(call.data.split('_')[-1])
        news = get_news()
        if news and idx < len(news):
            item = news[idx]
            text = f"📰 *{item['title']}*\n\n🔗 [Читать полностью]({item['link']})\n📅 {item['pub_date']}"
            bot.send_message(call.message.chat.id, text, parse_mode='Markdown', reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Новость не найдена.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'keyrate':
        data = get_key_rate()
        if data:
            bot.send_message(call.message.chat.id, f"🔑 Ключевая ставка: {data['rate']}%\n(на {data['date']})", reply_markup=main_menu_button())
        else:
            bot.send_message(call.message.chat.id, "❌ Не удалось получить ставку.", reply_markup=main_menu_button())
        bot.answer_callback_query(call.id)
        return

    if call.data == 'back_to_menu':
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
        return

    # Если ничего не подошло
    bot.answer_callback_query(call.id, "Неизвестная команда.")

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_alerts, 'interval', minutes=30)
    scheduler.start()
    print("Планировщик оповещений запущен.")
    print("Бот запущен!")
    bot.infinity_polling()
