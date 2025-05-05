from flask import (Flask, request, send_file, render_template_string, after_this_request, flash,
                   redirect, url_for, session)
from yt_dlp import YoutubeDL
from pydub import AudioSegment
import os
import uuid
import tempfile

app = Flask(__name__)
app.secret_key = 'supersecret'  # Required for flashing messages
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
# Save cookies from env var to temp file
# cookie_content = os.getenv('YOUTUBE_COOKIES')
# cookie_path = None
#
# if cookie_content:
#     try:
#         with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
#             f.write(cookie_content)
#             cookie_path = f.name
#         print(f"✅ Cookie file written to: {cookie_path}")
#     except Exception as e:
#         print(f"❌ Error writing cookie file: {e}")
# else:
#     print("⚠️ No YOUTUBE_COOKIES found in environment")


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        try:
            with YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
            session['video_url'] = url
            session['video_title'] = info['title']
            return redirect(url_for('preview'))
        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('index'))

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Tube2Tune - Convert YouTube to MP3</title>
        <link rel="stylesheet"
              href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>body { background-color: #f8f9fa; padding-top: 80px; }</style>
    </head>
    <body>
        <div class="container text-center">
            <h2 class="mb-4">🎧 Tube2Tune</h2>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, message in messages %}
                  <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            <form method="post">
                <div class="form-group">
                    <input type="url" name="url" class="form-control" placeholder="Paste YouTube URL" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Get Audio</button>
            </form>
        </div>
    </body>
    </html>
    ''')


@app.route('/preview', methods=['GET'])
def preview():
    if not session.get('video_url') or not session.get('video_title'):
        return redirect(url_for('index'))

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Confirm Download - Tube2Tune</title>
        <link rel="stylesheet"
              href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    </head>
    <body>
        <div class="container text-center" style="padding-top: 80px;">
            <h3>🎵 Ready to download:</h3>
            <p><strong>{{ session['video_title'] }}</strong></p>
            <form method="post" action="{{ url_for('download') }}">
                <button type="submit" class="btn btn-success">Download as MP3</button>
            </form>
            <a href="{{ url_for('index') }}" class="btn btn-secondary mt-2">Cancel</a>
        </div>
    </body>
    </html>
    ''')


@app.route('/download', methods=['POST'])
def download():
    url = session.get('video_url')
    if not url:
        flash("Invalid session. Please try again.", "danger")
        return redirect(url_for('index'))

    video_id = str(uuid.uuid4())
    temp_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.webm")
    mp3_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")

    # Define options first
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_file,
        'quiet': True,
        'postprocessors': [],
    }

    # ✅ Write cookies to temp file at request time
    cookie_path = None
    cookie_content = os.getenv('YOUTUBE_COOKIES')
    if cookie_content:
        try:
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
                f.write(cookie_content.strip('\"\''))
                cookie_path = f.name
            ydl_opts['cookiefile'] = cookie_path  # <-- NOW it's safe
            print(f"✅ Cookie file written to: {cookie_path}")
        except Exception as e:
            print(f"❌ Error writing cookie file: {e}")
    else:
        print("⚠️ No YOUTUBE_COOKIES found in environment")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        audio = AudioSegment.from_file(temp_file)
        audio.export(mp3_file, format='mp3')
        os.remove(temp_file)

        @after_this_request
        def remove_file(response):
            try:
                os.remove(mp3_file)
                if cookie_path:
                    os.remove(cookie_path)
                    print("🧹 Temp cookie file cleaned up")
            except Exception as e:
                app.logger.error(f"Cleanup failed: {e}")
            return response

        return send_file(mp3_file, as_attachment=True)

    except Exception as e:
        flash(f"Error: {str(e)}", 'danger')
        return redirect(url_for('index'))


@app.route('/health')
def health():
    return "OK", 200


if __name__ == '__main__':
    app.run(debug=True)
