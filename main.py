import sys
import random
import math
import tkinter as tk
from tkinter import messagebox

from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import QTimer, Qt, QPointF
from PyQt5.QtGui import QPainter, QPen, QColor


# =========================================================
# ARROW
# =========================================================
class Arrow:
    def __init__(self, x, y, angle, owner):
        self.x, self.y = x, y
        self.angle = angle
        self.owner = owner
        self.speed = 11
        self.life = 140
        self.dead = False
        self.damage = 1

    def update(self, men):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.life -= 1
        if self.life <= 0:
            self.dead = True
            return

        for m in men:
            if m is self.owner or m.dead:
                continue
            if math.hypot(m.x - self.x, m.y - self.y) < m.size * 1.2:
                m.hp -= self.damage
                if m.hp <= 0:
                    m.die()
                self.dead = True
                return

    def draw(self, p):
        # Shaft
        p.setPen(QPen(self.owner.color, 2))
        x2 = self.x - math.cos(self.angle) * 16
        y2 = self.y - math.sin(self.angle) * 16
        p.drawLine(QPointF(self.x, self.y), QPointF(x2, y2))
        # Arrow head
        p.drawLine(QPointF(self.x, self.y),
                   QPointF(self.x - math.cos(self.angle - 0.4) * 6,
                           self.y - math.sin(self.angle - 0.4) * 6))
        p.drawLine(QPointF(self.x, self.y),
                   QPointF(self.x - math.cos(self.angle + 0.4) * 6,
                           self.y - math.sin(self.angle + 0.4) * 6))


