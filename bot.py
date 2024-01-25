from config import TOKEN
import telebot
from telebot import types
from telegram_bot_calendar import DetailedTelegramCalendar
from config import TOKEN
from datetime import datetime
import locale
import os, sys
from requests.exceptions import ConnectionError, ReadTimeout



# conn = psycopg2.connect(dbname=DB_NAME, user=DB_LOGIN, password=DB_PASSWORD)
# cursor = conn.cursor()
locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
bot = telebot.TeleBot(TOKEN)

# Словарь для хранения данных пользователей
users_db = {}
cities = ["Санкт-Петербург", "Москва", "Новосибирск", "Екатеринбург"]
buttons = ['Опубликовать', 'Создать объявление заново']
channel_ids_long = {'Новосибирск': '-1002010810169', 'Москва': '-1002115842002', 'Екатеринбург': '-1002028710164', 'Санкт-Петербург': '-1002144192009'}
channel_ids_short = {'Новосибирск': '-1002120433604', 'Москва': '-1002106897762', 'Екатеринбург': '-1002008160160', 'Санкт-Петербург': '-1001856471244'}


base_headings = {'Бизнес': '#biz ',
            'Психология': '#Psy ',
            'Эзотерические': '#magic ',
            'Мужские': '#мужские ',
            'Женские': '#женские ',
            'Детские(с детьми)': '#детские ',
            'Образование/тренинги/обучение': '#обучение ',
            'Культура и искусство': '#культура ',
            'Музыкально-танцевальные': '#муз ',
            'Здоровье и спорт': '#здоровье ',
            'Настолки и дружеские встречи': '#games ',
            'Бесплатные': '#free💚 '}


biz_hashtags =  ['#networking', '#gameBiz', '#forum', '#marketing', '#sale', '#тренинг', '#manBiz', '#wonanBiz', '#ИИbiz']

# def create_db(chat_id, username, city):
#     cursor.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, chat_id BIGINT UNIQUE, username VARCHAR UNIQUE, city VARCHAR)")
#     conn.commit()
#
#     insert_query = """
#         INSERT INTO users (chat_id, username, city)
#         VALUES (%s, %s, %s)
#         ON CONFLICT (username)
#         DO UPDATE SET
#             chat_id = EXCLUDED.chat_id,
#             username = EXCLUDED.username,
#             city = EXCLUDED.city;
#     """
#     cursor.execute(insert_query, (chat_id, username, city))
#     conn.commit()


# Обработка команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    chat_id = message.chat.id

    if chat_id in users_db and 'current_message' in users_db[chat_id]:
        try:
            bot.edit_message_reply_markup(chat_id, users_db[chat_id]['current_message'])
        except Exception as e:
            pass

    city_buttons = types.InlineKeyboardMarkup()
    for city in cities:
        btn = types.InlineKeyboardButton(city, callback_data=city)
        city_buttons.add(btn)


    sent_message = bot.send_message(chat_id, "Привет! Я бот для создания объявлений. Давай начнем! Выбери свой город:\n",
                     reply_markup=city_buttons)
    users_db[chat_id] = {}
    users_db[chat_id]['current_message'] = sent_message.message_id

    try:
        user = message.from_user
        username = user.username
        users_db[chat_id]['username'] = username
    except KeyError:
        handle_cancel(message)
        return


# Обработка выбора города
@bot.callback_query_handler(func=lambda call: call.data in cities)
def handle_city_choice(call):
    if call.data:
        try:
            chat_id = call.message.chat.id
            users_db[chat_id]['city'] = call.data
        except KeyError:
            handle_cancel(call.message)
            return

        # create_db(chat_id, users_db[chat_id]['username'], users_db[chat_id]['city'])

        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        bot.send_message(chat_id, f"Ты выбрал город {call.data}. Теперь введи тему мероприятия:\n \n"
                              f'(Если вы хотите прервать процесс создания объявления, введите команду /cancel\n',
                    )

        bot.register_next_step_handler(call.message, handle_topic_input)
    else:
        bot.send_message(call.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(call, handle_city_choice)

# Обработка ввода темы мероприятия
def handle_topic_input(message):
    if message.text:
        if message.text[0] != '/':
            try:
                chat_id = message.chat.id
                users_db[chat_id]['topic'] = message.text
            except KeyError:
                handle_cancel(message)
                return

            bot.send_message(chat_id, f"Тема мероприятия: {message.text}. Теперь введи название мероприятия (максимум 200 символов):\n \n"
                                  f'(Если вы хотите прервать процесс создания объявления, введите команду /cancel\n',
                         )
            bot.register_next_step_handler(message, handle_event_name_input)
        elif message.text == '/cancel':
            handle_cancel(message)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_topic_input)

