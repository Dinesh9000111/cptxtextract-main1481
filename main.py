import requests
import json
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from logging.handlers import RotatingFileHandler
import os

# Logger setup
LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler("log.txt", maxBytes=5000000, backupCount=10),
        logging.StreamHandler(),
    ],
)

# Bot setup
bot = Client(
    "bot",
    api_id=24692763,
    api_hash="8e3840420e9d0895db3231d87c6d21a5",
    bot_token="7601280525:AAGK3HTLou0IzpTG1I2GShX0baxei4NExpc"
)

# Headers
headers = {
    'accept-encoding': 'gzip',
    'accept-language': 'EN',
    'api-version': '35',
    'app-version': '1.4.73.2',
    'build-number': '35',
    'connection': 'Keep-Alive',
    'content-type': 'application/json',
    'device-details': 'Xiaomi_Redmi 7_SDK-32',
    'device-id': 'c28d3cb16bbdac01',
    'host': 'api.classplusapp.com',
    'region': 'IN',
    'user-agent': 'Mobile-Android',
    'webengage-luid': '00000187-6fe4-5d41-a530-26186858be4c'
}

api = 'https://api.classplusapp.com/v2'

@bot.on_message(filters.command(["start"]))
async def start(bot, update):
    await update.reply_text(
        "Hi, I am **Classplus txt Downloader**.\n\n"
        "**NOW:-** Press **/classplus** to continue..\n\n"
    )

@bot.on_message(filters.command(["classplus"]))
async def account_login(bot: Client, m: Message):
    try:
        # Send clear instructions for input
        reply = await m.reply(
            '**'
            'Send your credentials in the following format:\n\n'
            'Organisation Code\n'
            'Phone Number\n\n'
            'Example:\n'
            'ABC123\n'
            '9876543210\n\n'
            'OR\n\n'
            'Access Token'
            '**'
        )

        creds = m.text.strip()  # Get the text sent by the user

        creds_list = creds.split('\n')  # Split by newline to get the credentials

        if len(creds_list) == 2:
            org_code, phone_no = creds_list

            # Validate organisation code and phone number format
            if not (org_code.isalpha() and phone_no.isdigit() and len(phone_no) == 10):
                raise Exception('Invalid Organisation Code or Phone Number format.')

        elif len(creds_list) == 1:
            token = creds.strip()
            session = requests.Session()
            session.headers['x-access-token'] = token
        else:
            raise Exception('Invalid input. Please send exactly two values: Organisation Code and Phone Number.')

        session = requests.Session()
        session.headers.update(headers)

        # Now start the login process
        logged_in = False
        if len(creds_list) == 2:  # If using Organisation Code and Phone Number
            org_code, phone_no = creds_list

            # Get Organization ID from the API
            res = session.get(f'{api}/orgs/{org_code}')
            if res.status_code == 200:
                res = res.json()
                org_id = int(res['data']['orgId'])

                # Generate OTP
                data = {
                    'countryExt': '91',
                    'mobile': phone_no,
                    'viaSms': 1,
                    'orgId': org_id,
                    'eventType': 'login',
                    'otpHash': 'j7ej6eW5VO'
                }

                res = session.post(f'{api}/otp/generate', data=json.dumps(data))
                if res.status_code == 200:
                    res = res.json()
                    session_id = res['data']['sessionId']

                    reply = await m.reply(
                        '**Send OTP**', reply_to_message_id=reply.id
                    )

                    if reply.text.isdigit():
                        otp = reply.text.strip()

                        data = {
                            'otp': otp,
                            'sessionId': session_id,
                            'orgId': org_id,
                            'fingerprintId': 'a3ee05fbde3958184f682839be4fd0f7',
                            'countryExt': '91',
                            'mobile': phone_no,
                        }

                        res = session.post(f'{api}/users/verify', data=json.dumps(data))
                        if res.status_code == 200:
                            res = res.json()
                            user_id = res['data']['user']['id']
                            token = res['data']['token']

                            session.headers['x-access-token'] = token
                            logged_in = True
                        else:
                            raise Exception('Failed to verify OTP.')
                    else:
                        raise Exception('Failed to validate OTP.')
                else:
                    raise Exception('Failed to generate OTP.')
            else:
                raise Exception('Failed to get organization Id.')

        elif len(creds_list) == 1:  # If using Access Token
            token = creds.strip()
            session.headers['x-access-token'] = token

            # Get user details with the token
            res = session.get(f'{api}/users/details')
            if res.status_code == 200:
                res = res.json()
                user_id = res['data']['responseData']['user']['id']
                logged_in = True
            else:
                raise Exception('Failed to get user details.')

        if logged_in:
            await m.reply(
                '**You are logged in successfully. Now proceed with downloading courses.**',
                reply_to_message_id=reply.id
            )
        else:
            raise Exception('Login failed.')

    except Exception as error:
        # Log error and notify the user
        LOGGER.error(f'Error: {error}')
        await m.reply(f'Error: {error}', quote=True)

bot.run()
