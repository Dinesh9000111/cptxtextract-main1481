import requests
import json
import subprocess
from pyrogram.types import Message
import helper
from pyromod import listen
import pyrogram
from pyrogram import Client, filters, idle
from details import api_id, api_hash, bot_token, auth_users, sudo_user, log_channel, txt_channel
from subprocess import getstatusoutput
from utils import get_datetime_str, create_html_file
import asyncio, logging
from logging.handlers import RotatingFileHandler
import tgcrypto
import os
import sys
import re

LOGGER = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(name)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
    handlers=[
        RotatingFileHandler(
            "log.txt", maxBytes=5000000, backupCount=10
        ),
        logging.StreamHandler(),
    ],
)

bot = Client(
    "bot",
    api_id= 24692763,
    api_hash= "8e3840420e9d0895db3231d87c6d21a5",    
    bot_token= "7601280525:AAGK3HTLou0IzpTG1I2GShX0baxei4NExpc"
)

api = 'https://api.classplusapp.com/v2'

headers = {
    'accept-encoding': 'gzip',
    'accept-language': 'EN',
    'api-version'    : '35',
    'app-version'    : '1.4.73.2',
    'build-number'   : '35',
    'connection'     : 'Keep-Alive',
    'content-type'   : 'application/json',
    'device-details' : 'Xiaomi_Redmi 7_SDK-32',
    'device-id'      : 'c28d3cb16bbdac01',
    'host'           : 'api.classplusapp.com',
    'region'         : 'IN',
    'user-agent'     : 'Mobile-Android',
    'webengage-luid' : '00000187-6fe4-5d41-a530-26186858be4c'
}

# Step 1: /start command
@bot.on_message(filters.command(["start"]))
async def start(bot, message):
    await message.reply_text(
        "Hi, I am **Classplus txt Downloader**.\n\n"
        "**NOW:**\nPress **/classplus** to continue.."
    )

# Step 2: /classplus command -> just instruction
@bot.on_message(filters.command(["classplus"]))
async def classplus(bot, message):
    await message.reply_text(
        "**Send your credentials as shown below:**\n\n"
        "`Organisation Code`\n"
        "`Phone Number`\n\n"
        "**OR**\n\n"
        "`Access Token`"
    )

# Step 3: Credentials handle
@bot.on_message(filters.text & ~filters.command(["start", "classplus"]))
async def handle_credentials(bot: Client, message: Message):
    try:
        session = requests.Session()
        session.headers.update(headers)

        text = message.text.strip()
        lines = text.split('\n')

        logged_in = False

        if len(lines) == 2:
            org_code = lines[0].strip()
            phone_no = lines[1].strip()

            if org_code.isalpha() and phone_no.isdigit() and len(phone_no) == 10:
                res = session.get(f'{api}/orgs/{org_code}')
                res.raise_for_status()
                org_id = res.json().get('data', {}).get('orgId', None)

                if org_id is None:
                    await message.reply_text("**Error:** Invalid Organization Code or API response error.")
                    return

                data = {
                    'countryExt': '91',
                    'mobile': phone_no,
                    'viaSms': 1,
                    'orgId': int(org_id),
                    'eventType': 'login',
                    'otpHash': 'j7ej6eW5VO'
                }
                res = session.post(f'{api}/otp/generate', data=json.dumps(data))
                res.raise_for_status()

                session_id = res.json().get('data', {}).get('sessionId', None)

                if session_id is None:
                    await message.reply_text("**Error:** OTP generation failed.")
                    return

                await message.reply_text("Please send the OTP received:")

                otp_msg = await bot.listen(message.chat.id)
                otp = otp_msg.text.strip()

                verify_data = {
                    'otp': otp,
                    'sessionId': session_id,
                    'orgId': int(org_id),
                    'fingerprintId': 'a3ee05fbde3958184f682839be4fd0f7',
                    'countryExt': '91',
                    'mobile': phone_no,
                }
                res = session.post(f'{api}/users/verify', data=json.dumps(verify_data))
                res.raise_for_status()

                token = res.json().get('data', {}).get('token', None)

                if token is None:
                    await message.reply_text("**Error:** OTP verification failed.")
                    return

                session.headers['x-access-token'] = token
                logged_in = True

                await message.reply_text(f"**Your Access Token:**\n`{token}`")

            else:
                await message.reply_text("**Invalid Organisation Code or Phone Number.**")

        elif len(lines) == 1:
            token = lines[0]
            session.headers['x-access-token'] = token

            res = session.get(f'{api}/users/details')
            res.raise_for_status()

            logged_in = True

        else:
            await message.reply_text("**Invalid input. Please send Organisation Code and Phone Number OR Access Token.**")
            return

        # If logged in successfully, fetch courses
        if logged_in:
            data = res.json().get('data', {})

            if 'responseData' in data:
                user_id = data['responseData']['user']['id']
            else:
                user_id = data.get('user', {}).get('id', None)

            if user_id is None:
                await message.reply_text("**Error:** User ID not found.")
                return

            params = {
                'userId': user_id,
                'tabCategoryId': 3
            }
            res = session.get(f'{api}/profiles/users/data', params=params)
            res.raise_for_status()

            courses = res.json().get('data', {}).get('responseData', {}).get('coursesData', [])

            if not courses:
                await message.reply_text("No courses found.")
                return

            course_list = ""
            for idx, course in enumerate(courses, 1):
                course_list += f"{idx}. {course['name']}\n"

            await message.reply_text(
                "**Send the index number of course to download:**\n\n" + course_list
            )

            selected = await bot.listen(message.chat.id)
            index = int(selected.text.strip())

            selected_course = courses[index - 1]
            course_id = selected_course['id']
            course_name = selected_course['name']

            # Now get all course content
            content = await get_course_content(session, course_id)

            if not content:
                await message.reply_text("No content found in the course.")
                return

            caption = f"**App Name:** Classplus\n**Batch Name:** {course_name}"

            txt_file = f'assets/{get_datetime_str()}.txt'
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))

            await bot.send_document(
                message.chat.id,
                txt_file,
                caption=caption,
                file_name=f"{course_name}.txt",
                reply_to_message_id=message.id
            )

            os.remove(txt_file)

    except Exception as e:
        LOGGER.error(f"Error: {e}")
        await message.reply_text(f"**Error:** {e}")

async def get_course_content(session, course_id, folder_id=0):
    fetched_contents = []
    params = {'courseId': course_id, 'folderId': folder_id}
    res = session.get(f'{api}/course/content/get', params=params)

    if res.status_code == 200:
        contents = res.json().get('data', {}).get('courseContent', [])
        for content in contents:
            if content['contentType'] == 1:
                if content.get('resources', {}).get('videos') or content.get('resources', {}).get('files'):
                    sub_contents = await get_course_content(session, course_id, content['id'])
                    fetched_contents += sub_contents
            else:
                name = content['name']
                url = content['url']
                fetched_contents.append(f'{name}: {url}')
    return fetched_contents

bot.run()
