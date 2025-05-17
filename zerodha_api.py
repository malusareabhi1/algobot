from kiteconnect import KiteConnect

api_key = "your_api_key"
api_secret = "your_api_secret"

kite = KiteConnect(api_key=api_key)

def get_login_url():
    return kite.login_url()

def generate_session(request_token):
    data = kite.generate_session(request_token, api_secret=api_secret)
    kite.set_access_token(data["access_token"])
    return kite
