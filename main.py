import os
import random
import threading
import time
import webbrowser
from urllib.parse import quote

import mutagen
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.lang import Builder
from kivy.properties import NumericProperty
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.utils import platform

EXTS = (".mp3", ".wav", ".ogg", ".flac", ".m4a")
GREEN = (0.114, 0.725, 0.329, 1)
WHITE = (1, 1, 1, 1)
GREY = (0.16, 0.16, 0.16, 1)

KV = """
#:import dp kivy.metrics.dp

<Btn@Button>:
    background_normal: ''
    background_color: 0.16, 0.16, 0.16, 1
    color: 1, 1, 1, 1
    font_size: '14sp'

<TrackRow>:
    background_normal: ''
    background_color: 0.08, 0.08, 0.08, 1
    halign: 'left'
    valign: 'middle'
    text_size: self.width - dp(24), self.height
    on_release: app.play_index(self.idx)

BoxLayout:
    orientation: 'vertical'
    padding: dp(10), dp(28), dp(10), dp(8)
    spacing: dp(8)
    canvas.before:
        Color:
            rgba: 0.043, 0.043, 0.043, 1
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        text: 'Musify'
        font_size: '26sp'
        bold: True
        color: 0.114, 0.725, 0.329, 1
        size_hint_y: None
        height: dp(40)
        halign: 'left'
        text_size: self.size
    TextInput:
        id: search
        hint_text: 'Search your library'
        multiline: False
        size_hint_y: None
        height: dp(42)
        background_color: 0.16, 0.16, 0.16, 1
        foreground_color: 1, 1, 1, 1
        hint_text_color: 0.65, 0.65, 0.65, 1
        cursor_color: 1, 1, 1, 1
        on_text: app.refresh()
    BoxLayout:
        size_hint_y: None
        height: dp(42)
        spacing: dp(6)
        Btn:
            text: 'Add Files'
            background_color: 0.114, 0.725, 0.329, 1
            color: 0, 0, 0, 1
            on_release: app.add_files()
        Btn:
            text: 'Scan'
            on_release: app.scan()
        Btn:
            text: 'A-Z'
            on_release: app.sort('title')
        Btn:
            text: 'Artist'
            on_release: app.sort('artist')
        Btn:
            text: 'Clear'
            on_release: app.clear()
    RecycleView:
        id: rv
        viewclass: 'TrackRow'
        RecycleBoxLayout:
            default_size: None, dp(56)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            spacing: dp(2)
    Label:
        id: toast
        text: ''
        font_size: '12sp'
        color: 0.114, 0.725, 0.329, 1
        size_hint_y: None
        height: dp(20)
    Label:
        id: title
        text: 'Nothing playing'
        font_size: '16sp'
        bold: True
        size_hint_y: None
        height: dp(24)
        shorten: True
        text_size: self.width, None
    Label:
        id: artist
        text: 'Add some music to get started'
        font_size: '13sp'
        color: 0.65, 0.65, 0.65, 1
        size_hint_y: None
        height: dp(20)
        shorten: True
        text_size: self.width, None
    BoxLayout:
        size_hint_y: None
        height: dp(36)
        Label:
            id: elapsed
            text: '0:00'
            size_hint_x: None
            width: dp(48)
        SeekSlider:
            id: seek
            min: 0
            max: 1
            value: 0
        Label:
            id: total
            text: '0:00'
            size_hint_x: None
            width: dp(48)
    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(6)
        Btn:
            id: shuf
            text: 'Shuffle'
            on_release: app.toggle_shuffle()
        Btn:
            text: 'Prev'
            on_release: app.prev_track()
        Btn:
            id: play
            text: 'Play'
            background_color: 0.114, 0.725, 0.329, 1
            color: 0, 0, 0, 1
            on_release: app.toggle_play()
        Btn:
            text: 'Next'
            on_release: app.next_track()
        Btn:
            id: rep
            text: 'Repeat'
            on_release: app.cycle_repeat()
    BoxLayout:
        size_hint_y: None
        height: dp(42)
        spacing: dp(6)
        Btn:
            id: mute
            text: 'Mute'
            size_hint_x: None
            width: dp(64)
            on_release: app.toggle_mute()
        Slider:
            id: vol
            min: 0
            max: 1
            value: 0.8
            on_value: app.set_volume(self.value)
        Btn:
            text: 'Remove'
            size_hint_x: None
            width: dp(76)
            on_release: app.remove_current()
        Btn:
            text: 'YouTube'
            size_hint_x: None
            width: dp(80)
            on_release: app.youtube()
"""


def fmt(seconds):
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 60}:{seconds % 60:02d}"


def read_meta(path):
    title = os.path.splitext(os.path.basename(path))[0]
    artist, length = "Unknown Artist", 0
    try:
        audio = mutagen.File(path, easy=True)
        if audio is not None:
            if audio.info is not None:
                length = audio.info.length
            t, a = audio.get("title"), audio.get("artist")
            if t:
                title = str(t[0])
            if a:
                artist = str(a[0])
    except Exception:
        pass
    return {"path": path, "title": title, "artist": artist, "length": length}


