
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

model_ollama = "gemma3:4b"

init_ollama = OllamaLLM(
    model=model_ollama,
    temperature = 0.3,
    streaming=True,
    num_ctx=4096,
    num_predict=512,
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
    Напиши только 1 абзац ответа, не пиши много, не пиши больше одного абзаца. В твоем ответе укажи ТОЛЬКО сам ответ на вопрос, ничего больше не пиши.
    """
    res = format_llm_prompt(template)
    return res


user_states = {}
user_history = {}
user_file_names = {}
user_file_contents= {}

main_menu = "Я бот-помощник, который умеет генерировать вопросы ❓ и ответы 🎯 для составления экзамена по учебному курсу. Отправь мне ниже файл в формате .txt / .md с материалами по **теме** курса *(один файл — одна тема)*"

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

                    if is_only_file_link == False or len(message['content'].strip())<= 5 or (message['content'].strip()[-5:].lower() != ".txt)" and message['content'].strip()[-4:].lower() != ".md)"):
                        self.send_reply(message, f'''Упс... это не текстовый файл формата .txt / .md, отправь файл в формате .txt / .md...''')
                    else:
                        match = re.search(r'\[(.*?)\]', raw_content)  # Non-greedy match
                        if match:
                            content_file_raw = match.group(1)  # "some content"
                            file_ext = content_file_raw.split(".")[-1]
                            file_name = ".".join(content_file_raw.split(".")[:-1])



                            with open("/home/user/vt5_file/test1.txt", "r", encoding="utf-8") as file_open:
                                test_file = file_open.read()



                            user_file_names[user_id] = str(file_name+"."+file_ext)
                            

                            match = re.search(r'\[(.*?)\]\((/user_uploads/.*?)\)', raw_content)
                            if match:
                                filename_ = match.group(1)  # "news_sents-1.txt"
                                file_path_ = match.group(2) # "/user_uploads/2/7f/2E1qbem0o7P3PaKush4CSg6u/news_sents-1.txt"

                            url_ = file_path_

                            print(url_)

                            # Construct full URL (replace with your Zulip server URL)
                            full_file_url = f"https://chat.miem.hse.ru{url_}"

                            print(full_file_url)
                            
                            # Download the file (using requests with your API key)
                            response = requests.get(
                                full_file_url,
                                auth=requests.auth.HTTPBasicAuth(
                                    "vt5_lesson_gen-bot@chat.miem.hse.ru",  # Your bot's email
                                    "oYY0z3KU0llUmkfyOHwH09mfyFa2KMYM"  # Your bot's API key
                                ),
                            )
                            response.raise_for_status()  # Check for HTTP errors
                            # Get file content
                            file_content = response.text
                            print('init')
                            print(file_content)
                            file_content = response.content.decode('utf-8', errors='replace')
                            print('utf-8')
                            print(file_ext)

                            user_file_contents[user_id] = file_content

                            test1 = self.client.get_attachments()
                            print(test1)


                            self.send_reply(message, f"Супер! Получил твой файл **`{file_name}.{file_ext}`**. Введи число вопросов для генерации:")
                            user_states[user_id] = {"state": "select_level"}
                            return
                        else:
                            content = None  # No brackets found
                            self.send_reply(message, "Ошибка: Файл не найден")


            elif user_states[user_id]["state"] == "select_level":
                if re.match(r"^\d+$", content.strip()):
                    user_states[user_id] = {"state": "chat"}


                    max_number_of_questions = content.strip()
                    max_number_of_questions = int(max_number_of_questions)


                   

                    self.send_reply(message, f'''Я получил твой файл и начал генерацию вопросов и ответов к ним. Я уведомлю тебя, как закончу. Пожалуйста, подожди окончания генерация, ты можешь уйти с этой страницы во время ожидания...''')

                    print(user_file_contents[user_id])

                    sents_paragraphs = user_file_contents[user_id].split("\n")

                    all_sents_splitted = []

                    for sent in sents_paragraphs:
                        res = sent_tokenize(sent)
                        for i in res:
                            if len(i) >= 30:
                                all_sents_splitted.append(i)

                    if len(all_sents_splitted) > max_number_of_questions:
                        all_sents_splitted = all_sents_splitted[:max_number_of_questions]

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

                        if i % 10 == 0:
                            self.send_reply(message, f'''Прогресс генерации: {formatted_percentage} %''')


                    
                    
                 
                        

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

                    df.to_excel(f"/home/user/vt5_file/test_{str(user_id)}.xlsx", index=False)

                    df_markdown = df.to_markdown()

                    self.send_reply(message, f'''Я завершил генерацию!''')

                    #self.send_reply(message, f"""Вот твой файл с вопросами:\n{df_markdown}""")

                    with open(f"/home/user/vt5_file/test_{str(user_id)}.xlsx", "rb") as fp:
                        result = self.client.upload_file(fp)
                        print(result)

                    mes_new = self.client.send_message({
                            "type": "private",
                            "to": message["sender_email"],
                            "content": "Смотри, вот твой [файлик с вопросами]({})...".format(result["uri"]),
                    })


                    user_states[user_id]["state"] = "main_menu"



                    return
                
                else:
                    self.send_reply(message, "Пожалуйста, введи только целое число вопросов для генерации (например, 10)...")

            elif user_states[user_id]["state"] == "chat":
                topic = user_states[user_id]["topic"]
                level = user_states[user_id]["level"]

                self.send_reply(message, "👨‍🏫 Давай посмотрим, что нам предстоит узнать в рамках этой темы.")

    handler_class = GenerateBot

except Exception:
    traceback.print_exc()

