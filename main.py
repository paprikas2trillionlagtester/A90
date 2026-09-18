# main.py — a90 jump-scare app
# ─────────────────────────────────────────────────────────────────────────────
# BEHAVIOUR
#   Open the app → it tucks itself to the background after a moment.
#   Sometime in the next ~minute the a90 face pops up fullscreen for 3 s.
#   Touch the screen while he's there → scare flash + scream, then he vanishes
#   and the app hides again and re-arms for the next pop-up.
#   No reaction → the face silently disappears and the cycle repeats.
#
#   This is an honest jump-scare app: it is named a90 (no disguise), it never
#   pretends your phone is damaged, and it uninstalls like any normal app.
#
# EXIT  tap the four screen corners in order TL→TR→BR→BL within 5 s to stop it,
#       or just uninstall it normally.
# ─────────────────────────────────────────────────────────────────────────────

from kivy.app    import App
from kivy.uix.widget      import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label       import Label
from kivy.graphics        import (Color, Ellipse, Rectangle, Line,
                                   PushMatrix, PopMatrix, Rotate, Translate)
from kivy.clock           import Clock
from kivy.core.window     import Window
from kivy.core.audio      import SoundLoader
from kivy.utils           import platform
import random, math, os

# ── Android background helpers (no-ops on desktop) ───────────────────────────
if platform == 'android':
    from jnius import autoclass

    _Activity     = autoclass('org.kivy.android.PythonActivity')
    _Intent       = autoclass('android.content.Intent')
    _PowerManager = autoclass('android.os.PowerManager')
    _Context      = autoclass('android.content.Context')

    def _send_to_back():
        _Activity.mActivity.moveTaskToBack(True)

    def _bring_to_front():
        act    = _Activity.mActivity
        intent = _Intent(act, act.__class__)
        intent.addFlags(_Intent.FLAG_ACTIVITY_REORDER_TO_FRONT)
        act.startActivity(intent)

    def _acquire_wake_lock():
        """Partial wake lock — keeps CPU running so the pop-up timer fires."""
        act  = _Activity.mActivity
        pm   = act.getSystemService(_Context.POWER_SERVICE)
        wl   = pm.newWakeLock(_PowerManager.PARTIAL_WAKE_LOCK, 'a90:wl')
        wl.acquire()
        return wl

else:
    # Desktop: no-ops so the file still runs for testing
    def _send_to_back():    pass
    def _bring_to_front():  pass
    def _acquire_wake_lock(): return None


# ── Tunables ──────────────────────────────────────────────────────────────────
SCARE_DURATION = 3.0          # how long the face lingers before giving up
FLASH_DURATION = 1.0          # how long the scare flash + scream lasts
INTERVAL       = (10, 60)     # seconds until the next pop-up

# Flat palette — no glow
BG_COL    = (0.05, 0.04, 0.04, 1)
FACE_COL  = (0.15, 0.02, 0.02, 1)
EYE_W     = (0.91, 0.90, 0.83, 1)
EYE_P     = (0.03, 0.02, 0.02, 1)
MOUTH_COL = (0.01, 0.01, 0.01, 1)
LINE_COL  = (0.76, 0.07, 0.07, 1)

EYE_LAYOUT = [
    (-0.48,  0.55, 0.20, 0.11),
    ( 0.00,  0.60, 0.23, 0.13),
    ( 0.48,  0.55, 0.20, 0.11),
    (-0.44,  0.18, 0.18, 0.10),
    ( 0.20,  0.22, 0.20, 0.11),
    (-0.18, -0.12, 0.19, 0.10),
    ( 0.46, -0.08, 0.17, 0.09),
    (-0.42, -0.42, 0.16, 0.09),
    ( 0.10, -0.38, 0.17, 0.09),
    ( 0.44, -0.42, 0.15, 0.08),
]


