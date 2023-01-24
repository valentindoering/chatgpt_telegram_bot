import yaml
import os
import openai
import math
import requests
from urllib.parse import quote
import pprint
import time

config = yaml.load(open('config.yml'), Loader=yaml.FullLoader)

openai.organization = config['chat_gpt']['organization']
openai.api_key = config['chat_gpt']['api_key']
# print(openai.Model.list())

def ask_chat_gpt(question):
    answer = openai.Completion.create(
        model=config['chat_gpt']['model'],
        prompt=question,
        max_tokens=int(config['chat_gpt']['max_tokens_per_request']),
        temperature=0
    )
    text = answer['choices'][0]['text']
    return text

def telegram_fetch(message: str) -> bool:
    message = str(message)

    # updates and chatId https://api.telegram.org/bot<YourBOTToken>/getUpdates
    # For \n use %0A message = message.replace(/\n/g, "%0A")
    url = (
        "https://api.telegram.org/bot"
        + config["telegram"]["bot_key"]
        + "/sendMessage?chat_id="
        + config["telegram"]["chat_id"]
        + "&text="
        + quote(message)
    )

    try:
        response = (requests.get(url)).json()
        return response["ok"]
    except:
        return False

def send_telegram(message: str) -> None:
    packages_remaining = [message]
    max_messages_num = 40
    while len(packages_remaining) > 0 and max_messages_num > 0:
        curr_package = packages_remaining.pop(0)
        message_sent = telegram_fetch(curr_package)
        if message_sent:
            max_messages_num -= 1
        if not message_sent:
            if len(curr_package) < 10:
                telegram_fetch("Telegram failed")
                break
            num_of_chars_first = math.ceil(len(curr_package) / 2)
            first_package = curr_package[0:num_of_chars_first]
            second_package = curr_package[num_of_chars_first : len(curr_package)]

            packages_remaining.insert(0, second_package)
            packages_remaining.insert(0, first_package)
    if max_messages_num == 0:
        telegram_fetch("Sending failed. Too many messages sent.")

def poll_telegram():
    url = (
        "https://api.telegram.org/bot"
        + config["telegram"]["bot_key"]
        + "/getUpdates"
    )
    response = requests.get(url).json()
    
    if response["ok"]:
        return response["result"]

    telegram_fetch("Poll failed")

def latest_telegram_messages():
    response = poll_telegram()
    all_messages = [m["message"] for m in response if "message" in m]
    all_text_messages = [m for m in all_messages if "text" in m]
    chat_messages = [m for m in all_text_messages if int(m["chat"]["id"]) == int(config["telegram"]["chat_id"])]
    time_id_text = [(m["date"], m["message_id"], m["text"]) for m in chat_messages]
    time_id_text.sort(key=lambda x: x[0], reverse=True)
    return time_id_text

latest_message_id = None
while True:
    time.sleep(int(config['telegram']['polling_interval_in_seconds']))
    messages = latest_telegram_messages()
    if len(messages) == 0 or messages[0][1] == latest_message_id:
        continue
    latest_message_id = messages[0][1]
    text = messages[0][2]
    send_telegram(ask_chat_gpt(text))


