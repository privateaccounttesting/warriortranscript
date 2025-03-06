import os
import tempfile
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import whisper

# Inicializace transkripčního modelu
# Použij "medium" pro kompromis mezi kvalitou a výkonem, nebo "large" pro nejvyšší kvalitu
model = whisper.load_model("turbo")

# Funkce pro start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Ahoj! Jsem bot pro transkripci videa a audia.\n\n"
        "Pošli mi video nebo audio soubor a já ti vytvořím textový přepis."
    )

# Funkce pro nápovědu
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📝 *Jak mě používat:*\n"
        "1. Pošli mi video nebo audio soubor\n"
        "2. Počkej na zpracování (může trvat delší dobu u větších souborů)\n"
        "3. Obdržíš textový přepis\n\n"
        "Podporované formáty:\n"
        "- Video: mp4, avi, mov, mkv\n"
        "- Audio: mp3, ogg, wav, m4a\n"
        "- Hlasové zprávy Telegram\n\n"
        "Maximální velikost souboru: 20 MB (limit Telegramu)", 
        parse_mode="Markdown"
    )

# Funkce pro extrakci audia z videa
def extract_audio(video_path, audio_path):
    command = [
        "ffmpeg",
        "-i", video_path,
        "-q:a", "0",
        "-map", "a",
        "-f", "wav",
        audio_path
    ]
    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

# Funkce pro zpracování video/audio souborů
async def process_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Informování uživatele
    processing_message = await update.message.reply_text("🔄 Přijímám soubor... Probíhá zpracování, prosím čekej. Větší soubory mohou trvat delší dobu.")
    
    try:
        # Určení typu média
        is_video = False
        if update.message.video:
            media_file = await update.message.video.get_file()
            is_video = True
        elif update.message.audio:
            media_file = await update.message.audio.get_file()
        elif update.message.voice:
            media_file = await update.message.voice.get_file()
        elif update.message.document:
            media_file = await update.message.document.get_file()
            file_name = update.message.document.file_name.lower()
            is_video = any(file_name.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv'])
        else:
            await processing_message.edit_text("❌ Nepodporovaný typ souboru. Pošli prosím video nebo audio soubor.")
            return
        
        # Vytvoření dočasných souborů
        with tempfile.NamedTemporaryFile(suffix='.mp4' if is_video else '.ogg', delete=False) as temp_media:
            media_filename = temp_media.name
        
        # Stažení souboru
        await processing_message.edit_text("⬇️ Stahuji soubor...")
        await media_file.download_to_drive(media_filename)
        
        # Pokud je to video, extrahujeme audio
        if is_video:
            await processing_message.edit_text("🔊 Extrahuji audio z videa...")
            audio_filename = media_filename + ".wav"
            if not extract_audio(media_filename, audio_filename):
                await processing_message.edit_text("❌ Nepodařilo se extrahovat audio z videa.")
                os.unlink(media_filename)
                return
        else:
            audio_filename = media_filename
        
        # Transkripce
        await processing_message.edit_text("🔍 Provádím transkripci... Toto může trvat několik minut.")
        result = model.transcribe(audio_filename)
        transcript = result["text"].strip()
        
        # Odeslání transkripce
        if transcript:
            # Pokud je transkripce příliš dlouhá, rozdělíme ji na více zpráv
            if len(transcript) > 4000:
                chunks = [transcript[i:i+4000] for i in range(0, len(transcript), 4000)]
                await processing_message.edit_text("✅ *Transkripce dokončena!* Vzhledem k délce posílám ve více zprávách:", parse_mode="Markdown")
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(f"*Část {i+1}/{len(chunks)}:*\n\n{chunk}", parse_mode="Markdown")
            else:
                await processing_message.edit_text(f"✅ *Transkripce:*\n\n{transcript}", parse_mode="Markdown")
        else:
            await processing_message.edit_text("❌ Nepodařilo se rozpoznat žádný text. Zkus prosím jiný soubor.")
        
        # Vymazání dočasných souborů
        os.unlink(media_filename)
        if is_video and os.path.exists(audio_filename):
            os.unlink(audio_filename)
        
    except Exception as e:
        await processing_message.edit_text(f"❌ Došlo k chybě při zpracování: {str(e)}\n\nZkus menší soubor nebo jiný formát.")

# Hlavní funkce
def main() -> None:
    # Získání tokenu z proměnných prostředí
    TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Chyba: Nezadán TELEGRAM_TOKEN v proměnných prostředí.")
        return
    
    # Vytvoření aplikace
    application = Application.builder().token(TOKEN).build()
    
    # Registrace handlerů
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.AUDIO | filters.VOICE | filters.Document.ALL, process_media))
    
    # Spuštění bota
    print("Bot byl spuštěn. Stiskni Ctrl+C pro ukončení.")
    application.run_polling()

if __name__ == "__main__":
    main()