class PrankWidget(Widget):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.state        = "idle"
        self._scare_t     = 0.0
        self._corner_seq  = []
        # prefer mp3, fall back to wav if someone swaps the file
        _snd_file = next((f for f in ("scare.mp3", "scare.wav")
                          if os.path.exists(f)), None)
        self._sound = SoundLoader.load(_snd_file) if _snd_file else None

        Window.clearcolor = (0, 0, 0, 1)
        self.bind(size=self._on_resize)
        self._schedule_next()

    def _on_resize(self, *_):
        if self.state in ("face", "scare"):
            self._redraw()

    # ── scheduling ────────────────────────────────────────────────────────────

    def _schedule_next(self):
        Clock.schedule_once(self._show_face, random.uniform(*INTERVAL))

    def _show_face(self, *_):
        self.state, self._scare_t = "face", 0.0
        _bring_to_front()                    # pop out of background
        Window.fullscreen = "auto"
        self._redraw()
        Clock.schedule_interval(self._face_tick, 0.05)

    def _face_tick(self, dt):
        if self.state != "face":
            return False
        self._scare_t += dt
        if self._scare_t >= SCARE_DURATION:
            self.state = "idle"
            self.canvas.clear()
            _send_to_back()                  # nobody reacted — hide again
            self._schedule_next()
            return False
        self._redraw()

    # ── touch ─────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        self._check_corner(touch)
        if self.state == "face":
            self._trigger_scare()            # touch anything → scare
        return True

    def _check_corner(self, touch):
        """Secret exit: tap TL → TR → BR → BL within 5 s."""
        w, h = Window.width, Window.height
        m = min(w, h) * 0.15
        corners = [
            touch.x < m     and touch.y > h - m,
            touch.x > w - m and touch.y > h - m,
            touch.x > w - m and touch.y < m,
            touch.x < m     and touch.y < m,
        ]
        idx = next((i for i, c in enumerate(corners) if c), None)
        if idx is None:
            return
        now = Clock.get_time()
        if self._corner_seq and now - self._corner_seq[-1][1] > 5:
            self._corner_seq.clear()
        if idx == len(self._corner_seq):
            self._corner_seq.append((idx, now))
            if len(self._corner_seq) == 4:
                App.get_running_app().stop()

    # ── scare flash ───────────────────────────────────────────────────────────

    def _trigger_scare(self):
        if self.state != "face":
            return
        self.state, self._scare_t = "scare", 0.0
        Clock.unschedule(self._face_tick)
        if self._sound:
            self._sound.loop = True
            self._sound.play()
        Clock.schedule_interval(self._scare_flash, 0.06)

    def _scare_flash(self, dt):
        self._scare_t += dt
        self._redraw(scare=True)
        if self._scare_t > FLASH_DURATION:
            Clock.unschedule(self._scare_flash)
            self._end_scare()
            return False

    def _end_scare(self):
        if self._sound:
            self._sound.stop()
        self.state = "idle"
        self.canvas.clear()
        _send_to_back()                      # hide again
        self._schedule_next()                # re-arm for the next pop-up

    # ── face drawing ──────────────────────────────────────────────────────────

    def _redraw(self, *_, scare=False):
        if self.state not in ("face", "scare"):
            return
        w, h   = Window.width, Window.height
        cx, cy = w / 2, h / 2
        face_w = min(w, h) * 0.52
        face_h = min(w, h) * 0.82
        drift  = math.sin(self._scare_t * 1.8) * (h * 0.012)

        self.canvas.clear()
        with self.canvas:
            Color(*BG_COL)
            Rectangle(pos=(0, 0), size=(w, h))

            Color(*FACE_COL)
            Ellipse(pos=(cx - face_w/2, cy - face_h/2 + drift),
                    size=(face_w, face_h))

            scale = 1.0 + (0.08 if scare else 0.02 * math.sin(self._scare_t * 3))
            for (rx, ry, rw, rh) in EYE_LAYOUT:
                ex = cx + rx * face_w * 0.92
                ey = cy + ry * face_h * 0.52 + drift
                ew, eh = rw * face_w * scale, rh * face_h * scale
                Color(*EYE_W)
                Ellipse(pos=(ex - ew, ey - eh), size=(ew*2, eh*2))
                pr = min(ew, eh) * 0.52
                Color(*EYE_P)
                Ellipse(pos=(ex - pr, ey - pr*1.1), size=(pr*2, pr*2))

            mw = face_w * 0.88
            mh = face_h * 0.14
            mx = cx - mw / 2
            my = cy - face_h * 0.44 + drift
            Color(*MOUTH_COL)
            Rectangle(pos=(mx, my), size=(mw, mh))
            tw = mw / 7
            for i in range(7):
                th = mh * (0.55 if i % 2 == 0 else 0.30)
                Color(*FACE_COL)
                Rectangle(pos=(mx + i*tw + 1, my + mh - th), size=(tw - 2, th))

            if scare:
                Color(*LINE_COL)
                for _ in range(18):
                    ang  = random.uniform(0, math.pi * 2)
                    dist = random.uniform(face_w * 0.6, max(w, h) * 0.9)
                    Line(points=[cx, cy + drift,
                                 cx + math.cos(ang)*dist,
                                 cy + math.sin(ang)*dist + drift],
                         width=random.uniform(1.0, 3.0))


class PrankApp(App):

    def build(self):
        Window.fullscreen = "auto"
        self._wake_lock   = _acquire_wake_lock()   # keep CPU alive for the timer
        widget = PrankWidget()
        # tuck to background shortly after launch so the pop-up is a surprise
        Clock.schedule_once(lambda dt: _send_to_back(), 0.4)
        return widget

    def on_pause(self):
        return True        # keep running when Android pauses us

    def on_resume(self):
        pass


if __name__ == "__main__":
    PrankApp().run()
