from selenium import webdriver
from os import path
import subprocess


def _release_profile_lock(profile_path):
    """Kill any Firefox process holding the profile lock before starting."""
    lock_file = path.join(profile_path, '.parentlock')
    if path.exists(lock_file):
        try:
            result = subprocess.run(
                ['lsof', lock_file],
                capture_output=True, text=True
            )
            pids = [
                line.split()[1]
                for line in result.stdout.splitlines()[1:]
                if line.strip()
            ]
            for pid in set(pids):
                subprocess.run(['kill', pid], capture_output=True)
            if pids:
                print(f'Released Firefox profile lock (killed PIDs: {pids})')
        except Exception as e:
            print(f'Warning: could not release profile lock: {e}')


def start_driver(head):
    print('Starting driver')
    options = webdriver.FirefoxOptions()
    if not head:
        options.add_argument('--headless')
    script_path = path.dirname(path.abspath(__file__))
    profile_path = f'{script_path}/FirefoxProfile'
    _release_profile_lock(profile_path)
    options.add_argument('-profile')
    options.add_argument(profile_path)
    driver = webdriver.Firefox(options=options)
    driver.maximize_window()
    print('Driver activated')

    return driver