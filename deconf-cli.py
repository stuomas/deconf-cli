import requests
import json
import sys

try:
    print('''
██████╗ ███████╗ ██████╗ ██████╗ ███╗   ██╗███████╗
██╔══██╗██╔════╝██╔════╝██╔═══██╗████╗  ██║██╔════╝
██║  ██║█████╗  ██║     ██║   ██║██╔██╗ ██║█████╗  
██║  ██║██╔══╝  ██║     ██║   ██║██║╚██╗██║██╔══╝  
██████╔╝███████╗╚██████╗╚██████╔╝██║ ╚████║██║     
╚═════╝ ╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝\n''')
except UnicodeEncodeError:
    print('\nWelcome to deconf!\n')

print('''Currently supported parameters for easy configuration are 'sensitivity'
for ZHAVibration types and 'duration' for ZHAPresence types. Other parameters
will be added if needed.
        
0) Help
1) Auto-discover gateway (online)
2) Acquire a deCONZ REST API key
3) Print saved gateway information
4) Print all entities
5) Print configurable entities
6) Modify entity configuration
7) Purge saved gateway information
''')


class Gateway:
    filename = 'deconz_gateway_data.json'
    info = {}  # decoded json
    configurables = []  # list of configurable entities
    ip = ''
    port = ''
    key = ''
    state_ok = False


def discover_gateway():
    # Auto-discovery needs Internet connection!
    try:
        response = requests.get('https://dresden-light.appspot.com/discover')
    except requests.ConnectionError:
        print('Connection error')
        return None
    if response.status_code == requests.codes.ok:
        print('Gateway found! Next acquire an API key.')
        return response.json()[0]  # Takes into account only one gateway device
    else:
        print(response.status_code)


def get_api_key(gw):
    name = input('Select name for the API key: ')
    print('Gateway needs to be unlocked. Go to Phoscon web app Settings -> Gateway -> Advanced -> Authenticate app')
    input('Press ENTER when the gateway is unlocked...')
    response = requests.post(
        'http://{}:{}/api'.format(gw.ip, gw.port), data=json.dumps({"devicetype": name}))
    if response.status_code == requests.codes.ok:
        return response.json()[0]['success']['username']
    else:
        print('Error retrieving key, is gateway unlocked?')


def purge_json():
    confirm = input(
        'Are you sure you want to remove locally saved gateway information? (y/n)')
    if confirm == 'y':
        print('Purged')


def save_gateway_info(gw):
    data = gw.info
    data.update({'apikey': gw.key})
    with open(gw.filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    gw.state_ok = True
    print('Success! Saved gateway information and API key {} to {}'.format(
        gw.key, gw.filename))


def list_entities(gw):
    try:
        response = requests.get(
            'http://{}:{}/api/{}/sensors'.format(gw.ip, gw.port, gw.key))
    except requests.ConnectionError:
        print('Connection error')
    if response.status_code == requests.codes.ok:
        return json.dumps(response.json(), indent=2)
    else:
        print(response.status_code)


def list_configurables(gw):
    entities = json.loads(list_entities(gw))
    print('Configurable entities:')
    configurables = []
    for ids, config in entities.items():
        entry = {}
        for key, value in config.items():
            if value == 'ZHAPresence':
                entry['id'] = int(ids)
                entry['name'] = config['name']
                entry['type'] = value
                entry['duration'] = config['config']['duration']
                configurables.append(entry)
            elif value == 'ZHAVibration':
                entry['id'] = int(ids)
                entry['name'] = config['name']
                entry['type'] = value
                entry['sensitivity'] = config['config']['sensitivity']
                configurables.append(entry)
    print(json.dumps(configurables, indent=2))
    return configurables


def modify_config(gw):
    id = int(input('Enter entity ID to modify: '))
    new = 0
    response = None
    for i in gw.configurables:
        if i['id'] == id:
            if i['type'] == "ZHAPresence":
                new = input(
                    'Current duration {}. Enter new value: '.format(i['duration']))
                response = requests.put('http://{}:{}/api/{}/sensors/{}/config'.format(
                    gw.ip, gw.port, gw.key, id), data=json.dumps({'duration': new}))
                if response.status_code == requests.codes.ok:
                    print('Success!')
                    return
            elif i['type'] == "ZHAVibration":
                new = input(
                    'Current sensitivity {}. Enter new value: '.format(i['sensitivity']))
                response = requests.put('http://{}:{}/api/{}/sensors/{}/config'.format(
                    gw.ip, gw.port, gw.key, id), data=json.dumps({'sensitivity': new}))
                if response.status_code == requests.codes.ok:
                    print('Success!')
                    return
    print('ID {} is not in the list of configurable IDs'.format(id))
    return


def load_gw_data(gw):
    try:
        with open(gw.filename) as f:
            gw_data = json.load(f)
            gw.info = gw_data
            gw.ip = gw_data['internalipaddress']
            gw.port = gw_data['internalport']
            gw.key = gw_data['apikey']
            gw.state_ok = True
        print('Saved gateway data and API key found.')
    except FileNotFoundError:
        print('No saved gateway data. Discover gateway and acquire an API key first.')


def error_gw_missing():
    print('Gateway information missing!')


gateway = Gateway()
load_gw_data(gateway)

while True:
    try:
        cmd = int(input('\nSelect action (0-7): '))
    except ValueError:
        print('Quitting')
        sys.exit()
    if cmd == 0:
        print('Send help')
    elif cmd == 1:
        gw_info = discover_gateway()
        gateway.info = gw_info
        gateway.ip = gw_info['internalipaddress']
        gateway.port = gw_info['internalport']
    elif cmd == 2:
        if gateway.info:
            gateway.key = get_api_key(gateway)
            save_gateway_info(gateway)
        else:
            error_gw_missing()
    elif cmd == 3:
        if gateway.state_ok:
            print(json.dumps(gateway.info, indent=2))
        else:
            error_gw_missing()
    elif cmd == 4:
        if gateway.state_ok:
            print(list_entities(gateway))
        else:
            error_gw_missing()
    elif cmd == 5:
        if gateway.state_ok:
            gateway.configurables = list_configurables(gateway)
        else:
            error_gw_missing()
    elif cmd == 6:
        if gateway.state_ok:
            gateway.configurables = list_configurables(gateway)
            modify_config(gateway)
        else:
            error_gw_missing()
    else:
        print('Quitting')
        sys.exit()
