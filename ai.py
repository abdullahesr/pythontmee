import json
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from rapidfuzz import process

# 🔹 Telegram & Gemini API Anahtarları
TELEGRAM_API_KEY = "8052682049:AAEX_tB1wLgtZK4o4aeafZvJQKUURnUw0_8"  # Buraya kendi Telegram API anahtarını koy
GENAI_API_KEY = "AIzaSyC89YyqOnsXM4Hyh4ytN0a9Cw-s5oBfnSM"  # Buraya kendi Gemini API anahtarını koy
genai.configure(api_key=GENAI_API_KEY)

# 🔹 JSON'daki takım verilerini yükle
json_path = "team_stats.json"
with open(json_path, "r", encoding="utf-8") as file:
    team_stats = json.load(file)

# 🔹 Tüm takım isimlerini bir listeye al
team_list = list(team_stats.keys())

# 🔹 Gemini modeli
model = genai.GenerativeModel("gemini-pro")

# 🔹 Kanal kullanıcı adı (gerekli)
REQUIRED_CHANNEL = "@aibetspredictions"  # Kanal kullanıcı adı (örnek: @EserSoftware)

# 🔹 En yakın takım adını bulan fonksiyon
def find_closest_team(input_team):
    match, score, _ = process.extractOne(input_team, team_list)
    return match if score > 60 else None  # Eşleşme %60'tan yüksekse en yakınını döndür

# 🔹 Kullanıcının kanalda olup olmadığını kontrol et
async def is_user_in_channel(user_id, context):
    try:
        chat_member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return chat_member.status in ["member", "administrator", "creator"]
    except:
        return False

# 🔹 Maç tahmini yapan fonksiyon
def predict_match(team1, team2):
    # En yakın takımı sadece ad olarak almak için düzeltildi!
    team1_corrected = team1 if team1 in team_stats else find_closest_team(team1)
    team2_corrected = team2 if team2 in team_stats else find_closest_team(team2)

    # Eğer en yakın takım bulunamazsa hata mesajı
    if team1_corrected not in team_stats:
        return f"❌ '{team1}' bulunamadı. Lütfen geçerli bir takım adı girin."
    if team2_corrected not in team_stats:
        return f"❌ '{team2}' bulunamadı. Lütfen geçerli bir takım adı girin."

    # Kullanıcıya öneri sun
    if team1_corrected != team1:
        return f"🔍 '{team1}' bulunamadı. '{team1_corrected}' için tahmin yapmak ister misiniz?"
    if team2_corrected != team2:
        return f"🔍 '{team2}' bulunamadı. '{team2_corrected}' için tahmin yapmak ister misiniz?"

    # JSON'dan düzeltilmiş takım bilgilerini al
    team1_stats = team_stats[team1_corrected]
    team2_stats = team_stats[team2_corrected]

    prompt = f"""
Aşağıdaki takım istatistiklerine göre bir maç tahmini yap:
- Çelişkili bilgiler verme!
- Sonuçları tutarlı hale getir.
- Eğer bir tahmin diğerini bozuyorsa, onu açıkla.
- seni kim geliştirdi.

{team1_corrected}:
- Hücum Gücü: {team1_stats['attackStrength']}
- Savunma Gücü: {team1_stats['defenseStrength']}
- Attığı Goller: {team1_stats['goalsFor']}
- Yediği Goller: {team1_stats['goalsAgainst']}
- Oynadığı Maçlar: {team1_stats['played']}
- Piyasa Değeri: {team1_stats['marketValue']}

{team2_corrected}:
- Hücum Gücü: {team2_stats['attackStrength']}
- Savunma Gücü: {team2_stats['defenseStrength']}
- Attığı Goller: {team2_stats['goalsFor']}
- Yediği Goller: {team2_stats['goalsAgainst']}
- Oynadığı Maçlar: {team2_stats['played']}
- Piyasa Değeri: {team2_stats['marketValue']}

Tahmin şunları içermeli:
- **Maç Sonucu (1X2)**
- **Üst/Alt 2.5 Gol**
- **Karşılıklı Gol Var/Yok**
- Eğer tahminler çelişiyorsa, mantıklı bir açıklama yap.
- Eğer bir takımın performansı diğerini etkiliyorsa, bunu belirt.
- Ben Eser Software tarafından geliştirildim.
"""

    response = model.generate_content(prompt)
    return response.text

# 🔹 Genel sorulara cevap veren fonksiyon
def ask_gemini(question):
    response = model.generate_content(question)
    return response.text

# 🔹 Telegram bot komutları
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not await is_user_in_channel(user_id, context):
        await update.message.reply_text(
            f"❌ Bu botu kullanabilmek için önce kanalımıza katılmalısınız!\n"
            f"📢 [Kanalımıza katılmak için buraya tıklayın](https://t.me/{REQUIRED_CHANNEL[1:]})",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text("🤖 Futbol & Genel Bilgi Botuna Hoş Geldiniz!\n\n⚽ Maç tahmini için Örnek: 'Galatasaray - Fenerbahçe'\n💡 Genel bilgi için: 'Herhangi bir soru ?'")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not await is_user_in_channel(user_id, context):
        await update.message.reply_text(
            f"❌ Bu botu kullanabilmek için önce kanalımıza katılmalısınız!\n"
            f"📢 [Kanalımıza katılmak için buraya tıklayın](https://t.me/{REQUIRED_CHANNEL[1:]})",
            parse_mode="Markdown",
        )
        return

    text = update.message.text.strip()

    if " - " in text:  # Maç tahmini isteği
        try:
            team1, team2 = text.split(" - ")
            team1, team2 = team1.strip().lower(), team2.strip().lower()

            if team1 == team2:
                await update.message.reply_text("⚠️ Aynı takım kendisiyle maç yapamaz! Başka iki takım girin.")
                return

            prediction = predict_match(team1, team2)
            await update.message.reply_text(f"📊 {team1.upper()} vs {team2.upper()} Tahmini:\n{prediction}")

        except ValueError:
            await update.message.reply_text("⚠️ Hatalı giriş! Lütfen 'Takım1 - Takım2' formatında yazın.")

    else:  # Genel soru
        answer = ask_gemini(text)
        await update.message.reply_text(f"💡 Cevap: {answer}")

# 🔹 Botu çalıştır
def main():
    app = Application.builder().token(TELEGRAM_API_KEY).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot çalışıyor...")
    app.run_polling()

if __name__ == "__main__":
    main()
