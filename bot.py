import logging
import asyncio
import requests
import yfinance as yf
from datetime import datetime
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ===== НАСТРОЙКИ (УЖЕ ЗАПОЛНЕНЫ) =====
BOT_TOKEN = "8803016019:AAFO-bV1y8NaIMmEe1VAdD3pQmBLe3hY1Nk"
CHANNEL_ID = "@FinKompass"
# =======================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С API ---

def get_cbr_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'windows-1251'
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        rates = {}
        for valute in root.findall('Valute'):
            char_code = valute.find('CharCode').text
            value = valute.find('Value').text.replace(',', '.')
            nominal = valute.find('Nominal').text
            name = valute.find('Name').text
            rates[char_code] = {
                'value': float(value),
                'nominal': int(nominal),
                'name': name
            }
        return rates
    except:
        return None

def get_key_rate():
    url = "https://www.cbr.ru/hd_base/KeyRate/"
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        table = soup.find('table', class_='data')
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                last_row = rows[1].find_all('td')
                if len(last_row) >= 2:
                    date = last_row[0].text.strip()
                    rate = last_row[1].text.strip()
                    return {'rate': rate, 'date': date}
        return None
    except:
        return None

def get_inflation():
    url = "https://rosstat.gov.ru/storage/mediabank/Inflation_month_2025.xml"
    try:
        response = requests.get(url, timeout=10)
        root = BeautifulSoup(response.text, 'xml')
        months = root.find_all('month')
        if months:
            last = months[-1]
            return {
                'month': last.find('name').text,
                'value': last.find('infl').text + '%'
            }
        return None
    except:
        return None

def get_moex_index():
    url = "https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        row = data['marketdata']['data'][0]
        return {
            'value': row[2],
            'change': row[5],
            'time': row[1]
        }
    except:
        return None

def get_stock_quote(ticker):
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1d")
        if data.empty:
            return None
        last = data['Close'].iloc[-1]
        prev = data['Close'].iloc[0] if len(data) > 1 else last
        change = ((last - prev) / prev) * 100
        return {
            'price': round(last, 2),
            'change': round(change, 2),
            'currency': 'USD' if '.' not in ticker else 'RUB'
        }
    except:
        return None

def get_crypto(coin='bitcoin'):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur,rub"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if coin in data:
            return data[coin]
        return None
    except:
        return None

def get_news():
    url = "https://www.finam.ru/analysis/export/rss/analytical/"
    try:
        response = requests.get(url, timeout=10)
        root = BeautifulSoup(response.text, 'xml')
        items = root.find_all('item')[:5]
        news = []
        for item in items:
            title = item.find('title').text
            pub_date = item.find('pubDate').text[:16]
            news.append(f"• {title} ({pub_date})")
        return news
    except:
        return None

# --- ПРОВЕРКА ПОДПИСКИ ---
async def is_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except:
        return False

# --- КОМАНДЫ ---

