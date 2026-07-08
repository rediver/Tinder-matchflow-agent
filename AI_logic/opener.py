import os
import json
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from tenacity import retry, stop_after_attempt, wait_fixed
from dotenv import load_dotenv, find_dotenv


# API keys import
load_dotenv(find_dotenv(), override=True)
language = os.environ['USE_LANGUAGE']

current_dir = os.path.dirname(os.path.realpath(__file__))
with open(f'{current_dir}/user_context.txt', 'r', encoding='utf-8') as file:
    user_context = file.read()

with open(f'{current_dir}/prompts/opener.prompt', 'r') as file:
    prompt_template = file.read()

prompt = PromptTemplate.from_template(prompt_template)

llm = ChatOpenAI(model='gpt-5.4-mini', temperature=0.8)

chain = prompt | llm | StrOutputParser()

def log_retry(retry_state):
    print("Did not received response from OpenAI. Retrying request...")


@retry(stop=stop_after_attempt(3), wait=wait_fixed(90), before_sleep=log_retry)
def generate_opener(name, description):
    result = chain.invoke({
        'name': name,
        'description': description,
        'language': language,
        'user_context': user_context,
    })
    return [result.strip().strip('"\"')]
