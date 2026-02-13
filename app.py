
import os
import smtplib
import zipfile
from flask import Flask, request, render_template
from email.message import EmailMessage
import yt_dlp
from pydub import AudioSegment
from moviepy.editor import VideoFileClip

app = Flask(__name__)

def download_videos(singer, num_videos, download_dir):
    search_query = f"ytsearch{num_videos}:{singer} official song"
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([search_query])

def convert_videos_to_audio(video_dir, audio_dir):
    os.makedirs(audio_dir, exist_ok=True)
    audio_files = []
    for file in os.listdir(video_dir):
        if file.endswith((".mp4", ".mkv", ".webm", ".flv")):
            video_path = os.path.join(video_dir, file)
            audio_name = os.path.splitext(file)[0] + ".mp3"
            audio_path = os.path.join(audio_dir, audio_name)
            clip = VideoFileClip(video_path)
            clip.audio.write_audiofile(audio_path, logger=None)
            clip.close()
            audio_files.append(audio_path)
    return audio_files

def trim_audios(audio_files, duration_sec, trimmed_dir):
    os.makedirs(trimmed_dir, exist_ok=True)
    trimmed_files = []
    for file in audio_files:
        audio = AudioSegment.from_file(file)
        trimmed = audio[:duration_sec * 1000]
        out_path = os.path.join(trimmed_dir, os.path.basename(file))
        trimmed.export(out_path, format="mp3")
        trimmed_files.append(out_path)
    return trimmed_files

def merge_audios(audio_files, output_file):
    combined = AudioSegment.empty()
    for file in audio_files:
        audio = AudioSegment.from_file(file)
        combined += audio
    combined.export(output_file, format="mp3")

def send_email(receiver, zip_path):
    sender_email = os.environ.get("SENDER_EMAIL")
    app_password = os.environ.get("APP_PASSWORD")
    msg = EmailMessage()
    msg["Subject"] = "Your Mashup File"
    msg["From"] = sender_email
    msg["To"] = receiver
    msg.set_content("Your mashup is attached.")
    with open(zip_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="zip",
            filename=os.path.basename(zip_path),
        )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(msg)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        singer = request.form["singer"]
        num = int(request.form["num"])
        dur = int(request.form["dur"])
        email = request.form["email"]

        base = "web_mashup"
        video_dir = os.path.join(base, "videos")
        audio_dir = os.path.join(base, "audios")
        trimmed_dir = os.path.join(base, "trimmed")

        os.makedirs(video_dir, exist_ok=True)

        download_videos(singer, num, video_dir)
        audios = convert_videos_to_audio(video_dir, audio_dir)
        trimmed = trim_audios(audios, dur, trimmed_dir)

        output_mp3 = "mashup.mp3"
        merge_audios(trimmed, output_mp3)

        zip_name = "mashup.zip"
        with zipfile.ZipFile(zip_name, "w") as z:
            z.write(output_mp3)

        send_email(email, zip_name)

        return "Mashup sent to your email!"

    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
