import datetime
import json
import urllib2
import ssl
import functools

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import psycopg2
from websocket import create_connection
from flasgger import Swagger

import config

app = Flask(__name__)
CORS(app)

app.config['SWAGGER'] = {
    'title': 'Bitshares Python API',
    'uiversion': 2
}
Swagger(app, template_file='api.yaml')


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)




def use_ws_connection(url=config.WEBSOCKET_URL):
    def decorator_use_ws_connection(func):
      @functools.wraps(func)
      def wrapper(*args, **kwargs):
        ws = create_connection(url)
        try:
            result = func(ws, *args, **kwargs)
        finally:
            ws.close()
        return result

      return wrapper

    return decorator_use_ws_connection



@app.route('/header')
@use_ws_connection()
def header(ws):
    ws.send('{"id":1, "method":"call", "params":[0,"get_dynamic_global_properties",[]]}')
    result =  ws.recv()
    j = json.loads(result)

    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["2.3.0"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)

    current_supply = j2["result"][0]["current_supply"]
    confidental_supply = j2["result"][0]["confidential_supply"]

    market_cap = int(current_supply) + int(confidental_supply)
    j["result"]["bts_market_cap"] = int(market_cap/1000000)
    #print j["result"][0]["bts_market_cap"]

    # to avoid error 'URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed'
    gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    contents = urllib2.urlopen(config.COINMARKETCAP_API + "/ticker/" + str(config.VIN_CURRENCY_ID), context=gcontext).read()
    res = json.loads(contents)
    j["result"]["quote_volume"] = round(res['data']['quotes']['USD']['volume_24h'])

    ws.send('{"id":1, "method":"call", "params":[0,"get_global_properties",[]]}')
    result5 = ws.recv()
    j5 = json.loads(result5)
    #print j5

    commitee_count = len(j5["result"]["active_committee_members"])
    witness_count = len(j5["result"]["active_witnesses"])

    j["result"]["commitee_count"] = commitee_count
    j["result"]["witness_count"] = witness_count

    return jsonify(j["result"])


@app.route('/account')
def account():
    account_id = request.args.get('account_id')
    return jsonify(_account(account_id))


@use_ws_connection()
def _account(ws, account_id):
    ws.send('{"id":1, "method":"call", "params":[0,"get_accounts",[["'+account_id+'"]]]}')
    result =  ws.recv()
    j = json.loads(result)
    return j["result"]

@app.route('/account_name')
def account_name():
    account_id = request.args.get('account_id')
    return jsonify(_account_name(account_id))


@use_ws_connection()
def _account_name(ws, account_id):
    ws.send('{"id":1, "method":"call", "params":[0,"get_accounts",[["'+account_id+'"]]]}')
    result =  ws.recv()
    j = json.loads(result)
    return j["result"][0]["name"]


@app.route('/account_id')
def account_id():
    account_name = request.args.get('account_name')
    return jsonify(_account_id(account_name))


@use_ws_connection()
def _account_id(ws, account_name):
    ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_name + '"], 0]]}')
    result = ws.recv()
    j = json.loads(result)
    account_id = j["result"][0]["id"]
    return account_id


@app.route('/operation')
@use_ws_connection()
def get_operation(ws):
    operation_id = request.args.get('operation_id')
    ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["'+operation_id+'"]]]}')
    result =  ws.recv()
    j = json.loads(result)

    ws.send('{"id":1, "method":"call", "params":[0,"get_dynamic_global_properties",[]]}')
    result2 =  ws.recv()
    j2 = json.loads(result2)

    if not j["result"][0]:
        j["result"][0] = {}

    j["result"][0]["accounts_registered_this_interval"] = j2["result"]["accounts_registered_this_interval"]

    # get market cap
    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["2.3.0"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)

    current_supply = j2["result"][0]["current_supply"]
    confidental_supply = j2["result"][0]["confidential_supply"]

    market_cap = int(current_supply) + int(confidental_supply)
    j["result"][0]["bts_market_cap"] = int(market_cap/100000000)
    #print j["result"][0]["bts_market_cap"]


    ws.send('{"id":1, "method":"call", "params":[0,"get_24_volume",["BTS", "OPEN.BTC"]]}')
    result3 = ws.recv()
    j3 = json.loads(result3)
    #print j3["result"]["quote_volume"]
    # j["result"][0]["quote_volume"] = j3["result"]["quote_volume"]
    j["result"][0]["quote_volume"] = 0

    # TODO: making this call with every operation is not very efficient as this are static properties
    ws.send('{"id":1, "method":"call", "params":[0,"get_global_properties",[]]}')
    result5 = ws.recv()
    j5 = json.loads(result5)

    commitee_count = len(j5["result"]["active_committee_members"])
    witness_count = len(j5["result"]["active_witnesses"])

    j["result"][0]["commitee_count"] = commitee_count
    j["result"][0]["witness_count"] = witness_count


    #print j['result']

    return jsonify(j["result"])


