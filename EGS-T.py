import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
import os

# Koneksi ke MongoDB
client = MongoClient(os.environ['MONGODB_URI'])
db = client['EPIC_GAMES_FGDB']  # Mengubah nama database
collection = db['sent_entries']  # Koleksi untuk menyimpan ID entri

# URL RSS Feed
rss_url = 'https://feed.phenx.de/lootscraper_epic_game.xml'
response = requests.get(rss_url)

# Parsing XML
soup = BeautifulSoup(response.content, 'xml')
entries = soup.find_all('entry')

# Kirim setiap entry untuk analisis demo
for entry in entries:
    title = entry.title.text.replace("Epic Games (Game) - ", "").strip()  # Menghapus "Epic Games (Game) - "
    link = entry.link['href']
    content = entry.content
    image_url = content.find('img')['src']

    # Mengambil tanggal dari konten
    offer_valid_from = content.find_all('li')[0].text.split(": ")[1].split(" - ")[0] if len(content.find_all('li')) > 0 else "Not Available"
    offer_valid_to = content.find_all('li')[1].text.split(": ")[1].split(" - ")[0] if len(content.find_all('li')) > 1 else "Not Available"

    # Informasi tambahan
    game_description = content.find_all('li')[5].text.split(": ")[1] if len(content.find_all('li')) > 5 else "Not Available"  # Deskripsi game
    release_date = content.find_all('li')[3].text.split(": ")[1] if len(content.find_all('li')) > 3 else "Not Available"  # Tanggal rilis game
    genre = content.find_all('li')[6].text.split(": ")[1] if len(content.find_all('li')) > 6 else "Not Available"  # Genre game
    recommended_price = content.find_all('li')[4].text.split(": ")[1].replace("EUR", "").strip() if len(content.find_all('li')) > 4 else "00.00"  # Harga rekomendasi

    max_description_length = 500  # Batasi deskripsi maksimal 1000 karakter
    if len(game_description) > max_description_length:
       game_description = game_description[:max_description_length] + "..."  # Tambahkan "..." di akhir

    # Format pesan
    message = (
        f"🎮 <b>{title}</b>\n\n"
        f"💬 <code>Description:</code>\n<blockquote>{game_description}</blockquote>\n\n"
        f"<blockquote>🃏 Game Genre: <b>{genre}</b>\n"
        f"💰 Original Price: <b><s>€ {recommended_price}</s></b> Now <b>Free</b>\n"
        f"🗓️ Release Date: <b>{release_date}</b></blockquote>\n\n"
        f"📅 Offer valid from: <b>{offer_valid_from}</b> to <b>{offer_valid_to}</b>"
    )

    # Mengambil ID dari entry
    entry_id = entry.id.text  # Mengambil ID dari feed RSS

    # Cek apakah entri sudah ada di database
    if collection.find_one({"entry_id": entry_id}) is None:  # Menggunakan entry_id sebagai kunci
        # Kirim pesan ke Telegram
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
        response = requests.post(telegram_url, json=payload)

        # Output status pengiriman
        if response.status_code == 200:
            print(f"✅ Berhasil mengirim pesan: {title}")
            # Simpan entri ke database untuk menghindari duplikasi
            collection.insert_one({"entry_id": entry_id})  # Menyimpan ID entri
        else:
            print(f"❌ Gagal mengirim pesan: {title}. Kode status: {response.status_code}")
            print(f"Respon Telegram: {response.text}")  # Debugging tambahan
            
    else:
        print(f"🚫 Sudah melewati entri yang sudah dikirim: {title}")
