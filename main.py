import asyncio
import logging
import aiohttp
import re
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import TimeoutError

# Your Bot Credentials
api_id = '24692763'
api_hash = '8e3840420e9d0895db3231d87c6d21a5'
bot_token = '8073469304:AAFS0nwpbKhAfsPaS87v_9j5AHA_lVlIqmo'

# Pyrogram Client
app = Client("my_bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

@app.on_message(filters.command("start"))
async def start_handler(bot: Client, message: Message):
    await message.reply(
        "Welcome! Please choose an option:\n\n"
        "/start to start your process or\n"
        "Click the button below",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Start Process", callback_data="button_command")]
        ])
    )

@app.on_callback_query()
async def callback_query_handler(bot: Client, query: CallbackQuery):
    await handle_query(bot, query)

# Handle Button Query
async def handle_query(bot: Client, query: CallbackQuery):
    user_id = query.from_user.id
    await query.answer()

    if query.data == "button_command":
        await process_cpwp(bot, query.message, user_id)
    else:
        await query.message.reply("Invalid command!")

# Main Function
async def process_cpwp(bot: Client, m: Message, user_id: int):
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

    loop = asyncio.get_event_loop()
    CONNECTOR = aiohttp.TCPConnector(limit=1000, loop=loop)
    async with aiohttp.ClientSession(connector=CONNECTOR, loop=loop) as session:
        editable = await m.reply_text("**Enter ORG Code Of Your Classplus App**")

        try:
            input1 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
            org_code = input1.text.lower()
            await input1.delete(True)
        except TimeoutError:
            await editable.edit("**Timeout! You took too long to respond**")
            return
        except Exception as e:
            logging.exception("Error during input1 listening:")
            await editable.edit(f"**Error: {e}**")
            return

        hash_headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f'https://{org_code}.courses.store',
            'Sec-CH-UA': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            'Sec-CH-UA-Mobile': '?0',
            'Sec-CH-UA-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0.0.0 Safari/537.36'
        }

        async with session.get(f"https://{org_code}.courses.store", headers=hash_headers) as response:
            html_text = await response.text()
            hash_match = re.search(r'"hash":"(.*?)"', html_text)

            if not hash_match:
                await editable.edit("**Couldn't Find Course Hash!**")
                return

            token = hash_match.group(1)

            async with session.get(f"https://api.classplusapp.com/v2/course/preview/similar/{token}?limit=20", headers=headers) as response:
                if response.status != 200:
                    await editable.edit("**Failed to fetch course list!**")
                    return

                res_json = await response.json()
                courses = res_json.get('data', {}).get('coursesData', [])

                if not courses:
                    await editable.edit("**No Courses Found!**")
                    return

                text = ''
                for cnt, course in enumerate(courses):
                    name = course['name']
                    price = course['finalPrice']
                    text += f'{cnt + 1}. ```{name} 💵₹{price}```\n'

                await editable.edit(f"**Send index number of the Category Name\n\n{text}\nIf Your Batch Not Listed Then Enter Your Batch Name**")

                try:
                    input2 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                    raw_text2 = input2.text
                    await input2.delete(True)
                except TimeoutError:
                    await editable.edit("**Timeout! You took too long to respond**")
                    return
                except Exception as e:
                    logging.exception("Error during input2 listening:")
                    await editable.edit(f"**Error: {e}**")
                    return

                if raw_text2.isdigit() and 1 <= int(raw_text2) <= len(courses):
                    selected_course_index = int(raw_text2.strip())
                    course = courses[selected_course_index - 1]
                else:
                    search_url = f"https://api.classplusapp.com/v2/course/preview/similar/{token}?search={raw_text2}"
                    async with session.get(search_url, headers=headers) as response:
                        if response.status != 200:
                            await editable.edit("**Failed to search batch!**")
                            return

                        res_json = await response.json()
                        courses = res_json.get("data", {}).get("coursesData", [])

                        if not courses:
                            await editable.edit("**Didn't Find Any Course**")
                            return

                        text = ''
                        for cnt, course in enumerate(courses):
                            name = course['name']
                            price = course['finalPrice']
                            text += f'{cnt + 1}. ```{name} 💵₹{price}```\n'
                        await editable.edit(f"**Send index number of the Batch to download.\n\n{text}**")

                        try:
                            input3 = await bot.listen(chat_id=m.chat.id, filters=filters.user(user_id), timeout=120)
                            raw_text3 = input3.text
                            await input3.delete(True)
                        except TimeoutError:
                            await editable.edit("**Timeout! You took too long to respond**")
                            return
                        except Exception as e:
                            logging.exception("Error during input3 listening:")
                            await editable.edit(f"**Error: {e}**")
                            return

                        if raw_text3.isdigit() and 1 <= int(raw_text3) <= len(courses):
                            selected_course_index = int(raw_text3.strip())
                            course = courses[selected_course_index - 1]
                        else:
                            await editable.edit("**Wrong Index Number Provided!**")
                            return

                # Successfully selected a course
                selected_batch_id = course['id']
                selected_batch_name = course['name']
                price = course['finalPrice']
                clean_batch_name = selected_batch_name.replace("/", "-").replace("|", "-")
                clean_file_name = f"{user_id}_{clean_batch_name}"

                await editable.edit(f"**Batch Selected Successfully!**\n\n**Batch Name:** {selected_batch_name}\n**Price:** ₹{price}")

if __name__ == "__main__":
    app.run()