@app.route('/operation_full')
@use_ws_connection(config.FULL_WEBSOCKET_URL)
def operation_full(ws):
    # lets connect the operations to a full node

    operation_id = request.args.get('operation_id')
    ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["'+operation_id+'"]]]}')
    result = ws.recv()
    j = json.loads(result)

    ws.send('{"id":1, "method":"call", "params":[0,"get_dynamic_global_properties",[]]}')
    result2 =  ws.recv()
    j2 = json.loads(result2)

    if not j["result"][0]:
        j["result"][0] = {}

    j["result"][0]["accounts_registered_this_interval"] = j2["result"]["accounts_registered_this_interval"]

    # get market cap
    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["2.3.0"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)

    current_supply = j2["result"][0]["current_supply"]
    confidental_supply = j2["result"][0]["confidential_supply"]

    market_cap = int(current_supply) + int(confidental_supply)
    j["result"][0]["bts_market_cap"] = int(market_cap/100000000)
    #print j["result"][0]["bts_market_cap"]


    ws.send('{"id":1, "method":"call", "params":[0,"get_24_volume",["BTS", "OPEN.BTC"]]}')
    result3 = ws.recv()
    j3 = json.loads(result3)
    #print j3["result"]["quote_volume"]
    j["result"][0]["quote_volume"] = j3["result"]["quote_volume"]

    # TODO: making this call with every operation is not very efficient as this are static properties
    ws.send('{"id":1, "method":"call", "params":[0,"get_global_properties",[]]}')
    result5 = ws.recv()
    j5 = json.loads(result5)

    commitee_count = len(j5["result"]["active_committee_members"])
    witness_count = len(j5["result"]["active_witnesses"])

    j["result"][0]["commitee_count"] = commitee_count
    j["result"][0]["witness_count"] = witness_count


    #print j['result']

    return jsonify(j["result"])


@app.route('/operation_full_elastic')
@use_ws_connection()
def operation_full_elastic(ws):

    operation_id = request.args.get('operation_id')
    contents = urllib2.urlopen(config.ES_WRAPPER + "/get_single_operation?operation_id=" + operation_id).read()

    ws.send('{"id":1, "method":"call", "params":[0,"get_dynamic_global_properties",[]]}')
    result2 =  ws.recv()
    j2 = json.loads(result2)

    #if not j["result"][0]:
    #    j["result"][0] = {}

    accounts_registered_this_interval = j2["result"]["accounts_registered_this_interval"]

    # get market cap
    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["2.3.0"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)

    current_supply = j2["result"][0]["current_supply"]
    confidental_supply = j2["result"][0]["confidential_supply"]

    market_cap = int(current_supply) + int(confidental_supply)
    bts_market_cap = int(market_cap/100000000)

    quote_volume = 0
    if config.TESTNET != 1: # Todo: had to do something else for the testnet
        ws.send('{"id":1, "method":"call", "params":[0,"get_24_volume",["BTS", "OPEN.BTC"]]}')
        result3 = ws.recv()
        j3 = json.loads(result3)
        # quote_volume = j3["result"]["quote_volume"]
    else:
        quote_volume = 0

    # TODO: making this call with every operation is not very efficient as this are static properties
    ws.send('{"id":1, "method":"call", "params":[0,"get_global_properties",[]]}')
    result5 = ws.recv()
    j5 = json.loads(result5)

    commitee_count = len(j5["result"]["active_committee_members"])
    witness_count = len(j5["result"]["active_witnesses"])

    #j["result"][0]["commitee_count"] = commitee_count
    #j["result"][0]["witness_count"] = witness_count

    res = json.loads(contents)
    j = {"result": { "op": json.loads(res[0]["operation_history"]["op"]),
         "accounts_registered_this_interval": accounts_registered_this_interval,
         "bts_market_cap": bts_market_cap, "quote_volume": quote_volume, "commitee_count": commitee_count, "witness_count": witness_count,
         "block_num": res[0]["block_data"]["block_num"], "op_in_trx": res[0]["operation_history"]["op_in_trx"],
         "result": res[0]["operation_history"]["operation_result"], "trx_in_block": res[0]["operation_history"]["trx_in_block"],
         "virtual_op": res[0]["operation_history"]["virtual_op"], "block_time": res[0]["block_data"]["block_time"]}}

    a = [0]
    a[0] = j["result"]
    return jsonify(a)


@app.route('/accounts')
@use_ws_connection()
def accounts(ws):
    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  ws.recv()
    #print  result2

    ws.send('{"id":2,"method":"call","params":[1,"asset",[]]}')

    asset =  ws.recv()
    asset_j = json.loads(asset)

    asset_api = str(asset_j["result"])

    ws.send('{"id":1, "method":"call", "params":['+asset_api+',"get_asset_holders",["1.3.0", 0, 100]]}')
    result =  ws.recv()
    j = json.loads(result)

    #print j["result"]

    return jsonify(j["result"])


@app.route('/full_account')
@use_ws_connection()
def full_account(ws):
    account_id = request.args.get('account_id')

    ws.send('{"id":1, "method":"call", "params":[0,"get_full_accounts",[["'+account_id+'"], 0]]}')
    result =  ws.recv()
    j = json.loads(result)

    #print j["result"]

    return jsonify(j["result"])


@app.route('/assets')
def assets():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT * FROM assets WHERE volume > 0 ORDER BY volume DESC"
    cur.execute(query)
    results = cur.fetchall()
    con.close()
    #print results
    return jsonify(results)


@app.route('/fees')
@use_ws_connection()
def fees(ws):
    ws.send('{"id":1, "method":"call", "params":[0,"get_global_properties",[]]}')
    result =  ws.recv()
    j = json.loads(result)

    #print j["result"]

    return jsonify(j["result"])


