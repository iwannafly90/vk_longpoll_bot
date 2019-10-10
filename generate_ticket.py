from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import requests

TEMPLATE_PATH = 'files/ticket-base.PNG'
FONT_PATH = 'files/Roboto-Regular.ttf'
FONT_SIZE = 20

BLACK = (0, 0, 0, 255)
NAME_OFFSET = (290, 150)
EMAIL_OFFSET = (290, 175)

AVATAR_SIZE = 80
AVATAR_OFFSET = (80, 140)


def generate_ticket(name, email):
    """
    Generating the ticket, that will then send to user

    :param name: name on the badge
    :param email: email on the badge
    :return: file with image of ticket
    """
    base = Image.open(TEMPLATE_PATH).convert('RGBA')
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    draw = ImageDraw.Draw(base)
    draw.text(NAME_OFFSET, name, font=font, fill=BLACK)
    draw.text(EMAIL_OFFSET, email, font=font, fill=BLACK)

    response = requests.get(url=f'https://api.adorable.io/avatars/{AVATAR_SIZE}/{email}')
    avatar_file_like = BytesIO(response.content)
    avatar = Image.open(avatar_file_like)

    base.paste(avatar, AVATAR_OFFSET)

    temp_file = BytesIO()
    base.save(temp_file, 'png')
    temp_file.seek(0)

    return temp_file
