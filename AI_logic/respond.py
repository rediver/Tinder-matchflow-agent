import os
import json
import requests
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from AI_logic.rule_base.rules_db_conn import query_rule
from AI_logic.airtable import get_record, upsert_record
from dotenv import load_dotenv, find_dotenv
from pushbullet import Pushbullet
from tenacity import retry, stop_after_attempt, wait_fixed
from pydantic import BaseModel, Field

# api keys import
load_dotenv(find_dotenv(), override=True)
language = os.environ['USE_LANGUAGE']
city = os.environ['CITY']
personality = os.getenv('PERSONALITY')
notifications_hook = os.getenv('NOTIFICATIONS_HOOK')

current_dir = os.path.dirname(os.path.realpath(__file__))
# load user context
with open(f'{current_dir}/user_context.txt', 'r', encoding='utf-8') as file:
    user_context = file.read()

# import prompt files
with open(f'{current_dir}/prompts/analyzer.prompt', 'r') as file:
    prompt_template = file.read()
analyzer_prompt = PromptTemplate.from_template(prompt_template)

with open(f'{current_dir}/prompts/commander_step1.prompt', 'r') as file:
    prompt_template = file.read()
commander_step1_prompt = PromptTemplate.from_template(prompt_template)

with open(f'{current_dir}/prompts/commander_step2.prompt', 'r') as file:
    prompt_template = file.read()
commander_step2_prompt = PromptTemplate.from_template(prompt_template)

with open(f'{current_dir}/prompts/writer.prompt', 'r') as file:
    prompt_template = file.read()
writer_prompt = PromptTemplate.from_template(prompt_template)

pushbullet_key = os.getenv('PUSHBULLET_API_KEY')
if pushbullet_key:
    pushbullet = Pushbullet(pushbullet_key)


class AnalyzerOutput(BaseModel):
    summary: str = Field(
        ...,
        description='If in step 1, it should look like: "We are on step 1.\n'
                    'Bond. Important information I know about her (x/3): some info, another info ... .\n'
                    'Image of unavailable guy (x/1): tools used and context.\n'
                    'Fun stries (x/1): what stories Conversator have told.".'
                    'If in step 2, it should look like: "We are on step 2.\n'
                    'Provide here informations about if non-obligatory meeting was proposed, if she was asked '
                    'about number, if comfort was built etc. and some context around that informations."'
                         )
    future_step: str = Field(
        ...,
        description='"step1" if we are currently in step 1 and not all the conditions of that step are completed, '
                    '"step2" if we are currently in step 1 and all the conditions are completed (at least 3 info known,'
                    '1 unavailability tool used, 1 fun story told), "step2" if we are currently in step 2.'
    )
    contact: str = Field(
        ...,
        description='type of contact and contact itself if it was provided by her in last messages. '
                    'For example, "Phone 123456789", "Facebook Name Surname", "Instagram insta_nick". '
                    'If no contact were provided, just leave that field blank.'
    )


class CommanderStep1Output(BaseModel):
    reasoning: str = Field(..., description='Step-by-step reasoning about what abous should be next message and why in 2 sentenses.')
    tags: list = Field(..., description='Choose tags among "Bond", "Attractive guy image", "Storytelling". Make sure you are writing only the tags directly related to your suggestion. Write tags in the array like ["tag1", "tag2"], even if you proposing single tag.')


class CommanderStep2Output(BaseModel):
    reasoning: str = Field(..., description='Step-by-step reasoning about what abous should be next message and why in 2 sentenses.')
    tags: list = Field(..., description='Choose tags among "Suggesting meeting", "Comfort", "Providing meeting details", "Ask for contact". Make sure you are writing only the tags directly related to your suggestion. Write tags in the array like ["tag1", "tag2"], even if you proposing single tag.')


Analyzer = ChatOpenAI(model='gpt-5.4-mini', temperature=0)
Commander = ChatOpenAI(model='gpt-5.4-mini', temperature=0.4)
Writer = ChatOpenAI(model='gpt-5.4-mini', temperature=0.7)

