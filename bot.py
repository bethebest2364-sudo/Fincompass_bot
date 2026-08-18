import logging
import requests
import xml.etree.ElementTree as ET
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "8803016019:AAFO-bV1y8NaIMmEe1VAdD3pQmBLe3hY1Nk"
CHANNEL_ID = "@FinKompass"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- КУРСЫ ВАЛЮТ (ЦБ РФ) ---
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
            nominal = valute.find('Nominal').text
            rates[code] = {'value': float(value), 'nominal': int(nominal)}
        return rates
    except:
        return None

# --- ИНДЕКС МОСБИРЖИ (MOEX ISS) ---
def get_moex_index():
    url = "https://iss.moex.com/iss/engines/stock/markets/index/boards/SNDX/securities/IMOEX.json"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        row = data['marketdata']['data'][0]
        return {'value': row[2], 'change': row[5]}
    except:
        return None

# --- КРИПТОВАЛЮТЫ (CoinGecko) ---
def get_crypto(coin):
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd,eur"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return data.get(coin, None)
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
            [InlineKeyboardButton("₿ Криптовалюты", callback_data="crypto")]
        ])
        await message.answer(
            "✅ Добро пожаловать!\n"
            "Команды: /usd, /eur, /moex, /crypto\n"
            "Или нажми кнопку.",
            reply_markup=keyboard
        )
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton("📢 Подписаться", url="https://t.me/FinKompass")],
            [InlineKeyboardButton("🔄 Проверить", callback_data="check_sub")]
        ])
        await message.answer("❌ Подпишись на канал!", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_sub(callback: types.CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.edit_text("✅ Подписка подтверждена! Нажми /start.")
    else:
        await callback.answer("❌ Ты ещё не подписан!", show_alert=True)

@dp.callback_query(lambda c: c.data == "rates")
async def show_rates(callback: types.CallbackQuery):
    rates = get_cbr_rates()
    if rates and 'USD' in rates and 'EUR' in rates:
        text = f"💵 Доллар: {rates['USD']['value']:.2f} ₽\n"
        text += f"💶 Евро: {rates['EUR']['value']:.2f} ₽"
        await callback.message.answer(text)
    else:
        await callback.message.answer("❌ Ошибка курсов.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "moex")
async def show_moex(callback: types.CallbackQuery):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        await callback.message.answer(f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
    else:
        await callback.message.answer("❌ Ошибка индекса.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "crypto")
async def show_crypto(callback: types.CallbackQuery):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        text = f"₿ BTC: ${btc['usd']:.0f} / €{btc['eur']:.0f}\n"
        text += f"⟠ ETH: ${eth['usd']:.0f} / €{eth['eur']:.0f}"
        await callback.message.answer(text)
    else:
        await callback.message.answer("❌ Ошибка крипты.")
    await callback.answer()

@dp.message(Command("usd"))
async def cmd_usd(message: types.Message):
    rates = get_cbr_rates()
    if rates and 'USD' in rates:
        await message.answer(f"💵 Доллар: {rates['USD']['value']:.2f} ₽")
    else:
        await message.answer("❌ Ошибка")

@dp.message(Command("eur"))
async def cmd_eur(message: types.Message):
    rates = get_cbr_rates()
    if rates and 'EUR' in rates:
        await message.answer(f"💶 Евро: {rates['EUR']['value']:.2f} ₽")
    else:
        await message.answer("❌ Ошибка")

@dp.message(Command("moex"))
async def cmd_moex(message: types.Message):
    data = get_moex_index()
    if data:
        sign = "+" if data['change'] >= 0 else ""
        await message.answer(f"📈 MOEX: {data['value']:.2f} ({sign}{data['change']:.2f}%)")
    else:
        await message.answer("❌ Ошибка")

@dp.message(Command("crypto"))
async def cmd_crypto(message: types.Message):
    btc = get_crypto('bitcoin')
    eth = get_crypto('ethereum')
    if btc and eth:
        await message.answer(f"₿ BTC: ${btc['usd']:.0f}  ⟠ ETH: ${eth['usd']:.0f}")
    else:
        await message.answer("❌ Ошибка")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("/usd, /eur, /moex, /crypto, /help")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Бот запущен!")
    dp.run_polling(bot)
