import requests
from pymongo import MongoClient
from bs4 import BeautifulSoup
import os

# Koneksi ke MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client['AMZN_PRIMEGAMING']
collection = db['sent_entries']

# URL API Telegram
telegram_url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendPhoto"

# URL RSS Feed
rss_url = 'https://feed.phenx.de/lootscraper_amazon_game.xml'
response = requests.get(rss_url)

# Parsing XML
soup = BeautifulSoup(response.content, 'xml')
entries = soup.find_all('entry')

# Kirim setiap entry yang belum pernah dikirim
for entry in entries:
    title = entry.title.text.replace("Amazon Prime (Game) - ", "")
    link = entry.link['href']
    
    # Periksa apakah entri sudah dikirim
    if collection.find_one({"link": link}):
        print(f"[INFO] '{title}' sudah pernah dikirim. SKIP.")
        continue  # Lewati entri yang sudah dikirim

    content = entry.content

    # Gambar
    image_url = content.find('img')['src']

    # Tanggal Penawaran
    offer_valid_from = content.find_all('li')[0].text.split(": ")[1].split(" - ")[0]
    offer_valid_to = content.find_all('li')[1].text.split(": ")[1].split(" - ")[0]

    # Genre
    try:
        genre = next(li.text.split(": ")[1] for li in content.find_all('li') if "Genres:" in li.text)
    except (IndexError, StopIteration):
        genre = "Not Available"

    # Deskripsi
    try:
        description = next(li.text.split(": ")[1] for li in content.find_all('li') if "Description:" in li.text)
    except (IndexError, StopIteration):
        description = "Description not available"

    # Tanggal Rilis
    try:
        release_date = next(li.text.split(": ")[1] for li in content.find_all('li') if "Release date:" in li.text)
    except (IndexError, StopIteration):
        release_date = "Unknown"

    # Pesan Telegram
    message = (
        f"🎮 <b>{title}</b>\n\n"
        f"🔜 Offer valid from: <b>{offer_valid_from}</b> to <b>{offer_valid_to}</b>\n"
        f"📌 Release date: <b>{release_date}</b>\n"
        f"✳️ Genres: <b>{genre}</b>\n\n"
        f"<b>Description:</b>\n"
        f"<blockquote>{description}</blockquote>"
    )

    # Cek panjang pesan dan atur jika terlalu panjang
    if len(message) > 1024:
        print(f"[WARNING] Caption terlalu panjang untuk '{title}'. Menggunakan 'Description not available'.")
        message = (
            f"🎮 <b>{title}</b>\n\n"
            f"🔜 Offer valid from: <b>{offer_valid_from}</b> to <b>{offer_valid_to}</b>\n"
            f"📌 Release date: <b>{release_date}</b>\n"
            f"✳️ Genres: <b>{genre}</b>\n\n"
            f"<b>Description:</b>\n"
            f"<blockquote>Description not available</blockquote>"
        )

    # Kirim ke Telegram
    payload = {
        "chat_id": -1001852513952,
        "photo": image_url,
        "caption": message,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [[
                {"text": "💵 Get Games", "url": link}
            ]]
        }
    }
    response = requests.post(telegram_url, json=payload)

    # Tambahkan log untuk setiap hasil
    if response.status_code == 200:
        print(f"[SUCCESS] Pesan terkirim untuk '{title}'.")
        
        # Simpan entri ke database untuk menghindari duplikasi
        collection.insert_one({"link": link})
    else:
        print(f"[FAILED] Gagal mengirim pesan untuk '{title}'. Error: {response.text}")