@app.route('/account_history')
@use_ws_connection()
def account_history(ws):
    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login = ws.recv()

    ws.send('{"id":2,"method":"call","params":[1,"history",[]]}')
    history =  ws.recv()
    history_j = json.loads(history)
    history_api = str(history_j["result"])
    #print history_api

    account_id = request.args.get('account_id')

    if not isObject(account_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    ws.send('{"id":1, "method":"call", "params":['+history_api+',"get_account_history",["'+account_id+'", "1.11.1", 20, "1.11.9999999999"]]}')
    result =  ws.recv()
    j = json.loads(result)

    if(len(j["result"]) > 0):
        for c in range(0, len(j["result"])):
            ws.send(
                '{"id":1, "method":"call", "params":[0,"get_block_header",[' + str(j["result"][c]["block_num"]) + ', 0]]}')
            result2 = ws.recv()
            j2 = json.loads(result2)

            j["result"][c]["timestamp"] = j2["result"]["timestamp"]
            j["result"][c]["witness"] = j2["result"]["witness"]
    try:
        return jsonify(j["result"])
    except:
        return {}


@app.route('/get_asset')
def get_asset():
    asset_id = request.args.get('asset_id')
    return jsonify(_get_asset(asset_id))


@use_ws_connection()
def _get_asset(ws, asset_id):
    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]

    #print asset_id
    ws.send('{"id":1, "method":"call", "params":[0,"get_assets",[["' + asset_id + '"], 0]]}')
    result = ws.recv()
    j = json.loads(result)

    dynamic_asset_data_id =  j["result"][0]["dynamic_asset_data_id"]

    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+dynamic_asset_data_id+'"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)
    #print j2["result"][0]["current_supply"]

    j["result"][0]["current_supply"] = j2["result"][0]["current_supply"]
    j["result"][0]["confidential_supply"] = j2["result"][0]["confidential_supply"]
    #print j["result"]

    j["result"][0]["accumulated_fees"] = j2["result"][0]["accumulated_fees"]
    j["result"][0]["fee_pool"] = j2["result"][0]["fee_pool"]

    issuer = j["result"][0]["issuer"]
    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+issuer+'"]]]}')
    result3 = ws.recv()
    j3 = json.loads(result3)
    j["result"][0]["issuer_name"] = j3["result"][0]["name"]

    return j["result"]


@app.route('/get_asset_and_volume')
@use_ws_connection()
def get_asset_and_volume(ws):
    asset_id = request.args.get('asset_id')

    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]

    #print asset_id
    ws.send('{"id":1, "method":"call", "params":[0,"get_assets",[["' + asset_id + '"], 0]]}')
    result = ws.recv()
    j = json.loads(result)

    dynamic_asset_data_id =  j["result"][0]["dynamic_asset_data_id"]

    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+dynamic_asset_data_id+'"]]]}')
    result2 = ws.recv()
    j2 = json.loads(result2)
    #print j2["result"][0]["current_supply"]

    j["result"][0]["current_supply"] = j2["result"][0]["current_supply"]
    j["result"][0]["confidential_supply"] = j2["result"][0]["confidential_supply"]
    #print j["result"]

    j["result"][0]["accumulated_fees"] = j2["result"][0]["accumulated_fees"]
    j["result"][0]["fee_pool"] = j2["result"][0]["fee_pool"]

    issuer = j["result"][0]["issuer"]
    ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+issuer+'"]]]}')
    result3 = ws.recv()
    j3 = json.loads(result3)
    j["result"][0]["issuer_name"] = j3["result"][0]["name"]


    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT volume, mcap FROM assets WHERE aid=%s"
    cur.execute(query, (asset_id,))
    results = cur.fetchall()
    con.close()
    try:
        j["result"][0]["volume"] = results[0][0]
        j["result"][0]["mcap"] = results[0][1]
    except:
        j["result"][0]["volume"] = 0
        j["result"][0]["mcap"] = 0

    return jsonify(j["result"])


@app.route('/block_header')
@use_ws_connection()
def block_header(ws):
    block_num = request.args.get('block_num')

    ws.send('{"id":1, "method":"call", "params":[0,"get_block_header",[' + block_num + ', 0]]}')
    result = ws.recv()
    j = json.loads(result)

    #print j["result"]

    return jsonify(j["result"])


@app.route('/get_block')
@use_ws_connection()
def get_block(ws):
    block_num = request.args.get('block_num')

    ws.send('{"id":1, "method":"call", "params":[0,"get_block",[' + block_num + ', 0]]}')
    result = ws.recv()
    j = json.loads(result)

    #print j["result"]

    return jsonify(j["result"])


@app.route('/get_ticker')
def get_ticker():
    base = request.args.get('base')
    quote = request.args.get('quote')
    return jsonify(_get_ticker(base, quote))


@use_ws_connection()
def _get_ticker(ws, base, quote):
    ws.send('{"id":1, "method":"call", "params":[0,"get_ticker",["' + base + '", "'+quote+'"]]}')
    result = ws.recv()
    j = json.loads(result)
    return j["result"]


@app.route('/get_volume')
def get_volume():
    base = request.args.get('base')
    quote = request.args.get('quote')
    return jsonify(_get_volume(base, quote))


@use_ws_connection()
def _get_volume(ws, base, quote):
    ws.send('{"id":1, "method":"call", "params":[0,"get_24_volume",["' + base + '", "'+quote+'"]]}')
    result = ws.recv()
    j = json.loads(result)
    return j["result"]


@app.route('/lastnetworkops')
def lastnetworkops():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT * FROM ops ORDER BY block_num DESC LIMIT 10"
    cur.execute(query)
    results = cur.fetchall()
    con.close()

    # add operation data
    for o in range(0, len(results)):
        operation_id = results[o][2]
        object = _get_object(operation_id)
        if object[0] is not None:
            print('!! OK operation={} object={}'.format(results[o], object))
            results[o] = results[o] + tuple(object[0]["op"])
        else:
            print('!! Wrong operation={}'.format(results[o]))

    return jsonify(results)


@app.route('/get_object')
def get_object():
    obj = request.args.get('object')
    return jsonify(_get_object(obj))


@use_ws_connection()
def _get_object(ws, obj):
    ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["'+obj+'"]]]}')
    result =  ws.recv()
    j = json.loads(result)
    return j["result"]


@app.route('/get_asset_holders_count')
def get_asset_holders_count():
    asset_id = request.args.get('asset_id')
    return jsonify(_get_asset_holders_count(asset_id))


@use_ws_connection()
def _get_asset_holders_count(ws, asset_id):
    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]

    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  ws.recv()
    #print  result2

    ws.send('{"id":2,"method":"call","params":[1,"asset",[]]}')

    asset =  ws.recv()
    asset_j = json.loads(asset)

    asset_api = str(asset_j["result"])

    ws.send('{"id":1, "method":"call", "params":['+asset_api+',"get_asset_holders_count",["'+asset_id+'"]]}')
    result =  ws.recv()
    j = json.loads(result)

    return j["result"]


