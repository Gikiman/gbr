#-------------------------------------------------------------------------------
# Name:        Go board recognition project
# Purpose:     UI classes and functions
#
# Author:      kol
#
# Created:     04.07.2019
# Copyright:   (c) kol 2019
# Licence:     MIT
#-------------------------------------------------------------------------------
import sys
import os
from PIL import Image, ImageTk
from pathlib import Path
import random

if sys.version_info[0] < 3:
    from grdef import *
    from utils import img_to_imgtk
else:
    from gr.grdef import *
    from gr.utils import img_to_imgtk

if sys.version_info[0] < 3:
    import Tkinter as tk
    import ttk
    import tkFont as font
else:
    import tkinter as tk
    from tkinter import ttk, font

UI_DIR = 'ui'    # directory containing ImgButton images
PADX = 5
PADY = 5

class NLabel(tk.Label):
    """Label with additional tag"""
    def __init__(self, master, tag=None, *args, **kwargs):
        tk.Label.__init__(self, master, *args, **kwargs)
        self.master, self.tag = master, tag

# ImageButton
class ImgButton(tk.Label):
    """Button with image face"""
    def __init__(self, master, tag, state, callback, *args, **kwargs):
        """Creates new ImgButton. Parameters:

        master     Tk windows/frame
        tag        Button tag. Files names "<tag>_down.png" and "<tag>_up.png" must exist in UI_DIR.
        state      Initial state (true/false)
        callback   Callback function. Function signature:
                      event - Tk event
                      tag   - button's tag
                      state - target state (true/false)
                   Function shall return if new state accepted, or false otherwise
        """
        tk.Label.__init__(self, master, *args, **kwargs)

        self._tag = tag
        self._state = state
        self._callback = callback

        # Load button images
        self._images = [ImageTk.PhotoImage(Image.open(os.path.join(UI_DIR, self._tag + '_up.png'))),
                        ImageTk.PhotoImage(Image.open(os.path.join(UI_DIR, self._tag + '_down.png')))]

        # Update kwargs
        w = self._images[0].width() + 4
        h = self._images[0].height() + 4
        self.configure(borderwidth = 1, relief = "groove", width = w, height = h)
        self.configure(image = self._images[self._state])

        self.bind("<Button-1>", self.mouse_click)

    def mouse_click(self, event):
        new_state = not self._state
        self.configure(image = self._images[new_state])
        if new_state: self._root().update()
        if self._callback(event = event, tag = self._tag, state = new_state):
           self._state = new_state
        else:
           if new_state:
              # Unpress after small delay
              self.after(300, lambda: self.configure(image = self._images[self._state]))
           else:
              self.configure(image = self._images[self._state])

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, new_state):
        self._state = new_state
        self.configure(image = self._images[new_state])

# Tooltip
class ToolTip(object):
    """ToolTip class (see https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter)"""

    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0

    def showtip(self, text):
        "Display text in tooltip window"
        self.text = text
        if self.tipwindow or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 27
        y = y + cy + self.widget.winfo_rooty() +27
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                      background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                      font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

# Add a toolip
def createToolTip(widget, text):
    """Creates a tooltip with given text for given widget"""
    toolTip = ToolTip(widget)
    def enter(event):
        toolTip.showtip(text)
    def leave(event):
        toolTip.hidetip()
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)

