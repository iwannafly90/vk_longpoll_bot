from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock

from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotMessageEvent, VkBotEventType

import generate_ticket
import settings
from bot import Bot


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session as session:
            test_func(*args, **kwargs)
            rollback()
    return wrapper


class Test(TestCase):
    RAW_EVENT = {'type': VkBotEventType.MESSAGE_NEW,
                 'object': {'date': 1568752761, 'from_id': 80901374, 'id': 31, 'out': 0,
                            'peer_id': 80901374, 'text': 'test', 'conversation_message_id': 31,
                            'fwd_messages': [], 'important': False, 'random_id': 0, 'attachments': [],
                            'is_hidden': False},
                 'group_id': 186460053}

    INPUTS = [
        'Привет',
        "А когда?",
        "Где будет конферецния?",
        "Зарегистрируй меня",
        "Вениамин",
        "мой адрес email@email",
        "email@email.ru",
    ]

    EXPECTED_OUTPUTS = [
        settings.DEFAULT_ANSWER,
        settings.INTENTS[0]['answer'],
        settings.INTENTS[1]['answer'],
        settings.SCENARIOS['registration']['steps']['step1']['text'],
        settings.SCENARIOS['registration']['steps']['step2']['text'],
        settings.SCENARIOS['registration']['steps']['step2']['failure_text'],
        settings.SCENARIOS['registration']['steps']['step3']['text'].format(name='Вениамин', email='email@email.ru')
    ]

    @isolate_db
    def test_run_ok(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['text'] = input_text
            events.append(VkBotMessageEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('bot.bot_longpoll.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.send_image = Mock()
            bot.run()

        assert send_mock.call_count == len(self.INPUTS)

        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])

        assert real_outputs == self.EXPECTED_OUTPUTS

    def test_image_generation(self):
        with open('files/Rty.png', 'rb') as avatar_file:
            avatar_mock = Mock()
            avatar_mock.content = avatar_file.read()

        with patch('requests.get', return_value=avatar_mock):
            ticket_file = generate_ticket.generate_ticket('Qwe', 'Rty')

        with open('files/ticket-example.png', 'rb') as expected_file:
            expected_bytes = expected_file.read()

        assert ticket_file.read() == expected_bytes
