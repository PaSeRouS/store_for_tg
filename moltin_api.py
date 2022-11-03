import time
import requests

expires_on = 0
access_token = None


def get_headers(client_id, client_secret):
    global expires_on, access_token

    now = time.time()

    if access_token and now < expires_on:
        return {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        }

    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
    }

    response = requests.post('https://api.moltin.com/oauth/access_token', data=data)
    response.raise_for_status()

    access_token = response.json()['access_token']
    expires_on = now + response.json()['expires_in']

    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }


def get_products(client_id, client_secret):
    headers = get_headers(client_id, client_secret)

    response = requests.get('https://api.moltin.com/pcm/products', headers=headers)
    response.raise_for_status()

    product_data = response.json()

    return {
            product['attributes']['name']: product['id'] 
            for product in product_data['data']
        }

def get_product_by_id(product_id, client_id, client_secret):
    headers = get_headers(client_id, client_secret)

    url = f'https://api.moltin.com/pcm/products/{product_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()


def get_price_book(client_id, client_secret, price_book_id):
    headers = get_headers(client_id, client_secret)

    params = {
        'include': 'prices',
    }

    url = f'https://api.moltin.com/pcm/pricebooks/{price_book_id}'
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()

    return response.json()


def get_image_id(image_path, client_id, client_secret):
    headers = get_headers(client_id, client_secret)

    url = f'https://api.moltin.com/pcm{image_path}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()['data']['id']


def get_image_url(image_path, client_id, client_secret):
    headers = get_headers(client_id, client_secret)
    image_id = get_image_id(image_path, client_id, client_secret)

    url = f'https://api.moltin.com/v2/files/{image_id}'

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    return response.json()['data']['link']['href']


def add_product_to_cart(
    cart_id,
    product_id,
    quantity,
    client_id,
    client_secret
):
    headers = get_headers(client_id, client_secret)

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


def get_amount_on_stock(product_id, client_id, client_secret):
    headers = get_headers(client_id, client_secret)

    url = f'https://api.moltin.com/v2/inventories/{product_id}'
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    stock_info = response.json()
    return stock_info['data']['available']


def get_cart_and_full_price(cart_id, client_id, client_secret):
    headers = get_headers(client_id, client_secret)

    url = f'https://api.moltin.com/v2/carts/{cart_id}/items'

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    items_info = response.json()

    return (
        items_info['data'], 
        items_info['meta']['display_price']['with_tax']['formatted']
    )


def remove_product_from_cart(cart_id, item_id, client_id, client_secret):
    headers = get_headers(client_id, client_secret)

    url = f'https://api.moltin.com/v2/carts/{cart_id}/items/{item_id}'

    response = requests.delete(url, headers=headers)
    response.raise_for_status()


def create_customer_by_email(email, client_id, client_secret):
    headers = get_headers(client_id, client_secret)

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
