import requests

from environs import Env

def get_headers():
    env = Env()
    env.read_env()

    data = {
        'client_id': env('CLIENT_ID'),
        'client_secret': env('CLIENT_SECRET'),
        'grant_type': 'client_credentials',
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()

    access_token = response.json()['access_token']

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    return headers


def get_products():
    headers = get_headers()

    # Получить все продукты
    response = requests.get('https://api.moltin.com/pcm/products', headers=headers)
    response.raise_for_status()

    product_data = response.json()

    return {
            product['attributes']['name']: product['id'] 
            for product in product_data['data']
        }

def get_product_by_id(product_id):
    headers = get_headers()

    # Получить продукт по id
    url = f'https://api.moltin.com/pcm/products/{product_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_price_book():
    headers = get_headers()

    # Получить price_book
    env = Env()
    env.read_env()
    price_book_id = env('PRICE_BOOK_ID')

    params = {
        'include': 'prices',
    }

    url = f'https://api.moltin.com/pcm/pricebooks/{price_book_id}'
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()


def get_image_id(image_path):
    headers = get_headers()

    url = f'https://api.moltin.com/pcm{image_path}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()['data']['id']


def get_image_url(image_path):
    headers = get_headers()
    image_id = get_image_id(image_path)

    url = f'https://api.moltin.com/v2/files/{image_id}'

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()['data']['link']['href']


def add_product_to_cart(cart_id, product_id, quantity):
    headers = get_headers()

    url = f'https://api.moltin.com/v2/carts/{cart_id}/items'

    json = {
        'data':{
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity
        }
    }

    response = requests.post(url, headers=headers, json=json)
    response.raise_for_status()


def get_amount_on_stock(product_id):
    headers = get_headers()

    # Получить запас по id
    url = f'https://api.moltin.com/v2/inventories/{product_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    stock_info = response.json()
    return stock_info['data']['available']


def get_cart_and_full_price(cart_id):
    headers = get_headers()

    url = f'https://api.moltin.com/v2/carts/{cart_id}/items'

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    items_info = response.json()

    return (
        items_info['data'], 
        items_info['meta']['display_price']['with_tax']['formatted']
    )


def remove_product_from_cart(cart_id, item_id):
    headers = get_headers()

    url = f'https://api.moltin.com/v2/carts/{cart_id}/items/{item_id}'

    response = requests.delete(url, headers=headers)
    response.raise_for_status()


def create_customer_by_email(email):
    headers = get_headers()

    url = 'https://api.moltin.com/v2/customers'

    json = {
        'data': {
            'type': 'customer',
            'name': 'Покупатель',
            'email': email,
            'password': 'mysecretpassword'
        }
    }

    response = requests.post(url, headers=headers, json=json)
    response.raise_for_status()
