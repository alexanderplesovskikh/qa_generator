
import zulip

class GenerateBot:

    def initialize(self, bot_handler):
        self.bot_handler = bot_handler
        self.setup_logging()
        logging.debug("Инициализация бота")
        self.user_sessions = {}

        # Инициализация клиента Zulip
        self.client = zulip.Client(config_file=os.path.join(os.getcwd(), 'zuliprc'))


    def handle_message(self, message, bot_handler):
        user_id = message["sender_id"]
        content = message["content"].strip().lower()

        if user_id not in user_history:
            user_history[user_id] = []

        if user_id not in user_states:
            user_states[user_id] = {"state": "main_menu"}

        state = user_states[user_id]["state"]

        if content in ["помощь", 'help', 'start', 'exit']:
            user_states[user_id] = {"state": "main_menu"}
            self.send_reply(message, main_menu)
            return

        if state == "main_menu":
            if re.match(r"^\d+$", content.strip()) and int(content.strip()) in all_theme_ids:
                user_states[user_id] = {"state": "select_level", "topic": int(content)}
                self.send_reply(message, "Какой у вас уровень знаний по теме? Выбери, введя соответствующую цифру: \n**`1. начальный`**\n**`2. средний`**\n**`3. продвинутый`**\n\nЧтобы вернуться в главное меню, введи: **`помощь`**")
            else:
                self.send_reply(message, main_menu)

        elif state == "select_level":
            if content in ["1", "2", "3"]:
                user_states[user_id] = {"state": "chat", "topic": user_states[user_id]["topic"], "level": content}
                #open file
                #prompt model to summorize it
                topic = user_states[user_id]["topic"]

                user_history[user_id] = []

                file_path_summary = base_dir + 'course_materials/' + str(topic) + ".txt"

                with open(file_path_summary, 'r', encoding="utf-8") as sum_file:
                    sum_lines = sum_file.readlines()

                sum_firstlines = sum_lines[0]

                if sum_firstlines[0] == "#":
                    sum_firstlines = sum_firstlines[1:].strip()

                sum_restlines = " ".join(sum_lines[1:])

                summary_prompt = f"""- Текст: {sum_restlines}.
- Задание: ты ИИ-ассистент, напиши короткое резюме данного тебе содержания темы курса, кратко по пунктам обозначь основные разделы, через знак "-".
- Не пиши много текста, просто приведи подтемы данного тебе материала по курсу, через "-", каждый пункт начинай с новой строки.
- В конце резюме с нового абзаца, спроси про что-то одно из резюме - задай открытый вопрос по типу: А знаешь ли ты, что такое ..."""

                self.send_reply(message, "👨‍🏫 Давай посмотрим, что нам предстоит узнать в рамках этой темы.")

                llm_summary = format_llm_prompt(summary_prompt)

                user_states[user_id]['init_message'] = ""
                user_states[user_id]['last_updated_messsage'] = ""


                user_states[user_id]['init_message'] = f"Проведу тебе краткий экскурс по теме: **{sum_firstlines}**\n---\n"

                event_id = self.send_reply(message, user_states[user_id]['init_message'])

                if event_id:
                    count = 0
                    for token in llm_summary:
                        user_states[user_id]['init_message'] += token
                        count+= 1 
                        if count % token_speed == 0:
                            self.update_reply(message, user_states[user_id]['init_message'], event_id)
                            user_states[user_id]['init_message'] = user_states[user_id]['init_message']
                            
                    
                    if user_states[user_id]['init_message'] != user_states[user_id]['last_updated_messsage']:
                        self.update_reply(message, user_states[user_id]['init_message'], event_id)

                    ending_message = "\n---\n**❓ Давай начнём изучение темы! Можешь задать вопрос по любому аспекту темы, я отвечу с опорй на материалы курса Сетевых видеотехнологий или можем начать беседу по предложенному мной вопросу — в любом случае выбирать тебе! Просто `напиши свой вопрос` или отправь мне: `Расскажи, что такое <...>` — и мы начнем беседу 😉**\n---\nДля возврата в меню введите **`помощь`**."
                    self.update_reply(message, user_states[user_id]['init_message'] + ending_message, event_id)

                    if len(user_history[user_id]) > 10:
                        del user_history[user_id][0]

                    user_history[user_id].append({"role": "AI-assistant", "message": user_states[user_id]['init_message']})
            
            else:
                self.send_reply(message, "Пожалуйста, выберите уровень, введя соответствующую цифру: \n**`1. начальный`** \n**`2. средний`** \n**`3. продвинутый`**\n\nЧтобы вернуться в главное меню, введи: **`помощь`**")

        elif state == "chat":
            topic = user_states[user_id]["topic"]
            level = user_states[user_id]["level"]
            topic_name = lines[int(str(topic).strip())-1]

            model_level_desc = ''
            if str(level).strip() == '1':
                model_level_desc = 'объяснения попроще с простой лексикой и покроче'
            if str(level).strip() == '2':
                model_level_desc = 'средний уровень сложности лексики и средний уровень сложности объяснений'
            if str(level).strip() == '3':
                model_level_desc = 'сложный уровень лексики научный академический формальный язык и продвинутые объяснения'

            #Main answer

            chunks_for_llm = search_chunks(content)

           


handler_class = GenerateBot
