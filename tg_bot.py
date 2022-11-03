import logging
import redis
from textwrap import dedent

from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from moltin_api import (get_products, get_product_by_id, get_price_book,
                       get_image_url, add_product_to_cart, get_amount_on_stock,
                       get_cart_and_full_price, remove_product_from_cart,
                       create_customer_by_email)


_database = None
logger = logging.getLogger(__name__)


def get_menu_keyboard():
    env = get_env()
    products = get_products(env['client_id'], env['client_secret'])

    keyboard = [
        [InlineKeyboardButton(product_name, callback_data=product_id)]
        for product_name, product_id 
        in products.items()
    ]

    keyboard.append([InlineKeyboardButton("Корзина", callback_data="cart")])

    return keyboard


def get_cart(cart_id):
    env = get_env()
    cart_items, full_price = get_cart_and_full_price(cart_id, env['client_id'], env['client_secret'])
    cart_items_display = [
        dedent(
            f"""\
            {item['name']}
            {item['description']}
            {item['meta']['display_price']['with_tax']['unit']['formatted']} за кг
            {item['quantity']} кг за {item['meta']['display_price']['with_tax']['value']['formatted']}\
            """
        )
        for item in cart_items
    ]

    cart_items_display.append(f"Общая сумма: {full_price}")

    text = (
        "\n\n".join(cart_items_display) if cart_items else
        "Корзина пуста. Заполните её чем-нибудь."
    )

    cart_keyboard = [
        [InlineKeyboardButton(f"Удалить товар '{item['name']}'", callback_data=item["id"])]
        for item in cart_items 
    ]

    cart_keyboard.append([InlineKeyboardButton("В меню", callback_data="return")])

    if cart_items:
        cart_keyboard.append([InlineKeyboardButton("Оплатить", callback_data="checkout")])

    return text, cart_keyboard


def start(update, context):
    keyboard = get_menu_keyboard()

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Пожалуйста, выберите:', reply_markup=reply_markup)
    
    return 'HANDLE_MENU'


def handle_menu(update, context):
    users_reply = update.callback_query.data

    env = get_env()

    if users_reply == "cart":
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        
        text, cart_keyboard = get_cart(update.effective_chat.id)

        update.callback_query.message.reply_text(
            text=text,
            reply_markup = InlineKeyboardMarkup(cart_keyboard)
        )

        return 'HANDLE_CART'

    product_data = get_product_by_id(
        users_reply,
        env['client_id'],
        env['client_secret']
    )
    price_book = get_price_book(
        env['client_id'],
        env['client_secret'],
        env['price_book_id']
    )

    product_sku = product_data['data']['attributes']['sku']
    image_url = get_image_url(
        product_data['data']['relationships']['main_image']['links']['self'],
        env['client_id'],
        env['client_secret']
    )
    amount_on_stock = get_amount_on_stock(
        users_reply,
        env['client_id'],
        env['client_secret']
    )

    for price in price_book['included']:
        if price['attributes']['sku'] == product_sku:
            product_price = price['attributes']['currencies']['USD']['amount']/100

    text = dedent(
        f"""\
        {product_data['data']['attributes']['name']}

        {product_price}$ за килограмм
        {amount_on_stock} кг на складе

        {product_data['data']['attributes']['description']}\
        """
    )

    options_keyboard = [
        [
            InlineKeyboardButton("1 кг", callback_data=f"{product_data['data']['id']}:1"),
            InlineKeyboardButton("5 кг", callback_data=f"{product_data['data']['id']}:5"),
            InlineKeyboardButton("10 кг", callback_data=f"{product_data['data']['id']}:10")
        ],
        [
            InlineKeyboardButton("Назад", callback_data="return"),
            InlineKeyboardButton("Корзина", callback_data="cart")
        ]
    ]

    update.callback_query.message.reply_photo(
        image_url,
        caption=text,
        reply_markup=InlineKeyboardMarkup(options_keyboard)
    )

    return 'HANDLE_DESCRIPTION'


def handle_description(update, context):
    if not update.callback_query:
        return 'HANDLE_DESCRIPTION'

    users_reply = update.callback_query.data

    env = get_env()

    if users_reply == "cart":
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        
        text, cart_keyboard = get_cart(update.effective_chat.id)

        update.callback_query.message.reply_text(
            text=text,
            reply_markup = InlineKeyboardMarkup(cart_keyboard)
        )

        return 'HANDLE_CART'

    if users_reply == "return":
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        keyboard = get_menu_keyboard()

        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text(
            'Что Вам интересно?',
            reply_markup=reply_markup
        )

        return 'HANDLE_MENU'

    product_id, quantity = users_reply.split(":")
    add_product_to_cart(
        update.effective_chat.id,
        product_id,
        int(quantity),
        env['client_id'],
        env['client_secret']
    )
    update.callback_query.answer(text="Товар добавлен в корзину")

    return 'HANDLE_DESCRIPTION'


def handle_cart(update, context):
    if not update.callback_query:
        return 'HANDLE_CART'

    users_reply = update.callback_query.data

    env = get_env()

    if users_reply == "return":
        update.callback_query.edit_message_reply_markup(reply_markup=None)

        product_keyboard = get_menu_keyboard()

        update.callback_query.message.reply_text(
            text="Что Вам интересно?",
            reply_markup=InlineKeyboardMarkup(product_keyboard)
        )

        return 'HANDLE_MENU'

    if users_reply == 'checkout':
        update.callback_query.edit_message_reply_markup(reply_markup=None)

        update.callback_query.message.reply_text(
            text="Для оплаты введите ваш email:"
        )

        return 'WAITING_EMAIL'


    remove_product_from_cart(
        update.effective_chat.id,
        users_reply,
        env['client_id'],
        env['client_secret']
    )

    text, cart_keyboard = get_cart(update.effective_chat.id)

    update.callback_query.answer(text='Товар удалён из корзины')
    update.callback_query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(cart_keyboard)
    )

    return 'HANDLE_CART'


def waiting_email(update, context):
    users_reply = update.message.text

    env = get_env()

    create_customer_by_email(
        users_reply,
        env['client_id'],
        env['client_secret']
    )

    text = f'Пользователь с email {users_reply} создан'

    options_keyboard = [
        [
            InlineKeyboardButton("В меню", callback_data="return")
        ]
    ]

    update.message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(options_keyboard)
    )
    
    return 'HANDLE_DESCRIPTION'


def handle_users_reply(update, context):
    env = get_env()
    db = get_database_connection(
        env['database_password'],
        env['database_host'],
        env['database_port']
    )
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email
    }
    state_handler = states_functions[user_state]

    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)

def get_database_connection(password, host, port):
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        _database = redis.Redis(host=host, port=port, password=password)
    return _database


def get_env():
    env = Env()
    env.read_env()

    return {
        'tg_token': env("TELEGRAM_TOKEN"),
        'client_id': env('CLIENT_ID'),
        'client_secret': env('CLIENT_SECRET'),
        'price_book_id': env('PRICE_BOOK_ID'),
        'database_password': env("REDIS_PASSWORD"),
        'database_host': env("REDIS_HOST"),
        'database_port': env("REDIS_PORT")
    }


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    env = get_env()
    updater = Updater(env['tg_token'])
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    dispatcher.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
