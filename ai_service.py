import random

def suggest_price(price):
    return round(price * random.uniform(1.1, 1.4), 2)