analyzer_chain = analyzer_prompt | Analyzer.with_structured_output(AnalyzerOutput)
writer_chain = writer_prompt | Writer | StrOutputParser()


def commander_chain(future_step):
    if future_step == 'step1':
        return commander_step1_prompt | Commander.with_structured_output(CommanderStep1Output)
    else:
        return commander_step2_prompt | Commander.with_structured_output(CommanderStep2Output)


# retry decorator to retry if openai request didn't return
@retry(stop=stop_after_attempt(3), wait=wait_fixed(90))
def invoke_chain(chain, args, module_name=None):
    try:
        output = chain.invoke(args)
        output = json.loads(output)
        print(f'\n{module_name} says:')
        print(json.dumps(output, indent=4, ensure_ascii=False))
        return output
    except Exception as e:
        print(f"Error encountered: \n{str(e)}]n{str(e.args)}\nRetrying...")
        raise e


@retry(stop=stop_after_attempt(3), wait=wait_fixed(90))
def invoke_stuctured_runnable(chain, args, module_name=None):
    try:
        output = chain.invoke(args)
        print(f'\n{module_name} says:')
        print(output)
        return output
    except Exception as e:
        print(f"Error encountered: \n{str(e)}]n{str(e.args)}\nRetrying...")
        raise e


def _mirroring_stats(messages: str) -> dict:
    """Extract last Girl message length for mirroring guidance."""
    lines = [l for l in messages.strip().split('\n') if l.strip()]
    girl_lines = [l[5:].strip() for l in lines if l.startswith('Girl:')]
    if not girl_lines:
        return {'words': 15, 'chars': 80, 'guidance': 'medium (15 words)'}
    last = girl_lines[-1]
    words = len(last.split())
    chars = len(last)
    if words <= 5:
        guidance = f'very short ({words} words) — reply in 1-6 words, ultra-brief'
    elif words <= 15:
        guidance = f'short ({words} words) — reply in 5-15 words'
    elif words <= 35:
        guidance = f'medium ({words} words) — reply in 15-35 words'
    else:
        guidance = f'long ({words} words) — reply in 25-50 words max'
    return {'words': words, 'chars': chars, 'guidance': guidance}


def respond_to_girl(name_age, messages):
    previous_summary = get_record(name_age)
    analyzer_output = invoke_stuctured_runnable(
        analyzer_chain,
        {'summary': previous_summary, 'messages': messages},
        'Analyzer'
    )

    future_step = analyzer_output.future_step
    summary = analyzer_output.summary
    contact = analyzer_output.contact

    if contact:
        if notifications_hook:
            requests.get(notifications_hook, params={'name_age': name_age, 'contact': contact})
        pushbullet.push_note(f"I planned date with {name_age}", contact)
        upsert_record(name_age, not_to_rise=True)
        return

    commander_output = invoke_stuctured_runnable(
        commander_chain(future_step),
        {'summary': summary, 'messages': messages},
        'Commander'
    )
    tags = commander_output.tags
    rules = "\n###\n- ".join([query_rule(tag) for tag in tags])

    mirror = _mirroring_stats(messages)
    print(f'Mirroring: {mirror["guidance"]}')

    writer_output = invoke_chain(writer_chain, {
        'rules': rules,
        'messages': messages,
        'summary': summary,
        'language': language,
        'city': city,
        'personality': personality,
        'user_context': user_context,
        'commander_tags': str(tags),
        'commander_reasoning': commander_output.reasoning,
        'mirror_guidance': mirror['guidance'],
    }, 'Writer')

    print("writer_output: ")
    print(writer_output)
    # safety net: never send more than 1 message (prevents double-texting)
    messages_to_send = writer_output["messages"][:1]
    # update summary in case of attractive guy image or storytelling
    if 'Attractive guy image' in tags or 'Storytelling' in tags:
        analyzer2_output = invoke_stuctured_runnable(
            analyzer_chain,
            {'summary': summary, 'messages': f'Conversator: {messages_to_send}'}, 'Analyzer'
        )
        summary = analyzer2_output.summary

    upsert_record(name_age, summary)
    return messages_to_send
