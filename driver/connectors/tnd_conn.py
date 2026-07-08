from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as ExpCon
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from AI_logic.airtable import girls_to_rise, upsert_record
from AI_logic.misc import translate_rise_msg
import time
import random
import os
import sys


class TinderConnector():
    def __init__(self, driver):
        self.driver = driver
        # xpathes
        self.message_tab_xpath = "//button[normalize-space(text())='Messages']"
        self.match_tab_xpath = "//button[normalize-space(text())='Matches']"
        # red dot = Sq(14px) circle with brand background color
        self.new_msg_flag_xpath = (
            "//a[contains(@href,'/app/messages/') and @aria-label"
            " and not(contains(@aria-label,'Start chat'))"
            " and .//*[contains(@class,'background-brand') and contains(@class,'Bdrs(50%')]]"
        )
        self.icons_xpath = "//a[contains(@aria-label,'Start chat')]"
        self.messages_xpath = "//span[contains(@class,'text D(ib)')]"
        self.written_girl_bio_xpath = "//textarea[@placeholder='Type a message']"
        self.unwritten_girl_full_bio_xpath = "//h2[normalize-space(text())='Essentials']/ancestor::section[1]"
        self.unwritten_girl_short_bio_xpath = "//h2[normalize-space(text())='Essentials']/ancestor::section[1]"
        self.written_girl_name_age_xpath = "//h1[contains(@class,'display-1-strong')]"
        self.main_page_element_for_wait = "//button[normalize-space(text())='Messages']"
        self.text_area_xpath = "//textarea[@placeholder='Type a message']"
        self.return_to_main_page_xpath = "//a[normalize-space(text())='Back']"
        self.name_xpath = "//h1[contains(@class,'display-1-strong')]"
        self.close_tnd_gold_enforser_xpath = "/html[1]/body[1]/div[2]/main[1]/div[1]/div[1]/div[3]/button[2]/span[1]"
        self.not_opened_girls_css_selector = r'ul > li.P\(8px\)'

        current_dir = os.path.dirname(os.path.realpath(__file__))
        self.project_dir = os.path.dirname(os.path.dirname(current_dir))

        self.translate_rise_msg_if_needed()

    def load_main_page(self):
        self.driver.get("https://tinder.com")
        print('Waiting for the main page to load')
        try:
            Wait(self.driver, 120).until(
                ExpCon.presence_of_element_located((By.XPATH, self.main_page_element_for_wait)))
        except TimeoutException:
            time.sleep(random.uniform(0, 10))
        # wait for loading screen overlay to clear
        try:
            Wait(self.driver, 20).until(
                ExpCon.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
        except TimeoutException:
            pass

        # delay to let gold enforser to appear
        time.sleep(random.uniform(2, 3))
        if self.driver.find_elements('xpath', self.close_tnd_gold_enforser_xpath):
            self.driver.find_element('xpath', self.close_tnd_gold_enforser_xpath).click()
            print('Tinder gold enforcer closed')


    def close_app(self):
        print('Closing Tinder')
        self.driver.get("about:blank")

    def send_messages(self, messages):
        text_field = self.driver.find_element('xpath', self.text_area_xpath)
        for message in messages:
            print('Thinking about what to write...')
            time.sleep(random.uniform(3, 6))
            text_field.send_keys(message)
            print('Typing...')
            time.sleep(random.uniform(6, 11))
            text_field.send_keys(Keys.RETURN)
        print('Messages sent')
        time.sleep(random.uniform(1, 4))
        # return to main page
        self.driver.get('https://tinder.com/app/matches')
        time.sleep(random.uniform(1, 3))

    # girl_nr is number of girl from the top of the list of message history
    def get_msgs(self, girl_nr=None):
        self.enter_messages(girl_nr)
        messages = self.driver.find_elements('xpath', self.messages_xpath)
        print('messages found')
        messages = messages[-20:]  # last 20 for better context
        return align_messages(messages)

    def get_msgs_by_id(self, chat_id: str):
        """Navigate directly to a chat by Tinder chat ID (hex string from URL)."""
        print(f'navigating directly to chat {chat_id}')
        self.driver.get(f'https://tinder.com/app/messages/{chat_id}')
        try:
            Wait(self.driver, 20).until(
                ExpCon.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
        except TimeoutException:
            pass
        Wait(self.driver, 60).until(
            ExpCon.presence_of_element_located((By.XPATH, self.written_girl_bio_xpath)))
        print('message history entered by ID')
        time.sleep(random.uniform(1.5, 3))
        messages = self.driver.find_elements('xpath', self.messages_xpath)
        print('messages found')
        return align_messages(messages[-20:])

    def enter_messages(self, girl_nr=None):
        print('trying to get messages')
        # navigate to matches page and click Messages tab — most reliable path
        self.driver.get('https://tinder.com/app/matches')
        Wait(self.driver, 60).until(
            ExpCon.presence_of_element_located((By.XPATH, self.message_tab_xpath)))
        # wait for loading screen overlay to disappear before clicking
        try:
            Wait(self.driver, 15).until(
                ExpCon.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
        except TimeoutException:
            pass
        self.driver.find_element('xpath', self.message_tab_xpath).click()
        # wait for conversation links to appear
        Wait(self.driver, 30).until(
            ExpCon.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'/app/messages/') and @aria-label]")))
        time.sleep(random.uniform(1, 1.5))
        if girl_nr:
            # Messages tab conversations: aria-label = name only (no 'Start chat')
            numbered_girl_xpath = (
                f"(//a[contains(@href,'/app/messages/') and @aria-label"
                f" and not(contains(@aria-label,'Start chat'))])[{girl_nr}]"
            )
            self.driver.find_element('xpath', numbered_girl_xpath).click()
        else:
            self.driver.find_element('xpath', self.new_msg_flag_xpath).click()

        # waiting for chat to load
        Wait(self.driver, 30).until(ExpCon.presence_of_element_located((By.XPATH, self.written_girl_bio_xpath)))
        print('message history entered')
        time.sleep(random.uniform(1.5, 4))

    def respond_to_unread(self, limit=None):
        """Navigate to messages list, click each unread (red dot) conversation,
        read messages, call AI, send response, return to list, repeat."""
        import AI_logic.respond
        from AI_logic.airtable import get_record, upsert_record

        processed = 0
        max_rounds = limit or 20

        for _ in range(max_rounds):
            # navigate to messages list each iteration (fresh elements)
            self.driver.get('https://tinder.com/app/matches')
            Wait(self.driver, 60).until(
                ExpCon.presence_of_element_located((By.XPATH, self.message_tab_xpath)))
            try:
                Wait(self.driver, 15).until(
                    ExpCon.invisibility_of_element_located(
                        (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
            except TimeoutException:
                pass
            self.driver.find_element('xpath', self.message_tab_xpath).click()
            Wait(self.driver, 30).until(
                ExpCon.presence_of_element_located(
                    (By.XPATH, "//a[contains(@href,'/app/messages/') and @aria-label]")))
            time.sleep(random.uniform(1, 1.5))

            # find first unread conversation (red dot)
            unread = self.driver.find_elements('xpath', self.new_msg_flag_xpath)
            if not unread:
                print('No more unread conversations found')
                break

            print(f'Clicking unread conversation ({processed + 1})')
            unread[0].click()

            # wait for chat to load
            try:
                Wait(self.driver, 15).until(
                    ExpCon.invisibility_of_element_located(
                        (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
            except TimeoutException:
                pass
            Wait(self.driver, 30).until(
                ExpCon.presence_of_element_located((By.XPATH, self.written_girl_bio_xpath)))
            print('message history entered')
            time.sleep(random.uniform(1.5, 3))

            # read messages and name
            messages_els = self.driver.find_elements('xpath', self.messages_xpath)
            messages = align_messages(messages_els[-20:])
            name_age = self.get_name_age()
            print(f'Responding to {name_age}')

            # call AI
            try:
                response = AI_logic.respond.respond_to_girl(name_age, messages)
                if response:
                    self.send_messages(response)
            except Exception as e:
                print(f'AI error for {name_age}: {e}')
                # return to list even on error
                self.driver.get('https://tinder.com/app/matches')

            processed += 1
            print(f'Done {processed} conversations')

        print(f'respond_to_unread finished: {processed} processed')
        return processed

    def get_unread_conversations(self, max_convos=20):
        """Returns list of chat IDs that have unread messages (first max_convos checked)."""
        self.driver.get('https://tinder.com/app/matches')
        Wait(self.driver, 60).until(
            ExpCon.presence_of_element_located((By.XPATH, self.message_tab_xpath)))
        try:
            Wait(self.driver, 15).until(
                ExpCon.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
        except TimeoutException:
            pass
        self.driver.find_element('xpath', self.message_tab_xpath).click()
        Wait(self.driver, 30).until(
            ExpCon.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'/app/messages/') and @aria-label]")))
        time.sleep(random.uniform(1.5, 2.5))

        # find unread conversations using badge selector in one query
        unread_links = self.driver.find_elements(
            'xpath', self.new_msg_flag_xpath
        )[:max_convos]

        # diagnostic: also count all conversations visible
        all_convos = self.driver.find_elements(
            'xpath',
            "//a[contains(@href,'/app/messages/') and @aria-label"
            " and not(contains(@aria-label,'Start chat'))]"
        )
        print(f'Total conversations visible: {len(all_convos)}')
        print(f'Unread (badge) found: {len(unread_links)}')

        # if badge selector found nothing, dump badge candidates for debugging
        if not unread_links:
            badges = self.driver.find_elements(
                By.CSS_SELECTOR, '[class*="badge"]')
            print(f'Badge elements on page: {len(badges)}')
            for b in badges[:5]:
                print(f'  badge class: {(b.get_attribute("class") or "")[:80]}')

        unread_ids = []
        for link in unread_links:
            href = link.get_attribute('href') or ''
            chat_id = href.split('/app/messages/')[-1]
            if chat_id:
                unread_ids.append(chat_id)
        print(f'Unread chat IDs: {unread_ids}')
        return unread_ids

    # ── helpers shared by scan methods ────────────────────────
    def _open_messages_list(self):
        """Navigate to /app/matches and click the Messages tab."""
        self.driver.get('https://tinder.com/app/matches')
        Wait(self.driver, 60).until(
            ExpCon.presence_of_element_located((By.XPATH, self.message_tab_xpath)))
        try:
            Wait(self.driver, 15).until(
                ExpCon.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
        except TimeoutException:
            pass
        self.driver.find_element('xpath', self.message_tab_xpath).click()
        Wait(self.driver, 30).until(
            ExpCon.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'/app/messages/') and @aria-label]")))
        time.sleep(random.uniform(1, 1.5))

    def _click_conversation(self, position: int):
        """Click the Nth conversation (1-indexed) in the Messages list."""
        xpath = (
            f"(//a[contains(@href,'/app/messages/') and @aria-label"
            f" and not(contains(@aria-label,'Start chat'))])[{position}]"
        )
        self.driver.find_element('xpath', xpath).click()
        try:
            Wait(self.driver, 15).until(
                ExpCon.invisibility_of_element_located(
                    (By.CSS_SELECTOR, '[class*="loadingScreen"]')))
        except TimeoutException:
            pass
        Wait(self.driver, 25).until(
            ExpCon.presence_of_element_located((By.XPATH, self.written_girl_bio_xpath)))
        time.sleep(random.uniform(0.8, 1.5))

    def scan_pending(self, n: int = 5):
        """Scan first n conversations. Return list of those where last message is from Girl.
        Each result: {position, name, last_message, preview_messages}
        """
        results = []
        self._open_messages_list()

        for pos in range(1, n + 1):
            try:
                print(f'Scanning conversation {pos}/{n}')
                self._click_conversation(pos)

                # read last 8 messages
                els = self.driver.find_elements('xpath', self.messages_xpath)
                raw = align_messages(els[-8:] if len(els) >= 8 else els)
                name = self.get_name_age()

                # check if last non-empty line is from Girl
                lines = [l for l in raw.strip().split('\n') if l.strip()]
                if lines and lines[-1].startswith('Girl:'):
                    last_msg = lines[-1][5:].strip()
                    results.append({
                        'position':         pos,
                        'name':             name,
                        'last_message':     last_msg,
                        'preview':          raw.strip(),
                    })
                    print(f'  → pending: {name} | {last_msg[:60]}')
                else:
                    print(f'  → ok (last msg is yours or empty): {name}')

            except Exception as e:
                print(f'  → error at position {pos}: {e}')

            # back to list for next iteration
            if pos < n:
                self._open_messages_list()

        print(f'scan_pending done: {len(results)} pending out of {n} scanned')
        return results

    def count_new_messages(self):
        self.driver.get('https://tinder.com/app/matches')
        Wait(self.driver, 60).until(
            ExpCon.presence_of_element_located((By.XPATH, self.message_tab_xpath)))
        self.driver.find_element('xpath', self.message_tab_xpath).click()
        Wait(self.driver, 30).until(
            ExpCon.presence_of_element_located(
                (By.XPATH, "//a[contains(@href,'/app/messages/') and @aria-label]")))
        time.sleep(random.uniform(1, 2))
        return len(self.driver.find_elements('xpath', self.new_msg_flag_xpath))

    def count_not_opened_girls(self):
        self.driver.find_element('xpath', self.match_tab_xpath).click()
        time.sleep(random.uniform(2, 4))

        number_of_girls = self.driver.find_elements(By.CSS_SELECTOR, self.not_opened_girls_css_selector)
        number_of_girls = len(number_of_girls) - 2

        return number_of_girls

    # gets name_age from opened written girl
    def get_name_age(self):
        name_age = self.driver.find_element('xpath', self.written_girl_name_age_xpath).text
        print(f'Got name_age: {name_age}')
        return name_age

    def get_bio(self, girl_nr=0):
        print('get bio function')
        self.driver.get('https://tinder.com/app/matches')
        Wait(self.driver, 30).until(
            ExpCon.presence_of_element_located((By.XPATH, self.match_tab_xpath)))
        time.sleep(random.uniform(2, 3))
        # filter out /app/recs links — those are special matches that don't open a chat modal
        all_icons = self.driver.find_elements('xpath', self.icons_xpath)
        icons = [i for i in all_icons
                 if '/app/messages/' in (i.get_attribute('href') or '')]
        print(f'Match icons with chat thread: {len(icons)}')
        if not icons:
            print('No girls to start a conversation with')
            return
        icons[girl_nr].click()
        time.sleep(3)
        Wait(self.driver, 45).until(ExpCon.presence_of_element_located((By.XPATH, self.name_xpath)))
        name = self.driver.find_element('xpath', self.name_xpath).text
        # collect profile sections: About me, Interests, Essentials, custom prompts
        bio_parts = []
        priority_sections = ['About me', 'O mnie', 'Interests', 'Zainteresowania']
        other_sections = ['Essentials', 'Lifestyle', 'Basics']
        # grab sections by their h2 heading
        for heading in priority_sections + other_sections:
            try:
                section = self.driver.find_element(
                    'xpath',
                    f"//h2[normalize-space(text())='{heading}']/ancestor::section[1]"
                )
                text = section.text.strip()
                if text and len(text) > 5:
                    bio_parts.append(text)
            except NoSuchElementException:
                pass
        # also grab custom Tinder prompt answers (h2 + sibling content)
        try:
            custom_h2s = self.driver.find_elements(
                'xpath',
                "//h2[contains(@class,'Mstart') and not(contains(text(),'About')) "
                "and not(contains(text(),'Interest')) and not(contains(text(),'Essential')) "
                "and not(contains(text(),'Lifestyle')) and not(contains(text(),'Basic')) "
                "and not(contains(text(),'Looking')) and not(contains(text(),'Reply')) "
                "and not(contains(text(),'conversation'))]"
            )
            for h2 in custom_h2s[:3]:  # max 3 custom prompts
                q = h2.text.strip()
                try:
                    ans_el = h2.find_element('xpath', 'following-sibling::*[1]')
                    ans = ans_el.text.strip()
                    if q and ans and len(ans) > 3:
                        bio_parts.append(f"{q}\n{ans}")
                except NoSuchElementException:
                    pass
        except Exception:
            pass
        bio = '\n\n'.join(bio_parts) if bio_parts else ''
        # fallback
        if not bio:
            try:
                bio = self.driver.find_element('xpath', self.unwritten_girl_full_bio_xpath).text
            except NoSuchElementException:
                bio = ''

        return name, bio

    def rise_girls(self):
        # open message tab
        self.driver.find_element('xpath', self.message_tab_xpath).click()
        time.sleep(random.uniform(1, 1.5))

        self.translate_rise_msg_if_needed()
        with open(f'{self.project_dir}/AI_logic/cached_messages/rise_msg.txt', 'r', encoding='utf-8') as file:
            rise_msg = file.read()
            print(rise_msg)

        to_rise = girls_to_rise()
        for girl_nr in range(11, 20):
            print(girl_nr)
            self.enter_messages(girl_nr)
            name_age = self.get_name_age()

            if name_age in to_rise:
                print(f'Rising {name_age}')
                self.send_messages([rise_msg])
                upsert_record(name_age, not_to_rise=True)
                time.sleep(random.uniform(1, 2))

        print("All girls rised")

    def translate_rise_msg_if_needed(self):
        if not os.path.isfile(f'{self.project_dir}/AI_logic/cached_messages/rise_msg.txt'):
            with open(f'{self.project_dir}/AI_logic/cached_messages/rise_msg_orig.txt', 'r', encoding='utf-8') as file:
                orig_rise_msg = file.read()
            rise_msg = translate_rise_msg(orig_rise_msg)
            with open(f'{self.project_dir}/AI_logic/cached_messages/rise_msg.txt', 'w', encoding='utf-8') as file:
                file.write(rise_msg)

# misc functions
def align_messages(messages):
    your_color = 'rgb(255, 255, 255)'
    her_color = 'rgb(36, 38, 42)'
    message_prompt = ''
    for message in messages:
        if message.value_of_css_property('color') == your_color:
            message_prompt += 'You: ' + message.text + '\n'
        elif message.value_of_css_property('color') == her_color:
            message_prompt += 'Girl: ' + message.text + '\n'

    return message_prompt