# Обработка названия мероприятия
def handle_event_name_input(message):
    if message.text:
        if len(message.text) > 200:
            bot.send_message(message.chat.id, 'Слишком длинное сообщение')
            bot.register_next_step_handler(message, handle_event_name_input)
        else:
            if message.text[0] != '/':
                try:
                    chat_id = message.chat.id
                    users_db[chat_id]['event_name'] = message.text
                except KeyError:
                    handle_cancel(message)
                    return

                bot.send_message(chat_id, f"Название мероприятия: {message.text}. \nТеперь загрузите изображение для поста:\n \n"
                                          f'(Если вы хотите прервать процесс создания объявления, введите команду /cancel\n',
                                )
                bot.register_next_step_handler(message, handle_event_image_input)
            elif message.text == '/cancel':
                handle_cancel(message)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_event_name_input)

#Обработка изображения для поста
def handle_event_image_input(message):
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        else:
            bot.send_message(message.chat.id, 'Загрузите изображение\n \n'
                                              f'(Если вы хотите прервать процесс создания объявления, введите команду /cancel\n',
                             )
            bot.register_next_step_handler(message, handle_event_image_input)
    elif message.photo:
        try:
            chat_id = message.chat.id
            users_db[chat_id]['image'] = message.photo[-1].file_id
            send_current_state(chat_id, 'user')
        except KeyError:
            handle_cancel(message)
            return

        calendar, step = DetailedTelegramCalendar().build()
        sent_message = bot.send_message(message.chat.id,
                         f"Выберите дату",
                         reply_markup=calendar)
        users_db[chat_id]['current_message'] = sent_message.message_id
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_event_image_input)


#ОБРАБОТЧИК ДЛЯ ДАТЫ
@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c):
    if c.data:
        result, key, step = DetailedTelegramCalendar().process(c.data)
        if not result and key:
            bot.edit_message_text(f"Выберите дату",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=key)
        elif result:
            bot.edit_message_text(f"Вы выбрали {result}",
                                  c.message.chat.id,
                                  c.message.message_id)
            try:
                users_db[c.message.chat.id]['date'] = result
            except KeyError:
                handle_cancel(c)
                bot.send_message(c.message.chat.id, f'Для создания объявления напишите /start')
                return
            send_current_state(chat_id=c.message.chat.id, source='user')


            bot.send_message(c.message.chat.id, f'Введите время мероприятия\n'
                                              f'Примеры: \n'
                                              f'14:00 - 18:00\n'
                                              f'14:00 до 18:00\n \n'
                                              f'(Если вы хотите прервать процесс создания объявления, введите команду /cancel\n',
                         )
            bot.register_next_step_handler(c.message, handle_event_time_input)
    else:
        bot.send_message(c.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(c, cal)


#обработчик ввода времени
def handle_event_time_input(message):
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        try:
            users_db[message.chat.id]['time'] = message.text
        except KeyError:
            handle_cancel(message)
            return
        send_current_state(chat_id=message.chat.id, source='user')
        bot.send_message(message.chat.id, f'Введите количество человек на мероприятии\n \n'
                                          f'(Если вы хотите прервать процесс создания объявления, введите команду /cancel\n',
                         )
        bot.register_next_step_handler(message, handle_event_people_count)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_event_time_input)


#обработчик ввода кол-ва людей
def handle_event_people_count(message):
    # number_pattern = re.compile(r'^\d+$')
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        else:
            # if number_pattern.match(message.text):
            try:
                users_db[message.chat.id]['people_count'] = message.text
                try:
                    people = int(message.text)
                    if people > 50:
                        users_db[message.chat.id]['hashtags'] = '#BiG '
                except ValueError:
                    pass
                send_current_state(chat_id=message.chat.id, source='user')
            except KeyError:
                handle_cancel(message)
                return

            skip_button = types.KeyboardButton("Пропустить")
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            keyboard.add(skip_button)

            bot.send_message(message.chat.id, f'Введите оффер (необязательно):', reply_markup=keyboard)
            bot.register_next_step_handler(message, handle_event_offer)

            # else:
            # bot.send_message(message.chat.id,
            #                 f'Неверный формат, нужно ввести число людей без лишних подписей (Например: 300)')
            # bot.register_next_step_handler(message, handle_event_people_count)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_event_people_count)



