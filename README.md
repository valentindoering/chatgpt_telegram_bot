# Setup
1. Message the Telegram bot father, create a new bot, remember the bot token
2. create a new group and add you bot as admin
3. send a message in the group
4. "https://api.telegram.org/bot<YourBOTToken>/getUpdates" insert your bot token in this url and paste it in your browser
5. search for the message, that you sent in the group, find and remember the chatid this message belongs to 
    - chatid = request["results"][<find your message idx>]["message"]["chat"]["id"]
7. Go to "https://beta.openai.com/account/api-keys", login, create and remember your api key
6. create a config.yml that looks like that, enter your data
    chat_gpt:
        api_key: <your api key>
        organization: "org-TsigPfWvInpE1XeO5gbpe2jm"
        # feel free to choose another model, if you want
        model: "text-davinci-003"
        # determines the maximimum answer length, the bigger this number is the faster your free apikey trial is over
        max_tokens_per_request: 100 
    telegram:
        bot_key: <your bot key>
        chat_id: <your chat id>
        # the smaller the interval the faster you will get a response, but also the more processing power is required over time
        polling_interval_in_seconds: 3
7. Host the script: Suggestion pythonanywhere.com (free), go on their website, create a free account
8. From the Pythonanwhere dashboard go to "File" (top right) and upload the run.py file as well as the config.yml
9. Create a new Bash Console and run the command `pip install openai`, if you uploaded the requirements.txt you can also run `pip install -r requirements.txt`
10. start the script by running `python run.py`, done, your bot should work now




