"""Shared canvas interactions: mouse-wheel zoom, fast rotation, and full-screen plot dialog."""
import numpy as np
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas, NavigationToolbar2QT as NavBar
from matplotlib.figure import Figure

ZOOM_STEP = 1.15


def attach_interaction(canvas):
    """Wheel zoom for every view (3D: box zoom, 2D: zoom about the cursor); while a 3D model is dragged the
    heavy text artists are hidden so rotation stays smooth, and the corner axes follow the rotation."""
    def fig():
        return canvas.figure

    def on_scroll(ev):
        f = fig(); step = ZOOM_STEP if ev.button == "up" else 1 / ZOOM_STEP
        ax3 = getattr(f, "_main3d", None)
        if ax3 is not None:
            f._zoom = float(np.clip(f._zoom * step, 0.4, 8.0))
            ax3.set_box_aspect(f._aspect, zoom=f._zoom)
        else:
            ax = ev.inaxes
            if ax is None or ev.xdata is None: return
            x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim(); k = 1 / step
            ax.set_xlim(ev.xdata - (ev.xdata - x0) * k, ev.xdata + (x1 - ev.xdata) * k)
            ax.set_ylim(ev.ydata - (ev.ydata - y0) * k, ev.ydata + (y1 - ev.ydata) * k)
        canvas.draw_idle()

    def on_press(ev):
        f = fig()
        if ev.inaxes is not None and ev.inaxes is getattr(f, "_main3d", None):
            for a in getattr(f, "_heavy", []): a.set_visible(False)

    def on_move(ev):
        f = fig(); gz, ax = getattr(f, "_gizmo", None), getattr(f, "_main3d", None)
        if gz is not None and ax is not None and ev.button is not None and ev.inaxes is ax:
            gz.view_init(ax.elev, ax.azim)

    def on_release(ev):
        f = fig()
        if getattr(f, "_main3d", None) is not None:
            for a in getattr(f, "_heavy", []): a.set_visible(True)
            gz, ax = getattr(f, "_gizmo", None), f._main3d
            if gz is not None: gz.view_init(ax.elev, ax.azim)
            canvas.draw_idle()

    canvas.mpl_connect("scroll_event", on_scroll)
    canvas.mpl_connect("button_press_event", on_press)
    canvas.mpl_connect("motion_notify_event", on_move)
    canvas.mpl_connect("button_release_event", on_release)


class FullScreenDialog(QDialog):
    """Full-screen matplotlib figure with the standard toolbar (pan, zoom, save). Esc or the button closes it."""
    def __init__(self, parent, title, draw_fn):
        super().__init__(parent)
        self.setWindowTitle(title)
        lay = QVBoxLayout(self)
        top = QHBoxLayout(); top.addWidget(QLabel(f"<b>{title}</b>   (mouse wheel = zoom, Esc = close)")); top.addStretch()
        b = QPushButton("✕ Exit full screen"); b.clicked.connect(self.close); top.addWidget(b); lay.addLayout(top)
        self.fig = Figure(figsize=(12, 7)); self.canvas = Canvas(self.fig)
        lay.addWidget(NavBar(self.canvas, self)); lay.addWidget(self.canvas, 1)
        attach_interaction(self.canvas)
        draw_fn(self.fig); self.canvas.draw()