@app.route('/get_asset_holders')
@use_ws_connection()
def get_asset_holders(ws):
    asset_id = request.args.get('asset_id')
    start = request.args.get('start', 0)
    limit = request.args.get('limit', 20)

    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]

    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  ws.recv()

    ws.send('{"id":2,"method":"call","params":[1,"asset",[]]}')

    asset =  ws.recv()
    asset_j = json.loads(asset)

    asset_api = str(asset_j["result"])

    ws.send('{"id":1, "method":"call", "params":['+asset_api+',"get_asset_holders",["'+asset_id+'", '+str(start)+', '+str(limit)+']]}')
    result =  ws.recv()

    j = json.loads(result)

    return jsonify(j["result"])


@app.route('/get_workers')
@use_ws_connection()
def get_workers(ws):
    ws.send('{"jsonrpc": "2.0", "method": "get_worker_count", "params": [], "id": 1}')

    count =  ws.recv()
    count_j = json.loads(count)

    workers_count = count_j["result"]

    #print workers_count

    # get the votes of woirker 114.0 - refund 400k
    ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["1.14.0"]]]}')
    result_0 = ws.recv()
    j_0 = json.loads(result_0)
    #account_id = j["result"][0]["worker_account"]
    thereshold =  int(j_0["result"][0]["total_votes_for"])

    workers = []
    for w in range(0, workers_count):
        ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["1.14.'+str(w)+'"]]]}')
        result =  ws.recv()

        j = json.loads(result)
        account_id = j["result"][0]["worker_account"]
        ws.send('{"id":1, "method":"call", "params":[0,"get_accounts",[["' + account_id + '"]]]}')
        result2 = ws.recv()
        j2 = json.loads(result2)

        account_name = j2["result"][0]["name"]
        j["result"][0]["worker_account_name"] = account_name

        current_votes = int(j["result"][0]["total_votes_for"])
        perc = (current_votes*100)/thereshold
        j["result"][0]["perc"] = perc

        workers.append(j["result"])

    r_workers = workers[::-1]
    return jsonify(filter(None, r_workers))


def isObject(string):
    parts = string.split(".")
    if len(parts) == 3:
        return True
    else:
        return False


@app.route('/get_markets')
@use_ws_connection()
def get_markets(ws):
    asset_id = request.args.get('asset_id')

    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]


    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT * FROM markets WHERE aid=%s"
    cur.execute(query, (asset_id,))
    results = cur.fetchall()
    con.close()
    return jsonify(results)


def get_markets_data():
    pairs_data = {}
    # to avoid error 'URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed'
    gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/73.0.3683.86 Chrome/73.0.3683.86 Safari/537.36',}
    req = urllib2.Request(config.IDAX_API + '/tickers', headers=headers)
    contents = urllib2.urlopen(req, context=gcontext, ).read()
    res = json.loads(contents)
    pair_prefix = '{}_'.format(config.CORE_ASSET_SYMBOL)  # 'VIN_'
    for pair in res['data']:
        if pair['market'].startswith(pair_prefix):
            pairs_data[pair['market']] = {'pair': pair['market'],
                                'price': pair['lastPrice'],
                                'volume': pair['volume']}
    return pairs_data


@app.route('/get_most_active_markets')
def get_most_active_markets():
    pairs_data = get_markets_data()
    return jsonify(pairs_data)


@app.route('/get_order_book')
@use_ws_connection()
def get_order_book(ws):
    base = request.args.get('base')
    quote = request.args.get('quote')
    limit = request.args.get('limit', False)
    if not limit:
        limit = 10
    elif int(limit) > 50:
        limit = 50
    ws.send('{"id":1, "method":"call", "params":[0,"get_order_book",["'+base+'", "'+quote+'", '+str(limit)+']]}')
    result = ws.recv()
    j = json.loads(result)

    return jsonify(j["result"])


@app.route('/get_margin_positions')
@use_ws_connection()
def get_open_orders(ws):
    account_id = request.args.get('account_id')
    ws.send('{"id":1, "method":"call", "params":[0,"get_margin_positions",["'+account_id+'"]]}')
    result =  ws.recv()
    j = json.loads(result)

    return jsonify(j["result"])


@app.route('/get_witnesses')
@use_ws_connection()
def get_witnesses(ws):
    ws.send('{"jsonrpc": "2.0", "method": "get_witness_count", "params": [], "id": 1}')
    count =  ws.recv()
    count_j = json.loads(count)

    witnesses_count = count_j["result"]

    witnesses = []
    for w in range(0, witnesses_count):
        ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["1.6.'+str(w)+'"]]]}')
        result =  ws.recv()
        j = json.loads(result)
        if j["result"] and j["result"][0] is not None:
            account_id = j["result"][0]["witness_account"]
            #print account_id
            ws.send('{"id":1, "method":"call", "params":[0,"get_accounts",[["' + account_id + '"]]]}')
            result2 = ws.recv()
            j2 = json.loads(result2)

            account_name = j2["result"][0]["name"]
            j["result"][0]["witness_account_name"] = account_name
        else:
            #j["result"][0]["witness_account_name"] = ""
            continue

        witnesses.append(j["result"])


    witnesses = sorted(witnesses, key=lambda k: int(k[0]['total_votes']))
    r_witnesses = witnesses[::-1]

    return jsonify(filter(None, r_witnesses))


