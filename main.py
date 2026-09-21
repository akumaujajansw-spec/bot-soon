import os
import html
import base64
import requests
import threading
from flask import Flask, request, jsonify
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Config Token & API Keys
TOKEN = os.getenv("BOT_TOKEN", "8834766580:AAHYJpXJmV9hPQWMjblDW0xCfouahh0FsHM")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8953615855"))

MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY", "Mid-server-pFVjkKnZS56RezFUtfuzbfLZ")
# Set True untuk Production, False untuk Sandbox (testing)
IS_PRODUCTION = False  

ALL_GROUP_IDS = [
    -1003721629607,
    -1003646177202,
    -1003727409464,
    -1003713991635,
    -1003839151133,
    -1003561794613,
    -1003634689467,
    -1003853297361,
    -1004451939488,
    -1004486985873,
    -1003813292350
]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Base URL Midtrans Core API
BASE_URL_MIDTRANS = "https://api.midtrans.com/v2" if IS_PRODUCTION else "https://api.sandbox.midtrans.com/v2"

def get_auth_header():
    # Menyiapkan Basic Auth Header dari Server Key Midtrans
    auth_string = f"{MIDTRANS_SERVER_KEY}:"
    encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_auth}"
    }

def create_qris_charge(order_id, gross_amount):
    """Fungsi untuk membuat transaksi QRIS Dinamis ke Midtrans dengan expired 15 menit"""
    url = f"{BASE_URL_MIDTRANS}/charge"
    payload = {
        "payment_type": "qris",
        "transaction_details": {
            "order_id": order_id,
            "gross_amount": gross_amount
        },
        "qris": {
            "acquirer": "gopay" # default acquirer QRIS Midtrans
        },
        "custom_expiry": {
            "expiry_duration": 15,
            "unit": "minute"
        }
    }
    
    response = requests.post(url, json=payload, headers=get_auth_header())
    return response.json()