@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    if await is_subscribed(user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("💵 Курсы валют", callback_data="rates"),
             InlineKeyboardButton("📈 Индекс MOEX", callback_data="moex")],
            [InlineKeyboardButton("₿ Криптовалюты", callback_data="crypto"),
             InlineKeyboardButton("📰 Новости", callback_data="news")],
            [InlineKeyboardButton("🔑 Ключевая ставка", callback_data="keyrate"),
             InlineKeyboardButton("📊 Инфляция", callback_data="inflation")]
        ])
        await message.answer(
            "✅ Добро пожаловать в Финансовый Компас!\n"
            "Выбери нужный раздел или введи команду:\n"
            "/usd, /eur, /moex, /crypto, /keyrate, /inflation, /news, /stock AAPL",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/FinKompass")],
            [InlineKeyboardButton("🔄 Проверить", callback_data="check_sub")]
        ])
        await message.answer("❌ Подпишись на канал!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.edit_text("✅ Подписка подтверждена! Нажми /start для меню.")
    else:
        await callback.answer("❌ Ты ещё не подписан!", show_alert=True)

# Обработчики кнопок
@dp.callback_query(lambda c: c.data == "rates")
async def show_rates(callback: types.CallbackQuery):
    rates = get_cbr_rates()
    if rates and 'USD' in rates and 'EUR' in rates:
        text = f"💵 Доллар: {rates['USD']['value']:.2f} ₽\n"
        text += f"💶 Евро: {rates['EUR']['value']:.2f} ₽"
        await callback.message.answer(text)
    else:
        await callback.message.answer("❌ Не удалось получить курсы.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "moex")
async def show_moex(callback: types.CallbackQuery):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        await callback.message.answer(
            f"📈 Индекс МосБиржи: {data['value']:.2f}\n"
            f"Изменение: {sign}{data['change']:.2f}%"
        )
    else:
        await callback.message.answer("❌ Не удалось получить индекс.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "crypto")
async def show_crypto(callback: types.CallbackQuery):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        text = f"₿ Bitcoin: ${btc['usd']:.0f} / €{btc['eur']:.0f}\n"
        text += f"⟠ Ethereum: ${eth['usd']:.0f} / €{eth['eur']:.0f}"
        await callback.message.answer(text)
    else:
        await callback.message.answer("❌ Не удалось получить курс криптовалют.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "news")
async def show_news(callback: types.CallbackQuery):
    news = get_news()
    if news:
        text = "📰 *Свежие новости:*\n\n" + "\n".join(news)
        await callback.message.answer(text, parse_mode="Markdown")
    else:
        await callback.message.answer("❌ Новости временно недоступны.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "keyrate")
async def show_keyrate(callback: types.CallbackQuery):
    data = get_key_rate()
    if data:
        await callback.message.answer(f"🔑 Ключевая ставка: {data['rate']}%\n(на {data['date']})")
    else:
        await callback.message.answer("❌ Не удалось получить ставку.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "inflation")
async def show_inflation(callback: types.CallbackQuery):
    data = get_inflation()
    if data:
        await callback.message.answer(f"📊 Инфляция за {data['month']}: {data['value']}")
    else:
        await callback.message.answer("❌ Данные по инфляции недоступны.")
    await callback.answer()

# Текстовые команды
@dp.message(Command("usd"))
async def cmd_usd(message: types.Message):
    rates = get_cbr_rates()
    if rates and 'USD' in rates:
        await message.answer(f"💵 Доллар: {rates['USD']['value']:.2f} ₽")
    else:
        await message.answer("❌ Ошибка получения курса.")

@dp.message(Command("eur"))
async def cmd_eur(message: types.Message):
    rates = get_cbr_rates()
    if rates and 'EUR' in rates:
        await message.answer(f"💶 Евро: {rates['EUR']['value']:.2f} ₽")
    else:
        await message.answer("❌ Ошибка получения курса.")

@dp.message(Command("moex"))
async def cmd_moex(message: types.Message):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        await message.answer(f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
    else:
        await message.answer("❌ Ошибка.")

@dp.message(Command("crypto"))
async def cmd_crypto(message: types.Message):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        await message.answer(f"₿ BTC: ${btc['usd']:.0f}  ⟠ ETH: ${eth['usd']:.0f}")
    else:
        await message.answer("❌ Ошибка.")

@dp.message(Command("keyrate"))
async def cmd_keyrate(message: types.Message):
    data = get_key_rate()
    if data:
        await message.answer(f"🔑 Ставка: {data['rate']}% ({data['date']})")
    else:
        await message.answer("❌ Ошибка.")

@dp.message(Command("inflation"))
async def cmd_inflation(message: types.Message):
    data = get_inflation()
    if data:
        await message.answer(f"📊 Инфляция: {data['value']} ({data['month']})")
    else:
        await message.answer("❌ Ошибка.")

@dp.message(Command("news"))
async def cmd_news(message: types.Message):
    news = get_news()
    if news:
        await message.answer("📰 Новости:\n" + "\n".join(news))
    else:
        await message.answer("❌ Ошибка.")

@dp.message(Command("stock"))
async def cmd_stock(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажи тикер: /stock AAPL")
        return
    ticker = args[1].upper()
    data = get_stock_quote(ticker)
    if data:
        sign = "+" if data['change'] >= 0 else ""
        await message.answer(f"📊 {ticker}: {data['price']} {data['currency']} ({sign}{data['change']}%)")
    else:
        await message.answer("❌ Не найден тикер.")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "Доступные команды:\n"
        "/usd, /eur, /moex, /crypto, /keyrate, /inflation, /news, /stock [тикер], /help"
    )

# --- ЗАПУСК ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Бот Финансовый Компас запущен!")
    dp.run_polling(bot)
