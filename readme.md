<div align="center"><img src="/images/readme.gif" width="650" ></div>

# Tinder matchflow agent 
### Your automatic dating assistant 😎

TinderGPT automates the process of writing and arranging dates with girls on Tinder, enabling you to generate romantic meetings with almost zero effort. Your only role is to like the profiles that catch your eye. After that, TinderGPT comes into the play. It initiates a conversation with the girl, using details from her profile, continues by building an emotional bond and highlighting your attractive traits, and finishes by arranging a meeting and giving you a push-up on your phone with her number.


## How it works (with a wink 😏)
TinderGPT is your digital mate working a 24/7 shift and never having an "off day". You do exactly one thing — swipe right on the profiles you like. The dirty work (the actual talking) is handled by the machine. Under the hood it goes like this:

### 1. The hands — the browser (`driver/`)
Tinder has no friendly public API for us, so TinderGPT simply **pretends to be a human**. `TinderConnector` drives a real Firefox instance through Selenium: it clicks the *Messages* tab, watches for the **red dot** on unread conversations, opens a chat, reads the history and types replies.
To avoid looking like a bot that answers in 0.2 seconds, it takes random breaks — it "thinks about what to write" (`sleep 3–6 s`) and "taps on the keyboard" (`sleep 6–11 s`). Classic fake hesitation, just like before a first date.

### 2. The brain — the AI logic (`AI_logic/`)
This is where the magic happens. There are two main modes:

**🎣 Opener (`/opener`)**
The bot reads the girl's bio (About me, Interests, Essentials, and even her answers to Tinder prompts), sends it to GPT, and gets back a personalized pick-up line. No generic "hey, what's up?" — unless that's what you want.

**💬 Responding (`/respond`, `/respond_new`)**
This is the interesting part. A reply isn't produced in a single shot, but by a **three-person crisis team** (three separate model calls):
1. **Analyzer** — the psychologist. Reads the conversation and decides which stage we're at:
   - **Stage 1 (building rapport):** learn a few facts about her, build the "image of an unavailable guy" once, and tell one fun story.
   - **Stage 2 (closing the deal):** propose a meeting, build comfort, and extract a phone number / contact.
2. **Commander** — the strategist. Based on the stage, it decides what the next message should be about and picks *tags* (e.g. "Bond", "Storytelling", "Suggesting meeting"). Each tag pulls matching pick-up rules from the knowledge base (`rule_base/rules_db.sqlite`).
3. **Writer** — the copywriter. Takes the strategy, the rules, your context (`user_context.txt`), personality, city and language, and writes the final message. It also applies **mirroring** — if she writes briefly, so does it; if she rambles, it replies longer. And it deliberately sends **only one message** at a time (to avoid awkward double-texting).

### 3. Memory (Airtable)
The bot has no "dating amnesia". After each conversation it stores a summary of what it already knows about a given person in Airtable, so next time it continues the thread instead of asking the same thing twice. Bonus: the memory is shared across devices.

### 4. Happy end 🎉
When the Analyzer detects that the girl shared a contact (phone, Insta, whatever), TinderGPT **ends the conversation** and sends you a **phone notification via Pushbullet** saying something like *"I planned a date with {name}"*. It also marks that person as `not_to_rise` so it won't message them again. Your turn now, human.

### 5. Autopilot (`scheduler.py`)
On a Raspberry Pi you can run the scheduler, which every day at **random times** (within defined time windows) fires the sessions itself: open Tinder → reply to everyone → send openers → "rise" old conversations → close. The randomness is there so it doesn't look like a machine acting to the exact second.

### Bonus: control panel
There's also a web panel (`/ui`) where you can watch live stats (uptime, messages sent, model, last action) and **edit the prompts and pipeline without restarting the app** (`/reload`).


## Installation
While for a regular (production hehe) use it's recommended to use Raspberry Pi, or any other computer that you can leave turned on day and night, I suggest to try application first on your PC. PC installation process is simplier and doesn't requeres having Raspberry Pi, while allow you to test application and decide if you want to use it further.

### PC Installation

1. Clone repository 
2. Go to repository `cd Tinder-matchflow-agent`
3. Create virtual envinronment with `python -m venv env`
4. Activate envinronment with `env\Scripts\activate` on Windows or `source env/bin/activate` on Linux
5. Install dependencies `pip install -r requirements.txt`
6. Create new Firefox profile for application: 
In your Firefox browser (install Firefox if you have no) write `about:profiles` in the search field. The profile management page will open. Click "Create new profile". Proceed on profile creation window. Write name of your profile and choose profile folder to <path>/TinderGPT/driver/FirefoxProfile. Careful here - if you change profile name after choosing profile directory, it'll change you profile directory as well; so write profile name first and after it choose profile directory.
![Firefox profile creation](images/Profile_creation.png)
After profile is created, set up your old profile default again (it sets created profile default by default) an click "Launch profile in the new browser" under newly created profile.
7. Login to tinder. In opened window proceed to tinder.com and login to your account. Here will appear few windows asking about permission to localisation, enebling some features, ask about buying tinder gold. Close all that windows manually as TinderGPT will not manage it by it's own. Check out "messages" tab also and close windows that will appear here.
8. Change name of `.env.template` file to `.env` and open it with text editor.
9. Here we need to fullfil provided fields. After "Language" provide your language (language TinderGPT will write in) without any parenthesis. For example, in my case it looks like: `LANGUAGE=Polish`. Also provide city you living in after "City".
10. Provede your OpenAI API key from OpenAI website.
11. Airtable:
Now we need to set up Airtable to TinderGPT be available remember informations about girls. Additional plus of Airtable is that memory will be common for diifferent devices if you'll use TInderGPT on more than one computer. Go to airtable.com and create account if you have no. Go to Yor profile icon -> "Developer Hub" -> "Personal access token" and create new token. Write some name, under the "scopes" choose all possible options. Under the scope choose "All current and future bases in all current and future workspaces". Paste it to .env file after "AIRTABLE_TOKEN=".
After to to main page -> "All workspaces" -> click on "My first workspace". When you entered workspace, at the adress bar of your browser you'll find workspace id as shown on the image. IMPORTANT: Question mark at the end is not part of the workspace id.
![Airtable workspace](images/Airtable_workspace.png)
Paste provided id after "AIRTABLE_WORKSPACE_ID=" on `.env` file.

