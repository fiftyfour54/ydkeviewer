import asyncio
import base64
import json
import math
import os.path
import random
import sqlite3
import string
import urllib
from io import BytesIO

import aiofiles
import discord
import os
import tempfile
from dotenv import load_dotenv
from urllib import request

import numpy

from PIL import Image, ImageDraw, ImageFont, ImageFilter

load_dotenv("token.env")


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
            raise (Exception("Missing ydk URL component"))
            return
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
        try:
            request.urlretrieve(
                'https://storage.googleapis.com/ygoprodeck.com/pics/{0}.jpg'.format(c_id), 'pics/{0}.jpg'.format(c_id)
            )
        except urllib.error.HTTPError as ex:
            if os.path.exists("pics_old/{0}.jpg".format(c_id)):
                return "pics_old/{0}.jpg".format(c_id)
            else:
                return None
    return 'pics/{0}.jpg'.format(c_id)


def get_image_art(c_id):
    if not os.path.exists("pics/{0}.jpg".format(c_id)):
        try:
            request.urlretrieve(
                'https://storage.googleapis.com/ygoprodeck.com/pics_artgame/{0}.jpg'.format(c_id),
                'field/{0}.jpg'.format(c_id)
            )
        except urllib.error.HTTPError as ex:
            return None
    return 'field/{0}.jpg'.format(c_id)


def get_card(db, c_id):
    for i in db["data"]:
        if i["id"] == c_id:
            return i
        for img in i["card_images"]:  # alt arts
            if img["id"] == c_id:
                return i
    return None


def build_database(c_id):
    db = sqlite3.connect("cards.cdb")
    sql_cursor = db.execute("SELECT * FROM datas WHERE id = ? OR alias = ?", (c_id, c_id))
    c_data = sql_cursor.fetchone()
    if c_data is not None:
        return db
    else:  # rebuild database to look for new cards
        lst = os.listdir("delta-utopia/")
        cursor = db.cursor()
        for fle in lst:
            if ".cdb" in fle:
                # print(fle)
                db.execute("ATTACH DATABASE ? AS datab", ("delta-utopia/" + fle,))
                cursor.execute(
                    "INSERT INTO datas SELECT * FROM datab.datas WHERE datab.datas.id NOT IN (SELECT id FROM datas);")
                cursor.execute(
                    "INSERT INTO texts SELECT * FROM datab.texts WHERE datab.texts.id NOT IN (SELECT id FROM texts);")
                db.commit()
                cursor.execute("DETACH DATABASE 'datab';")
        cursor.close()
    return db


# get from edopro database as backup and convert to YGOPRODECK format
def get_card_edopro(c_id):
    db = build_database(c_id)
    sql_cursor = db.execute("SELECT * FROM datas WHERE id = ? OR alias = ?", (c_id, c_id))
    c_data = sql_cursor.fetchone()
    if c_data is None:
        return None
    sql_cursor = db.execute("SELECT * FROM texts WHERE id = ?", (c_data[0],))
    c_text = sql_cursor.fetchone()
    out = {"id": c_id}
    out["name"] = c_text[1]
    out["desc"] = c_text[2]
    out["race"] = ""
    if hex(c_data[4])[-1] == "1":
        out["type"] = "Monster"
    elif hex(c_data[4])[-1] == "2":
        out["type"] = "Spell"
        if len(hex(c_data[4])) >= 5 and hex(c_data[4])[-5] == 8:
            out["race"] = "Field"
    elif hex(c_data[4])[-1] == "4":
        out["type"] = "Trap"
    out["card_sets"] = {}
    out["card_images"] = {0: {"id": c_id, "image_url": "", "image_url_small": ""}}
    out["card_prices"] = {}
    return out


