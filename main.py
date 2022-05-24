import base64
import json
import math
import os.path
import urllib
from urllib import request

import numpy
import sqlite3

from PIL import Image, ImageDraw, ImageFont, ImageFilter


def base64_to_passcodes(base64: str):
    pass


def parse_url(url: str):
    try:
        if not url.startswith("ydke://"):
            raise (IOError("ydke url not found"))
        elems = url[len("ydke://"):].split("!")
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

def get_image(id):
    if not os.path.exists("pics/{0}.jpg".format(id)):
        request.urlretrieve(
            'https://storage.googleapis.com/ygoprodeck.com/pics/{0}.jpg'.format(id), 'pics/{0}.jpg'.format(id)
        )
    return 'pics/27551.jpg'

def get_card(db, id):
    for i in db:
        if i["id"] == id:
            return i
    return None

if __name__ == '__main__':
    with open("cardinfo.json") as read_file:
        json_db = json.load(read_file)

    db = sqlite3.connect("cards.cdb")
    x = input("string: ")
    a = parse_url(x)
    cursor_x = 25.0
    cursor_y = 42.0
    bg = Image.open("bg.jpg").convert('RGBA')

    i = 0
    sp_ct = 0
    t_ct = 0
    m_ct = 0
    f_sp = {}
    for img in a.get("main"):
        sql_cursor = db.execute("SELECT * FROM datas WHERE id = ? OR alias = ?", (img,img))
        c_data = sql_cursor.fetchone()
        if c_data is None:
            print("NO CARD FOUND WTF " + str(img))
        else:
            if hex(c_data[4])[-1] == "1":
                m_ct += 1
            elif hex(c_data[4])[-1] == "2":
                sp_ct += 1
                if len(hex(c_data[4])) >= 5 and hex(c_data[4])[-5] == "8":
                    if img not in f_sp:
                        f_sp[img] = 0
                    f_sp[img] = f_sp[img] + 1
            elif hex(c_data[4])[-1] == "4":
                t_ct += 1
    for img in a.get("side"):
        sql_cursor = db.execute("SELECT * FROM datas WHERE id = ? OR alias = ?", (img,img))
        c_data = sql_cursor.fetchone()
        if c_data is None:
            print("NO CARD FOUND WTF " + str(img))
        else:
            if hex(c_data[4])[-1] == "2":
                sp_ct += 1
                if len(hex(c_data[4])) >= 5 and hex(c_data[4])[-5] == "8":
                    if img not in f_sp:
                        f_sp[img] = 0
                    f_sp[img] = f_sp[img] + 1
    if len(f_sp) != 0:
        key = max(f_sp)
        if os.path.exists("field/" + str(key) +".png"):
            img = Image.open("field/" + str(key) +".png")
            img = img.resize((1000, 1000), resample=Image.LANCZOS)
            img = img.filter(ImageFilter.GaussianBlur(5))
            bg.paste(img, (0,0))
    img_boxes = Image.open("boxes.png")
    bg.paste(img_boxes, (0,0), mask=img_boxes)
    for img in a.get("main"):
        img1 = Image.open("pics/" + str(img) + ".jpg")
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.LANCZOS)
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
    for img in a.get("extra"):
        sql_cursor = db.execute("SELECT * FROM datas WHERE id = ? OR alias = ?", (img,img))
        c_data = sql_cursor.fetchone()
        if c_data is None:
            print("NO CARD FOUND WTF "+ str(img))
        else:
            if len(hex(c_data[4])) >= 4 and hex(c_data[4])[-2]  in ("6","4"):
                fm_ct += 1
            elif len(hex(c_data[4])) >= 6 and hex(c_data[4])[-4] in ("2","3"):
                sm_ct += 1
            elif len(hex(c_data[4])) >= 8 and hex(c_data[4])[-6] == "8":
                xm_ct += 1
            elif len(hex(c_data[4])) >= 9 and hex(c_data[4])[-7] == "4":
                lm_ct += 1
        img1 = Image.open("pics/" + str(img) + ".jpg")
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))
        cursor_x += min(860 / (len(a.get("extra")) - 1), 95)
    cursor_x = 25.0
    cursor_y = 815.0
    s_sp_ct = 0
    s_t_ct = 0
    s_m_ct = 0
    for img in a.get("side"):
        sql_cursor = db.execute("SELECT * FROM datas WHERE id = ? OR alias = ?", (img,img))
        c_data = sql_cursor.fetchone()
        if c_data is None:
            print("NO CARD FOUND WTF " + str(img))
        else:
            if hex(c_data[4])[-1] == "1":
                s_m_ct += 1
            elif hex(c_data[4])[-1] == "2":
                s_sp_ct += 1
            elif hex(c_data[4])[-1] == "4":
                s_t_ct += 1
        img1 = Image.open("pics/" + str(img) + ".jpg")
        max_size = (90, 128)
        img1.thumbnail(max_size, Image.LANCZOS)
        bg.paste(img1, (int(cursor_x), int(cursor_y)))
        cursor_x += min(860 / (len(a.get("side")) - 1), 95)
    db.close()
    mfont = ImageFont.truetype("DejaVuSans.ttf", 20)
    boxbg = Image.new('RGBA', bg.size, (255, 255, 255, 0))
    boxtxt = ImageDraw.Draw(boxbg)
    # main text
    twidth, theight = mfont.getsize("Monsters: {0} Spells: {1} Traps: {2}".format(m_ct,sp_ct,t_ct))
    boxtxt.rounded_rectangle((16,0,30+twidth,9+theight),fill=(64,64,64,192), radius=5)
    twidth, theight = mfont.getsize("Fusion: {0} Synchro: {1} Xyz: {2} Link: {3}".format(fm_ct,sm_ct,xm_ct, lm_ct))
    boxtxt.rounded_rectangle((16,588,30+twidth,588+12+theight),fill=(64,64,64,192), radius=5)
    twidth, theight = mfont.getsize("Monsters: {0} Spells: {1} Traps: {2}".format(s_m_ct,s_sp_ct,s_t_ct))
    boxtxt.rounded_rectangle((16,774,30+twidth,774+6+theight),fill=(64,64,64,192), radius=5)
    bg = Image.alpha_composite(bg, boxbg)
    bg2 = ImageDraw.Draw(bg)
    bg2.text((25,5), "Monsters: {0} Spells: {1} Traps: {2}".format(m_ct,sp_ct,t_ct),fill=(255,255,255),font=mfont)
    # side text
    bg2.text((25,595), "Fusion: {0} Synchro: {1} Xyz: {2} Link: {3}".format(fm_ct,sm_ct,xm_ct, lm_ct),fill=(255,255,255),font=mfont)
    # extra text
    bg2.text((25,777), "Monsters: {0} Spells: {1} Traps: {2}".format(s_m_ct,s_sp_ct,s_t_ct),fill=(255,255,255),font=mfont)
    bg.show()
    print(m_ct)
    print(sp_ct)
    print(t_ct)

    if (input("save y/n: ") == "y"):
        bg.save("temp.png")
