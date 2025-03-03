import re
import requests
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = 'ТВОЙ_БОТ_ТОКЕН'  # Замените на токен вашего бота

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_article(text: str) -> str | None:
    # Регулярное выражение для извлечения артикула из ссылок и текста
    patterns = [
        r'/(\d+)/detail\.aspx',  # Ссылки вида /catalog/1234567/detail.aspx
        r'nm=(\d+)',             # Параметр nm в URL
        r'(\d{6,12})'            # Прямой артикул (6-12 цифр)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            article = match.group(1)
            if article.isdigit() and 6 <= len(article) <= 12:
                return article
    return None

def get_wb_product(article: str) -> dict | None:
    url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=0&nm={article}"
    try:
        response = requests.get(url).json()
        product = response['data']['products'][0]
        return {
            'name': product['name'],
            'brand': product['brand'],
            'price': product['priceU'] // 100,
            'sale_price': product['salePriceU'] // 100,
            'discount': product['sale'],
            'rating': product.get('rating', 0),
            'reviews': product.get('feedbacks', 0),
            'colors': [color['name'] for color in product['colors']],
            'sizes': [
                {
                    'name': size['name'],
                    'available': sum(stock['qty'] for stock in size.get('stocks', []))
                } 
                for size in product.get('sizes', []) if size.get('stocks')
            ],
            'delivery': f"{product.get('time1', 0)}-{product.get('time2', 0)} дней"
        }
    except Exception:
        return None

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🔍 <b>Wildberries Price Bot</b>\n\n"
                        "Отправь артикул (6-12 цифр) или ссылку на товар:",
                        parse_mode="HTML")

@dp.message()
async def process_input(message: Message):
    article = extract_article(message.text.strip())
    
    if not article:
        await message.answer("❌ Неверный формат\n"
                            "Отправь артикул (6-12 цифр) или ссылку на товар")
        return
    
    product = get_wb_product(article)
    
    if not product:
        await message.answer(f"❌ Товар с артикулом <b>{article}</b> не найден\n"
                            "Проверьте правильность данных",
                            parse_mode="HTML")
        return

    # Создаем ссылку на товар
    product_link = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    
    colors = "\n".join([f"▫️ {color}" for color in product['colors']])
    sizes = "\n".join([
        f"▫️ {size['name']} (в наличии: {size['available']})"
        for size in product['sizes'] if size['available'] > 0
    ]) or "Нет доступных размеров"

    message_text = (
        f"🛍 <b>{product['name']}</b>\n\n"
        f"🔖 Бренд: {product['brand']}\n"
        f"💰 Цена: <s>{product['price']} ₽</s> → <b>{product['sale_price']} ₽</b>\n"
        f"🔥 Скидка: {product['discount']}%\n"
        f"⭐ Рейтинг: {product['rating']}/5 (отзывов: {product['reviews']})\n\n"
        f"🎨 Цвета:\n{colors}\n\n"
        f"📏 Размеры:\n{sizes}\n\n"
        f"🚚 Доставка: {product['delivery']}\n\n"
        f"🌐 <a href='{product_link}'>Перейти к товару</a>"
    )

    await message.answer(
        message_text,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

if __name__ == '__main__':
    dp.run_polling(bot)