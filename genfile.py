
import zulip
import os
import logging
import re
import traceback
import requests
from urllib.parse import urljoin

user_states = {}
user_history = {}

main_menu = "Привет! Я бот-помощник, который умеет генерировать вопросы и ответы для составления экзамена по учебному курсу. Отправь мне ниже файл в формате txt с материалами по ТЕМЕ курса, один файл - одна тема:"

try:

    class GenerateBot:

        def initialize(self, bot_handler):
            self.bot_handler = bot_handler
            logging.debug("Инициализация бота")
            self.user_sessions = {}

            # Инициализация клиента Zulip
            self.client = zulip.Client(config_file=os.path.join(os.getcwd(), 'genfile/zuliprc'))

        def usage(self):
            return main_menu
        
        
        def send_reply(self, message, response):
            response = self.client.send_message({
                    "type": "private",
                    "to": message["sender_email"],
                    "content": response
                })
            return response



        def handle_message(self, message, bot_handler):
            user_id = message["sender_id"]
            content = message["content"].strip().lower()

            if user_id not in user_history:
                user_history[user_id] = []

            if user_id not in user_states:
                user_states[user_id] = {"state": "main_menu"}

   

            if content in ["помощь", 'help', 'start', 'exit']:
                user_states[user_id] = {"state": "main_menu"}
                self.send_reply(message, main_menu)
                return
            
            if user_states[user_id]["state"] == "main_menu":

                self.send_reply(message, main_menu)
                user_states[user_id] = {"state": "wait_for_file"}
                return
            
            if user_states[user_id]['state'] == 'wait_for_file':

                print(message)

                if 'content' in message and message['content'] != '':
                    raw_content = message['content'].strip()
                    file_pattern = r'^\[.*?\]\(/user_uploads/.*?\)$'
                    is_only_file_link = bool(re.fullmatch(file_pattern, raw_content))
                    print(is_only_file_link)
                    print(message['content'].strip()[-5:])

                    if is_only_file_link == False or len(message['content'].strip())<= 5 or message['content'].strip()[-5:] != ".txt)":
                        self.send_reply(message, f'''Ooops, not txt file, send me file again...''')
                    else:
                        match = re.search(r'\[(.*?)\]', raw_content)  # Non-greedy match
                        if match:
                            content_file_raw = match.group(1)  # "some content"
                            file_ext = content_file_raw.split(".")[-1]
                            file_name = ".".join(content_file_raw.split(".")[:-1])

                            result = self.client.get_attachments()
                            print(result)
                            print()
                            print(message)


                            self.send_reply(message, f"Super filename {file_name} ext {file_ext} enter number\n{1}:")
                            user_states[user_id] = {"state": "select_level"}
                            return
                        else:
                            content = None  # No brackets found
                            self.send_reply(message, "No file, press start")


            elif user_states[user_id]["state"] == "select_level":
                if re.match(r"^\d+$", content.strip()):
                    user_states[user_id] = {"state": "chat"}
                    
                    self.send_reply(message, "👨‍🏫 Давай посмотрим, что нам предстоит узнать в рамках этой темы.")

                    return
                
                else:
                    self.send_reply(message, "Пожалуйста, выберите уровень, введя соответствующую цифру: \n**`1. начальный`** \n**`2. средний`** \n**`3. продвинутый`**\n\nЧтобы вернуться в главное меню, введи: **`помощь`**")

            elif user_states[user_id]["state"] == "chat":
                topic = user_states[user_id]["topic"]
                level = user_states[user_id]["level"]

                self.send_reply(message, "👨‍🏫 Давай посмотрим, что нам предстоит узнать в рамках этой темы.")

    handler_class = GenerateBot

except Exception:
    traceback.print_exc()
