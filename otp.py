import os
import random
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv, set_key

ENV_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), '.env')

load_dotenv(ENV_PATH, override=True)

_from_mail    = os.getenv('GMAIL', '')
_app_password = os.getenv('GMAIL_APP_PASSWORD', '')


def configure(email, password):
    global _from_mail, _app_password
    _from_mail    = email
    _app_password = password
    set_key(ENV_PATH, 'GMAIL', email)
    set_key(ENV_PATH, 'GMAIL_APP_PASSWORD', password)


def is_configured():
    return bool(_from_mail) and bool(_app_password)


def generate_otp():
    return ''.join(str(random.randint(0, 9)) for _ in range(6))


def send_otp(to_email, otp):
    if not is_configured():
        raise RuntimeError('Gmail not configured. Visit /setup-gmail.')
    msg = EmailMessage()
    msg['Subject'] = 'Your verification code'
    msg['From']    = _from_mail
    msg['To']      = to_email
    msg.set_content(f'Your OTP is: {otp}\n\nDo not share this code with anyone.')
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(_from_mail, _app_password)
        server.send_message(msg)