@app.route('/get_committee_members')
@use_ws_connection()
def get_committee_members(ws):
    ws.send('{"jsonrpc": "2.0", "method": "get_committee_count", "params": [], "id": 1}')
    count =  ws.recv()
    count_j = json.loads(count)
    committee_count = int(count_j["result"])

    committee_members = []
    for w in range(0, committee_count):
        ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["1.5.'+str(w)+'"]]]}')
        result =  ws.recv()

        j = json.loads(result)
        if j["result"][0]:
            account_id = j["result"][0]["committee_member_account"]
            #print account_id
            ws.send('{"id":1, "method":"call", "params":[0,"get_accounts",[["' + account_id + '"]]]}')
            result2 = ws.recv()
            j2 = json.loads(result2)

            account_name = j2["result"][0]["name"]
            j["result"][0]["committee_member_account_name"] = account_name
        else:
            #j["result"][0]["witness_account_name"] = ""
            continue

        committee_members.append(j["result"])

    committee_members = sorted(committee_members, key=lambda k: int(k[0]['total_votes']))
    r_committee = committee_members[::-1] # this reverses array

    return jsonify(filter(None, r_committee))


@app.route('/market_chart_dates')
def market_chart_dates():
    base = datetime.date.today()
    date_list = [base - datetime.timedelta(days=x) for x in range(0, 100)]
    date_list = [d.strftime("%Y-%m-%d") for d in date_list]
    #print len(list(reversed(date_list)))
    return jsonify(list(reversed(date_list)))


@app.route('/market_chart_data')
@use_ws_connection()
def market_chart_data(ws):
    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  ws.recv()

    ws.send('{"id":2,"method":"call","params":[1,"history",[]]}')
    history =  ws.recv()
    history_j = json.loads(history)
    history_api = str(history_j["result"])

    base = request.args.get('base')
    quote = request.args.get('quote')

    ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + base + '"], 0]]}')
    result_l = ws.recv()
    j_l = json.loads(result_l)
    base_id = j_l["result"][0]["id"]
    base_precision = 10**j_l["result"][0]["precision"]
    #print base_id

    ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + quote + '"], 0]]}')
    result_l = ws.recv()
    j_l = json.loads(result_l)
    #print j_l
    quote_id = j_l["result"][0]["id"]
    quote_precision = 10**j_l["result"][0]["precision"]
    #print quote_id

    now = datetime.date.today()
    ago = now - datetime.timedelta(days=100)
    ws.send('{"id":1, "method":"call", "params":['+history_api+',"get_market_history", ["'+base_id+'", "'+quote_id+'", 86400, "'+ago.strftime("%Y-%m-%dT%H:%M:%S")+'", "'+now.strftime("%Y-%m-%dT%H:%M:%S")+'"]]}')
    result_l = ws.recv()
    j_l = json.loads(result_l)

    data = []
    for w in range(0, len(j_l["result"])):

        open_quote = float(j_l["result"][w]["open_quote"])
        high_quote = float(j_l["result"][w]["high_quote"])
        low_quote = float(j_l["result"][w]["low_quote"])
        close_quote = float(j_l["result"][w]["close_quote"])

        open_base = float(j_l["result"][w]["open_base"])
        high_base = float(j_l["result"][w]["high_base"])
        low_base = float(j_l["result"][w]["low_base"])
        close_base = float(j_l["result"][w]["close_base"])

        open = 1/(float(open_base/base_precision)/float(open_quote/quote_precision))
        high = 1/(float(high_base/base_precision)/float(high_quote/quote_precision))
        low = 1/(float(low_base/base_precision)/float(low_quote/quote_precision))
        close = 1/(float(close_base/base_precision)/float(close_quote/quote_precision))

        ohlc = [open, close, low, high]

        data.append(ohlc)

    append = [0,0,0,0]
    if len(data) < 99:
        complete = 99 - len(data)
        for c in range(0, complete):
            data.insert(0, append)

    return jsonify(data)


def findMax(a,b):
    if a != 'Inf' and b != 'Inf':
        return max([a, b])
    elif a == 'Inf':
        return b
    else:
        return a


def findMin(a, b):
    if a != 0 and b != 0:
        return min([a, b])
    elif a == 0:
        return b
    else:
        return a


@app.route('/top_proxies')
def top_proxies():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT sum(amount) FROM holders"
    cur.execute(query)
    total = cur.fetchone()
    total_votes = total[0]

    query = "SELECT voting_as FROM holders WHERE voting_as<>'1.2.5' group by voting_as"
    cur.execute(query)
    results = cur.fetchall()
    #con.close()

    proxies = []

    for p in range(0, len(results)):

        proxy_line = [0] * 5

        proxy_id = results[p][0]
        proxy_line[0] = proxy_id

        query = "SELECT account_name, amount FROM holders WHERE account_id=%s LIMIT 1"
        cur.execute(query, (proxy_id,))
        proxy = cur.fetchone()

        try:
            proxy_name = proxy[0]
            proxy_amount = proxy[1]
        except:
            proxy_name = "unknown"
            proxy_amount = 0


        proxy_line[1] = proxy_name

        query = "SELECT amount, account_id FROM holders WHERE voting_as=%s"
        cur.execute(query, (proxy_id,))
        results2 = cur.fetchall()

        proxy_line[2] = int(proxy_amount)

        for p2 in range(0, len(results2)):
            amount = results2[p2][0]
            account_id = results2[p2][1]
            proxy_line[2] = proxy_line[2] + int(amount)  # total proxy votes
            proxy_line[3] = proxy_line[3] + 1       # followers

        if proxy_line[3] > 2:
            percentage = float(float(proxy_line[2]) * 100.0/ float(total_votes))
            proxy_line[4] = percentage
            proxies.append(proxy_line)

    con.close()

    proxies = sorted(proxies, key=lambda k: int(k[2]))
    r_proxies = proxies[::-1]

    return jsonify(filter(None, r_proxies))


@app.route('/top_holders')
def top_holders():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT * FROM holders WHERE voting_as='1.2.5' ORDER BY amount DESC LIMIT 10"
    cur.execute(query)
    results = cur.fetchall()
    con.close()
    return jsonify(results)