# =========================================================
# STICKMAN  (8-segment arms/legs)
# =========================================================
class Stickman:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.x = random.uniform(80, max(160, w - 80))
        self.y = random.uniform(80, max(160, h - 80))
        self.speed = random.uniform(0.9, 1.9)
        self.angle = random.uniform(0, math.tau)
        self.facing = self.angle
        self.color = QColor(random.randint(80, 255),
                            random.randint(80, 255),
                            random.randint(80, 255))
        self.size = random.uniform(16, 22)     # body scale
        self.phase = random.uniform(0, math.tau)
        self.walk_speed = random.uniform(0.22, 0.38)

        self.hp = 5
        self.dead = False
        self.fall_t = 0

        # state machine: walk | fight_melee | draw_bow | shoot | fall
        self.state = "walk"
        self.target = None
        self.action_timer = 0
        self.attack_cd = random.randint(60, 180)
        self.bow_pull = 0.0
        self.punch_phase = 0.0

    # ------------- helpers -------------
    def set_bounds(self, w, h):
        self.w, self.h = w, h

    def die(self):
        if self.dead:
            return
        self.dead = True
        self.fall_t = 30

    # ------------- update -------------
    def update(self, men, arrows):
        if self.dead:
            if self.fall_t > 0:
                self.fall_t -= 1
            return

        self.phase += self.walk_speed

        # clear dead / self target
        if self.target is not None and (self.target.dead or self.target is self):
            self.target = None
            if self.state in ("fight_melee", "draw_bow", "shoot"):
                self.state = "walk"

        if self.state == "walk":
            self._walk(men, arrows)
        elif self.state == "fight_melee":
            self._melee()
        elif self.state == "draw_bow":
            self._draw_bow(arrows)
        elif self.state == "shoot":
            self.action_timer -= 1
            if self.action_timer <= 0:
                self.state = "walk"

        # position update only while walking
        if self.state == "walk":
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed
            self.facing = self.angle

        # walls
        m = 40
        if self.x < m:
            self.x, self.angle = m, math.pi - self.angle
        elif self.x > self.w - m:
            self.x, self.angle = self.w - m, math.pi - self.angle
        if self.y < m:
            self.y, self.angle = m, -self.angle
        elif self.y > self.h - m:
            self.y, self.angle = self.h - m, -self.angle

    def _walk(self, men, arrows):
        self.attack_cd -= 1
        for other in men:
            if other is self or other.dead or other.state != "walk":
                continue
            d = math.hypot(other.x - self.x, other.y - self.y)
            if d < 90:
                # melee fight
                self.state = "fight_melee"
                self.target = other
                other.state = "fight_melee"
                other.target = self
                self.action_timer = random.randint(30, 45)
                other.action_timer = random.randint(30, 45)
                return
            elif d < 380 and self.attack_cd <= 0 and random.random() < 0.02:
                # bow shot
                self.state = "draw_bow"
                self.target = other
                self.bow_pull = 0.0
                self.action_timer = 25
                return

    def _melee(self):
        if self.target is None or self.target.dead:
            self.state, self.target = "walk", None
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        d = math.hypot(dx, dy)
        if d > 110:
            self.state, self.target = "walk", None
            return
        # face target
        self.facing = math.atan2(dy, dx)
        self.action_timer -= 1
        # punch cycle
        self.punch_phase = (self.punch_phase + 0.18) % math.tau
        if self.action_timer <= 0:
            # hit at peak
            if math.sin(self.punch_phase) > 0.9:
                if math.hypot(self.target.x - self.x,
                              self.target.y - self.y) < 70:
                    self.target.hp -= 1
                    self.target.punch_phase = math.pi
                    if self.target.hp <= 0:
                        self.target.die()
                        self.state, self.target = "walk", None
                        self.action_timer = 0
                        return
                self.action_timer = random.randint(25, 40)

    def _draw_bow(self, arrows):
        if self.target is None or self.target.dead:
            self.state, self.target = "walk", None
            return
        dx = self.target.x - self.x
        dy = self.target.y - self.y
        d = math.hypot(dx, dy)
        if d > 500:
            self.state, self.target = "walk", None
            return
        self.facing = math.atan2(dy, dx)
        # pull bow
        self.bow_pull = min(1.0, self.bow_pull + 0.07)
        self.action_timer -= 1
        if self.action_timer <= 0 and self.bow_pull >= 0.99:
            # shoot
            ax = self.x + math.cos(self.facing) * self.size
            ay = self.y + math.sin(self.facing) * self.size
            arrows.append(Arrow(ax, ay, self.facing, self))
            self.bow_pull = 0.0
            self.attack_cd = random.randint(90, 200)
            self.state = "shoot"
            self.action_timer = 10

    # ------------- drawing -------------
    def draw(self, painter):
        if self.dead and self.fall_t <= 0:
            return

        s = self.size
        x, y = self.x, self.y
        color = self.color

        # Fallen pose (rotate everything)
        rot = 0.0
        if self.dead:
            rot = (1 - self.fall_t / 30) * (math.pi / 2)

        pen = QPen(color, 3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        # Body points relative to (x,y)
        # Head is at (0, -s)
        head_r = s * 0.28

        # helper: rotate a local vector by facing + rot
        ca, sa = math.cos(self.facing + rot), math.sin(self.facing + rot)
        def R(lx, ly):
            # rotate around origin then translate
            return QPointF(x + lx * ca - ly * sa,
                           y + lx * sa + ly * ca)

        # --- BODY ---
        neck = R(0, -s * 0.75)
        hip = R(0, s * 0.10)
        painter.drawLine(neck, hip)

        # --- HEAD ---
        head_c = R(0, -s * 0.75 - head_r - 1)
        painter.drawEllipse(head_c, head_r, head_r)

        # --- ARMS: 4 segments each side (shoulder → elbow1 → elbow2 → elbow3 → wrist) ---
        # walk swing
        sw = math.sin(self.phase) * 0.45
        shoulder = (-0.02 * 0 * ca, -s * 0.6)   # local coords
        # We compute arm points in *local* space then R()
        def draw_arm(side):
            # side = -1 (left) or +1 (right)
            arm_swing = sw * side
            # Base pose
            if self.state == "fight_melee":
                # punch: forward thrust
                p = math.sin(self.punch_phase) * 0.5 + 0.5
                shoulder_l = (0.0, -s * 0.6)
                elbow1 = (side * 0.10 * s + p * 0.25 * s, -s * 0.5)
                elbow2 = (side * 0.25 * s + p * 0.45 * s, -s * 0.45)
                elbow3 = (side * 0.40 * s + p * 0.65 * s, -s * 0.40)
                wrist  = (side * 0.55 * s + p * 0.85 * s, -s * 0.35)
            elif self.state in ("draw_bow", "shoot") and side == 1:
                # front arm straight forward, back arm pulling string
                # front arm
                shoulder_l = (0.0, -s * 0.6)
                elbow1 = (0.18 * s, -s * 0.58)
                elbow2 = (0.36 * s, -s * 0.56)
                elbow3 = (0.54 * s, -s * 0.54)
                wrist  = (0.72 * s, -s * 0.52)
            elif self.state in ("draw_bow", "shoot") and side == -1:
                # back arm pulling bowstring toward face
                pull = self.bow_pull
                shoulder_l = (0.0, -s * 0.6)
                elbow1 = (-0.20 * s, -s * 0.55 - 0.20 * pull * s)
                elbow2 = (-0.05 * s, -s * 0.50 - 0.30 * pull * s)
                elbow3 = (0.15 * s, -s * 0.48 - 0.10 * pull * s)
                wrist  = (0.05 * s, -s * 0.55 - 0.30 * pull * s)
            else:
                # walk swing
                shoulder_l = (0.0, -s * 0.6)
                elbow1 = (side * 0.10 * s, -s * 0.40 + arm_swing * 0.1 * s)
                elbow2 = (side * 0.20 * s, -s * 0.25 + arm_swing * 0.2 * s)
                elbow3 = (side * 0.28 * s, -s * 0.10 + arm_swing * 0.3 * s)
                wrist  = (side * 0.35 * s, s * 0.05 + arm_swing * 0.4 * s)

            pts = [R(*shoulder_l), R(*elbow1), R(*elbow2), R(*elbow3), R(*wrist)]
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])
            return wrist

        right_wrist = draw_arm(1)
        left_wrist = draw_arm(-1)

        # --- LEGS: 4 segments each side ---
        def draw_leg(side):
            leg_swing = -sw * side
            hip_l = (0.0, s * 0.10)
            if self.state == "fight_melee":
                # wide stance
                knee1 = (side * 0.12 * s, s * 0.30)
                knee2 = (side * 0.22 * s, s * 0.50)
                knee3 = (side * 0.30 * s, s * 0.70)
                foot  = (side * 0.36 * s, s * 0.90)
            else:
                knee1 = (side * 0.10 * s, s * 0.30 + leg_swing * 0.10 * s)
                knee2 = (side * 0.14 * s, s * 0.50 + leg_swing * 0.20 * s)
                knee3 = (side * 0.16 * s, s * 0.70 + leg_swing * 0.30 * s)
                foot  = (side * 0.18 * s, s * 0.90 + leg_swing * 0.40 * s)
            pts = [R(*hip_l), R(*knee1), R(*knee2), R(*knee3), R(*foot)]
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])

        draw_leg(1)
        draw_leg(-1)

        # --- BOW + STRING when drawing/shooting ---
        if self.state in ("draw_bow", "shoot"):
            bow_r = s * 0.55
            # bow center a bit in front of the front wrist
            bc = R(s * 0.80, -s * 0.50)
            painter.setPen(QPen(color, 2))
            painter.drawArc(int(bc.x() - bow_r), int(bc.y() - bow_r),
                            int(bow_r * 2), int(bow_r * 2),
                            int(math.degrees(self.facing) - 90) * 16,
                            180 * 16)
            # string
            top = R(s * 0.80, -s * 0.50 - bow_r)
            bot = R(s * 0.80, -s * 0.50 + bow_r)
            pull_x = s * 0.80 - self.bow_pull * s * 0.7
            pull = R(pull_x, -s * 0.50)
            painter.drawLine(top, pull)
            painter.drawLine(bot, pull)


