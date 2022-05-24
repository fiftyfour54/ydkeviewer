import base64
import json
import math
import os.path
import discord
import os
import tempfile
from dotenv import load_dotenv
from urllib import request

import numpy

from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv("token.env")
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot(debug_guilds=[747929507943415838], intents=intents)


# unimplemented
def base64_to_passcodes(b64: str):
    pass


def parse_url(url: str):
    try:
        if url.startswith("ydke://"):
            elems = url[len("ydke://"):].split("!")
        else:
            elems = url.split("!")
        if len(elems) < 3:
            raise (IOError("Missing ydk URL component"))
        a = base64.decodebytes(elems[0].encode("ascii"))
        b = base64.decodebytes(elems[1].encode("ascii"))
        c = base64.decodebytes(elems[2].encode("ascii"))
        return {"main": numpy.frombuffer(a, dtype=numpy.uint32).tolist(),
                "extra": numpy.frombuffer(b, dtype=numpy.uint32).tolist(),
                "side": numpy.frombuffer(c, dtype=numpy.uint32).tolist()}

    except IOError as e:
        print(e)


def get_image(c_id):
    if not os.path.exists("pics/{0}.jpg".format(c_id)):
        request.urlretrieve(
            'https://storage.googleapis.com/ygoprodeck.com/pics/{0}.jpg'.format(c_id), 'pics/{0}.jpg'.format(c_id)
        )
    return 'pics/{0}.jpg'.format(c_id)


def get_card(db, c_id):
    for i in db["data"]:
        for img in i["card_images"]:
            if img["c_id"] == c_id:
                return i
    return None


