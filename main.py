# main.py — Doors-esque Android prank
# ─────────────────────────────────────────────────────────────────────────────
# BEHAVIOUR
#   Open the app → it vanishes in < 0.5 s (sends itself to background).
#   A partial wake-lock keeps the CPU alive so the timer fires.
#   After 30-120 s the face pops up fullscreen.
#   Touch + drag during the 3-second window → scare flash → bootloop →
#   dead-Android robot screen → app hides again and resets.
#   No reaction → face silently disappears → app stays hidden → repeats.
#
# SECRET EXIT  tap the four screen corners in order TL→TR→BR→BL within 5 s.
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
        """Partial wake lock — keeps CPU running while screen is off."""
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
SCARE_DURATION = 3.0
GRACE          = 24
INTERVAL       = (30, 120)

# Flat Doors palette — no glow
BG_COL    = (0.05, 0.04, 0.04, 1)
FACE_COL  = (0.15, 0.02, 0.02, 1)
EYE_W     = (0.91, 0.90, 0.83, 1)
EYE_P     = (0.03, 0.02, 0.02, 1)
MOUTH_COL = (0.01, 0.01, 0.01, 1)
LINE_COL  = (0.76, 0.07, 0.07, 1)
ROBOT_GRAY = (0.60, 0.60, 0.60, 1)
WARN_RED   = (0.88, 0.12, 0.12, 1)

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
        self.state          = "idle"
        self._touch_start   = None
        self._scare_t       = 0.0
        self._overlay       = None
        self._boot_cycle    = 0
        self._flicker_count = 0
        self._corner_seq    = []
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
        self.state, self._touch_start, self._scare_t = "face", None, 0.0
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
            self._touch_start = (touch.x, touch.y)
        return True

    def on_touch_move(self, touch):
        if self.state == "face" and self._touch_start:
            dx = touch.x - self._touch_start[0]
            dy = touch.y - self._touch_start[1]
            if math.hypot(dx, dy) > GRACE:
                self._trigger_scare()
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
        if self._scare_t > 0.65:
            Clock.unschedule(self._scare_flash)
            self._show_bootloop()
            return False

    # ── bootloop ─────────────────────────────────────────────────────────────

    def _show_bootloop(self):
        self.state, self._boot_cycle = "crash", 0
        self._black()
        layout = FloatLayout(size=Window.size, pos=(0, 0), opacity=0)
        layout.add_widget(Label(
            text="android", font_size=52,
            color=(1, 1, 1, 0.96), italic=True,
            size_hint=(1, None), height=80,
            pos_hint={"center_x": 0.5, "center_y": 0.52},
        ))
        layout.add_widget(Label(
            text="Powered by android", font_size=17,
            color=(0.65, 0.65, 0.65, 0.85),
            size_hint=(1, None), height=36,
            pos_hint={"center_x": 0.5, "center_y": 0.42},
        ))
        self.add_widget(layout)
        self._overlay = layout
        Clock.schedule_once(self._boot_phase, 0.5)

    def _boot_phase(self, *_):
        self._boot_cycle += 1
        if self._boot_cycle > 3:
            Clock.schedule_once(self._show_dead_android, 0.25)
            return
        self._overlay.opacity = 1
        hold = 1.6 if self._boot_cycle == 1 else 0.85
        Clock.schedule_once(self._start_flicker, hold)

    def _start_flicker(self, *_):
        self._flicker_count = 0
        Clock.schedule_interval(self._flicker_tick, 0.07)

    def _flicker_tick(self, dt):
        self._flicker_count += 1
        self._overlay.opacity = 1 if self._flicker_count % 2 == 0 else 0
        if self._flicker_count >= 9:
            Clock.unschedule(self._flicker_tick)
            self._overlay.opacity = 0
            Clock.schedule_once(self._boot_phase, 0.38)
            return False

    # ── dead Android ─────────────────────────────────────────────────────────

    def _show_dead_android(self, *_):
        if self._sound:
            self._sound.stop()
        if self._overlay:
            self.remove_widget(self._overlay)
            self._overlay = None
        self._draw_dead_android()
        Clock.schedule_once(self._reset, 7.0)

    def _draw_dead_android(self):
        w, h  = Window.width, Window.height
        cx    = w / 2
        u     = min(w, h) * 0.075
        robot_cy = h * 0.56

        self.canvas.clear()
        with self.canvas:
            Color(0, 0, 0, 1)
            Rectangle(pos=(0, 0), size=(w, h))

            Color(*ROBOT_GRAY)

            # antennas
            Line(points=[cx - u*0.55, robot_cy + u*2.1,
                         cx - u*1.05, robot_cy + u*3.0], width=max(2, u*0.22))
            Line(points=[cx + u*0.55, robot_cy + u*2.1,
                         cx + u*1.05, robot_cy + u*3.0], width=max(2, u*0.22))
            Ellipse(pos=(cx - u*1.2,  robot_cy + u*2.95), size=(u*0.3, u*0.3))
            Ellipse(pos=(cx + u*0.92, robot_cy + u*2.95), size=(u*0.3, u*0.3))

            # head
            hw, hh = u*2.6, u*1.85
            Ellipse(pos=(cx - hw/2, robot_cy + u*0.5), size=(hw, hh))

            # X eyes
            Color(0, 0, 0, 1)
            ex_off, ey, s = u*0.62, robot_cy + u*1.35, u*0.32
            lw = max(2, u*0.18)
            for ex in (cx - ex_off, cx + ex_off):
                Line(points=[ex-s, ey-s, ex+s, ey+s], width=lw)
                Line(points=[ex-s, ey+s, ex+s, ey-s], width=lw)

            # body
            Color(*ROBOT_GRAY)
            bw, bh = u*2.6, u*2.6
            bx, by = cx - bw/2, robot_cy - u*2.3
            Rectangle(pos=(bx, by), size=(bw, bh))
            rc = u*0.28
            Ellipse(pos=(bx, by + bh - rc*2), size=(rc*2, rc*2))
            Ellipse(pos=(bx + bw - rc*2, by + bh - rc*2), size=(rc*2, rc*2))
            Rectangle(pos=(bx, by + bh - rc), size=(bw, rc))

            # arms
            aw, ah = u*0.65, u*2.0
            arm_top = by + bh - u*0.25
            for ax in (bx - aw - u*0.12, bx + bw + u*0.12):
                Rectangle(pos=(ax, arm_top - ah), size=(aw, ah))
                Ellipse(pos=(ax, arm_top - aw), size=(aw, aw))
                Ellipse(pos=(ax, arm_top - ah), size=(aw, aw))

            # legs
            lw_leg, lh = u*0.85, u*1.8
            gap = u*0.18
            for lx in (cx - lw_leg - gap/2, cx + gap/2):
                Rectangle(pos=(lx, by - lh), size=(lw_leg, lh))
                Ellipse(pos=(lx, by - lh), size=(lw_leg, lw_leg))

            # red ! on chest
            Color(*WARN_RED)
            Rectangle(pos=(cx - u*0.18, by + u*0.65), size=(u*0.36, u*1.05))
            Ellipse(pos=(cx - u*0.22, by + u*0.22),   size=(u*0.44, u*0.44))

    # ── reset ─────────────────────────────────────────────────────────────────

    def _reset(self, *_):
        if self._overlay:
            self.remove_widget(self._overlay)
            self._overlay = None
        self.canvas.clear()
        self.state = "idle"
        _send_to_back()                      # hide again
        self._schedule_next()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _black(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0, 0, 0, 1)
            Rectangle(pos=(0, 0), size=Window.size)

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
        self._wake_lock   = _acquire_wake_lock()   # keep CPU alive in background
        widget = PrankWidget()
        # go to background immediately — under 0.5 s after launch
        Clock.schedule_once(lambda dt: _send_to_back(), 0.4)
        return widget

    def on_pause(self):
        return True        # keep running when Android pauses us

    def on_resume(self):
        pass               # nothing special needed on resume


if __name__ == "__main__":
    PrankApp().run()