# =========================================================
# OVERLAY
# =========================================================
class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.W, self.H = screen.width(), screen.height()

        self.men = []
        self.arrows = []

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(16)

    def add_men(self, n):
        for _ in range(n):
            self.men.append(Stickman(self.W, self.H))

    def remove_men(self, n):
        for _ in range(min(n, len(self.men))):
            for i in range(len(self.men) - 1, -1, -1):
                if not self.men[i].dead:
                    del self.men[i]
                    break

    def clear(self):
        self.men.clear()
        self.arrows.clear()

    def alive_count(self):
        return sum(1 for m in self.men if not m.dead)

    def tick(self):
        for m in self.men:
            m.set_bounds(self.W, self.H)
            m.update(self.men, self.arrows)

        for a in self.arrows:
            a.update(self.men)

        self.arrows = [a for a in self.arrows if not a.dead]
        # keep fallen animation briefly then remove
        self.men = [m for m in self.men if (not m.dead) or m.fall_t > 0]

        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for m in self.men:
            m.draw(p)
        for a in self.arrows:
            a.draw(p)


# =========================================================
# CONTROL PANEL (scrollable, resizable)
# =========================================================
class ControlPanel:
    def __init__(self, root):
        self.root = root
        self.overlay = None

        root.title("Stickman Control Panel")
        root.geometry("380x540")
        root.minsize(320, 300)

        outer = tk.Frame(root)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-e.delta / 120), "units"))

        tk.Label(inner, text="Stickman Control Panel",
                 font=("Segoe UI", 14, "bold")).pack(pady=(15, 10))

        tk.Label(inner, text="Number of stickmen:",
                 font=("Segoe UI", 11)).pack()
        self.entry = tk.Entry(inner, font=("Segoe UI", 12), justify="center")
        self.entry.insert(0, "10")
        self.entry.pack(pady=5, ipadx=10, ipady=3)

        tk.Button(inner, text="▶ Start", bg="#4CAF50", fg="white",
                  font=("Segoe UI", 11, "bold"), width=24,
                  command=self.start).pack(pady=6)
        tk.Button(inner, text="+ Add more", bg="#2196F3", fg="white",
                  font=("Segoe UI", 11), width=24,
                  command=self.add).pack(pady=3)
        tk.Button(inner, text="– Remove some", bg="#FF9800", fg="white",
                  font=("Segoe UI", 11), width=24,
                  command=self.remove).pack(pady=3)
        tk.Button(inner, text="✖ Clear all", bg="#F44336", fg="white",
                  font=("Segoe UI", 11), width=24,
                  command=self.clear).pack(pady=3)

        self.status = tk.Label(inner, text="Status: stopped",
                               font=("Segoe UI", 10), fg="gray")
        self.status.pack(pady=(14, 8))

    def _get_count(self):
        raw = self.entry.get().strip()
        if not raw.isdigit():
            messagebox.showerror("Error", "Please enter a valid number.")
            return None
        n = int(raw)
        if n <= 0 or n > 300:
            messagebox.showerror("Error", "Number must be between 1 and 300.")
            return None
        return n

    def _update_status(self):
        if self.overlay:
            self.status.config(text=f"Status: running — {self.overlay.alive_count()} alive")
        else:
            self.status.config(text="Status: stopped")

    def start(self):
        n = self._get_count()
        if n is None:
            return
        if self.overlay is None:
            self.overlay = Overlay()
            self.overlay.show()
        self.overlay.clear()
        self.overlay.add_men(n)
        self._update_status()

    def add(self):
        if self.overlay is None:
            messagebox.showinfo("Info", "Press Start first.")
            return
        n = self._get_count()
        if n is None:
            return
        self.overlay.add_men(n)
        self._update_status()

    def remove(self):
        if self.overlay is None:
            return
        n = self._get_count()
        if n is None:
            return
        self.overlay.remove_men(n)
        self._update_status()

    def clear(self):
        if self.overlay:
            self.overlay.clear()
        self._update_status()


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    root = tk.Tk()
    panel = ControlPanel(root)

    def pump():
        app.processEvents()
        if panel.overlay:
            panel._update_status()
        root.after(30, pump)

    pump()
    root.mainloop()