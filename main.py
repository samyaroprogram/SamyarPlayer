import flet as ft
import os
import threading
import yt_dlp
import requests
import re
from mutagen.mp3 import MP3

current_lyrics = []
lyric_index = 0

def fetch_lyrics(track_name, artist_name):
    try:
        url = f"https://lrclib.net/api/get?track_name={track_name}&artist_name={artist_name}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data.get("syncedLyrics"): return data["syncedLyrics"]
        return None
    except: return None

def parse_lrc(lrc_text):
    if not lrc_text: return []
    lines = lrc_text.split('\n')
    parsed = []
    pattern = r'\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)'
    for line in lines:
        match = re.match(pattern, line)
        if match:
            minutes, seconds, ms, text = int(match.group(1)), int(match.group(2)), int(match.group(3)), match.group(4).strip()
            total_seconds = (minutes * 60) + seconds + (ms / 1000)
            if text: parsed.append((total_seconds, text))
    return parsed

def main(page: ft.Page):
    page.title = "Samyar Player"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.adaptive = True
    page.bgcolor = "#050505"
    page.decoration = ft.BoxDecoration(gradient=ft.LinearGradient(begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT, colors=["#1a0b2e", "#0f0c29", "#000000"]))

    file_picker = ft.FilePicker(on_result=lambda e: handle_file_pick(e))
    page.overlay.extend([file_picker])
    audio_player = ft.Audio(autoplay=False)
    page.overlay.append(audio_player)

    music_dir = os.path.join(page.get_application_documents_directory(), "SamyarMusic")
    if not os.path.exists(music_dir): os.makedirs(music_dir)

    playlist = []
    current_index = 0

    album_art = ft.Container(content=ft.Icon(ft.Icons.ALBUM, size=100, color=ft.Colors.with_opacity(0.5, "white")), width=220, height=220, border_radius=20, gradient=ft.LinearGradient(colors=["#6e8efb", "#a777e3"], begin=ft.Alignment.TOP_LEFT, end=ft.Alignment.BOTTOM_RIGHT), alignment=ft.Alignment.CENTER, shadow=ft.BoxShadow(blur_radius=30, color=ft.Colors.with_opacity(0.5, "#a777e3")), animate_rotation=ft.Animation(10000, ft.AnimationCurve.LINEAR))
    now_playing_title = ft.Text("آهنگی انتخاب نشده", size=20, weight=ft.FontWeight.W_900, color="white", text_align=ft.TextAlign.CENTER, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    now_playing_artist = ft.Text("Samyar Player", size=14, color=ft.Colors.with_opacity(0.6, "white"), text_align=ft.TextAlign.CENTER)
    lyric_text = ft.Text("متن آهنگ...", size=16, color="#a777e3", text_align=ft.TextAlign.CENTER, weight=ft.FontWeight.BOLD)
    progress_slider = ft.Slider(min=0, max=100, value=0, expand=True, active_color="#a777e3", inactive_color=ft.Colors.with_opacity(0.2, "white"), thumb_color="white")
    time_current = ft.Text("00:00", size=11, color="grey")
    time_total = ft.Text("00:00", size=11, color="grey")
    play_btn = ft.IconButton(icon=ft.Icons.PLAY_ARROW_ROUNDED, icon_size=60, icon_color="white", bgcolor=ft.Colors.with_opacity(0.1, "white"), style=ft.ButtonStyle(shape=ft.CircleBorder(), padding=10))
    prev_btn = ft.IconButton(icon=ft.Icons.SKIP_PREVIOUS_ROUNDED, icon_size=35, icon_color="white")
    next_btn = ft.IconButton(icon=ft.Icons.SKIP_NEXT_ROUNDED, icon_size=35, icon_color="white")
    music_list = ft.ListView(expand=True, spacing=8, padding=10)
    yt_results = ft.ListView(height=200)

    def handle_file_pick(e: ft.FilePickerResultEvent):
        if e.files:
            for f in e.files:
                if f.path not in playlist:
                    playlist.append(f.path)
                    add_music_to_ui(f.name, f.path)
            page.update()

    def add_music_to_ui(title, path):
        def play_this(e):
            global current_index
            current_index = playlist.index(path)
            play_song(path)
        row = ft.Container(content=ft.Row([ft.Container(content=ft.Icon(ft.Icons.MUSIC_NOTE_ROUNDED, color="white"), width=40, height=40, border_radius=10, bgcolor=ft.Colors.with_opacity(0.1, "#a777e3"), alignment=ft.Alignment.CENTER), ft.Column([ft.Text(title, color="white", weight=ft.FontWeight.BOLD, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS), ft.Text("Audio", color="grey", size=10)], expand=True, spacing=2), ft.IconButton(icon=ft.Icons.PLAY_ARROW, icon_color="#a777e3", on_click=play_this)]), padding=10, border_radius=15, bgcolor=ft.Colors.with_opacity(0.05, "white"), border=ft.Border.all(1, ft.Colors.with_opacity(0.1, "white")))
        music_list.controls.append(row)

    def format_time(ms):
        if not ms or ms < 0: return "00:00"
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def play_song(path):
        global current_lyrics, lyric_index
        filename = os.path.basename(path)
        now_playing_title.value = os.path.splitext(filename)[0]
        audio_player.src = path
        audio_player.update()
        audio_player.play()
        play_btn.icon = ft.Icons.PAUSE_ROUNDED
        album_art.rotate = ft.Rotate(angle=6.28)
        artist = "Unknown Artist"
        try:
            audio = MP3(path)
            if audio.get('TPE1'): artist = str(audio.get('TPE1'))
            now_playing_artist.value = artist
        except: now_playing_artist.value = "Samyar Player"
        lyric_text.value = "در حال دریافت متن..."
        page.update()
        def fetch_lyrics_thread():
            global current_lyrics, lyric_index
            search_name = os.path.splitext(filename)[0]
            lrc_raw = fetch_lyrics(search_name, artist)
            if lrc_raw:
                current_lyrics = parse_lrc(lrc_raw)
                lyric_index = 0
            else:
                current_lyrics = []
                lyric_text.value = "متن آهنگ پیدا نشد."
            page.update()
        threading.Thread(target=fetch_lyrics_thread, daemon=True).start()

    def on_position_changed(e):
        global lyric_index
        current_time = audio_player.get_current_position() / 1000
        duration = audio_player.get_duration()
        if duration > 0:
            progress_slider.value = (current_time / (duration / 1000)) * 100
            time_current.value = format_time(audio_player.get_current_position())
        if current_lyrics:
            while lyric_index < len(current_lyrics) - 1 and current_time >= current_lyrics[lyric_index + 1][0]:
                lyric_index += 1
            if current_time >= current_lyrics[lyric_index][0]:
                if lyric_text.value != current_lyrics[lyric_index][1]:
                    lyric_text.value = current_lyrics[lyric_index][1]
        page.update()

    audio_player.on_position_changed = on_position_changed
    audio_player.on_duration_changed = lambda e: setattr(time_total, 'value', format_time(audio_player.get_duration()))

    def toggle_play(e):
        if audio_player.is_playing:
            audio_player.pause()
            play_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
            album_art.rotate = ft.Rotate(angle=0)
        else:
            audio_player.resume()
            play_btn.icon = ft.Icons.PAUSE_ROUNDED
            album_art.rotate = ft.Rotate(angle=6.28)
        page.update()

    def next_song(e):
        global current_index
        if playlist:
            current_index = (current_index + 1) % len(playlist)
            play_song(playlist[current_index])

    def prev_song(e):
        global current_index
        if playlist:
            current_index = (current_index - 1) % len(playlist)
            play_song(playlist[current_index])

    play_btn.on_click = toggle_play
    next_btn.on_click = next_song
    prev_btn.on_click = prev_song

    search_input = ft.TextField(hint_text="جستجوی آهنگ در یوتیوب...", bgcolor=ft.Colors.with_opacity(0.1, "white"), border_radius=30, color="white", border=ft.InputBorder.NONE, prefix_icon=ft.Icons.SEARCH, text_size=13)

    def download_url(url, title):
        def run():
            ydl_opts = {'format': 'bestaudio/best', 'outtmpl': os.path.join(music_dir, '%(title)s.%(ext)s'), 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'm4a', 'preferredquality': '192'}]}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl: ydl.download([url])
                page.snack_bar = ft.SnackBar(ft.Text(f"دانلود {title} کامل شد!"))
                page.snack_bar.open = True
                for f in os.listdir(music_dir):
                    p = os.path.join(music_dir, f)
                    if p not in playlist:
                        playlist.append(p)
                        add_music_to_ui(f, p)
                page.update()
            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"خطا در دانلود: {ex}"))
                page.snack_bar.open = True
                page.update()
        threading.Thread(target=run).start()

    def search_yt(e):
        q = search_input.value
        if not q: return
        yt_results.controls.append(ft.ProgressBar(color="#a777e3"))
        page.update()
        def run_search():
            ydl_opts = {'format': 'bestaudio/best', 'quiet': True, 'extract_flat': True}
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"ytsearch5:{q}", download=False)
                    yt_results.controls.clear()
                    for entry in info.get('entries', []):
                        if entry:
                            row = ft.ListTile(leading=ft.Icon(ft.Icons.DOWNLOAD, color="#a777e3"), title=ft.Text(entry.get('title'), color="white", size=12), on_click=lambda e, u=entry.get('url'), t=entry.get('title'): download_url(u, t))
                            yt_results.controls.append(row)
                    page.update()
            except:
                yt_results.controls.append(ft.Text("خطا در جستجو (VPN لازم است)", color="red"))
                page.update()
        threading.Thread(target=run_search).start()

    search_input.on_submit = search_yt

    header = ft.Container(content=ft.Row([ft.Icon(ft.Icons.GRAPHIC_EQ_ROUNDED, color="#a777e3", size=25), ft.Text("Samyar Player", size=18, weight=ft.FontWeight.BOLD, color="white")]), padding=10)
    player_section = ft.Container(content=ft.Column([album_art, now_playing_title, now_playing_artist, ft.Container(content=lyric_text, padding=10, border_radius=10, bgcolor=ft.Colors.with_opacity(0.05, "white"), alignment=ft.Alignment.CENTER), ft.Row([time_current, progress_slider, time_total], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), ft.Row([prev_btn, play_btn, next_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=20)], horizontal_alignment=ft.CrossAxisAlignment.CENTER), padding=10)
    glass_container = ft.Container(content=player_section, bgcolor=ft.Colors.with_opacity(0.1, "white"), blur=20, border_radius=25, border=ft.Border.all(1, ft.Colors.with_opacity(0.2, "white")), margin=10)
    tab_offline = ft.Container(content=ft.Column([ft.ElevatedButton("📂 افزودن آهنگ از گوشی", icon=ft.Icons.FOLDER_OPEN, on_click=lambda _: file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.AUDIO), bgcolor="#a777e3", color="white", style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))), music_list], expand=True), padding=10)
    tab_download = ft.Container(content=ft.Column([search_input, yt_results]), padding=10)
    tabs = ft.Tabs(selected_index=0, animation_duration=300, tabs=[ft.Tab(text="پلیر", icon=ft.Icons.PLAY_CIRCLE, content=glass_container), ft.Tab(text="آهنگ‌ها", icon=ft.Icons.LIBRARY_MUSIC, content=tab_offline), ft.Tab(text="دانلود", icon=ft.Icons.CLOUD_DOWNLOAD, content=tab_download)], expand=True)
    page.add(ft.Column([header, tabs], expand=True, spacing=0))

ft.run(main)