@app.route('/witnesses_votes')
@use_ws_connection()
def witnesses_votes(ws):
    proxies = top_proxies()
    proxies = proxies.response
    proxies = ''.join(proxies)
    proxies = json.loads(proxies)
    proxies = proxies[:10]

    witnesses = get_witnesses()
    witnesses = witnesses.response
    witnesses = ''.join(witnesses)
    witnesses = json.loads(witnesses)
    witnesses = witnesses[:25]

    w, h = len(proxies) + 2, len(witnesses)
    witnesses_votes = [[0 for x in range(w)] for y in range(h)]

    for w in range(0, len(witnesses)):
        vote_id =  witnesses[w][0]["vote_id"]
        id_witness = witnesses[w][0]["id"]
        witness_account_name = witnesses[w][0]["witness_account_name"]

        witnesses_votes[w][0] = witness_account_name
        witnesses_votes[w][1] = id_witness

        c = 2

        for p in range(0, len(proxies)):
            id_proxy = proxies[p][0]

            #witnesses_votes[w][c] = id_proxy

            ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+id_proxy+'"]]]}')
            result = ws.recv()
            j = json.loads(result)

            votes = j["result"][0]["options"]["votes"]
            #print votes
            p_vote = "-"
            for v in range(0, len(votes)):

                if votes[v] == vote_id:
                    p_vote = "Y"

            witnesses_votes[w][c] = id_proxy + ":" + p_vote

            c = c + 1

    #print witnesses_votes
    return jsonify(witnesses_votes)


@app.route('/workers_votes')
@use_ws_connection()
def workers_votes(ws):
    proxies = top_proxies()
    proxies = proxies.response
    proxies = ''.join(proxies)
    proxies = json.loads(proxies)
    proxies = proxies[:10]

    workers = get_workers()
    workers = workers.response
    workers = ''.join(workers)
    workers = json.loads(workers)
    workers = workers[:30]
    #print workers

    w, h = len(proxies) + 3, len(workers)
    workers_votes = [[0 for x in range(w)] for y in range(h)]

    for w in range(0, len(workers)):
        vote_id =  workers[w][0]["vote_for"]
        id_worker = workers[w][0]["id"]
        worker_account_name = workers[w][0]["worker_account_name"]
        worker_name = workers[w][0]["name"]

        workers_votes[w][0] = worker_account_name
        workers_votes[w][1] = id_worker
        workers_votes[w][2] = worker_name

        c = 3

        for p in range(0, len(proxies)):
            id_proxy = proxies[p][0]

            #witnesses_votes[w][c] = id_proxy

            ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+id_proxy+'"]]]}')
            result = ws.recv()
            j = json.loads(result)

            votes = j["result"][0]["options"]["votes"]
            #print votes
            p_vote = "-"
            for v in range(0, len(votes)):

                if votes[v] == vote_id:
                    p_vote = "Y"

            workers_votes[w][c] = id_proxy + ":" + p_vote

            c = c + 1

    #print witnesses_votes
    return jsonify(workers_votes)


@app.route('/committee_votes')
@use_ws_connection()
def committee_votes(ws):
    proxies = top_proxies()
    proxies = proxies.response
    proxies = ''.join(proxies)
    proxies = json.loads(proxies)
    proxies = proxies[:10]

    committee = get_committee_members()
    committee = committee.response
    committee = ''.join(committee)
    committee = json.loads(committee)
    committee = committee[:11]
    #print workers

    w, h = len(proxies) + 2, len(committee)
    committee_votes = [[0 for x in range(w)] for y in range(h)]

    for w in range(0, len(committee)):
        vote_id =  committee[w][0]["vote_id"]
        id_committee = committee[w][0]["id"]
        committee_account_name = committee[w][0]["committee_member_account_name"]

        committee_votes[w][0] = committee_account_name
        committee_votes[w][1] = id_committee

        c = 2

        for p in range(0, len(proxies)):
            id_proxy = proxies[p][0]

            #witnesses_votes[w][c] = id_proxy

            ws.send('{"id": 1, "method": "call", "params": [0, "get_objects", [["'+id_proxy+'"]]]}')
            result = ws.recv()
            j = json.loads(result)

            votes = j["result"][0]["options"]["votes"]
            #print votes
            p_vote = "-"
            for v in range(0, len(votes)):

                if votes[v] == vote_id:
                    p_vote = "Y"
                    committee_votes[w][c] = id_proxy + ":" + p_vote
                    break
                else:
                    p_vote = "-"
                    committee_votes[w][c] = id_proxy + ":" + p_vote

            c = c + 1

    #print witnesses_votes
    return jsonify(committee_votes)


@app.route('/top_markets')
def top_markets():
    markets_data = get_markets_data()
    top_markets = [[val['pair'], val['volume']] for val in markets_data.itervalues()]
    return jsonify(top_markets)


@app.route('/top_smartcoins')
def top_smartcoins():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT volume FROM assets WHERE type='SmartCoin' ORDER BY volume DESC LIMIT 7"
    cur.execute(query)
    results = cur.fetchall()
    total = 0
    for v in range(0, len(results)):
        total = total + results[v][0]

    query = "SELECT aname, volume FROM assets WHERE type='SmartCoin' ORDER BY volume DESC LIMIT 7"
    cur.execute(query)
    results = cur.fetchall()

    w = 2
    h = len(results)
    top_smartcoins = [[0 for x in range(w)] for y in range(h)]

    for tp in range(0, h):
        #print results[tp][1]
        top_smartcoins[tp][0] = results[tp][0]
        #perc = (results[tp][1]*100)/total
        top_smartcoins[tp][1] = results[tp][1]

    con.close()
    return jsonify(top_smartcoins)