class TrackRow(Button):
    idx = NumericProperty(0)


class SeekSlider(Slider):
    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            App.get_running_app().scrubbing = True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        app = App.get_running_app()
        if app.scrubbing:
            app.scrubbing = False
            app.seek(self.value)
        return super().on_touch_up(touch)


class Musify(App):
    title = "Musify"

    def build(self):
        self.tracks = []
        self.index = -1
        self.sound = None
        self.playing = False
        self.paused = False
        self.scrubbing = False
        self.pos = 0
        self.length = 0
        self.started = 0
        self.shuffle = False
        self.repeat = 0
        self.volume = 0.8
        self.muted = False
        self.sort_rev = {}
        self.ui = Builder.load_string(KV)
        return self.ui

    def on_start(self):
        self.load_library()
        self.refresh()
        Clock.schedule_interval(self.tick, 0.25)
        if platform == "android":
            from android.permissions import request_permissions
            request_permissions(
                ["android.permission.READ_EXTERNAL_STORAGE", "android.permission.READ_MEDIA_AUDIO"],
                lambda perms, grants: Clock.schedule_once(lambda dt: self.scan(), 0))
        elif not self.tracks:
            self.scan()

    def on_stop(self):
        self.halt()
        self.save_library()

    def toast(self, message):
        self.ui.ids.toast.text = message
        Clock.unschedule(self.clear_toast)
        Clock.schedule_once(self.clear_toast, 3.5)

    def clear_toast(self, dt):
        self.ui.ids.toast.text = ""

    def library_file(self):
        return os.path.join(self.user_data_dir, "library.txt")

    def save_library(self):
        try:
            with open(self.library_file(), "w", encoding="utf-8") as f:
                f.write("\n".join(t["path"] for t in self.tracks))
        except Exception:
            pass

    def load_library(self):
        try:
            with open(self.library_file(), encoding="utf-8") as f:
                paths = [p.strip() for p in f if p.strip() and os.path.isfile(p.strip())]
        except Exception:
            return
        self.tracks = [read_meta(p) for p in paths]

    def refresh(self):
        q = self.ui.ids.search.text.strip().lower()
        data = []
        for i, t in enumerate(self.tracks):
            if q and q not in t["title"].lower() and q not in t["artist"].lower():
                continue
            data.append({
                "idx": i,
                "text": f"{t['title']}\n{t['artist']}  -  {fmt(t['length'])}",
                "color": GREEN if i == self.index else WHITE,
            })
        self.ui.ids.rv.data = data

    def add_paths(self, paths, autoplay=False):
        known = {t["path"] for t in self.tracks}
        fresh = []
        for p in paths:
            p = os.path.normpath(p)
            if p not in known and os.path.isfile(p):
                known.add(p)
                fresh.append(p)
        if not fresh:
            self.toast("No new tracks added")
            return

        def work():
            metas = [read_meta(p) for p in fresh]
            Clock.schedule_once(lambda dt: self.add_metas(metas, autoplay), 0)

        threading.Thread(target=work, daemon=True).start()

    def add_metas(self, metas, autoplay):
        first = len(self.tracks)
        self.tracks.extend(metas)
        self.refresh()
        self.toast(f"Added {len(metas)} track{'s' if len(metas) != 1 else ''}")
        if autoplay and not self.playing:
            self.play_index(first)

    def add_files(self):
        try:
            from plyer import filechooser
            filechooser.open_file(
                multiple=True,
                on_selection=lambda sel: Clock.schedule_once(
                    lambda dt: self.add_paths(sel or [], True), 0))
        except Exception as e:
            self.toast(f"File picker unavailable: {e}")

    def scan(self):
        def work():
            if platform == "android":
                from android.storage import primary_external_storage_path
                base = primary_external_storage_path()
            else:
                base = os.path.expanduser("~")
            found = []
            for name in ("Music", "Download", "Podcasts"):
                for d, _, files in os.walk(os.path.join(base, name)):
                    found += [os.path.join(d, f) for f in sorted(files) if f.lower().endswith(EXTS)]
            Clock.schedule_once(lambda dt: self.add_paths(found), 0)

        threading.Thread(target=work, daemon=True).start()
        self.toast("Scanning for music...")

    def clear(self):
        self.stop_playback()
        self.tracks, self.index = [], -1
        self.reset_now_playing()
        self.refresh()

    def sort(self, key):
        rev = self.sort_rev.get(key, False)
        current = self.tracks[self.index] if 0 <= self.index < len(self.tracks) else None
        self.tracks.sort(key=lambda t: t[key].lower(), reverse=rev)
        self.sort_rev[key] = not rev
        self.index = next((i for i, t in enumerate(self.tracks) if t is current), -1)
        self.refresh()

    def remove_current(self):
        if not 0 <= self.index < len(self.tracks):
            return
        self.stop_playback()
        del self.tracks[self.index]
        self.index = -1
        self.reset_now_playing()
        self.refresh()
        self.toast("Removed track")

    def reset_now_playing(self):
        ids = self.ui.ids
        ids.title.text = "Nothing playing"
        ids.artist.text = "Add some music to get started"
        ids.elapsed.text = ids.total.text = "0:00"
        ids.seek.value = 0

    def halt(self):
        if self.sound:
            try:
                self.sound.stop()
                self.sound.unload()
            except Exception:
                pass
            self.sound = None

    def stop_playback(self):
        self.halt()
        self.playing = self.paused = False
        self.ui.ids.play.text = "Play"
        self.ui.ids.seek.value = 0
        self.ui.ids.elapsed.text = "0:00"

    def play_index(self, i):
        if not 0 <= i < len(self.tracks):
            return
        self.halt()
        t = self.tracks[i]
        s = SoundLoader.load(t["path"])
        if not s:
            self.toast("Can't play this file")
            return
        s.volume = 0 if self.muted else self.volume
        s.play()
        self.sound = s
        self.index = i
        self.playing, self.paused = True, False
        self.pos = 0
        self.started = time.time()
        self.length = s.length or t["length"]
        ids = self.ui.ids
        ids.title.text = t["title"]
        ids.artist.text = t["artist"]
        ids.seek.max = max(self.length, 1)
        ids.seek.value = 0
        ids.elapsed.text = "0:00"
        ids.total.text = fmt(self.length)
        ids.play.text = "Pause"
        self.refresh()

    def toggle_play(self):
        if not self.tracks:
            self.add_files()
        elif not self.playing:
            self.play_index(self.index if self.index >= 0 else 0)
        elif self.paused:
            s = self.sound
            s.play()
            pos = self.pos
            Clock.schedule_once(lambda dt: s.seek(pos), 0.15)
            self.started = time.time()
            self.paused = False
            self.ui.ids.play.text = "Pause"
        else:
            self.pos = self.sound.get_pos() or self.pos
            self.sound.stop()
            self.paused = True
            self.ui.ids.play.text = "Play"

    def seek(self, seconds):
        if not self.sound:
            return
        self.pos = seconds
        self.ui.ids.elapsed.text = fmt(seconds)
        if not self.paused:
            self.sound.seek(seconds)
            self.started = time.time()

    def next_index(self):
        n = len(self.tracks)
        if n == 0:
            return None
        if self.shuffle and n > 1:
            return random.choice([i for i in range(n) if i != self.index])
        nxt = self.index + 1
        if nxt >= n:
            return 0 if self.repeat == 1 else None
        return nxt

    def next_track(self):
        if self.tracks:
            nxt = self.next_index()
            self.play_index(0 if nxt is None else nxt)

    def prev_track(self):
        if not self.tracks:
            return
        if self.playing and not self.paused and self.sound and (self.sound.get_pos() or 0) > 3:
            self.seek(0)
            return
        i = self.index - 1
        self.play_index(len(self.tracks) - 1 if i < 0 else i)

    def on_end(self):
        if self.repeat == 2:
            self.play_index(self.index)
            return
        nxt = self.next_index()
        if nxt is None:
            self.stop_playback()
        else:
            self.play_index(nxt)

    def tick(self, dt):
        s = self.sound
        if not s or not self.playing or self.paused:
            return
        pos = s.get_pos() or 0
        done = s.state == "stop" or (self.length > 0 and pos >= self.length - 0.4)
        if done and time.time() - self.started > 1:
            self.on_end()
            return
        self.pos = pos
        if not self.scrubbing:
            self.ui.ids.seek.value = min(pos, self.ui.ids.seek.max)
            self.ui.ids.elapsed.text = fmt(pos)

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        self.ui.ids.shuf.background_color = GREEN if self.shuffle else GREY
        self.toast("Shuffle on" if self.shuffle else "Shuffle off")

    def cycle_repeat(self):
        self.repeat = (self.repeat + 1) % 3
        self.ui.ids.rep.background_color = GREEN if self.repeat else GREY
        self.ui.ids.rep.text = ["Repeat", "Repeat all", "Repeat 1"][self.repeat]

    def apply_volume(self):
        if self.sound:
            self.sound.volume = 0 if self.muted else self.volume

    def set_volume(self, value):
        self.volume = value
        if value > 0 and self.muted:
            self.muted = False
            self.ui.ids.mute.text = "Mute"
        self.apply_volume()

    def toggle_mute(self):
        self.muted = not self.muted
        self.ui.ids.mute.text = "Unmute" if self.muted else "Mute"
        self.apply_volume()

    def youtube(self):
        q = self.ui.ids.search.text.strip()
        if not q and 0 <= self.index < len(self.tracks):
            t = self.tracks[self.index]
            q = f"{t['title']} {t['artist']}"
        if q:
            webbrowser.open("https://www.youtube.com/results?search_query=" + quote(q))
        else:
            self.toast("Type something to search")


if __name__ == "__main__":
    Musify().run()