class Banlist():
    def __init__(self, b_id):
        self.forb = []
        self.limit = []
        self.semi = []
        self.unlim = []
        self.whitelist = False
        self.b_id = b_id
        self.load_banlist()

    def load_banlist(self):
        pth = None
        if self.b_id == 0:  # tcg
            if os.path.exists("banlists/TCG.lflist.conf"):
                pth = "banlists/TCG.lflist.conf"
        elif self.b_id == 1:  # ocg
            if os.path.exists("banlists/OCG.lflist.conf"):
                pth = "banlists/OCG.lflist.conf"
        elif self.b_id == 2:  # goat
            if os.path.exists("banlists/GOAT.lflist.conf"):
                pth = "banlists/GOAT.lflist.conf"
        elif self.b_id == 3:  # edison
            if os.path.exists("banlists/Edison.lflist.conf"):
                pth = "banlists/Edison.lflist.conf"
        elif self.b_id == -1:  # disabled
            return
        if pth == None:
            raise Exception("No valid banlist found for \"{0}\"".format(self.b_id))
        fle = open(pth)
        lines = fle.readlines()
        fle.close()
        for line in lines:
            if len(line) == 0 or line[0] in ("#", "!"):  # skip comments, data
                continue
            elif "$whitelist" in line:
                self.whitelist = True
            else:
                elems = line.split()
                if len(elems) < 2:
                    continue
                if elems[1] == "1":
                    self.limit.append(elems[0])
                elif elems[1] == "0":
                    self.forb.append(elems[0])
                elif elems[1] == "2":
                    self.semi.append(elems[0])
                elif elems[1] == "3":
                    self.unlim.append(elems[0])

    def is_banned(self, card_id):
        return str(card_id) in self.forb

    def is_limited(self, card_id):
        return str(card_id) in self.limit

    def is_semi(self, card_id):
        return str(card_id) in self.semi

    def is_unlim(self, card_id):
        if self.whitelist:
            return str(card_id) in self.unlim
        else:
            return not (self.is_banned(card_id) or self.is_semi(card_id) or self.is_limited(card_id))

    def get_limit(self, card_id):
        if self.is_banned(card_id):
            return 0
        if self.is_limited(card_id):
            return 1
        if self.is_semi(card_id):
            return 2
        if self.whitelist:
            if self.is_unlim(card_id):
                return 3
            else:
                return 0
        return 3


async def gen_list(input_string, ban=-1):
    with open("cardinfo.json") as read_file:
        json_db = json.load(read_file)
    try:
        a = parse_url(input_string)
    except Exception as ex:
        raise ex
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
            c_data = get_card_edopro(img)
            if c_data is None:
                print("NO CARD FOUND WITH " + str(img))
                raise Exception("NO CARD FOUND WITH " + str(img))
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
                c_data = get_card_edopro(img)
                if c_data is None:
                    print("NO CARD FOUND WITH " + str(img))
                    raise Exception("NO CARD FOUND WITH " + str(img))
            if "Spell" in c_data["type"]:
                sp_ct += 1
                if "Field" in c_data["race"]:
                    if img not in f_sp:
                        f_sp[img] = 0
                    f_sp[img] = f_sp[img] + 1
    # Draw Background
    if len(f_sp) != 0:
        key = max(f_sp, key=f_sp.get)
        img_path = get_image_art(key)
        if img_path is not None:
            img = Image.open(img_path)
            img = img.resize((1000, 1000), resample=Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(5))
            bg.paste(img, (0, 0))
    # if os.path.exists("field/" + str(key) + ".png"):
    #    img = Image.open("field/" + str(key) + ".png")
    #   img = img.resize((1000, 1000), resample=Image.Resampling.LANCZOS)
    #  img = img.filter(ImageFilter.GaussianBlur(5))
    # bg.paste(img, (0, 0))
    # else:
    # fimg = get_image_art(key)
    # fmg = Image.open(fimg)
    # cropper = fmg.crop((49, 111, 49 + 323, 111 + 323))
    # cropper.save("field/" + str(key) + ".png")
    # img = cropper.resize((1000, 1000), resample=Image.Resampling.LANCZOS)
    # img = img.filter(ImageFilter.GaussianBlur(5))
    # bg.paste(img, (0, 0))
    img_boxes = Image.open("boxes.png")
    bg.paste(img_boxes, (0, 0), mask=img_boxes)
    blist = Banlist(ban)
    # Draw deck
    for img in a.get("main"):
        path = get_image(img)
        if path is None:
            path = "unknown.jpg"
        img1 = Image.open(path)
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.Resampling.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))
        # banlist paste
        lmt = blist.get_limit(img)
        if lmt != 3:
            badge = Image.open("textures/lim.png")
            if lmt == 0:
                badge = badge.crop((0, 0, 63, 63))
            elif lmt == 1:
                badge = badge.crop((64, 0, 127, 64))
            else:
                badge = badge.crop((0, 64, 64, 127))
            badge = badge.resize((32, 32), resample=Image.Resampling.LANCZOS)
            bg.paste(badge, (int(cursor_x), int(cursor_y)), mask=badge)

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
            c_data = get_card_edopro(img)
            if c_data is None:
                print("NO CARD FOUND WITH " + str(img))
                raise Exception("NO CARD FOUND WITH " + str(img))
        if "Fusion" in c_data["type"]:
            fm_ct += 1
        elif "Synchro" in c_data["type"]:
            sm_ct += 1
        elif "XYZ" in c_data["type"]:
            xm_ct += 1
        elif "Link" in c_data["type"]:
            lm_ct += 1
        path = get_image(img)
        if path is None:
            path = "unknown.jpg"
        img1 = Image.open(path)
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.Resampling.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))

        # banlist badge
        lmt = blist.get_limit(img)
        if lmt != 3:
            badge = Image.open("textures/lim.png")
            if lmt == 0:
                badge = badge.crop((0, 0, 63, 63))
            elif lmt == 1:
                badge = badge.crop((64, 0, 127, 64))
            else:
                badge = badge.crop((0, 64, 64, 127))
            badge = badge.resize((32, 32), resample=Image.Resampling.LANCZOS)
            bg.paste(badge, (int(cursor_x), int(cursor_y)), mask=badge)

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
            if c_data is None:
                c_data = get_card_edopro(img)
                if c_data is None:
                    print("NO CARD FOUND WITH " + str(img))
                    raise Exception("NO CARD FOUND WITH " + str(img))
        if "Monster" in c_data["type"]:
            s_m_ct += 1
        elif "Spell" in c_data["type"]:
            s_sp_ct += 1
        elif "Trap" in c_data["type"]:
            s_t_ct += 1
        path = get_image(img)
        if path is None:
            path = "unknown.jpg"
        img1 = Image.open(path)
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.Resampling.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))

        # banlist badge
        lmt = blist.get_limit(img)
        if lmt != 3:
            badge = Image.open("textures/lim.png")
            if lmt == 0:
                badge = badge.crop((0, 0, 63, 63))
            elif lmt == 1:
                badge = badge.crop((64, 0, 127, 64))
            else:
                badge = badge.crop((0, 64, 64, 127))
            badge = badge.resize((32, 32), resample=Image.Resampling.LANCZOS)
            bg.paste(badge, (int(cursor_x), int(cursor_y)), mask=badge)

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