#обработчик ввода оффера
def handle_event_offer(message):
    if message.text:
        if message.text[0] != '/':
            chat_id = message.chat.id
            try:
                if message.text == 'Пропустить':
                    users_db[chat_id]['offer'] = 'skip'
                else:
                    users_db[chat_id]['offer'] = message.text
            except KeyError:
                handle_cancel(message)
                return

            remove_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(chat_id, f'Оффер: {message.text}', reply_markup=remove_keyboard)


            headings_buttons = types.InlineKeyboardMarkup()
            for heading in base_headings.keys():
                btn = types.InlineKeyboardButton(heading, callback_data=heading)
                headings_buttons.add(btn)

            send_current_state(message.chat.id, 'user')
            sent_message = bot.send_message(chat_id, f"Выберите рубрику мероприятия", reply_markup=headings_buttons)
            users_db[chat_id]['current_message'] = sent_message.message_id
        elif message.text == '/cancel':
            handle_cancel(message)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_event_offer)




#обработка рубрики
@bot.callback_query_handler(func=lambda call: call.data in base_headings.keys())
def handle_event_heading(call):
    if call.data:
        if call.data == '/cancel':
            handle_cancel(call)
        else:
            try:
                chat_id = call.message.chat.id
                users_db[chat_id]['heading'] = call.data
            except KeyError:
                handle_cancel(call.message)
                return

            bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)

            modified_hashtags = ['`' + hashtag + '`' for hashtag in biz_hashtags]
            reccomend_biz_hashtag = '\n'.join(modified_hashtags)



            if call.data == 'Бизнес':
                bot.send_message(chat_id, f'Вы выбрали рубрику: {call.data}\n \n'
                                          f'Для навигации по приложению мы используем хэштеги \n'
                                          f"Введите хэштеги мероприятия через пробел (запятые между хэштегами ставить не нужно)\n \n"
                                          f'Рекомендуемые хэштеги в рубрике {call.data}:\n'
                                          f'{reccomend_biz_hashtag}\n \n'
                                          f'Для того, чтобы скопировать хэштег, просто тапните по нему. \n'
                                          f'Считаете, что в рубрике необходим хэштег? Напишите админу об этом \n'
                             , parse_mode='Markdown')
            else:
                bot.send_message(chat_id, f'Вы выбрали рубрику: {call.data}\n \n'
                                          f"Введите хэштеги мероприятия (запятые между хэштегами ставить не нужно)\n \n"
                                 )
            bot.register_next_step_handler(call.message, handle_hashtags)
    else:
        bot.send_message(call.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(call, handle_event_heading)

#обработка хэштегов
def handle_hashtags(message):
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        else:
            if message.text[0] == "#":
                try:
                    chat_id = message.chat.id

                    if 'heading' in users_db[chat_id]:
                        base_hash = base_headings[users_db[chat_id]['heading']]
                    else:
                        base_hash = ''


                    if 'hashtags' in users_db:
                        users_db[chat_id]['hashtags'] += base_hash
                    else:
                        users_db[chat_id]['hashtags'] = base_hash

                    if 'data_hashtag' in users_db[chat_id]:
                        date_hash = users_db[chat_id]['data_hashtag']
                        base_date_hash = base_hash[:-1] + '_' + date_hash[1:4] + date_hash[-2] + date_hash[-1] + ' '
                        users_db[chat_id]['hashtags'] += base_date_hash

                    for hashtag in message.text.split(' '):
                        if 'data_hashtag' in users_db[chat_id]:
                            date_hash = users_db[chat_id]['data_hashtag']
                            extra_date_hash = hashtag + '_' + date_hash[1:4] + date_hash[-2] + date_hash[-1] + ' '
                            users_db[chat_id]['hashtags'] += extra_date_hash
                        else:
                            users_db[chat_id]['hashtags'] += hashtag

                except KeyError:
                    handle_cancel(message)
                    return
                send_current_state(chat_id, 'user')
                bot.send_message(chat_id, 'Введите описание (максимум 600 символов) \n')
                bot.register_next_step_handler(message, handle_description)
            else:
                bot.send_message(message.chat.id, f'Введите хэштеги с решеткой:\n'
                                                  f'Пример: #biz #Psy #magic'
                                 )
                bot.register_next_step_handler(message, handle_hashtags)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_hashtags)