def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(KeyboardButton("🛒 Beli Paket VIP 11 Grup (Rp 85.000)"))
    markup.add(KeyboardButton("⭐ Testimoni"), KeyboardButton("❓ Bantuan"))
    markup.add(KeyboardButton("📞 Hubungi Admin"))
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(
        message, 
        "Halo! Selamat datang di bot WarungDosa.\n\n"
        "🔥 <b>Paket Hemat:</b> Dapatkan akses ke <b>11 Grup VIP Sekaligus</b> hanya dengan <b>Rp 85.000</b>!\n\n"
        "Silakan gunakan tombol menu di bawah untuk mulai:", 
        parse_mode="HTML", 
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda message: message.text == "🛒 Beli Paket VIP 11 Grup (Rp 85.000)")
def handle_buy_menu(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 Tampilkan QRIS Pembayaran", callback_data="show_qris"))
    
    bot.send_message(
        chat_id,
        "Anda memilih <b>Paket VIP 11 Grup Sekaligus (Rp 85.000)</b>.\n\nKlik tombol di bawah untuk buat QRIS Pembayaran (Berlaku 15 Menit):",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "⭐ Testimoni")
def handle_testimoni(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔗 Buka Channel Testimoni", url="https://t.me/testiwarungdosaa"))
    
    bot.send_message(
        chat_id,
        "⭐ <b>Testimoni Pelanggan WarungDosa</b>\n\n"
        "Ingin melihat bukti screenshot pembayaran dan kepuasan member lain yang sudah bergabung?\n\n"
        "Silakan klik tombol di bawah untuk melihat kumpulan testimoni lengkap kami:",
        parse_mode="HTML",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "❓ Bantuan")
def handle_faq(message):
    bot.send_chat_action(message.chat.id, 'typing')
    bot.reply_to(
        message,
        "💡 <b>Panduan & FAQ:</b>\n\n"
        "1. Klik tombol <b>'🛒 Beli Paket VIP 11 Grup'</b>.\n"
        "2. Klik <b>'💳 Tampilkan QRIS Pembayaran'</b>.\n"
        "3. Scan QR Code yang muncul lalu lakukan pembayaran sebelum masa berlaku 15 menit habis.\n"
        "4. Setelah pembayaran sukses, <b>link grup otomatis terkirim</b> tanpa menunggu admin!\n\n",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda message: message.text == "📞 Hubungi Admin")
def handle_contact_admin(message):
    chat_id = message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💬 Chat Admin Sekarang", url="https://t.me/WarungDosa"))
    
    bot.send_message(
        chat_id,
        "💬 Silakan hubungi Admin kami jika Anda mengalami kendala seputar pembayaran atau akses grup:",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "show_qris")
def process_show_qris(call):
    chat_id = call.message.chat.id
    bot.send_chat_action(chat_id, 'typing')
    
    # Format Order ID berisi ID Chat Pembeli untuk melacak callback webhook kelak
    # Format: VIP-<CHAT_ID>-<TIMESTAMP>
    import time
    order_id = f"VIP-{chat_id}-{int(time.time())}"
    amount = 85000
    
    bot.answer_callback_query(call.id, "Membuat QRIS...")
    
    qris_res = create_qris_charge(order_id, amount)
    
    if qris_res.get("status_code") == "201":
        # Ambil URL Gambar QR Code dari Midtrans (actions array)
        qr_url = None
        for action in qris_res.get("actions", []):
            if action.get("name") == "generate-qr-code":
                qr_url = action.get("url")
                break
                
        caption_text = (
            "<b>VIP WarungDosa - QRIS Dinamis</b>\n\n"
            "💰 Total Pembayaran: <b>Rp 85.000</b>\n"
            "⏱️ Masa Aktif: <b>15 Menit</b>\n\n"
            "<i>Silakan scan QR Code di atas menggunakan GoPay, OVO, Dana, ShopeePay, BCA, Mandiri, atau e-Wallet/Bank lainnya.</i>\n\n"
            "✅ Setelah pembayaran Anda diterima, link otomatis akan dikirimkan di sini!"
        )
        
        if qr_url:
            bot.send_photo(chat_id, qr_url, caption=caption_text, parse_mode="HTML")
        else:
            bot.send_message(chat_id, "Gagal mendapatkan QR Code dari Midtrans.")
    else:
        status_msg = qris_res.get("status_message", "Gagal menghubungi Midtrans.")
        bot.send_message(chat_id, f"Terjadi kesalahan saat memproses pembayaran: {status_msg}")

# ==========================================
# WEBHOOK ENDPOINT FOR MIDTRANS NOTIFICATION
# ==========================================
@app.route('/midtrans-webhook', methods=['POST'])
def midtrans_webhook():
    data = request.json
    if not data:
        return jsonify({"status": "no data"}), 400
        
    order_id = data.get("order_id", "")
    transaction_status = data.get("transaction_status", "")
    fraud_status = data.get("fraud_status", "")

    # Cek jika pembayaran berhasil (settlement / capture)
    if transaction_status in ["settlement", "capture"]:
        try:
            # Mengambil target_user_id dari order_id ("VIP-<CHAT_ID>-<TIMESTAMP>")
            target_user_id = int(order_id.split("-")[1])
            
            # Generate Link Invite Sekali Pakai
            generated_links = []
            for group_id in ALL_GROUP_IDS:
                invite = bot.create_chat_invite_link(chat_id=group_id, member_limit=1)
                generated_links.append(invite.invite_link)
            
            links_text = "\n".join([f"• {link}" for link in generated_links])
            
            # Kirim Link Otomatis ke Pembeli
            bot.send_message(
                target_user_id,
                f"✅ <b>Pembayaran Sukses Terverifikasi!</b>\n\n"
                f"Berikut link akses ke 11 Grup VIP (Sekali Pakai):\n\n{links_text}\n\n"
                f"<b>Catatan:</b>\n"
                f"- Link hanya bisa digunakan 1 kali per grup.\n"
                f"- Jika link kedaluwarsa, artinya Anda sudah berhasil masuk ke grup.\n"
                f"- Jika muncul pesan <i>'Too Many Attempts'</i> mohon tunggu beberapa menit lalu coba kembali.",
                parse_mode="HTML"
            )

            # Notifikasi Laporan ke Admin
            bot.send_message(
                ADMIN_ID,
                f"🔔 <b>Pembayaran Otomatis Diterima!</b>\n"
                f"ID Pembeli: <code>{target_user_id}</code>\n"
                f"Order ID: <code>{order_id}</code>\n"
                f"Nominal: Rp 85.000\n"
                f"Status: <b>LUNAS (Link Otomatis Terkirim)</b>",
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error handling success webhook: {e}")
            bot.send_message(ADMIN_ID, f"⚠️ Gagal mengirim link otomatis untuk Order ID `{order_id}`: {e}", parse_mode="Markdown")

    return jsonify({"status": "OK"}), 200

def run_flask():
    # Jalankan Flask Server di port 5000
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    print("Menjalankan Flask Webhook...")
    threading.Thread(target=run_flask, daemon=True).start()
    
    print("Bot berjalan...")
    bot.infinity_polling()