class StatusPanel(tk.Frame):
    """Status panel class"""
    def __init__(self, master, max_width, *args, **kwargs):
        """Creates StatusPanel instance. A StatusPanel is a frame with additional methods.

           Parameters:
               master          master frame
               max_width       maximal text width
        """
        tk.Frame.__init__(self, master, *args, **kwargs)

        self._max_width = max_width
        self._var = tk.StringVar()
        self._var.set("")

        self._label = tk.Label(self, textvariable = self._var, anchor = tk.W)
        self._label.pack(side = tk.LEFT, fill = tk.BOTH, expand = True)

    @property
    def status(self):
        """Status text"""
        return self._var.get()

    @status.setter
    def status(self, text):
        """Status text"""
        self.set(text)

    @property
    def max_width(self):
        """Max status panel width in pixels"""
        return self._max_width

    @max_width.setter
    def max_width(self, v):
        """Max status panel width in pixels"""
        self._max_width = v

    def _get_maxw(self):
        w = self.winfo_width()
        return w

    def set(self, text):
        """Set status as text. If text is larger than current panel size, it's been
        truncated from the end, ... added"""
        f = font.Font(font = self._label['font'])
        chw = f.measure('W')

        maxw = self._get_maxw()
        curw = f.measure(text)
        maxw -= chw*3
        if curw > maxw:
           strip_len = int((curw - maxw) / chw) + 3
           text = text[:-strip_len] + '...'

        self._var.set(text)

    def set_file(self, text, file):
        """Set text + file name as status. If file name is too long, it's been
        shrinken by eliminating some path parts in the middle"""
        f = font.Font(font = self._label['font'])
        chw = f.measure('W')

        maxw = self._get_maxw()
        if maxw == 0:
           maxw = self.winfo_width()
           if maxw < 20:
              # Window not updated yet
              self._var.set(text)
              return

        maxw -= chw*3
        if f.measure(text + file) > maxw:
           # Exclude file path parts to fit in starting from 3 entry
           parts = list(Path(file).parts)
           for n in range(len(parts)-3):
               parts.pop(len(parts)-2)
               t = parts[0] + '\\'.join(parts[1:])
               if f.measure(text + t) < maxw: break
           file = parts[0] + '\\'.join(parts[1:-2])
           file += '\\...\\' + parts[-1]

        self._var.set(text + file)

# Image panel class
class ImagePanel(tk.Frame):
    def __init__(self, master, caption = None, btn_params = None, image = None, frame_callback = None, max_size = None, *args, **kwargs):
        """Creates ImagePanel instance.

           Parameters:
               master          master frame
               caption        Panel caption
               btn_params     Params for ImgButtons: tag, initial state, callback function, (optional) tooltip
               image          OpenCv or PhotoImage. If none provided, an empty frame is created
               frame_callback Callback for panel mouse click
               max_width       maximal text width
        """
        tk.Frame.__init__(self, master, *args, **kwargs)
        self._max_size = max_size
        if image is None:
           self._image = image
           self._imgtk = None
        elif type(image) is ImageTk.PhotoImage:
           self._image = None
           self._imgtk = image
        else:
           self._image = image
           self._imgtk = img_to_imgtk(image)

        # Panel itself
        self.internalPanel = tk.Frame(self)
        self.internalPanel.pack(fill = tk.BOTH, expand = True)

        # Header panel and label
        self.headerPanel = tk.Frame(self.internalPanel)
        self.headerPanel.pack(side = tk.TOP, fill = tk.X, expand = True)
        if caption is None: caption = ""
        self.headerLabel = tk.Label(self.headerPanel, text = caption)
        self.headerLabel.pack(side = tk.LEFT, fill = tk.X, expand = True)

        # Buttons
        self.buttons = dict()
        if not btn_params is None:
            for b in btn_params:
                btn = ImgButton(self.headerPanel, b[0], b[1], b[2])
                if len(b) > 3:
                    createToolTip(btn, b[3])
                self.buttons[b[0]] = btn
                btn.pack(side = tk.RIGHT, padx = 2, pady = 2)

        # Body
        if self._imgtk is None:
           self.body = tk.Frame(self.internalPanel)
        else:
           self.body = tk.Label(self.internalPanel, image = self._imgtk)

        self.body.pack(side = tk.TOP, fill = tk.BOTH, expand = True)
        if not frame_callback is None:
            self.body.bind('<Button-1>', frame_callback)

    @property
    def image(self):
        """Current OpenCv image"""
        return self._image

    @property
    def imagetk(self):
        """Current PhotoImage image"""
        return self._imagetk

    @image.setter
    def image(self, img):
        self.set_image(img)

    @imagetk.setter
    def imagetk(self, imgtk):
        self.set_image(imgtk)

    def set_image(self, img):
        """Changes image. img can be either OpenCv or PhotoImage"""
        if img is None:
           self._image = None
           self._imgtk = None
        elif type(img) is ImageTk.PhotoImage:
           self._image = None
           self._imgtk = img
        else:
           self._image = img
           self._imgtk = img_to_imgtk(img)

        if type(self.body) is tk.Label:
           if self._imgtk is None:
              self.body.configure(text = "", image = None)
           else:
              self.body.configure(image = self._imgtk)



