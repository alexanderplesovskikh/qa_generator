
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
    Не пытайся задать вопрос, который охватывает сразу всю информацию, которую я тебе предоставил выше, вопрос может охватывать или суть текста, или только какую-то основную часть текста выше.
    В твоем ответе укажи ТОЛЬКО сам один вопрос, ничего больше в ответе не пиши (кроме "Нет вопроса.", смотри инструкцию дальше.)
    Твой вопрос должен иметь смысл и быть понятен студенту, который не видит контекст и информации, которую я даю тебе. 
    При этом вопрос должен иметь ответ, который очевиден человеку, разбирающемуся в этой теме, это не должен быть вопрос, ответ на который является узконаправленным, контекстным, локальным или мало знакомым.
    Поэтому не нужно ссылать на текст при формулировании вопроса. В вопросе не должно быть ссылки на текст.
    Если вопрос нельзя сгенерировать исходя из всех перечисленных здесь ограничений, то в ответе просто напиши "Нет вопроса."
    """
    res = format_llm_prompt(template)
    return res

def generate_answer(question, reference):
    template = f"""Тебе нужно сгенерировать ответ на данный вопрос:
    {question}.

    Ответ на этот вопрос ты должен взять из данного контекста ниже, используй только эту информацию для написания ответа на вопрос и не используй никакой другой информации:
    {reference}.

    Напиши только 1 абзац ответа, не пиши много, не пиши больше одного абзаца. Если ты получил вопрос: "Нет вопроса.", то в ответе напиши "Нет ответа.".
    В твоем ответе укажи ТОЛЬКО сам ответ на вопрос, ничего больше не пиши.
    """
    res = format_llm_prompt(template)
    return res

def merge_n_neighbors(strings, n=2):
    if n < 1:
        raise ValueError("n must be at least 1")
    
    merged = [
        " ".join(strings[i:i+n]) 
        for i in range(0, len(strings), n)
    ]
    
    return merged


user_states = {}
user_history = {}
user_file_names = {}
user_file_contents = {}
user_file_dfs = {}

main_menu = "🤖 Я бот-помощник, который умеет генерировать вопросы ❓ и ответы 🎯 для составления экзамена по учебному курсу.\n\n📩 Отправь мне ниже файлы в формате .txt / .md с материалами по **теме** курса *(один файл — одна тема).*\n\n🆕 Теперь я поддерживаю загрузку нескольких файлов за один раз 🌟"

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

                #print(message)

                if 'content' in message and message['content'] != '':

                    raw_content = message['content'].strip()

                    raw_content_files = raw_content.split("\n")

                    user_file_names[user_id] = []
                    user_file_contents[user_id] = []

                    for file in raw_content_files:
                        try:
                            file_pattern = r'^\[.*?\]\(/user_uploads/.*?\)$'
                            is_only_file_link = bool(re.fullmatch(file_pattern, file))
                            print(is_only_file_link)
                            print(message['content'].strip()[-5:])

                            if is_only_file_link == False or len(file.strip())<= 5 or (file.strip()[-5:].lower() != ".txt)" and file.strip()[-4:].lower() != ".md)"):
                                self.send_reply(message, f'''😥 Упс... есть файлики формата не .txt / .md, я их тихо пропущу...''')
                            else:
                                match = re.search(r'\[(.*?)\]', file)  # Non-greedy match
                                if match:
                                    content_file_raw = match.group(1)  # "some content"
                                    file_ext = content_file_raw.split(".")[-1]
                                    file_name = ".".join(content_file_raw.split(".")[:-1])



                                    

                                    user_file_names[user_id].append(str(file_name+"."+file_ext))
                                    

                                    match = re.search(r'\[(.*?)\]\((/user_uploads/.*?)\)', file)
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
                                
                                
                            
                                    file_content = response.content.decode('utf-8', errors='replace')
                                

                                    
                                    user_file_contents[user_id].append(file_content)



                                    print('lists')
                    
                                    print(user_file_names[user_id])

                        except:
                            self.send_reply(message, f"⚠ Some files caused an error.") 
                            continue
                            
                    
                    

                    self.send_reply(message, f"👍 Получил твои файлы: **`{", ".join(user_file_names[user_id])}`**.\n\n🔢 Введи *примерное* число вопросов для генерации (например, **10**).\n\nℹ *Фактическое число бот определит на основе твоих файлов*")
                    user_states[user_id] = {"state": "select_level"}
                    return
                        


            elif user_states[user_id]["state"] == "select_level":
                if re.match(r"^\d+$", content.strip()):
                    user_states[user_id] = {"state": "chat"}


                    max_number_of_questions = content.strip()
                    max_number_of_questions = int(max_number_of_questions)


                   

                    self.send_reply(message, f'''🕣 Я получил твои файлы и начал генерацию вопросов и ответов к ним.\n\n📧 Я уведомлю тебя, как закончу.\n\n⏲ Пожалуйста, подожди окончания генерация, ты можешь уйти с этой страницы во время ожидания...''')

                    #print(user_file_contents[user_id])

                    user_file_dfs[user_id] = []

                    for user_file_idx in range(len(user_file_contents[user_id])):

                        self.send_reply(message, f'''📁 Файл {user_file_idx+1} из {len(user_file_contents[user_id])}''')

                        try:

                            sents_paragraphs = user_file_contents[user_id][user_file_idx].split("\n")

                            all_sents_splitted = []

                            for sent in sents_paragraphs:
                                sentences = re.split(r'(?<=[.!?])\s', sent)
                                sentences = [s for s in sentences if s]
                                res = sentences
                                for i in res:
                                    if len(i.strip()) >= 70:
                                        if i.strip()[-1] in [".", "!", "?"]:
                                            all_sents_splitted.append(i)

                            #print(all_sents_splitted[0:10])

                            all_sents_splitted = merge_n_neighbors(all_sents_splitted, n=3)

                            #print(all_sents_splitted[0:10])


                            if len(all_sents_splitted) > max_number_of_questions:
                                all_sents_splitted = all_sents_splitted[:max_number_of_questions]

                            generated_questions = []
                            generated_answers = []

                            for i in range(len(all_sents_splitted)):
                                current_question = generate_question(all_sents_splitted[i])
                                print(current_question)
                                generated_questions.append(current_question)

                                current_answer = generate_answer(current_question, all_sents_splitted[i])
                                print(current_answer)
                                generated_answers.append(current_answer)

                                percentage = i / len(all_sents_splitted) * 100
                                formatted_percentage = f"{percentage:.2f}"

                                if i % 10 == 0:
                                    self.send_reply(message, f'''⏳ Прогресс генерации: {formatted_percentage} %''')
                                

                            all_massive = []
                            current_date = datetime.now().strftime("%d.%m.%Y")
                            for i in range(len(generated_questions)):
                                all_massive.append([
                                    i+1,
                                    user_file_names[user_id][user_file_idx],
                                    current_date,
                                    generated_questions[i], 
                                    generated_answers[i], 
                                    all_sents_splitted[i]
                                ])

                            # 2. Convert to a Pandas DataFrame
                            df = pd.DataFrame(
                                all_massive,
                                columns=["#", "File", "Date", "Question", "Answer", "Reference"]
                            )

                            user_file_dfs[user_id].append(df)

                            

                            #df_markdown = df.to_markdown()

                            self.send_reply(message, f'''✅ Я завершил генерацию для файла {user_file_idx+1} из {len(user_file_contents[user_id])}''')

                            #self.send_reply(message, f"""Вот твой файл с вопросами:\n{df_markdown}""")
                        
                        except:
                            self.send_reply(message, "⚠ Some files caused an error.")
                            continue

                    
                    try:
                        # Example list of DataFrames
                        output_path = f"/home/user/vt5_file/userData_{user_id}.xlsx"

                        print(user_file_dfs[user_id])

                        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                            for idx, df in enumerate(user_file_dfs[user_id]):
                                sheet_name = f"Sheet_{idx + 1}"  # Or use sheet_names[idx] if predefined
                                df.to_excel(writer, sheet_name=sheet_name, index=False)

                        with open(f"/home/user/vt5_file/userData_{str(user_id)}.xlsx", "rb") as fp:
                            result = self.client.upload_file(fp)
                            print(result)

                        mes_new = self.client.send_message({
                                    "type": "private",
                                    "to": message["sender_email"],
                                    "content": "🏁 Смотри, вот твой [файлик с вопросами 📄]({})...".format(result["uri"]),
                        })
                    
                    except:
                        self.send_reply(message, "⚠ Some files caused an error.")



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
