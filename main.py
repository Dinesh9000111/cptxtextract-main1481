import os
import json
import requests
import logging
from pyrogram import Client, filters
from logging.handlers import RotatingFileHandler
from details import api_id, api_hash, bot_token, auth_users, sudo_user, log_channel, txt_channel
from utils import get_datetime_str, create_html_file

# Logging configuration
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

# Ensure assets directory exists
if not os.path.exists('assets'):
    os.makedirs('assets')

# Bot initialization with environment variables
bot = Client(
    "bot",
    api_id=os.getenv('API_ID', 4942197),  # Default to your API_ID if not set in environment
    api_hash=os.getenv('API_HASH', '13248a2c551b73193969b42194023635'),
    bot_token=os.getenv('BOT_TOKEN', '7601280525:AAGK3HTLou0IzpTG1I2GShX0baxei4NExpc'),
)

# Helper function to get course content
def get_course_content(session, course_id, folder_id=0):
    fetched_contents = []
    params = {'courseId': course_id, 'folderId': folder_id}
    res = session.get(f'{api}/course/content/get', params=params)

    if res.status_code == 200:
        res = res.json()
        contents = res['data']['courseContent']
        for content in contents:
            if content['contentType'] == 1:
                resources = content['resources']
                if resources['videos'] or resources['files']:
                    sub_contents = get_course_content(session, course_id, content['id'])
                    fetched_contents += sub_contents
            else:
                name = content['name']
                url = content['url']
                fetched_contents.append(f'{name}: {url}')
    return fetched_contents

@bot.on_message(filters.command(["start"]))
async def start(bot, update):
    await update.reply_text(
        "Hi! I am **Classplus txt Downloader**.\n\n"
        "**NOW:-** Press **/classplus** to continue..\n\n"
    )

@bot.on_message(filters.command(["classplus"]))
async def account_login(bot: Client, m: Message):
    try:
        # Ensure the message for login credentials is sent
        reply = await m.reply(
            '**Send your credentials as shown below.\n\n'
            'Organisation Code\n'
            'Phone Number\n\n'
            'OR\n\n'
            'Access Token**'
        )
        
        creds = reply.text  # Retrieve the user's credentials
        session = requests.Session()
        session.headers.update(headers)

        logged_in = False
        if '\n' in creds:  # If credentials include org code and phone number
            org_code, phone_no = [cred.strip() for cred in creds.split('\n')]

            if org_code.isalpha() and phone_no.isdigit() and len(phone_no) == 10:
                res = session.get(f'{api}/orgs/{org_code}')
                if res.status_code == 200:
                    res = res.json()
                    org_id = int(res['data']['orgId'])

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
                        otp_reply = await message.chat.ask(
                            '**Send OTP?**', reply_to_message_id=reply.id
                        )

                        if otp_reply.text.isdigit():
                            otp = otp_reply.text.strip()
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
                                await reply.reply(
                                    f'Your Access Token for future uses - \n\n<pre>{token}</pre>',
                                    quote=True
                                )
                                logged_in = True
                            else:
                                raise Exception('Failed to verify OTP.')
                        else:
                            raise Exception('Failed to validate OTP.')
                    else:
                        raise Exception('Failed to generate OTP.')
                else:
                    raise Exception('Failed to get organization Id.')
            else:
                raise Exception('Failed to validate credentials.')
        else:  # Using access token directly
            token = creds.strip()
            session.headers['x-access-token'] = token
            res = session.get(f'{api}/users/details')

            if res.status_code == 200:
                res = res.json()
                user_id = res['data']['responseData']['user']['id']
                logged_in = True
            else:
                raise Exception('Failed to get user details.')

        # If logged in successfully, fetch and send course content
        if logged_in:
            params = {'userId': user_id, 'tabCategoryId': 3}
            res = session.get(f'{api}/profiles/users/data', params=params)

            if res.status_code == 200:
                res = res.json()
                courses = res['data']['responseData']['coursesData']
                if courses:
                    text = ''
                    for cnt, course in enumerate(courses):
                        name = course['name']
                        text += f'{cnt + 1}. {name}\n'
                    reply = await message.chat.ask(
                        f'**Send index number of the course to download.**\n\n{text}',
                        reply_to_message_id=reply.id
                    )

                    if reply.text.isdigit() and len(reply.text) <= len(courses):
                        selected_course_index = int(reply.text.strip())
                        course = courses[selected_course_index - 1]
                        selected_course_id = course['id']
                        selected_course_name = course['name']

                        loader = await reply.reply('**Extracting course...**', quote=True)
                        course_content = get_course_content(session, selected_course_id)

                        await loader.delete()

                        if course_content:
                            caption = (
                                '**App Name : Classplus\n'
                                f'Batch Name : {selected_course_name}'
                            )

                            # Write to text and html files
                            text_file = f'assets/{get_datetime_str()}.txt'
                            with open(text_file, 'w') as f:
                                f.writelines(course_content)

                            await bot.send_document(
                                m.chat.id,
                                text_file,
                                caption=caption,
                                file_name=f"{selected_course_name}.txt",
                                reply_to_message_id=reply.id
                            )

                            html_file = f'assets/{get_datetime_str()}.html'
                            create_html_file(html_file, selected_course_name, course_content)

                            await bot.send_document(
                                m.chat.id,
                                html_file,
                                caption=caption,
                                file_name=f"{selected_course_name}.html",
                                reply_to_message_id=reply.id
                            )

                            # Cleanup files
                            os.remove(text_file)
                            os.remove(html_file)
                        else:
                            raise Exception('No content found in the course.')
                    else:
                        raise Exception('Invalid course selection.')
                else:
                    raise Exception('No courses found.')
            else:
                raise Exception('Failed to get courses.')

    except Exception as error:
        LOGGER.error(f'Error: {error}')  # Log the error
        await m.reply(f'**Error:** {str(error)}', quote=True)

bot.run()
