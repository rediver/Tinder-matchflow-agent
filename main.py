from fastapi import FastAPI, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import argparse
from typing import Dict
from driver.connectors.tnd_conn import TinderConnector
from driver.driver import start_driver
import AI_logic.respond
import AI_logic.opener
import AI_logic.airtable
from dotenv import load_dotenv, find_dotenv
from importlib import reload
import os
import time as _time

_start_time = _time.time()
_stats = {'api_calls': 0, 'messages_sent': 0, 'last_action': None}


load_dotenv(find_dotenv(), override=True)
use_tindebielik = os.getenv('USE_TINDEBIELIK')

if use_tindebielik:
    import AI_logic.respond_tindebielik

app = FastAPI()

_static = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
app.mount('/static', StaticFiles(directory=_static), name='static')

@app.get('/ui')
def serve_ui():
    return FileResponse(os.path.join(_static, 'index.html'))

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)
parser = argparse.ArgumentParser()
parser.add_argument('-he', '--head', action='store_true',
                    help='selenium in head (non-headless) option')
args = parser.parse_args()


@app.get('/')
def check_driver_state():
    response = "Driver up and running" if dating_connector.driver else "Driver not running"
    return response


@app.get('/start_tnd')
def load_main_page_tnd():
    print("main page request arrived")
    global dating_connector
    dating_connector = tinder_connector
    dating_connector.load_main_page()
    _stats['api_calls'] += 1
    _stats['last_action'] = f'start_tnd ({_time.strftime("%H:%M:%S")})'
    return 200



@app.get('/respond/{chat_id}')
def respond_nr(chat_id: str = None):
    print("msgs request arrived")
    # if chat_id is a number — use position in list; otherwise treat as Tinder chat ID
    try:
        girl_nr = int(chat_id)
        messages = dating_connector.get_msgs(girl_nr)
    except (ValueError, TypeError):
        messages = dating_connector.get_msgs_by_id(chat_id)
    name_age = dating_connector.get_name_age()
    if not use_tindebielik:
        response = AI_logic.respond.respond_to_girl(name_age, messages)
    else:
        response = AI_logic.respond_tindebielik.respond_to_girl_tindebielik(name_age, messages)
    send_messages_endpoint(payload={'message': response})
    return 200


@app.get('/respond')
def respond():
    return respond_nr()

@app.get('/respond_all')
def respond_to_all():
    print("respond all request arrived")
    new_messages_nr = dating_connector.count_new_messages()
    for i in range(new_messages_nr):
        respond()
    return 200


def _process_unread(limit):
    """Background worker: click through unread conversations and respond."""
    print(f"Background: starting respond_new (limit={limit})")
    try:
        dating_connector.respond_to_unread(limit=limit)
    except Exception as e:
        print(f"Background error: {e}")
    print("Background: respond_new finished")


@app.get('/respond_new')
def respond_new(background_tasks: BackgroundTasks, limit: int = None):
    """Detect unread conversations via red dot and respond by clicking.
    Returns immediately. Optional ?limit=N.
    """
    print("respond_new request arrived")
    background_tasks.add_task(_process_unread, limit)
    return {"status": "processing in background"}


@app.get('/opener')
def write_opener():
    print("opener request arrived")
    name, bio = dating_connector.get_bio()
    message = AI_logic.opener.generate_opener(name, bio)
    send_messages_endpoint({'message': message})
    return 200


# function to send predefined nr of openers
@app.get('/batch_openers/{nr_openers}')
def write_openers(nr_openers: int = None):
    print("batch of openers request arrived")
    for i in range(nr_openers):
        name, bio = dating_connector.get_bio()
        message = AI_logic.opener.generate_opener(name, bio)
        send_messages_endpoint({'message': message})
    return 200


@app.get('/opener/{girl_nr}')
def write_opener(girl_nr: int = None):
    print("opener request arrived")
    name, bio = dating_connector.get_bio(girl_nr)
    message = AI_logic.opener.generate_opener(name, bio)
    send_messages_endpoint({'message': message})
    return 200


@app.get('/rise')
def rise_girls():
    print("Rise request arrived")
    dating_connector.rise_girls()
    return 200


@app.get('/clear_base')
def remove_expired():
    print("Clear base request arrived")
    AI_logic.airtable.remove_expired_girls()
    return 200