#обработка описания
def handle_description(message):
    if message.text:
        if len(message.text) > 600:
            bot.send_message(message.chat.id, 'Слишком длинное сообщение')
            bot.register_next_step_handler(message, handle_description)
        else:
            if message.text == '/cancel':
                handle_cancel(message)
            else:
                try:
                    chat_id = message.chat.id
                    users_db[chat_id]['description'] = message.text
                except KeyError:
                    handle_cancel(message)
                    return
                send_current_state(chat_id, 'user')
                bot.send_message(chat_id, 'Введите адрес мероприятия \n')
                bot.register_next_step_handler(message, handle_address)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_description)


#обработка адреса
def handle_address(message):
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        else:
            try:
                chat_id = message.chat.id
                users_db[chat_id]['address'] = message.text
            except KeyError:
                handle_cancel(message)
                return
            send_current_state(chat_id, 'user')
            bot.send_message(chat_id, 'Укажите стоимость участия \n')
            bot.register_next_step_handler(message, handle_price)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_address)

#обработка стоимости
def handle_price(message):
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        else:
            try:
                chat_id = message.chat.id
                users_db[chat_id]['price'] = message.text
            except KeyError:
                handle_cancel(message)
                return
            send_current_state(chat_id, 'user')
            bot.send_message(chat_id, 'Укажите ссылку на регистрацию билетов,  '
                                      'это может быть сайт, лид форма, личка менеджера ТГ. '
                                      'В приложении запрещены ссылки на ватсап чаты, '
                                      'телеграм каналы и чаты (это реклама) \n')
            bot.register_next_step_handler(message, handle_url)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_price)

