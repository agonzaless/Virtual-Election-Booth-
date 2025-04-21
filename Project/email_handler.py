from flask_mail import Mail, Message
import os
import random
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

class MultiEmailHandler:
    def __init__(self, app):
        self.app = app
        self.primary_email = "Virtiualelection123456789@outlook.com"
        self.email_configs = {}
        self.logger = self._setup_logger()
        self.setup_email_providers()

        print("Current Environment Variables:")
        print(f"OUTLOOK_1: {os.getenv('OUTLOOK_USERNAME_1')}")
        print("Email Configurations Loaded:", bool(self.email_configs))

    def _setup_logger(self):
        logger = logging.getLogger('MultiEmailHandler')
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler('email_debug.log')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def setup_email_providers(self):
        gmail_config = {
            'username': os.getenv('GMAIL_USERNAME_1'),
            'password': os.getenv('GMAIL_PASSWORD_1'),
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587
        }

        outlook_config = {
            'username': os.getenv('OUTLOOK_USERNAME_1'),
            'password': os.getenv('OUTLOOK_PASSWORD_1'),
            'smtp_server': 'smtp-mail.outlook.com',
            'smtp_port': 587
        }

        self.email_configs['gmail'] = gmail_config
        self.email_configs['outlook'] = outlook_config

        print(f"Email providers configured: {list(self.email_configs.keys())}")

    def _load_gmail_accounts(self):
        accounts = []
        i = 1
        while True:
            username = os.getenv(f'GMAIL_USERNAME_{i}')
            password = os.getenv(f'GMAIL_PASSWORD_{i}')
            if not username or not password:
                break
            accounts.append({
                'id': i,
                'username': username,
                'password': password
            })
            i += 1
        return accounts

    def _load_outlook_accounts(self):
        accounts = []
        i = 1
        while True:
            username = os.getenv(f'OUTLOOK_USERNAME_{i}')
            password = os.getenv(f'OUTLOOK_PASSWORD_{i}')
            if not username or not password:
                break
            accounts.append({
                'id': i,
                'username': username,
                'password': password
            })
            i += 1
        return accounts

    def send_email(self, to_email, subject, body, provider='outlook'):
        try:
            print(f"Attempting to send email to {to_email} using {provider}")
            config = self.email_configs.get(provider)

            if not config:
                print(f"{provider} configuration not found")
                return False

            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'])
            server.starttls()
            print(f"Connecting to {provider} SMTP with username: {config['username']}")
            server.login(config['username'], config['password'])

            msg = MIMEMultipart()
            msg['From'] = self.primary_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))

            server.send_message(msg)
            server.quit()
            print(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            print(f"Error sending email: {str(e)}")
            self.logger.error(f"Failed to send email via {provider}: {str(e)}")

            if provider == 'gmail':
                print("Attempting to send via Outlook as fallback")
                return self.send_email(to_email, subject, body, provider='outlook')
            return False
