from dotenv import load_dotenv, find_dotenv
import os
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser


load_dotenv(find_dotenv(), override=True)
language = os.environ['USE_LANGUAGE']


def translate_rise_msg(message):
    prompt = ("Translate message to {language}, leave same style and emoticons. Message is directed to woman."
              "\n\nMessage: {message}")
    prompt = PromptTemplate.from_template(prompt)
    llm = ChatOpenAI(model='gpt-5.4-mini', temperature=0.5)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({'message': message, 'language': language})