### DISCORD INTEGRATION ###

async def save_image(path: str, image: memoryview) -> None:
    async with aiofiles.open(path, "wb") as file:
        await file.write(image)


def random_string(length: int):
    return ''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(length))


class MyModal(discord.ui.Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(discord.ui.InputText(label="ydke url:", style=discord.InputTextStyle.long))
        self.add_item(discord.ui.InputText(label="Ban", value="Banlist - 0: TCG, 1: OCG, 2: GOAT, 3: EDISON"))

    async def callback(self, interaction: discord.Interaction):
        ban = self.children[1].value
        if isinstance(ban, str):
            if not ban.isnumeric():
                if ban.lower().strip() == "ocg":
                    ban = 1
                elif ban.lower().strip() == "goat":
                    ban = 2
                elif ban.lower().strip() == "edison":
                    ban = 3
                elif ban.lower().strip() == "tcg":
                    ban = 0
                else:
                    ban = -1
            else:
                ban = int(ban)
        try:
            a = await gen_list(self.children[0].value, ban)
        except Exception as ex:
            await interaction.response.send_message(content=ex, ephemeral=True)
            return
        rname = random_string(14)
        bytes = BytesIO()
        a.save(bytes, format="PNG")
        await save_image("cache/{0}.png".format(rname), bytes.getbuffer())
        await interaction.response.send_message(content=self.children[0].value,
                                                file=discord.File("cache/{0}.png".format(rname)))
        os.unlink("cache/{0}.png".format(rname))


intents = discord.Intents.default()
intents.message_content = True

client = discord.Bot(debug_guilds=[738453639332364365, 747929507943415838], intents=intents)


@client.slash_command(description="Generate decklist with extra options.")
async def ydke(ctx: discord.ApplicationContext):
    modal = MyModal(title="Generate Decklist")
    await ctx.send_modal(modal)


@client.event
async def on_ready():
    print(f"{client.user} is ready and online!")


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content.startswith("ydke://"):
        await message.add_reaction(emoji="🕔")
        try:
            a = await gen_list(message.content)
        except Exception as ex:
            await message.reply(content=ex)
            await message.remove_reaction(emoji="🕔", member=client.user)
            return
        temp = tempfile.TemporaryFile(suffix=".png", delete=False)
        a.save(temp, "PNG")
        temp.seek(0)
        await message.reply(file=discord.File(temp.name))
        await message.remove_reaction(emoji="🕔", member=client.user)
        temp.close()
        os.unlink(temp.name)


client.run(os.getenv('TOKEN'))
