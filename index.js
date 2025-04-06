const puppeteer = require('puppeteer');
const axios = require('axios');
const fs = require('fs').promises;

// Mengambil token dan chat ID dari variabel lingkungan
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

async function sendMessageToTelegram(message) {
    const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
    try {
        await axios.post(url, {
            chat_id: TELEGRAM_CHAT_ID,
            text: message
        });
    } catch (error) {
        console.error('Failed to send message to Telegram:', error);
    }
}

function formatBandwidth(bytes) {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log10(bytes) / 3);
    return (bytes / Math.pow(1000, i)).toFixed(2) + ' ' + sizes[i];
}

async function fetchLinkInfo(link) {
    let browser;
    try {
        browser = await puppeteer.launch({ args: ['--no-sandbox', '--disable-setuid-sandbox'] });
        const page = await browser.newPage();

        console.log(`Opening link: ${link}`);
        await page.goto(link, { waitUntil: 'networkidle2' });

        const viewerData = await page.evaluate(() => window.viewer_data || null);

        if (viewerData && viewerData.api_response) {
            const apiResponse = viewerData.api_response;
            const fileName = apiResponse.name || 'Unknown';
            const fileId = apiResponse.id || 'Unknown';
            const fileSize = formatBandwidth(apiResponse.size) || 'Unknown';
            const views = apiResponse.views || 'Unknown';
            const downloads = apiResponse.downloads || 'Unknown';
            const bandwidthUsed = formatBandwidth(apiResponse.bandwidth_used) || 'Unknown';
            const dateUpload = apiResponse.date_upload ? new Date(apiResponse.date_upload).toLocaleString() : 'Unknown';
            const dateLastView = apiResponse.date_last_view ? new Date(apiResponse.date_last_view).toLocaleString() : 'Unknown';

            const message = `
File Name: ${fileName}
File ID: ${fileId}
Size: ${fileSize}
Views: ${views}
Downloads: ${downloads}
Bandwidth Used: ${bandwidthUsed}
Date Uploaded: ${dateUpload}
Date Last Viewed: ${dateLastView}
`;

            await sendMessageToTelegram(message);
        } else {
            console.error('No viewer data found for link:', link);
        }
    } catch (error) {
        console.error('Error fetching link info:', error);
    } finally {
        if (browser) await browser.close();
    }
}

async function main() {
    try {
        const data = await fs.readFile('links-wh.txt', 'utf-8');
        const encodedLinks = data.split('\n').filter(Boolean);
        
        // Decode Base64 ke URL sebelum digunakan
        const links = encodedLinks.map(encoded => Buffer.from(encoded, 'base64').toString('utf-8'));

        for (const link of links) {
            await fetchLinkInfo(link);
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
    } catch (error) {
        console.error('Error in main function:', error);
    }
}

main().catch(console.error);
