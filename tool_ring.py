#!/usr/bin/env python3
"""Tool Ring: a ring of launcher badges around the cursor.

Pure helpers live at module scope (import-safe, no display required).
GTK/layer-shell code is imported lazily inside main()/run_overlay().
"""

import math

# --- Badge geometry / appearance constants ---
DIAMETER = 40
RADIUS = DIAMETER // 2          # 20
RING_RADIUS = 48                # px from ring center to each badge center


GLOBE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" \
fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" \
stroke-linejoin="round"><circle cx="12" cy="12" r="10"/>\
<path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>\
<path d="M2 12h20"/></svg>"""

TERMINAL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" \
fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" \
stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/>\
<line x1="12" x2="20" y1="19" y2="19"/></svg>"""

CLAUDE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" \
fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" \
stroke-linejoin="round"><polyline points="3 16 8 11 3 6"/>\
<line x1="10" x2="16" y1="18" y2="18"/>\
<path d="M19 2.5 l0.9 2.1 2.1 0.9 -2.1 0.9 -0.9 2.1 -0.9 -2.1 -2.1 -0.9 2.1 -0.9 z" \
fill="#ffffff" stroke="#ffffff" stroke-width="0.5"/></svg>"""

MUSIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" \
fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" \
stroke-linejoin="round"><path d="M9 18V5l12-2v13"/>\
<circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>"""

FOLDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" \
fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" \
stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 \
2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>"""

# Phosphor-Bold "camera" glyph (U+E10E), extracted from Phosphor-Bold.ttf so it
# matches the screenshot/camera icon in the Ambxst bar's tools menu. Font space is
# y-up (UPM 1024); the <g> flips it to SVG y-down and the viewBox centers it.
CAMERA_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-40 0 1024 1024" '
    'fill="#ffffff"><g transform="translate(0,960) scale(1,-1)">'
    '<path d="M832 752H730L680 827Q673 836 663.0 842.0Q653 848 640 848Q640 848 640.0 848.0Q640 848 640 848H384Q384 848 384.0 848.0Q384 848 384 848Q371 848 361.0 842.0Q351 836 344 827L294 752H192Q146 752 113.0 719.0Q80 686 80 640V192Q80 146 113.0 113.0Q146 80 192 80H832Q878 80 911.0 113.0Q944 146 944 192V640Q944 686 911.0 719.0Q878 752 832 752ZM848 192Q848 185 843.5 180.5Q839 176 832 176H192Q185 176 180.5 180.5Q176 185 176 192V640Q176 647 180.5 651.5Q185 656 192 656H320Q320 656 320.0 656.0Q320 656 320 656Q333 656 343.0 662.0Q353 668 360 677L410 752H614L664 677Q671 668 681.0 662.0Q691 656 704 656Q704 656 704.0 656.0Q704 656 704 656H832Q839 656 843.5 651.5Q848 647 848 640ZM512 624Q432 624 376.0 568.0Q320 512 320 432Q320 352 376.0 296.0Q432 240 512 240Q592 240 648.0 296.0Q704 352 704 432Q704 511 647.5 567.5Q591 624 512 624ZM512 336Q472 336 444.0 364.0Q416 392 416 432Q416 472 444.0 500.0Q472 528 512 528Q552 528 580.0 500.0Q608 472 608 432Q608 392 580.0 364.0Q552 336 512 336Z"/>'
    '</g></svg>'
)

ITEMS = [
    {"svg": GLOBE_SVG, "cmd": ["firefox", "--new-window"]},
    {"svg": TERMINAL_SVG, "cmd": ["kitty"]},
    {"svg": CLAUDE_SVG, "cmd": ["kitty", "-e", "claude"]},
    {"svg": MUSIC_SVG, "cmd": ["spotify"]},
    {"svg": FOLDER_SVG, "cmd": ["dolphin"]},
    {"svg": CAMERA_SVG, "cmd": ["sh", "-c", 'grim -g "$(slurp)" - | wl-copy']},
]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------

def parse_cursorpos(s):
    """Parse 'x, y' (the format printed by `hyprctl cursorpos`)."""
    x_str, y_str = s.strip().split(",")
    return (int(x_str.strip()), int(y_str.strip()))


def ring_positions(ccx, ccy, ring_r, n):
    """n badge centers evenly spaced around (ccx,ccy), first at top (-90deg)."""
    out = []
    for i in range(n):
        a = -math.pi / 2 + i * (2 * math.pi / n)
        out.append((ccx + ring_r * math.cos(a), ccy + ring_r * math.sin(a)))
    return out


def place_ring_center(cur_x, cur_y, mon_w, mon_h, ring_r, badge_r):
    """Cursor-centered ring origin, clamped so all badges stay on the monitor."""
    margin = ring_r + badge_r + 4
    cx = max(margin, min(cur_x, mon_w - margin))
    cy = max(margin, min(cur_y, mon_h - margin))
    return (cx, cy)


def hit_test(px, py, cx, cy, radius):
    """True if (px, py) is within `radius` of the badge center (cx, cy)."""
    dx = px - cx
    dy = py - cy
    return (dx * dx + dy * dy) <= (radius * radius)


def item_at(px, py, centers, radius):
    """Index of the badge whose circle contains (px,py), or -1."""
    for i, (ix, iy) in enumerate(centers):
        if hit_test(px, py, ix, iy, radius):
            return i
    return -1


def resolve_monitor(cur_x, cur_y, monitors):
    """Find the monitor under the cursor.

    `monitors`: list of {"x","y","width","height"} in global coords.
    Returns (index, local_x, local_y). Falls back to index 0.
    """
    for i, m in enumerate(monitors):
        if (m["x"] <= cur_x < m["x"] + m["width"]
                and m["y"] <= cur_y < m["y"] + m["height"]):
            return (i, cur_x - m["x"], cur_y - m["y"])
    m = monitors[0]
    return (0, cur_x - m["x"], cur_y - m["y"])


import json
import os
import subprocess


def get_cursor_xy():
    """Global cursor position via hyprctl (falls back to axctl)."""
    try:
        out = subprocess.check_output(["hyprctl", "cursorpos"], text=True)
        return parse_cursorpos(out)
    except Exception:
        out = subprocess.check_output(
            ["axctl", "system", "get-cursor-position"], text=True)
        d = json.loads(out)
        return (int(d["x"]), int(d["y"]))


def get_monitor_geoms(display):
    """List of {'x','y','width','height'} for every monitor, in order."""
    geoms = []
    monitors = display.get_monitors()
    for i in range(monitors.get_n_items()):
        g = monitors.get_item(i).get_geometry()
        geoms.append({"x": g.x, "y": g.y, "width": g.width, "height": g.height})
    return geoms


# Per-SVG Rsvg handle cache (module-level, keyed by svg string).
_SVG_CACHE = {}


def draw_badge(cr, cx, cy, scale, lift, svg):
    """Solid black circle with a white icon centered inside.

    scale: combined animation scale factor (entrance * hover).
    lift:  vertical offset in px (negative = up).
    svg:   SVG source string for the icon.
    """
    import gi
    gi.require_version("Rsvg", "2.0")
    from gi.repository import Rsvg

    eff_r = RADIUS * scale
    if eff_r < 0.5:
        return

    ny = cy + lift

    cr.set_source_rgb(0.0, 0.0, 0.0)
    cr.arc(cx, ny, eff_r, 0, 2 * math.pi)
    cr.fill()

    handle = _SVG_CACHE.get(svg)
    if handle is None:
        handle = Rsvg.Handle.new_from_data(svg.encode("utf-8"))
        _SVG_CACHE[svg] = handle

    icon_px = DIAMETER * 0.64 * scale
    vp = Rsvg.Rectangle()
    vp.x = cx - icon_px / 2.0
    vp.y = ny - icon_px / 2.0
    vp.width = icon_px
    vp.height = icon_px
    handle.render_document(cr, vp)


def run_overlay(cur_x, cur_y):
    """Full-screen transparent overlay with the badge ring; handles click/Esc."""
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk, Gdk, GLib, Gtk4LayerShell as LayerShell

    app = Gtk.Application(application_id="dev.nethum.toolring")

    def on_activate(app):
        display = Gdk.Display.get_default()
        gdk_monitors = display.get_monitors()
        monitors = get_monitor_geoms(display)
        mon_index, local_x, local_y = resolve_monitor(cur_x, cur_y, monitors)
        mon = monitors[mon_index]

        ccx, ccy = place_ring_center(
            local_x, local_y, mon["width"], mon["height"], RING_RADIUS, RADIUS)
        centers = ring_positions(ccx, ccy, RING_RADIUS, len(ITEMS))

        # Make windows transparent so only the badges are visible.
        css = Gtk.CssProvider()
        css.load_from_data(b"window { background: transparent; }")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        win = Gtk.ApplicationWindow(application=app)
        LayerShell.init_for_window(win)
        LayerShell.set_layer(win, LayerShell.Layer.OVERLAY)
        LayerShell.set_namespace(win, "tool-ring")
        LayerShell.set_monitor(win, gdk_monitors.get_item(mon_index))
        for edge in (LayerShell.Edge.TOP, LayerShell.Edge.BOTTOM,
                     LayerShell.Edge.LEFT, LayerShell.Edge.RIGHT):
            LayerShell.set_anchor(win, edge, True)
        LayerShell.set_keyboard_mode(win, LayerShell.KeyboardMode.EXCLUSIVE)

        area = Gtk.DrawingArea()

        # --- Check reduced-motion preference ---
        gtk_settings = Gtk.Settings.get_default()
        animations_enabled = True
        if gtk_settings is not None:
            try:
                animations_enabled = gtk_settings.get_property("gtk-enable-animations")
            except Exception:
                animations_enabled = True

        # --- Mutable animation state ---
        # One shared entrance spring (escale, evel).
        # Per-item hover springs stored in state["items"] list.
        state = {
            "escale": 1.0 if not animations_enabled else 0.0,
            "evel": 0.0,
            "items": [
                {"hscale": 1.0, "hvel": 0.0, "hlift": 0.0, "hliftvel": 0.0,
                 "hovered": False}
                for _ in ITEMS
            ],
            "last": None,
            "running": False,
        }

        def draw(area, cr, width, height):
            es = state["escale"]
            for i, item in enumerate(ITEMS):
                ix, iy = centers[i]
                it = state["items"][i]
                total_scale = es * it["hscale"]
                draw_badge(cr, ix, iy, total_scale, it["hlift"], item["svg"])

        area.set_draw_func(draw)
        win.set_child(area)

        def ensure_tick():
            if not state["running"]:
                state["running"] = True
                state["last"] = None
                area.add_tick_callback(on_tick)

        EPS = 1e-3

        def on_tick(widget, frame_clock):
            now = frame_clock.get_frame_time()  # microseconds

            if state["last"] is None:
                state["last"] = now
                return GLib.SOURCE_CONTINUE

            dt = (now - state["last"]) / 1_000_000.0
            state["last"] = now
            dt = min(dt, 1.0 / 30.0)

            # Shared entrance spring (k=300, c=22), target always 1.0
            if not animations_enabled:
                state["escale"] = 1.0
                state["evel"] = 0.0
            else:
                accel = 300.0 * (1.0 - state["escale"]) - 22.0 * state["evel"]
                state["evel"] += accel * dt
                state["escale"] += state["evel"] * dt

            # Per-item hover springs (k=420, c=30)
            for it in state["items"]:
                h_scale_target = 1.08 if it["hovered"] else 1.0
                h_lift_target = -3.0 if it["hovered"] else 0.0

                accel_s = 420.0 * (h_scale_target - it["hscale"]) - 30.0 * it["hvel"]
                it["hvel"] += accel_s * dt
                it["hscale"] += it["hvel"] * dt

                accel_l = 420.0 * (h_lift_target - it["hlift"]) - 30.0 * it["hliftvel"]
                it["hliftvel"] += accel_l * dt
                it["hlift"] += it["hliftvel"] * dt

            widget.queue_draw()

            # Check if any spring is still active.
            entrance_active = (
                abs(1.0 - state["escale"]) > EPS or abs(state["evel"]) > EPS
            )
            items_active = any(
                abs((1.08 if it["hovered"] else 1.0) - it["hscale"]) > EPS
                or abs(it["hvel"]) > EPS
                or abs((-3.0 if it["hovered"] else 0.0) - it["hlift"]) > EPS
                or abs(it["hliftvel"]) > EPS
                for it in state["items"]
            )
            if not (entrance_active or items_active):
                state["running"] = False
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE

        ensure_tick()

        # --- Hover detection via EventControllerMotion ---
        motion = Gtk.EventControllerMotion()

        def on_motion(ctrl, x, y):
            idx = item_at(x, y, centers, RADIUS)
            for i, it in enumerate(state["items"]):
                it["hovered"] = (i == idx)
            ensure_tick()

        def on_leave(ctrl):
            for it in state["items"]:
                it["hovered"] = False
            ensure_tick()

        motion.connect("motion", on_motion)
        motion.connect("leave", on_leave)
        area.add_controller(motion)

        # --- Click to launch or dismiss ---
        click = Gtk.GestureClick()

        def on_pressed(gesture, n_press, px, py):
            idx = item_at(px, py, centers, RADIUS)
            if idx >= 0:
                env = dict(os.environ)
                env.pop("LD_PRELOAD", None)
                subprocess.Popen(ITEMS[idx]["cmd"], env=env, start_new_session=True)
            app.quit()

        click.connect("pressed", on_pressed)
        area.add_controller(click)

        key = Gtk.EventControllerKey()

        def on_key(ctrl, keyval, keycode, state_flags):
            if keyval == Gdk.KEY_Escape:
                app.quit()
            return False

        key.connect("key-pressed", on_key)
        win.add_controller(key)

        win.present()

    app.connect("activate", on_activate)
    app.run(None)


def main():
    import gi
    gi.require_version("Gtk", "4.0")
    from gi.repository import Gtk
    if not Gtk.init_check():
        raise SystemExit("GTK could not initialize a display")
    cur_x, cur_y = get_cursor_xy()
    run_overlay(cur_x, cur_y)


if __name__ == "__main__":
    main()
