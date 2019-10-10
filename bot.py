import requests
import vk_api
import vk_api.bot_longpoll as bot_longpoll
import os
import random
import logging

from pony.orm import db_session

import handlers
from models import UserState, Registration

try:
    import settings
except ImportError:
    print('DO cp settings.py.default settings.py and set token')


log = logging.getLogger('bot')


def configure_logging():
    """Configuring loggers to log"""

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    stream_handler.setLevel(logging.DEBUG)
    log.addHandler(stream_handler)

    file_handler = logging.FileHandler('bot.log', encoding='utf8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', "%d-%m-%Y %H:%M"))
    log.addHandler(file_handler)
    log.setLevel(logging.DEBUG)


class Bot:

    def __init__(self, group_id, token):
        """

        :param group_id: vk group id
        :param token: token, generated vk for api
        """
        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=token)
        self.long_poller = bot_longpoll.VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """
        Bot run
        """
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception as err:
                log.exception('ошибка в обработке события')

    @db_session
    def on_event(self, event):
        """
        Handles vk bot events

        :param event: VkBotMessageEvent object
        :return: None
        """
        if event.type != bot_longpoll.VkBotEventType.MESSAGE_NEW:
            log.info('мы пока не умеем обрабатывать событие такого типа %s', event.type)
            return

        user_id = event.object.peer_id
        text = event.object.text

        state = UserState.get(user_id=str(user_id))

        if state is not None:
            # continue scenario
            self.continue_scenario(text, state, user_id)
        else:
            # search intent
            for intent in settings.INTENTS:
                if any(token in text.lower() for token in intent['tokens']):
                    if intent['answer']:
                        # text_to_send = intent['answer']
                        self.send_text(intent['answer'], user_id)
                    else:
                        self.start_scenario(user_id, intent['scenario'], text)
                    break
            else:
                self.send_text(settings.DEFAULT_ANSWER, user_id)

    def send_text(self, text_to_send, user_id):
        """
        Sending text to user

        :param text_to_send: text, that will be send
        :param user_id: vk user id
        :return: None
        """
        self.api.messages.send(
            message=text_to_send,
            random_id=random.randint(0, 2**20),
            peer_id=user_id)

    def send_image(self, image, user_id):
        """
        Sending image to user

        :param image: image, that will be send
        :param user_id: vk user id
        :return: None
        """
        upload_url = self.api.photos.getMessagesUploadServer()['upload_url']
        upload_data = requests.post(url=upload_url, files={'photo': ('image.png', image, 'image/png')}).json()
        image_data = self.api.photos.saveMessagesPhoto(**upload_data)

        owner_id = image_data[0]['owner_id']
        media_id = image_data[0]['id']
        attachment = f'photo{owner_id}_{media_id}'

        self.api.messages.send(
            attachment=attachment,
            random_id=random.randint(0, 2 ** 20),
            peer_id=user_id)

    def send_step(self, step, user_id, text, context):
        """
        Executes the scenario step

        :param step: current scenario step
        :param user_id: vk user id
        :param text: text for handler
        :param context: dict with parameters
        :return: None
        """
        if 'text' in step:
            self.send_text(step['text'].format(**context), user_id)
        if 'image' in step:
            handler = getattr(handlers, step['image'])
            image = handler(text, context)
            self.send_image(image, user_id)

    def start_scenario(self, user_id, scenario_name, text):
        """
        Starts user scenario

        :param user_id: vk user id
        :param scenario_name: name of the starting scenario
        :param text: parameter for handler
        :return: None
        """
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        self.send_step(step, user_id, text, context={})
        UserState(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})

    def continue_scenario(self, text, state, user_id):
        """
        Continues user scenario

        :param text: parameter for handler
        :param state: current state
        :param user_id: vk user id
        :return: None
        """
        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]

        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            # next step
            next_step = steps[step['next_step']]
            self.send_step(next_step, user_id, text, state.context)
            if next_step['next_step']:
                # switch to next_step
                state.step_name = step['next_step']
            else:
                # finish scenario
                log.info('Зарегистрирован: {name} {email}'.format(**state.context))
                Registration(name=state.context['name'], email=state.context['email'])
                state.delete()
        else:
            # retry current step
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send, user_id)


if __name__ == '__main__':
    configure_logging()
    bot = Bot(settings.GROUP_ID, settings.TOKEN)
    bot.run()
