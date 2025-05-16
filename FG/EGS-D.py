import requests
from bs4 import BeautifulSoup
import os
import json

# Konfigurasi ENV manual jika tidak pakai .env
os.environ['TELEGRAM_BOT_TOKEN'] = 'ISI_TOKEN_BOTMU'
os.environ['TELEGRAM_CHAT_ID'] = 'ISI_CHAT_ID_MU'
os.environ['GEMINI_API_KEY'] = 'ISI_API_KEY_GEMINI_MU'

# ====== Fungsi AI ======
def get_age_rating(title, genre):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={os.environ['GEMINI_API_KEY']}"
    headers = {"Content-Type": "application/json"}
    prompt = f"""
Game "{title}" is a {genre} game. Based on the content, what is the most appropriate age rating (ESRB or PEGI)?
Answer with one of: "Everyone", "Teen", "Mature", "18+", or "Unknown" only.
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, headers=headers, data=json.dumps(payload))
    if res.status_code == 200:
        return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    return "Unknown"

def check_discount_history(title):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={os.environ['GEMINI_API_KEY']}"
    headers = {"Content-Type": "application/json"}
    prompt = f'''
Has the game titled "{title}" ever been given away for free before by Epic Games? 
If so, mention the date. If you don't know, answer "Unknown" and just make it Without a long yapping or mucho texto if there is one list all of that.
'''
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(url, headers=headers, data=json.dumps(payload))
    if res.status_code == 200:
        return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    return "Unknown"

def is_valid_price(text):
    return text.replace('.', '', 1).isdigit()

def ambil_li_berdasarkan_label(li_elements, label):
    for li in li_elements:
        if li.text.strip().startswith(label):
            return li.text.split(": ", 1)[1]
    return "Not Available"

# ====== Load & Parse Feed ======
rss_url = 'https://feed.phenx.de/lootscraper_epic_game.xml'
response = requests.get(rss_url)
soup = BeautifulSoup(response.content, 'xml')
entries = soup.find_all('entry')

# ====== Proses 1 Entry Saja (Demo) ======
for entry in entries[:1]:
    title = entry.title.text.replace("Epic Games (Game) - ", "").strip()
    link = entry.link['href']
    content = entry.content
    image_url = content.find('img')['src']
    li_items = content.find_all('li')

    offer_valid_from = ambil_li_berdasarkan_label(li_items, "Offer valid from")
    offer_valid_to = ambil_li_berdasarkan_label(li_items, "Offer valid to")
    release_date = ambil_li_berdasarkan_label(li_items, "Release Date")
    recommended_price = ambil_li_berdasarkan_label(li_items, "Original Price").replace("EUR", "").strip()
    game_description = ambil_li_berdasarkan_label(li_items, "Description")
    genre = ambil_li_berdasarkan_label(li_items, "Genre")

    if len(game_description) > 500:
        game_description = game_description[:500] + "..."

    if not is_valid_price(recommended_price):
        print(f"[!] Harga tidak valid: {recommended_price}")
        recommended_price = "Unknown"

    # === AI Validation ===
    rating = get_age_rating(title, genre)
    history = check_discount_history(title)

    # === Format Pesan ===
    message = (
        f"🎮 <b>{title}</b>\n\n"
        f"💬 <code>Description:</code>\n<blockquote>{game_description}</blockquote>\n\n"
        f"❓ <b>Has this game ever been given for free?</b>\n"
        f"<blockquote>{history}</blockquote>\n\n"
        f"🃏 Game Genre: <b>{genre}</b>\n"
        f"💰 Original Price: <b><s>€ {recommended_price}</s></b> Now <b>Free</b>\n"
        f"🧒 Age Rating: <b>{rating}</b>\n"
        f"🗓️ Release Date: <b>{release_date}</b>\n\n"
        f"📅 Offer valid from: <b>{offer_valid_from}</b> to <b>{offer_valid_to}</b>"
    )

    # === Kirim ke Telegram ===
    telegram_url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"
    payload = {
        "chat_id": os.environ['TELEGRAM_CHAT_ID'],
        "photo": image_url,
        "parse_mode": "HTML",
        "caption": message,
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "🎁 Claim Game", "url": link}
            ]]
        }
    }

    tg_response = requests.post(telegram_url, json=payload)
    if tg_response.status_code == 200:
        print(f"[+] Berhasil kirim: {title}")
    else:
        print(f"[!] Gagal kirim: {tg_response.status_code}")
        print(tg_response.text)
