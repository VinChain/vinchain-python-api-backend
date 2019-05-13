import os


WEBSOCKET_URL = os.environ.get('WEBSOCKET_URL', "ws://127.0.0.1:8090/ws")
WEBSOCKET_PUBLIC_HELPER = os.environ.get('WEBSOCKET_URL', "wss://node.bitshares.eu/ws")

POSTGRES = {'host': os.environ.get('POSTGRES_HOST', 'localhost'),
            'database': os.environ.get('POSTGRES_DATABASE', 'explorer'),
            'user': os.environ.get('POSTGRES_USER', 'postgres'),
            'password': os.environ.get('POSTGRES_PASSWORD', 'somepassword'),
}

# a connection to a bitshares full node
FULL_WEBSOCKET_URL = os.environ.get('FULL_WEBSOCKET_URL', "ws://127.0.0.1:8090/ws")

# a connection to an ElasticSearch wrapper
ES_WRAPPER = os.environ.get('ES_WRAPPER', "http://127.0.0.1:5010")

COINMARKETCAP_API = os.environ.get('COINMARKETCAP_API', "https://api.coinmarketcap.com/v2")
IDAX_API = os.environ.get('IDAX_API', "https://openapi.idax.pro/api/v1")

CORE_ASSET_SYMBOL = 'VIN'
CORE_ASSET_ID = '1.3.0'

VIN_CURRENCY_ID = 3082

#TESTNET = 1 # 0 = not in the testnet, 1 = testnet
TESTNET = 0 # 0 = not in the testnet, 1 = testnet
CORE_ASSET_SYMBOL_TESTNET = 'TEST'
