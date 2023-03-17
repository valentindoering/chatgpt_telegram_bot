import yaml
import os
import openai
import math
import requests
from urllib.parse import quote
import pprint
import time
import sys
import traceback

config = yaml.load(open('config.yml'), Loader=yaml.FullLoader)

openai.organization = config['open_ai']['organization']
openai.api_key = config['open_ai']['api_key']
# print(openai.Model.list())

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

def on_error_send_traceback(log_func):
    def on_error_send_traceback_decorator(function):
        def wrapper_function(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as err:
                # traceback.print_tb(err.__traceback__)
                etype, value, tb = sys.exc_info()
                max_stack_number = 300
                traceback_string = ''.join(traceback.format_exception(etype, value, tb, max_stack_number))
                log_func('Exception in ' + function.__name__ + '\n' + traceback_string)

        return wrapper_function
    return on_error_send_traceback_decorator

@on_error_send_traceback(send_telegram)
def ask_open_ai(question):
    try:
        answer = openai.Completion.create(
            model=config['open_ai']['model'],
            prompt=question,
            max_tokens=int(config['open_ai']['max_tokens_per_request']),
            temperature=0
        )
        text = answer['choices'][0]['text']
        # new line in csv file with date, time, question, answer
        with open('open_ai_log.csv', 'a') as f:
            # remove new line characters
            log_text = text.replace('\n', ' ')
            f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")},{question},{log_text}')
        return text
    except Exception as err:
        with open('open_ai_log.csv', 'a') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")},{question},{"ChatGPT failed"}')
        raise err

@on_error_send_traceback(send_telegram)
def ask_chat_gpt(messages):
    assert config['open_ai']['model'] == "gpt-3.5-turbo", "ChatGPT model is not set to gpt-3.5-turbo"

    try:
        request = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=int(config['open_ai']['max_tokens_per_request']),
        )

        messages.append({"role": "assistant", "content": request['choices'][0]['message']['content']}) 
        
            
        # messages=[
        #     {"role": "system", "content": "You are a helpful assistant."},
        #     {"role": "user", "content": "Who won the world series in 2020?"},
        #     {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
        #     {"role": "user", "content": "Where was it played?"}
        # ]
        
        # openai.Completion.create(
        #     model=config[open_ai]['model'],
        #     prompt=question,
        #     max_tokens=int(config[open_ai]['max_tokens_per_request']),
        #     temperature=0
        # )

        return messages
    except Exception as err:
        with open('openai_log.csv', 'a') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")},{messages},{"ChatGPT failed"}')
        raise err

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

@on_error_send_traceback(send_telegram)
def exec_functionality(text):
    if config['bot']['python_exec_functionality']:
        text = text[5:]
        text = text.replace('”', '"').replace('‘', "'").replace('’', "'").replace('“', '"').replace('…', '...')
        
        output_dict = {}
        try:
            exec(text, output_dict)
        except Exception as err:
            return "Error: " + str(err)
        
        if "output" not in output_dict:
            return "Assign 'output' variable in your code."
        
        return output_dict["output"]

def how_functionality():
    if text == "how":
        with open('config.yml', 'r') as f:
            config_string = f.read()
        
        return f"""Commands:
- exec <code>: execute python code
- how: show this message
if config['open_ai']['model'] == "gpt-3.5-turbo":
    - new_chat: start a new chat (default system message: "You are a helpful assistant.")
    - system <message>: starts new chat with system message
    - show_chat: show current chat

config.yml:
{config_string}
"""


# main ----------------------------
chat_gpt_messages = []

latest_message_id = None
while True:

    # extract new messages
    time.sleep(int(config['telegram']['polling_interval_in_seconds']))
    messages = latest_telegram_messages()
    if len(messages) == 0 or messages[0][1] == latest_message_id:
        continue
    latest_message_id = messages[0][1]
    text = messages[0][2]

    # how functionality
    if text == "how":
        send_telegram(how_functionality())
        continue
    
    # execute functionality
    if text.startswith("exec"):
        send_telegram(exec_functionality(text))
        continue
    
    # other models
    if config['open_ai']['model'] != "gpt-3.5-turbo":
        send_telegram(ask_open_ai(text))
        continue
    
    # chat gpt
    if text.startswith("system "):
        chat_gpt_messages = [{"role": "system", "content": text[7:]}]
        send_telegram("New chat started")
        send_telegram(chat_gpt_messages)
        continue
    
    if text == "new_chat":
        chat_gpt_messages = [{"role": "system", "content": "You are a helpful assistant."}]
        send_telegram("New chat started")
        send_telegram(chat_gpt_messages)
        continue

    if text == "show_chat":
        send_telegram(chat_gpt_messages)
        continue
    
    if chat_gpt_messages == []:
        chat_gpt_messages = [{"role": "system", "content": "You are a helpful assistant."}]
        send_telegram(f"New chat started {chat_gpt_messages}")
        
    chat_gpt_messages.append({"role": "user", "content": text})
    chat_gpt_messages = ask_chat_gpt(chat_gpt_messages)
    send_telegram(chat_gpt_messages[-1]['content'])