@app.post("/send_message")
def send_messages_endpoint(payload: Dict[str, str]):
    print("message request arrived")
    dating_connector.send_messages(payload['message'])
    _stats['messages_sent'] += 1
    _stats['last_action'] = f'message sent ({_time.strftime("%H:%M:%S")})'
    return 200


@app.get("/close")
def close_app():
    dating_connector.close_app()
    return 200


# use that endpoint to reload AI modules after providing changes on propmts or AI modules code
# without restarting whole application
@app.get('/prompts')
def get_prompts():
    """Return all editable prompt/context file contents."""
    base = os.path.join(os.path.dirname(__file__), 'AI_logic')
    files = {
        'opener':          ('prompts/opener.prompt',          'Opener'),
        'analyzer':        ('prompts/analyzer.prompt',        'Analyzer'),
        'commander_step1': ('prompts/commander_step1.prompt', 'Commander Step 1'),
        'commander_step2': ('prompts/commander_step2.prompt', 'Commander Step 2'),
        'writer':          ('prompts/writer.prompt',          'Writer'),
        'user_context':    ('user_context.txt',               'User Context'),
    }
    result = {}
    for key, (rel, label) in files.items():
        path = os.path.join(base, rel)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                result[key] = {'label': label, 'content': f.read(), 'path': rel}
        except FileNotFoundError:
            result[key] = {'label': label, 'content': '', 'path': rel}
    return result


@app.get('/pipeline')
def get_pipeline():
    path = os.path.join(os.path.dirname(__file__), 'AI_logic', 'pipeline_config.json')
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


@app.post('/pipeline')
def save_pipeline(payload: Dict[str, str]):
    path = os.path.join(os.path.dirname(__file__), 'AI_logic', 'pipeline_config.json')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(payload.get('content', ''))
    return {'saved': True}


@app.post('/prompts')
def save_prompt(payload: Dict[str, str]):
    """Save a prompt file. payload: {name, content}"""
    base = os.path.join(os.path.dirname(__file__), 'AI_logic')
    name_to_rel = {
        'opener':          'prompts/opener.prompt',
        'analyzer':        'prompts/analyzer.prompt',
        'commander_step1': 'prompts/commander_step1.prompt',
        'commander_step2': 'prompts/commander_step2.prompt',
        'writer':          'prompts/writer.prompt',
        'user_context':    'user_context.txt',
    }
    name = payload.get('name', '')
    content = payload.get('content', '')
    if name not in name_to_rel:
        return {'error': f'Unknown prompt: {name}'}
    path = os.path.join(base, name_to_rel[name])
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return {'saved': name}


@app.get('/pending')
def get_pending(n: int = 5):
    """Scan first n conversations. Returns those where last message is from Girl."""
    _stats['last_action'] = f'scan_pending(n={n}) ({_time.strftime("%H:%M:%S")})'
    results = dating_connector.scan_pending(n=n)
    return {'pending': results, 'scanned': n, 'found': len(results)}


@app.get('/stats')
def get_stats():
    """Return live app status — used by the Stats UI tab."""
    uptime = int(_time.time() - _start_time)
    h, r  = divmod(uptime, 3600)
    m, s  = divmod(r, 60)

    try:
        driver_ok = bool(dating_connector and dating_connector.driver)
        browser_url = dating_connector.driver.current_url if driver_ok else None
    except Exception:
        driver_ok, browser_url = False, None

    return {
        'driver':       'running' if driver_ok else 'stopped',
        'browser_url':  browser_url,
        'uptime':       f'{h:02d}:{m:02d}:{s:02d}',
        'uptime_s':     uptime,
        'api_calls':    _stats['api_calls'],
        'messages_sent': _stats['messages_sent'],
        'last_action':  _stats['last_action'],
        'model':        os.getenv('OPENAI_MODEL', 'gpt-5.4-mini'),
        'language':     os.getenv('USE_LANGUAGE', '?'),
        'city':         os.getenv('CITY', '?'),
    }


@app.get('/reload')
async def reload_modules():
    reload(AI_logic.respond)
    reload(AI_logic.opener)
    reload(AI_logic.airtable)

    return {"message": "Modules reloaded"}


if __name__ == '__main__':
    driver = start_driver(args.head)
    tinder_connector = TinderConnector(driver)
    #badoo_connector = BadooConnector(driver)
    #bumble_connector = BumbleConnector(driver)
    dating_connector = tinder_connector
    uvicorn.run(app, host='127.0.0.1', port=8080)
