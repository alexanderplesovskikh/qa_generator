
import zulip
import os
import logging
import re
import traceback
import requests
from urllib.parse import urljoin
from langchain_ollama.llms import OllamaLLM
from datetime import datetime
from nltk.tokenize import sent_tokenize
import pandas as pd

#downloads
from nltk import download
download('punkt_tab')

model_ollama = "owl/t-lite:latest"

init_ollama = OllamaLLM(
    model=model_ollama,
    temperature = 0.3,
    streaming=True,
    num_ctx=4096,
)

def format_llm_prompt(query):
    response = init_ollama.invoke(query)
    return response

def generate_question(sentence):
    template = f"""Тебе нужно сгенерировать 1 (один вопрос), опираясь только на следующую информацию:
    {sentence}.
    В твоем ответе укажи ТОЛЬКО сам один вопрос, ничего больше в ответе не пиши.
    """
    res = format_llm_prompt(template)
    return res

def generate_answer(question):
    template = f"""Тебе нужно сгенерировать ответ на данный вопрос:
    {question}.
    В твоем ответе укажи ТОЛЬКО сам ответ на вопрос, ничего больше не пиши.
    """
    res = format_llm_prompt(template)
    return res


user_states = {}
user_history = {}
user_file_names = {}
user_file_contents= {}

main_menu = "Привет! Я бот-помощник, который умеет генерировать вопросы и ответы для составления экзамена по учебному курсу. Отправь мне ниже файл в формате .txt с материалами по **теме** курса (один файл - одна тема)"

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
                        self.send_reply(message, f'''Упс... это не текстовый файл формата .txt, отправь еще раз...''')
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

                            #for testing
                            test_file = f"""
Сегодня выдался прекрасный солнечный день, и я решил прогуляться по парку. Воздух был свежим, а вокруг цвели деревья, создавая уютную атмосферу. По дороге мне встретились несколько друзей, и мы вместе посидели на скамейке, обсуждая последние новости. Такие моменты напоминают, как важно ценить простые радости жизни.

Вечером я приготовил вкусный ужин — пасту с томатным соусом и свежей зеленью. После еды включил любимый фильм и устроился на диване с чашкой чая. За окном медленно наступали сумерки, а в комнате царило тепло и умиротворение. Иногда именно такие спокойные вечера становятся самыми приятными.

Если нужно что-то конкретное или определённого стиля — дай знать! 😊
                    """


                            user_file_names[user_id] = str(file_name+"."+file_ext)
                            user_file_contents[user_id] = str(test_file)


                            self.send_reply(message, f"Супер! Получил твой файл {file_name}.{file_ext} и уже начал генерацию вопросов...\nPress number to continue:")
                            user_states[user_id] = {"state": "select_level"}
                            return
                        else:
                            content = None  # No brackets found
                            self.send_reply(message, "No file, press start")


            elif user_states[user_id]["state"] == "select_level":
                if re.match(r"^\d+$", content.strip()):
                    user_states[user_id] = {"state": "chat"}


                    max_number_of_questions = content.strip()


                   

                    self.send_reply(message, f'''Hooray! I see file content and already generating answers. I will notify you when I'm done. Please wait a bit. Now you can leave this page...\nYou content is down below:\n{user_file_contents[user_id]}''')

                    sents_paragraphs = user_file_contents[user_id].split("\n")

                    all_sents_splitted = []

                    for sent in sents_paragraphs:
                        res = sent_tokenize(sent)
                        for i in res:
                            if len(i) >= 30:
                                all_sents_splitted.append(i)

                    generated_questions = []
                    generated_answers = []

                    for i in range(len(all_sents_splitted)):
                        current_question = generate_question(all_sents_splitted[i])
                        print(current_question)
                        generated_questions.append(current_question)

                        current_answer = generate_answer(current_question)
                        print(current_answer)
                        generated_answers.append(current_answer)

                        percentage = i / len(all_sents_splitted) * 100
                        formatted_percentage = f"{percentage:.2f}"

                        self.send_reply(message, f'''Progress: {formatted_percentage} %''')


                    
                    
                 
                        

                    all_massive = []
                    current_date = datetime.now().strftime("%d.%m.%Y")
                    for i in range(len(generated_questions)):
                        all_massive.append([
                            i+1,
                            user_file_names[user_id],
                            current_date,
                            generated_questions[i], 
                            generated_answers[i], 
                        ])

                    # 2. Convert to a Pandas DataFrame
                    df = pd.DataFrame(
                        all_massive,
                        columns=["#", "File", "Date", "Question", "Answer"]
                    )

                    df.to_excel("/home/user/vt5_file/test1.xlsx", index=False)

                    self.send_reply(message, f"""User id: {str(user_id)}""")


                    user_states[user_id]["state"] = "main_menu"



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