@app.route('/top_uias')
def top_uias():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT volume FROM assets WHERE type='User Issued' ORDER BY volume DESC LIMIT 7"
    cur.execute(query)
    results = cur.fetchall()
    total = 0
    for v in range(0, len(results)):
        total = total + results[v][0]

    query = "SELECT aname, volume FROM assets WHERE TYPE='User Issued' ORDER BY volume DESC LIMIT 7"
    cur.execute(query)
    results = cur.fetchall()

    w = 2
    h = len(results)
    top_uias = [[0 for x in range(w)] for y in range(h)]

    for tp in range(0, h):
        #print results[tp][1]
        top_uias[tp][0] = results[tp][0]
        #perc = (results[tp][1]*100)/total
        top_uias[tp][1] = results[tp][1]

    con.close()
    return jsonify(top_uias)


@app.route('/top_operations')
def top_operations():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT count(*) FROM ops"
    cur.execute(query)
    results = cur.fetchone()
    total = results[0]

    query = "SELECT op_type, count(op_type) AS counter FROM ops GROUP BY op_type ORDER BY counter DESC"
    cur.execute(query)
    results = cur.fetchall()


    w = 2
    h = len(results)
    top_operations = [[0 for x in range(w)] for y in range(h)]

    for tp in range(0, h):
        #print results[tp][1]
        top_operations[tp][0] = results[tp][0]
        #perc = (results[tp][1]*100)/total
        top_operations[tp][1] = results[tp][1]

    con.close()
    return jsonify(top_operations)


@app.route('/last_network_transactions')
def last_network_transactions():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT * FROM ops ORDER BY block_num DESC LIMIT 20"
    cur.execute(query)
    results = cur.fetchall()
    con.close()
    #print results
    return jsonify(results)


@app.route('/lookup_accounts')
@use_ws_connection()
def lookup_accounts(ws):
    start = request.args.get('start')
    ws.send('{"id":1, "method":"call", "params":[0,"lookup_accounts",["'+start+'", 1000]]}')
    result =  ws.recv()
    j = json.loads(result)

    #print j["result"]

    return jsonify(j["result"])


@app.route('/lookup_assets')
def lookup_assets():
    start = request.args.get('start')

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "SELECT aname FROM assets WHERE aname LIKE %s"
    cur.execute(query, (start+'%',))
    results = cur.fetchall()
    con.close()
    return jsonify(results)


@app.route('/getlastblocknumbher')
@use_ws_connection()
def getlastblocknumber(ws):
    ws.send('{"id":1, "method":"call", "params":[0,"get_dynamic_global_properties",[]]}')
    result =  ws.recv()
    j = json.loads(result)

    return jsonify(j["result"]["head_block_number"])


@app.route('/account_history_pager')
@use_ws_connection(config.FULL_WEBSOCKET_URL)
def account_history_pager(full_ws):
    page = request.args.get('page')
    account_id = request.args.get('account_id')

    # connecting into a full node.
    full_ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  full_ws.recv()

    full_ws.send('{"id":2,"method":"call","params":[1,"history",[]]}')
    history =  full_ws.recv()
    history_j = json.loads(history)
    history_api = str(history_j["result"])

    if not isObject(account_id):
        full_ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = full_ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    # need to get total ops for account
    full_ws.send('{"id":1, "method":"call", "params":[0,"get_accounts",[["' + account_id + '"]]]}')
    result_a = full_ws.recv()
    j_a = json.loads(result_a)

    stats = j_a["result"][0]["statistics"]

    full_ws.send('{"id":1, "method":"call", "params":[0,"get_objects",[["'+stats+'"]]]}')
    result_s =  full_ws.recv()
    j_s = json.loads(result_s)

    total_ops = j_s["result"][0]["total_ops"]
    #print total_ops
    start = total_ops - (20 * int(page))
    stop = total_ops - (40 * int(page))

    if stop < 0:
        stop = 0

    if start > 0:
        full_ws.send('{"id":1, "method":"call", "params":['+history_api+',"get_relative_account_history",["'+account_id+'", '+str(stop)+', 20, '+str(start)+']]}')
        result_f =  full_ws.recv()
        j_f = json.loads(result_f)

        for c in range(0, len(j_f["result"])):
            full_ws.send('{"id":1, "method":"call", "params":[0,"get_block_header",[' + str(j_f["result"][c]["block_num"]) + ', 0]]}')
            result2 = full_ws.recv()
            j2 = json.loads(result2)
            j_f["result"][c]["timestamp"] = j2["result"]["timestamp"]
            j_f["result"][c]["witness"] = j2["result"]["witness"]

        return jsonify(j_f["result"])
    else:
        return ""


