"""
Handler - функция, которая принимает на вход text (текст входящего сообщения) и context (dict), а возвращает bool:
True, если шаг пройден, False если данные введены неправильно.
"""
import re

from generate_ticket import generate_ticket

re_name = re.compile(r'^[\w\-\s]{3,30}$')
re_email = re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b")


def handle_name(text, context):
    """
    Check whether the name is correct or not and if it is - putting this in context dict

    :param text: name, that user entered
    :param context: dict with parameters
    :return: bool
    """
    match = re.match(re_name, text)
    if match:
        context['name'] = text
        return True
    else:
        return False


def handle_email(text, context):
    """
    Check whether the email is correct or not and if it is - putting this in context dict

    :param text: email, that user entered
    :param context: dict with parameters
    :return: bool
    """
    matches = re.findall(re_email, text)
    if len(matches) > 0:
        context['email'] = matches[0]
        return True
    else:
        return False


def generate_ticket_handler(text, context):
    """
    Generating the ticket

    :param text:
    :param context: dict with parameters for creating the ticket
    :return: ticket file
    """
    return generate_ticket(name=context['name'], email=context['email'])
