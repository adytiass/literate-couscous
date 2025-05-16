import requests
from bs4 import BeautifulSoup
import os
import json

# === ENV SETUP ===
os.environ['TELEGRAM_BOT_TOKEN'] = os.getenv('TELEGRAM_BOT_TOKEN')
os.environ['TELEGRAM_CHAT_ID'] = os.getenv('TELEGRAM_CHAT_ID')
os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')

# === Gemini Model URL ===
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=" + os.environ['GEMINI_API_KEY']

# === GEMINI FUNCTIONS ===

def get_age_rating(title, genre):
    headers = {"Content-Type": "application/json"}
    prompt = f"""
Game "{title}" is a {genre} game. Based on the content, what is the most appropriate age rating (ESRB or PEGI)?
Answer with one of: "Everyone", "Teen", "Mature", "18+", or "Unknown" only.
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
    if res.status_code == 200:
        jawaban = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        print(f"[Gemini-Rating] {title} → {jawaban}")
        return jawaban if jawaban in ["Everyone", "Teen", "Mature", "18+"] else "Unknown"
    print(f"[Gemini-Rating] ERROR: {res.text}")
    return "Unknown"

def check_discount_history(title):
    headers = {"Content-Type": "application/json"}
    prompt = f'''
Has the game titled "{title}" ever been given away for free before by Epic Games? 
If so, mention the date. If you don't know, answer "Unknown" and just make it Without a long yapping or mucho texto if there is one list all of that.
'''
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
    if res.status_code == 200:
        jawaban = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        print(f"[Gemini-History] {title} → {jawaban}")
        return jawaban
    print(f"[Gemini-History] ERROR: {res.text}")
    return "Unknown"

def cari_harga_dari_ai(title):
    headers = {"Content-Type": "application/json"}
    prompt = f"""
What is the current price of the game titled "{title}" on Steam store? 
Answer only the price in EUR (e.g. 59.99). If unknown or not found, respond with "Unknown".
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    res = requests.post(GEMINI_URL, headers=headers, data=json.dumps(payload))
    if res.status_code == 200:
        output = res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        print(f"[Gemini-Price] {title} → {output}")
        return output if output.replace('.', '', 1).isdigit() else "Unknown"
    print(f"[Gemini-Price] ERROR: {res.text}")
    return "Unknown"

# === UTIL ===

def is_valid_price(text):
    return text.replace('.', '', 1).isdigit()

def ambil_li_berdasarkan_label(li_elements, label):
    for li in li_elements:
        if li.text.strip().startswith(label):
            return li.text.split(": ", 1)[1]
    return "Not Available"

# === LOAD RSS FEED ===
rss_url = 'https://feed.phenx.de/lootscraper_epic_game.xml'
response = requests.get(rss_url)
soup = BeautifulSoup(response.content, 'xml')
entries = soup.find_all('entry')

# === PROSES 1 ENTRY (DEMO) ===
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
        print(f"[!] Harga tidak valid: {recommended_price}. Mencoba pakai AI...")
        recommended_price = cari_harga_dari_ai(title)

    # === AI Analysis ===
    rating = get_age_rating(title, genre)
    history = check_discount_history(title)

    # === Format Pesan Telegram ===
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
        print(f"[Telegram] ❌ Status: {tg_response.status_code}")
        print(f"[Telegram] Response: {tg_response.text}")