@app.route('/account_history_pager_elastic')
@use_ws_connection()
def account_history_pager_elastic(ws):
    page = request.args.get('page')
    account_id = request.args.get('account_id')

    if not isObject(account_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    from_ = int(page) * 20
    contents = urllib2.urlopen(config.ES_WRAPPER + "/get_account_history?account_id="+account_id+"&from_="+str(from_)+"&size=20&sort_by=-block_data.block_time").read()

    j = json.loads(contents)

    results = [0 for x in range(len(j))]
    for n in range(0, len(j)):
        results[n] = {"op": json.loads(j[n]["operation_history"]["op"]),
                      "block_num": j[n]["block_data"]["block_num"],
                      "id": j[n]["account_history"]["operation_id"],
                      "op_in_trx": j[n]["operation_history"]["op_in_trx"],
                      "result": j[n]["operation_history"]["operation_result"],
                      "timestamp": j[n]["block_data"]["block_time"],
                      "trx_in_block": j[n]["operation_history"]["trx_in_block"],
                      "virtual_op": j[n]["operation_history"]["virtual_op"]
                      }

    return jsonify(list(results))


@app.route('/get_limit_orders')
@use_ws_connection()
def get_limit_orders(ws):
    base = request.args.get('base')
    quote = request.args.get('quote')
    ws.send('{"id":1, "method":"call", "params":[0,"get_limit_orders",["' + base + '", "' + quote + '", 100]]}')
    result = ws.recv()
    j = json.loads(result)

    return jsonify(j["result"])


@app.route('/get_call_orders')
@use_ws_connection()
def get_call_orders(ws):
    base = request.args.get('base')
    quote = request.args.get('quote')
    ws.send('{"id":1, "method":"call", "params":[0,"get_call_orders",["' + base + '", "' + quote + '", 100]]}')
    result = ws.recv()
    j = json.loads(result)

    return jsonify(j["result"])


@app.route('/get_settle_orders')
@use_ws_connection()
def get_settle_orders(ws):
    base = request.args.get('base')
    quote = request.args.get('quote')
    ws.send('{"id":1, "method":"call", "params":[0,"get_settle_orders",["' + base + '", "' + quote + '", 100]]}')
    result = ws.recv()
    j = json.loads(result)

    return jsonify(j["result"])


@app.route('/get_fill_order_history')
@use_ws_connection()
def get_fill_order_history(ws):
    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  ws.recv()

    ws.send('{"id":2,"method":"call","params":[1,"history",[]]}')
    history =  ws.recv()
    history_j = json.loads(history)
    history_api = str(history_j["result"])

    base = request.args.get('base')
    quote = request.args.get('quote')

    ws.send('{"id":1, "method":"call", "params":[' + history_api + ',"get_fill_order_history",["' + base + '", "' + quote + '", 100]]}')
    result = ws.recv()
    j = json.loads(result)
    return jsonify(j["result"])


@app.route('/get_dex_total_volume')
def get_dex_total_volume():
    res = {"volume_bts": 0, "volume_usd": 0, "volume_cny": 0,
           "market_cap_bts": 0, "market_cap_usd": 0, "market_cap_cny": 0}
    return jsonify(res)

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "select price from assets where aname='USD'"
    cur.execute(query)
    results = cur.fetchone()
    usd_price = results[0]

    query = "select price from assets where aname='CNY'"
    cur.execute(query)
    results = cur.fetchone()
    cny_price = results[0]

    query = "select sum(volume) from assets WHERE aname!='BTS'"
    cur.execute(query)
    results = cur.fetchone()
    volume = results[0]

    query = "select sum(mcap) from assets"
    cur.execute(query)
    results = cur.fetchone()
    market_cap = results[0]
    con.close()

    res = {"volume_bts": round(volume), "volume_usd": round(volume/usd_price), "volume_cny": round(volume/cny_price),
          "market_cap_bts": round(market_cap), "market_cap_usd": round(market_cap/usd_price), "market_cap_cny": round(market_cap/cny_price)}
    return jsonify(res)


@app.route('/daily_volume_dex_dates')
def daily_volume_dex_dates():
    base = datetime.date.today()
    date_list = [base - datetime.timedelta(days=x) for x in range(0, 60)]
    date_list = [d.strftime("%Y-%m-%d") for d in date_list]
    #print len(list(reversed(date_list)))
    return jsonify(list(reversed(date_list)))


@app.route('/daily_volume_dex_data')
def daily_volume_dex_data():
    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "select value from stats where type='volume_bts' order by date desc limit 60"
    cur.execute(query)
    results = cur.fetchall()

    mod = [0 for x in range(len(results))]
    for r in range(0, len(results)):
        mod[r] = results[r][0]

    return jsonify(list(reversed(mod)))


@app.route('/get_all_asset_holders')
@use_ws_connection()
def get_all_asset_holders(ws):
    asset_id = request.args.get('asset_id')

    if not isObject(asset_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_asset_symbols",[["' + asset_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)
        asset_id = j_l["result"][0]["id"]

    ws.send('{"id":2,"method":"call","params":[1,"login",["",""]]}')
    login =  ws.recv()

    ws.send('{"id":2,"method":"call","params":[1,"asset",[]]}')

    asset =  ws.recv()
    asset_j = json.loads(asset)

    asset_api = str(asset_j["result"])

    all = []

    ws.send('{"id":1, "method":"call", "params":[' + asset_api + ',"get_asset_holders",["' + asset_id + '", 0, 100]]}')
    result = ws.recv()
    j = json.loads(result)

    for r in range(0, len(j["result"])):
        all.append(j["result"][r])

    len_result = len(j["result"])
    start = 100
    while  len_result == 100:
        start = start + 100
        ws.send('{"id":1, "method":"call", "params":[' + asset_api + ',"get_asset_holders",["' + asset_id + '", ' + str(start) + ', 100]]}')
        result = ws.recv()
        j = json.loads(result)
        len_result = len(j["result"])
        for r in range(0, len(j["result"])):
            all.append(j["result"][r])


    return jsonify(all)


@app.route('/referrer_count')
@use_ws_connection()
def referrer_count(ws):
    account_id = request.args.get('account_id')

    if not isObject(account_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    query = "select count(*) from referrers where referrer=%s"
    cur.execute(query, (account_id,))
    results = cur.fetchone()

    return jsonify(results)


@app.route('/get_all_referrers')
@use_ws_connection()
def get_all_referrers(ws):
    account_id = request.args.get('account_id')
    page = request.args.get('page', 0)

    if not isObject(account_id):
        ws.send('{"id":1, "method":"call", "params":[0,"lookup_account_names",[["' + account_id + '"], 0]]}')
        result_l = ws.recv()
        j_l = json.loads(result_l)

        account_id = j_l["result"][0]["id"]

    con = psycopg2.connect(**config.POSTGRES)
    cur = con.cursor()

    offset = int(page) * 20;

    query = "select * from referrers where referrer=%s ORDER BY rid DESC LIMIT 20 OFFSET %s"
    cur.execute(query, (account_id,str(offset), ))
    results = cur.fetchall()

    return jsonify(results)