def gen_list(input_string):
    with open("cardinfo.json") as read_file:
        json_db = json.load(read_file)

    a = parse_url(input_string)
    cursor_x = 25.0
    cursor_y = 42.0
    bg = Image.open("bg.jpg").convert('RGBA')

    i = 0
    sp_ct = 0
    t_ct = 0
    m_ct = 0
    f_sp = {}
    # Field Spell background
    for img in a.get("main"):
        c_data = get_card(json_db, img)
        if c_data is None:
            print("NO CARD FOUND WITH " + str(img))
        else:
            if "Monster" in c_data["type"]:
                m_ct += 1
            elif "Spell" in c_data["type"]:
                sp_ct += 1
                if "Field" in c_data["race"]:
                    if img not in f_sp:
                        f_sp[img] = 0
                    f_sp[img] = f_sp[img] + 1
            elif "Trap" in c_data["type"]:
                t_ct += 1
    if len(f_sp) == 0:
        for img in a.get("side"):
            c_data = get_card(json_db, img)
            if c_data is None:
                print("NO CARD FOUND WITH " + str(img))
            else:
                if "Spell" in c_data["type"]:
                    sp_ct += 1
                    if "Field" in c_data["race"]:
                        if img not in f_sp:
                            f_sp[img] = 0
                        f_sp[img] = f_sp[img] + 1
    # Draw Background
    if len(f_sp) != 0:
        key = max(f_sp, key=f_sp.get)
        if os.path.exists("field/" + str(key) + ".png"):
            img = Image.open("field/" + str(key) + ".png")
            img = img.resize((1000, 1000), resample=Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(5))
            bg.paste(img, (0, 0))
        else:
            fimg = get_image(key)
            fmg = Image.open(fimg)
            cropper = fmg.crop((49, 111, 49 + 323, 111 + 323))
            cropper.save("field/" + str(key) + ".png")
            img = cropper.resize((1000, 1000), resample=Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(5))
            bg.paste(img, (0, 0))
    img_boxes = Image.open("boxes.png")
    bg.paste(img_boxes, (0, 0), mask=img_boxes)
    # Draw deck
    for img in a.get("main"):
        img1 = Image.open(get_image(img))
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.Resampling.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))
        if len(a.get("main")) <= 40:
            cursor_x += 860 / 9
            if i >= 9:
                cursor_y += 135.0
                cursor_x = 25.0
                i = 0
            else:
                i += 1
        else:
            cursor_x += 860 / (math.ceil(len(a.get("main")) / 4) - 1)
            if i > math.ceil(len(a.get("main")) / 4) - 2:
                cursor_y += 135
                cursor_x = 25
                i = 0
            else:
                i += 1
    cursor_x = 25.0
    cursor_y = 635.0
    fm_ct = 0
    sm_ct = 0
    xm_ct = 0
    lm_ct = 0
    # Count cards
    for img in a.get("extra"):
        c_data = get_card(json_db, img)
        if c_data is None:
            print("NO CARD FOUND WITH " + str(img))
        else:
            if "Fusion" in c_data["type"]:
                fm_ct += 1
            elif "Synchro" in c_data["type"]:
                sm_ct += 1
            elif "XYZ" in c_data["type"]:
                xm_ct += 1
            elif "Link" in c_data["type"]:
                lm_ct += 1
        img1 = Image.open(get_image(img))
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.Resampling.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))
        if len(a.get("extra")) > 1:
            cursor_x += min(860 / (len(a.get("extra")) - 1), 95)
    cursor_x = 25.0
    cursor_y = 815.0
    s_sp_ct = 0
    s_t_ct = 0
    s_m_ct = 0
    for img in a.get("side"):
        c_data = get_card(json_db, img)
        if c_data is None:
            print("NO CARD FOUND WITH " + str(img))
        else:
            if "Monster" in c_data["type"]:
                s_m_ct += 1
            elif "Spell" in c_data["type"]:
                s_sp_ct += 1
            elif "Trap" in c_data["type"]:
                s_t_ct += 1
        img1 = Image.open(get_image(img))
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.Resampling.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))
        if len(a.get("side")) > 1:
            cursor_x += min(860 / (len(a.get("side")) - 1), 95)

    mfont = ImageFont.truetype("DejaVuSans.ttf", 20)
    boxbg = Image.new('RGBA', bg.size, (255, 255, 255, 0))
    boxtxt = ImageDraw.Draw(boxbg)
    # main text
    twidth, theight = mfont.getsize("Monsters: {0} Spells: {1} Traps: {2}".format(m_ct, sp_ct, t_ct))
    boxtxt.rounded_rectangle((16, 0, 30 + twidth, 9 + theight), fill=(64, 64, 64, 192), radius=5)
    # main count
    twidth, theight = mfont.getsize("Main Deck: {0}".format(str(len(a.get("main")))))
    boxtxt.rounded_rectangle((983 - twidth - 5, 0, 983, 32), fill=(64, 64, 64, 192), radius=5)

    # extra
    twidth, theight = mfont.getsize("Fusion: {0} Synchro: {1} Xyz: {2} Link: {3}".format(fm_ct, sm_ct, xm_ct, lm_ct))
    boxtxt.rounded_rectangle((16, 588, 30 + twidth, 588 + 12 + theight), fill=(64, 64, 64, 192), radius=5)
    twidth, theight = mfont.getsize("Extra Deck: {0}".format(str(len(a.get("extra")))))
    boxtxt.rounded_rectangle((983 - twidth - 5, 588, 983, 588 + 35), fill=(64, 64, 64, 192), radius=5)
    # side
    if len(a.get("side")) > 0:
        twidth, theight = mfont.getsize("Monsters: {0} Spells: {1} Traps: {2}".format(s_m_ct, s_sp_ct, s_t_ct))
        boxtxt.rounded_rectangle((16, 774, 30 + twidth, 774 + 6 + theight), fill=(64, 64, 64, 192), radius=5)
        twidth, theight = mfont.getsize("{0}".format("Side Deck: " + str(len(a.get("side")))))
        boxtxt.rounded_rectangle((983 - twidth - 5, 774, 983, 774 + 29), fill=(64, 64, 64, 192), radius=5)

    bg = Image.alpha_composite(bg, boxbg)
    bg2 = ImageDraw.Draw(bg)

    # main text
    bg2.text((25, 5), "Monsters: {0} Spells: {1} Traps: {2}".format(m_ct, sp_ct, t_ct), fill=(255, 255, 255),
             font=mfont)
    twidth, theight = mfont.getsize("{0}".format("Main Deck: " + str(len(a.get("main")))))
    bg2.text((983 - twidth, 5), "Main Deck: {0}".format(len(a.get("main"))), fill=(255, 255, 255), font=mfont,
             align='center')

    # extra text
    bg2.text((25, 595), "Fusion: {0} Synchro: {1} Xyz: {2} Link: {3}".format(fm_ct, sm_ct, xm_ct, lm_ct),
             fill=(255, 255, 255), font=mfont)
    twidth, theight = mfont.getsize("Extra Deck: {0}".format(str(len(a.get("extra")))))
    bg2.text((983 - twidth, 595), "Extra Deck: {0}".format(str(len(a.get("extra")))), fill=(255, 255, 255),
             font=mfont, align='center')

    # side text
    if len(a.get("side")) > 0:
        bg2.text((25, 777), "Monsters: {0} Spells: {1} Traps: {2}".format(s_m_ct, s_sp_ct, s_t_ct),
                 fill=(255, 255, 255), font=mfont)
        twidth, theight = mfont.getsize("Side Deck: {0}".format(str(len(a.get("side")))))
        bg2.text((983 - twidth, 777), "Side Deck: {0}".format(str(len(a.get("side")))), fill=(255, 255, 255),
                 font=mfont, align='center')
    else:
        bg = bg.crop((0, 0, 1000, 790))
    return bg


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"{bot.user} is ready and online!")


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith("ydke://"):
        await message.add_reaction(emoji="🕔")
        a = gen_list(message.content)
        temp = tempfile.TemporaryFile(suffix=".png", delete=False)
        a.save(temp, "PNG")
        temp.seek(0)
        await message.reply(file=discord.File(temp.name))
        await message.remove_reaction(emoji="🕔", member=client.user)
        temp.close()
        os.unlink(temp.name)


client.run(os.getenv('TOKEN'))