def addImagePanel(parent, caption = None, btn_params = None, image = None, frame_callback = None):
    """Creates a panel with caption and buttons

    Parameters:
        parent         Tk window/frame to add panel to
        caption        Panel caption
        btn_params     Params for ImgButtons: tag, initial state, callback function, (optional) tooltip
        image          OpenCv image. If none provided, an empty frame is created
        frame_callback Callback for panel mouse click

    Returns:
        panel          A panel frame
    """
    return ImagePanel(parent, caption, btn_params, image, frame_callback)

def treeview_sort_columns(tv):
    """Set up Treeview tv for column sorting (see https://stackoverflow.com/questions/1966929/tk-treeview-column-sort)"""

    def _sort(tv, col, reverse):
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        l.sort(reverse=reverse)

        # rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # reverse sort next time
        tv.heading(col, command = lambda: _sort(tv, col, not reverse))

    for col in range(len(tv['columns'])):
        tv.heading(col, command = lambda _col=col: _sort(tv, _col, col == 0))


def addStatusPanel(parent, max_width = 0):
    """Creates a status panel"""
    return StatusPanel(parent, max_width)

def addField(parent, type_, caption, nrow, ncol, def_val):
    """Add an text entry or combobox"""
    _var = tk.StringVar()
    if not def_val is None: _var.set(str(def_val))
    tk.Label(parent, text = caption).grid(row = nrow, column = ncol)

    _entry = None
    if type_ == 'cb':
        _entry = ttk.Combobox(parent, state="readonly", textvariable = _var)
    else:
        _entry = tk.Entry(parent, textvariable = _var)
    _entry.grid(row = nrow, column = ncol + 1)
    return _var, _entry

def is_on(a, b, c):
    """Return true if point c intersects the line segment from a to b."""

    def collinear(a, b, c):
        "Return true iff a, b, and c all lie on the same line."
        return (b[0] - a[0]) * (c[1] - a[1]) == (c[0] - a[0]) * (b[1] - a[1])

    def within(p, q, r):
        "Return true iff q is between p and r (inclusive)."
        return p <= q <= r or r <= q <= p

    # (or the degenerate case that all 3 points are coincident)
    return (collinear(a, b, c)
            and (within(a[0], c[0], b[0]) if a[0] != b[0] else
                 within(a[1], c[1], b[1])))

def is_on_w(a,b,c,delta=1):
    """Return true if point c intersects the line segment from a to b. Delta specifies a gap"""
    for i in range(delta*3):
        x = c[0] + i - 1
        for j in range(delta*3):
            y = c[1] + j - 1
            if is_on(a, b, (x, y)): return True
    return False


