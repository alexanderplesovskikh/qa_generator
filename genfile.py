import zulip
import os
import logging
import re
import traceback

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

                    self.send_reply(message, f'''File got {is_only_file_link}''')

                '''if 'attachments' in message and message['attachments']:
                    for attachment in message['attachments']:
                        if attachment['name'].endswith('.txt'):
                            # Successful attachment case
                            user_states[user_id] = {
                                   "state": "select_level",
                                   "filename": attachment['name'],
                                   "file_id": attachment['id']
                                }
                            self.send_reply(message, "Какой у вас уровень знаний по теме? Выбери, введя соответствующую цифру: \n**`1. начальный`**\n**`2. средний`**\n**`3. продвинутый`**\n\nЧтобы вернуться в главное меню, введи: **`помощь`**")
                        else:
                            self.send_reply(message, "Passing for not txt file")
                else:
                    self.send_reply(message, "Пожалуйста, отправьте .txt файл с темой для обсуждения.\n\nЧтобы увидеть главное меню, введи: **`start`**")'''
                
            elif user_states[user_id]["state"] == "select_level":
                if re.match(r"^\d+$", content.strip()):
                    user_states[user_id] = {"state": "chat", "topic": user_states[user_id]["topic"], "level": content}
                    topic = user_states[user_id]["topic"]
                    user_history[user_id] = []
                    
                    self.send_reply(message, "👨‍🏫 Давай посмотрим, что нам предстоит узнать в рамках этой темы.")
                
                else:
                    self.send_reply(message, "Пожалуйста, выберите уровень, введя соответствующую цифру: \n**`1. начальный`** \n**`2. средний`** \n**`3. продвинутый`**\n\nЧтобы вернуться в главное меню, введи: **`помощь`**")

            elif user_states[user_id]["state"] == "chat":
                topic = user_states[user_id]["topic"]
                level = user_states[user_id]["level"]

                self.send_reply(message, "👨‍🏫 Давай посмотрим, что нам предстоит узнать в рамках этой темы.")

    handler_class = GenerateBot

except Exception:
    traceback.print_exc()

