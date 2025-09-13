import os
from datetime import datetime

from flask import make_response, request

EMAIL_BODY = ("""
To: {email}
Subject: PASSWORD RESET
Date: {date}

To reset your password, use the following token: {reset_token}
Or click the link below: {reset_url}
The token is valid for 1 hour.
If you did not request a password reset, please ignore this email.
""")


def generate_download_file(dictionary, user):
    total_translations = len(dictionary)
    text_content = (
        f'User dictionary: {user.username}\n'
        f'Translations count: {total_translations}\n'
        f'Date created: {datetime.utcnow().strftime("%d.%m.%Y %H:%M")}\n\n'
    )

    for i, item in enumerate(dictionary, 1):
        text_content += f'{i}. {item.text} - {item.translation}\n'

    response = make_response(text_content)
    response.headers['Content-Type'] = 'text/plain; charset=utf-8'
    response.headers['Content-Disposition'] = 'attachment; filename="my_dictionary.txt"'
    return response


def send_reset_email(email, reset_token):
    reset_url = (
        f'{request.host_url}api/auth/reset-password?token={reset_token}'
    )
    emails_dir = os.path.join(os.path.dirname(__file__), 'emails')
    os.makedirs(emails_dir, exist_ok=True)
    filename = f'{email}'
    filepath = os.path.join(emails_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(EMAIL_BODY.format(
            reset_url=reset_url, reset_token=reset_token,
            email=email, date={datetime.now().strftime("%d.%m.%Y %H:%M")}
        ))
    return True