# Mask class
class ImageMask(object):
    """Support class for drawing and changing mask on an image drawn on canvas"""

    def __init__(self, canvas, image_shape, mask = None, allow_change = True, f_show = True, min_dist = 5):
        """Creates a mask object.

        Parameters:
            canvas        A canvas object
            image_shape   Shape of image drawn on canvas(assuming from 0,0 coordinates)
            mask          Initial mask (if None, default mask is generated)
            allow_change  True to allow mask reshaping by user (dragging by mouse)
            f_show        True to show mask initially
            min_dist      Minimal allowed distance to edges

        Mask shading and colors can be set by shade_fill, shade_stipple, mask_color attributes
        Resulting mask can be obtained through mask attribute
        """
        # Parameters
        self.canvas = canvas
        self.image_shape = image_shape
        self.min_dist = min_dist
        self.allow_change = allow_change
        self.mask = mask
        if self.mask is None:
           self.default_mask()

        self.shade_fill = "gray"
        self.shade_stipple = "gray50"
        self.mask_color = "red"

        self.mask_area = None
        self.mask_rect = None
        self.last_cursor = None
        self.drag_side = None

        # Draw initial mask
        if f_show: self.show()

        # Set handlers if allowed
        if allow_change:
            self.canvas.bind("<Motion>", self.motion_callback)
            self.canvas.bind('<B1-Motion>', self.drag_callback)
            self.canvas.bind('<B1-ButtonRelease>', self.end_drag_callback)

    def motion_callback(self, event):
        """Callback for mouse move event"""
        CURSORS = ["left_side", "top_side", "right_side", "bottom_side"]
        c = None
        if not self.mask_rect is None:
            side = self.get_mask_rect_side(event.x, event.y)
            if not side is None: c = CURSORS[side]

        if c is None and not self.last_cursor is None:
            # Left rectangle, set cursor to default
            self.canvas.config(cursor='')
            self.last_cursor = None
        elif not c is None and self.last_cursor != c:
            # On a line, set a cursor
            self.canvas.config(cursor=c)
            self.last_cursor = c

    def drag_callback(self, event):
        """Callback for mouse drag event"""
        if self.drag_side is None:
           self.drag_side = self.get_mask_rect_side(event.x, event.y)
        if not self.drag_side is None:
           p = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
           if self.drag_side == 0:
                self.mask[0] = max(p[0], self.min_dist)
           elif self.drag_side == 1:
                self.mask[1] = max(p[1], self.min_dist)
           elif self.drag_side == 2:
                self.mask[2] = min(p[0], self.image_shape[1]-self.min_dist)
           elif self.drag_side == 3:
                self.mask[3] = min(p[1], self.image_shape[0]-self.min_dist)
           self.canvas.coords(self.mask_rect, self.mask[0], self.mask[1], self.mask[2], self.mask[3])
           self.draw_mask_shading()

    def end_drag_callback(self, event):
        """Callback for mouse button release event"""
        #print('Drag end')
        self.drag_side = None

    def get_mask_rect_side(self, x, y):
        """Returns a side where the cursor is on or None"""
        if self.mask_rect is None:
           return None

        p = (self.canvas.canvasx(x), self.canvas.canvasy(y))
        b = self.canvas.coords(self.mask_rect)

        side = None
        if is_on_w((b[0], b[1]), (b[0], b[3]), p):
            side = 0
        elif is_on_w((b[0], b[1]), (b[2], b[1]), p):
            side = 1
        elif is_on_w((b[2], b[1]), (b[2], b[3]), p):
            side = 2
        elif is_on_w((b[0], b[3]), (b[2], b[3]), p):
            side = 3

        return side

    def show(self):
        """Draw a mask on canvas"""
        self.draw_mask_shading()
        self.draw_mask_rect()

    def hide(self):
        """Hide a previously shown mask"""
        if not self.mask_area is None:
            for m in self.mask_area:
                self.canvas.delete(m)
            self.mask_area = None
        if not self.mask_rect is None:
            self.canvas.delete(self.mask_rect)
            self.mask_rect = None

    def draw_mask_shading(self):
        """Draw a shading part of mask"""
        def _rect(points):
            return self.canvas.create_polygon(
                  *points,
                  outline = "",
                  fill = self.shade_fill,
                  stipple = self.shade_stipple)

        # Clean up
        if not self.mask_area is None:
            for m in self.mask_area:
                self.canvas.delete(m)
            self.mask_area = None

        # Create mask points array
        ix = self.image_shape[1]
        iy = self.image_shape[0]
        mx = self.mask[0]
        my = self.mask[1]
        wx = self.mask[2]
        wy = self.mask[3]
        self.mask_area = [
          _rect([0, 0, ix, 0, ix, my, 0, my, 0, 0]),
          _rect([0, my, mx, my, mx, iy, 0, iy, 0, my]),
          _rect([mx, wy, ix, wy, ix, iy, mx, iy, mx, wy]),
          _rect([wx, my, ix, my, ix, wy, wx, wy, wx, my])
        ]

    def draw_mask_rect(self):
        """Draws a transparent mask part"""
        # Clean up
        if not self.mask_rect is None:
            self.canvas.delete(self.mask_rect)
            self.mask_rect = None

        # Draw rect
        mx = self.mask[0]
        my = self.mask[1]
        wx = self.mask[2]
        wy = self.mask[3]
        self.mask_rect = self.canvas.create_rectangle(
          mx, my,
          wx, wy,
          outline = self.mask_color,
          width = 2
        )

    def random_mask(self):
        """Generates a random mask"""
        cw = int(self.image_shape[1] / 2)
        ch = int(self.image_shape[0] / 2)
        self.mask = [
                random.randint(0, cw),
                random.randint(0, ch),
                random.randint(cw+1, self.image_shape[1]),
                random.randint(ch+1, self.image_shape[0])]

    def default_mask(self):
        """Generates default mask"""
        self.mask = [
                self.min_dist,
                self.min_dist,
                self.image_shape[1]-self.min_dist,
                self.image_shape[0]-self.min_dist]

