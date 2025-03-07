import os
import requests
from bs4 import BeautifulSoup
from xml.etree.ElementTree import Element, SubElement, ElementTree
import subprocess
import re

# Fungsi untuk mengupload gambar ke Rclone
def upload_to_rclone(image_bytes, remote_path):
    with open('temp_image.jpg', 'wb') as img_file:  # Simpan sementara di memori
        img_file.write(image_bytes)
    command = ['rclone', 'copy', 'temp_image.jpg', remote_path, '--quiet', '--config', 'rclone.conf']
    print(f"Executing command: {' '.join(command)}")  # Log command yang akan dieksekusi
    subprocess.run(command)

# Parsing RSS feed dari URL sumber
rss_url = 'https://feed.phenx.de/lootscraper_epic_game.xml'
response = requests.get(rss_url)
soup = BeautifulSoup(response.content, 'xml')
entries = soup.find_all('entry')

# Membuat elemen root untuk RSS
rss = Element('rss')
rss.set('version', '2.0')
rss.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')

# Membuat elemen channel dengan metadata lengkap
channel = SubElement(rss, 'channel')
SubElement(channel, 'title').text = 'Epic Games Free Games Feed'
SubElement(channel, 'link').text = 'https://example.com/epic-games-feed'
SubElement(channel, 'description').text = 'RSS feed for Epic Games free games'
SubElement(channel, 'generator').text = 'Custom Python Script'
SubElement(channel, 'language').text = 'en-us'  # Menentukan bahasa

# Proses setiap entry dari feed sumber
for entry in entries:
    title = entry.title.text
    # Menghapus bagian "Epic Games (Game)"
    title = title.replace("Epic Games (Game) - ", "").strip()
    
    link = entry.link['href']
    image_url = entry.content.find('img')['src']
    pub_date = entry.updated.text  # Mendapatkan tanggal publikasi dari entry

    # Mencari "Offer valid to" di konten
    content = entry.content.text
    offer_valid_to = re.search(r'Offer valid to:\s*(\d{4}-\d{2}-\d{2})', content)

    # Mengambil tanggal jika ditemukan
    if offer_valid_to:
        offer_valid_to_text = offer_valid_to.group(1)  # Ambil hanya tanggal
    else:
        offer_valid_to_text = 'N/A'

    # Menghilangkan parameter query dari URL gambar
    image_url_clean = image_url.split('?')[0]  # Hanya ambil bagian sebelum '?'
    
    # Mengunduh gambar
    img_response = requests.get(image_url_clean)
    if img_response.status_code == 200:
        # Mengupload gambar ke Rclone
        remote_path = f"ab:Arc.BiHU.0x/0x/0x/JPG/EC/{image_url_clean.split('/')[-1]}"  # Pastikan path benar
        print(f"Uploading to remote path: {remote_path}")  # Debugging

        # Upload gambar tanpa menyimpan ke disk
        upload_to_rclone(img_response.content, remote_path)

        # Menghasilkan URL baru setelah upload
        uploaded_image_url = f"https://archive.org/download/Arc.BiHU.0x/0x/0x/JPG/EC/{image_url_clean.split('/')[-1]}/temp_image.jpg"
        print(f"Uploaded image URL: {uploaded_image_url}")  # Debugging

        # Membuat elemen item
        item = SubElement(channel, 'item')
        SubElement(item, 'title').text = f"{title} - End: {offer_valid_to_text}"  # Format yang diinginkan
        SubElement(item, 'description').text = (
            f'<img src="{uploaded_image_url}"/><br/><br/><p>{title}</p>'
        )
        SubElement(item, 'link').text = link
        SubElement(item, 'guid').text = link
        SubElement(item, 'pubDate').text = pub_date  # Menambahkan tanggal publikasi

# Menulis RSS ke file XML dengan deklarasi encoding
output_file = 'EGS-E.xml'
with open(output_file, 'wb') as f:
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    tree = ElementTree(rss)
    tree.write(f, encoding='utf-8', xml_declaration=False)

print(f"RSS feed berhasil dibuat: {output_file}")
