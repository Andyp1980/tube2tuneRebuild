from flask import Flask, request, send_file, render_template_string, after_this_request, flash, redirect, url_for
from yt_dlp import YoutubeDL
from pydub import AudioSegment
import os
import uuid
import tempfile  # ✅ added

app = Flask(__name__)
app.secret_key = 'supersecret'
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        video_id = str(uuid.uuid4())
        temp_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.webm")
        mp3_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")

        # ✅ Handle YouTube cookies
        cookie_path = None
        cookie_content = os.getenv('YOUTUBE_COOKIES')
        if cookie_content:
            try:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as f:
                    f.write(cookie_content)
                    cookie_path = f.name
                print(f"✅ Cookie file written: {cookie_path}")
            except Exception as e:
                print(f"❌ Failed to write cookie file: {e}")
        else:
            print("⚠️ No YOUTUBE_COOKIES found in environment")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': temp_file,
            'quiet': True,
            'postprocessors': [],
        }

        if cookie_path:
            ydl_opts['cookiefile'] = cookie_path  # ✅ pass to yt_dlp

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            audio = AudioSegment.from_file(temp_file)
            audio.export(mp3_file, format='mp3')
            os.remove(temp_file)
            if cookie_path:
                os.remove(cookie_path)  # ✅ clean up

            @after_this_request
            def remove_file(response):
                try:
                    os.remove(mp3_file)
                except Exception as e:
                    app.logger.error(f"Failed to delete {mp3_file}: {e}")
                return response

            return send_file(mp3_file, as_attachment=True)

        except Exception as e:
            flash(f"Error: {str(e)}", 'danger')
            return redirect(url_for('index'))

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube to MP3 Converter</title>
        <link rel="stylesheet"
              href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
            body { background-color: #f8f9fa; padding-top: 80px; }
            .container { max-width: 600px; }
        </style>
    </head>
    <body>
        <div class="container text-center">
            <h2 class="mb-4">🎧 YouTube to MP3 Converter</h2>
            {% with messages = get_flashed_messages(with_categories=true) %}
              {% if messages %}
                {% for category, message in messages %}
                  <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                    {{ message }}
                    <button type="button" class="close" data-dismiss="alert">&times;</button>
                  </div>
                {% endfor %}
              {% endif %}
            {% endwith %}
            <form method="post">
                <div class="form-group">
                    <input type="url" name="url" class="form-control"
                           placeholder="Paste YouTube link here" required>
                </div>
                <button type="submit" class="btn btn-primary btn-block">Convert to MP3</button>
            </form>
        </div>
        <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(debug=True)