12. Now you set up! 

### PC usage

1. Open TinderGPT folder in terminal. Activate envinronment as in step for of installation.
2. Start TinderGPT using `python main.py --head`. `--head` argument means we are starting it in head mode (non-headless) to see on our screen how it perform.
3. After TinderGPT browser window will appear, on your old browser window paste `localhost:8080/start_tnd` to open tinder. Wait until you get response "200" in browser, it will take a while. Do not send next requests until you get response for a preious.
5. Use `localhost:8080/opener` to TinderGPT send opening message to last matched girl.
6. When girl respond, run 'localhost:8080/respond'. TinderGPT will open first unreaded message and will continue conversation. Advanced: You can use `localhost:8080/respond/<girl_nr>`, where instead of <girl_nr> provide nr 1-8 of girl from conversations list. Useful where you accasionally clicked on girl that responded you and unreaded message sign dissapeared.
7. Play around the app! When you get known with it, deploy it on raspberry for fully authomatic usage.




## Configuration
Beyond the installation steps, TinderGPT is tuned through a few files. Nothing here needs a code change unless noted.

### `.env` variables
| Variable | Required | Description |
| --- | --- | --- |
| `USE_LANGUAGE` | yes | Language the bot writes in, e.g. `USE_LANGUAGE=Polish` (no parentheses). |
| `CITY` | yes | Your city — used by the Writer when suggesting where to meet. |
| `PERSONALITY` | no | Free-text personality/tone injected into every Writer call. |
| `OPENAI_API_KEY` | yes | Your OpenAI API key. |
| `AIRTABLE_TOKEN` | yes | Airtable personal access token (used as the "memory" backend). |
| `AIRTABLE_WORKSPACE_ID` | yes | Airtable workspace id where the base is created. |
| `AIRTABLE_BASE_ID` | auto | Created automatically on first run and appended to `.env`. |
| `AIRTABLE_TABLE_ID` | auto | Created automatically on first run and appended to `.env`. |
| `PUSHBULLET_API_KEY` | no | Enables phone notifications when a contact is obtained. Leave empty to disable. |
| `NOTIFICATIONS_HOOK` | no | Optional webhook URL; a GET is fired with `name_age` and `contact` params when a date is planned. |
| `USE_TINDEBIELIK` | no | Set to use the experimental TindeBielik fine-tuned model path instead of the default OpenAI Writer. |

> Note: the actual OpenAI model is currently hardcoded to `gpt-5.4-mini` in `AI_logic/opener.py` and `AI_logic/respond.py`. The `OPENAI_MODEL` value is only shown in the `/stats` panel — to change the model, edit those files.

### Pipeline tuning (`AI_logic/pipeline_config.json`)
Adjust behavior without touching code:
- `responder.step1_conditions` — how many facts / tools / stories are required before moving from Stage 1 to Stage 2.
- `responder.custom_tags` — add your own tags (each needs a matching rule in `rules_db.sqlite`).
- `responder.pre_writer_instructions` — extra instructions injected into every Writer call (globally or per stage).
- `opener.pre_send_filter` / `opener.custom_instructions` — strip patterns / cap length / append instructions for openers.
- `global.response_delay_seconds` — the human-like "thinking" and "typing" delays.

### Prompts, context and rules
- `AI_logic/prompts/*.prompt` — the Opener, Analyzer, Commander (step 1/2) and Writer prompts.
- `AI_logic/user_context.txt` — facts about you, injected into the Opener and Writer.
- `AI_logic/rule_base/rules_db.sqlite` — pick-up rules keyed by tag.

All of the above can be edited live from the web panel (`/ui`, Prompts tab) or via the `/prompts` and `/pipeline` endpoints. After editing, hit `localhost:8080/reload` to apply changes without restarting the app.


## AI dating good practices
When going to date organized by TinderGPT, I recommend you to tell your match, that it was picked up by artificial intellegence. Beyond the fun value of the situation, it's a good practice to inform users that they are speaking with a bot.


## Contribution



While improving prompts, pick-up rules knowledge base or scripts in AI_logic folder, use `localhost:8080/reload` to reload changes immidiatelly without restarting whole the application (which is time-consuming).