#обработка ссылки
def handle_url(message):
    if message.text:
        if message.text == '/cancel':
            handle_cancel(message)
        else:
            try:
                chat_id = message.chat.id
                users_db[chat_id]['url'] = message.text
            except KeyError:
                handle_cancel(message)
                return
            all_correct(chat_id)
    else:
        bot.send_message(message.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(message, handle_url)

def all_correct(chat_id):
    res = send_current_state(chat_id, 'user')
    if res == 'Error':
        return


    keyboard = types.InlineKeyboardMarkup()
    for button in buttons:
        btn = types.InlineKeyboardButton(button, callback_data=button)
        keyboard.add(btn)

    sent_message = bot.send_message(chat_id, 'Проверьте, всё ли верно?', reply_markup=keyboard)
    users_db[chat_id]['current_message'] = sent_message.message_id


@bot.callback_query_handler(func=lambda call: call.data in buttons)
def result_correct(call):
    if call.data:
        try:
            chat_id = call.message.chat.id
            users_db[chat_id]['result'] = call.data
        except KeyError:
            handle_cancel(call.message)
            return


        bot.edit_message_reply_markup(chat_id=chat_id, message_id=call.message.message_id, reply_markup=None)
        if call.data == 'Опубликовать':
            send_channel_result(chat_id)
            bot.send_message(chat_id, f'Успешно отправлено')
            bot.send_message(chat_id, f'Для создания нового объявления напишите команду /start')
        elif call.data == 'Создать объявление заново':
            handle_cancel(call.message)
            bot.send_message(call.message.chat.id, 'Введите /start для создания объявления заново')

    else:
        bot.send_message(call.chat.id, 'Некорректный ввод')
        bot.register_next_step_handler(call, result_correct)



# Обработка команды /cancel для отмены создания объявления
@bot.message_handler(commands=['cancel'])
def handle_cancel(message):
    chat_id = message.chat.id


    if chat_id in users_db:
        if 'current_message' in users_db[chat_id]:
            try:
                bot.edit_message_reply_markup(chat_id=chat_id, message_id=users_db[chat_id]['current_message'],
                                              reply_markup=None)
            except telebot.apihelper.ApiTelegramException:
                pass
        del users_db[chat_id]

    bot.send_message(chat_id, "Создание объявления отменено. Для создания нового напишите /start")


# Отправление текущего состояния объявления
def send_current_state(chat_id, source):
    if type(source) is list:
        user_id = list(users_db.keys())[0]
        user_data = users_db.get(user_id, {})
    else:
        user_data = users_db.get(chat_id, {})

    if 'date' in user_data:
        date_res_hash = datetime.strptime(str(user_data['date']), "%Y-%m-%d")
        output_date_hash = f"#{date_res_hash.strftime('%b_%d_%y').lower()}"
        users_db[list(users_db.keys())[0]]['data_hashtag'] = output_date_hash

        date_res = datetime.strptime(str(user_data['date']), "%Y-%m-%d")
        output_date = date_res.strftime("%d %B (%A)")
    else:
        output_date, output_date_hash = "", ""

    if 'offer' in user_data:
        if user_data['offer'] == 'skip':
            offer = ''
        else:
            offer = user_data['offer']
    else:
        offer = ''


    pattern = '\n'

    post_text = f'<strong>{user_data.get("topic", "")}</strong>\n' \
                f'«{user_data.get("event_name", "")}»\n \n' \
                f'{user_data.get("description", "")} \n \n' \
                f'🗓{output_date}\n' \
                f'⏰{user_data.get("time", "")}\n' \
                f'👥Кол-во участников: {user_data.get("people_count", "")}\n' \
                f'🏢Место: {user_data.get("address", "")} \n' \
                f'💸Цена: {user_data.get("price", "")} \n \n' \
                f'{offer}\n \n' \
                f'Разместил: @{user_data.get("username", "")} \n \n' \
                f'{user_data.get("hashtags", "").replace(pattern, " ").strip()} {output_date_hash}'

    post_text_short = f'<strong>{user_data.get("topic", "")}</strong>\n' \
                f'«{user_data.get("event_name", "")}»\n \n' \
                f'🗓{output_date}\n' \
                f'⏰{user_data.get("time", "")}\n' \
                f'👥Кол-во участников: {user_data.get("people_count", "")}\n \n' \
                f'{offer}\n \n' \
                f'{user_data.get("hashtags", "").replace(pattern, " ").strip()} {output_date_hash}'

    url_button, inline_keyboard = None, None
    if 'url' in user_data:
        url_button = types.InlineKeyboardButton("Регистрация", url=user_data['url'])
        inline_keyboard = types.InlineKeyboardMarkup().row(url_button) if url_button else None


    if len(post_text) <= 1024:
        try:
            if source == 'user':
                bot.send_message(chat_id, 'Сейчас объявление выглядит так:\n')
                bot.send_photo(chat_id, user_data.get('image', ''), caption=post_text, parse_mode='HTML', reply_markup=inline_keyboard)
            elif type(source) is list:
                if source[0] == 'channel':
                    if source[1] == 'long':
                        bot.send_photo(chat_id, user_data.get('image', ''), caption=post_text, parse_mode='HTML', reply_markup=inline_keyboard)
                    elif source[1] == 'short':
                        bot.send_photo(chat_id, user_data.get('image', ''), caption=post_text_short, parse_mode='HTML')
        except telebot.apihelper.ApiTelegramException as e:
            if source == 'user':
                bot.send_message(chat_id, 'Некорректная ссылка, создайте объявление заново, написав команду /start')
                if chat_id in users_db:
                    del users_db[chat_id]
            return 'Error'
    else:
        bot.send_message(chat_id, 'Объявление получилось слишком длинным и бот не может его обработать, создание отменено\n'
                                  'Сократите текст и создайте объявление заново командой /start')
        if chat_id in users_db:
            del users_db[chat_id]




# Обработчик сообщений вне создания объявлений
@bot.message_handler(func=lambda message: True)
def other_message_handle(message):
        bot.send_message(message.chat.id, f'Для создания нового объявления напишите команду /start\n \n'
                                          f'Для отмены процесса создания нынешнего, напишите /cancel'
                         )



def send_channel_result(chat_id):
    user_data = users_db.get(chat_id, {})
    id_long, id_short = None, None
    if 'city' in user_data:
        city = user_data['city']
        id_long = channel_ids_long[city]
        id_short = channel_ids_short[city]

    send_current_state(id_long, ['channel', 'long'])
    send_current_state(id_short, ['channel', 'short'])







# Запуск бота
if __name__ == "__main__":
    try:
        bot.infinity_polling(timeout=5, long_polling_timeout=10)
    except (ConnectionError, ReadTimeout) as e:
        sys.stdout.flush()
        os.execv(sys.argv[0], sys.argv)
    else:
        bot.infinity_polling(timeout=5, long_polling_timeout=10)


# conn.close()