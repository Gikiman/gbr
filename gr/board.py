#-------------------------------------------------------------------------------
# Name:        Go board recognition project
# Purpose:     Go board class
#
# Author:      kol
#
# Created:     04.07.2019
# Copyright:   (c) kol 2019
# Licence:     MIT
#-------------------------------------------------------------------------------
from .grdef import *
from .gr import process_img, detect_board, generate_board, find_coord, find_position
from .utils import resize2
from .params import GrParams

from pathlib import Path
import cv2
from imutils.perspective import four_point_transform
import numpy as np
import json
import logging
from sgfmill import sgf

BOARD_PARAM_EXT = '.gpar'  # extension for board parameters file

class GrBoard(object):
    """ Go board """
    def __init__(self, image_file = None, board_shape = None):
        """ Create new instance either for image file or by generation

        Parameters:
            image_file       Name of image file to load
            board_shape      Generated board shape, if no image file is provided

        """
        self._params = GrParams()
        self._res = None
        self._img = None
        self._img_file = None
        self._src_img = None
        self._src_img_file = None
        self._gen_board = False

        if image_file is None or image_file == '':
            # Generate default board
            if board_shape is None: board_shape = DEF_IMG_SIZE
            self.generate(shape = board_shape)
        else:
            # Load board from file
            self.load_image(image_file)

    def load_image(self, filename, f_with_params = True, f_process = True):
        """Loads a new image to board

        Parameters:
            f_with_params     If True, image recognition params are loaed from <filename>.JSON file
            f_process         If True, starts image recongition
        """
        # Load image
        logging.info('Loading {}'.format(filename))
        img = cv2.imread(str(filename))
        if img is None:
           logging.error('Image file not found {}'.format(filename))
           raise Exception('Image file not found {}'.format(filename))

        self._gen_board = False
        self._img_file = filename
        self._src_img_file = filename
        self._img = img
        self._src_img = img.copy()
        self._res = None

        # Load params, if requested and file exists
        f_params_loaded = False
        if f_with_params:
            params_file = Path(filename).with_suffix(BOARD_PARAM_EXT)
            if params_file.is_file():
                self.load_params(str(params_file))
                f_params_loaded = True

        # Do a transformation, if specified
        if 'TRANSFORM' in self._params:
           self.transform_image(self._params['TRANSFORM'])

        # Analyze board
        if f_process: self.process()
        return f_params_loaded

    def generate(self, shape = DEF_IMG_SIZE):
        """Generates a new board image of given shape and stores it in this instance.
        If stones were recognized, displays them on the image. Sets is_gen_board flag to True.

        Parameters:
            shape       Shape of image to generate

        Returns:
            img         OpenCV image generated
        """
        self._img = generate_board(shape, res = self._res)
        self._img_file = None
        self._gen_board = True

    def save_image(self, filename = None, max_size = None):
        """Saves image under new name. If max_size provided, resizes image before"""
        if self._img is None:
           raise Exception('Image was not loaded')

        if filename is None: filename = self._img_file
        im = self._img
        if not max_size is None: im = resize(im, max_size)

        logging.info('Saving image to {}'.format(filename))
        try:
            cv2.imwrite(str(filename), im)
        except:
            logging.error(sys.exc_info()[1])
            raise

        self._img_file = filename
        self._gen_board = False

    def load_params(self, filename):
        """Loads recognition parameters from specified file (JSON)"""
        p = json.load(open(str(filename)))
        self._params.assign(p, copy_all = True)

    def save_params(self, filename = None, f_bak = True):
        """Saves recognition parameters to specified file (JSON)"""
        if filename is None:
            filename = str(Path(self._img_file).with_suffix(BOARD_PARAM_EXT))
        p = Path(filename)
        if p.exists() and f_bak:
            p.replace(p.with_suffix(BOARD_PARAM_EXT + ".bak"))
        with open(filename, "w+") as f:
            json.dump(self._params.todict(), f, indent=4, sort_keys=True, ensure_ascii=False)
        return filename

    def save_sgf(self, filename = None):
        """Saves recognition results to specified file (SGF)"""

        def _add_stone(game, bw, stone):
            node = game.extend_main_sequence()
            node.set_move(bw, (stone[GR_B], stone[GR_A]))

        if self._res is None:
            raise Exception("Recognition results are not available")

        if filename is None:
            filename = str(Path(self._img_file).with_suffix('.sgf'))

        game = sgf.Sgf_game(size = self.board_size)
        stones = self.stones
        for n in range(max(len(stones['W']), len(stones['B']))):
            if n < len(stones['B']):
                _add_stone(game, 'b', stones['B'][n]-1)
            if n < len(stones['W']):
                _add_stone(game, 'w', stones['W'][n]-1)

        with open(filename, "wb") as f:
            f.write(game.serialise())
            f.close()

        return filename

    def detect_edges(self):
        """Runs edges and size detection and stores result in params overriding
        BOARD_SIZE and BOARD_EDGES keys. Returns detection results."""
        if self._img is None or self._gen_board:
           return None, None
        else:
           edges, size = detect_board(self._img, self._params)
           self._params['BOARD_EDGES'] = edges
           self._params['BOARD_SIZE'] = size
           return edges, size

    def process(self):
        """Perform recognition of board image"""
        if self._img is None or self._gen_board:
            self._res = None
        else:
            self._res = process_img(self._img, self._params)
            if not self._res is None:
               if self._res[GR_STONES_B] is None: self._res[GR_STONES_B] = np.array([])
               if self._res[GR_STONES_W] is None: self._res[GR_STONES_W] = np.array([])

    def show_board(self, f_black = True, f_white = True, f_det = False, show_state = None):
        """Generates a new board image of given shape and returns it.
        If stones were found on the source image, displays them on the image.
        Does not change internal image or is_gen_board flag.

        Parameters:
            f_black     If True, black stones are displayed. Not used if show_state is provided
            f_white     If True, white stones are displayed. Not used if show_state is provided
            f_det       If True, stone circles are displayed. Not used if show_state is provided
            show_state  A dictionary of display parameters. If provided, overrides all f_xxx parameters

        Returns:
            img         OpenCV image generated
        """
        if not show_state is None:
           f_black = show_state['black']
           f_white = show_state['white']
           f_det = show_state['box']

        r = None
        if not self._res is None:
            r = self._res.copy()
            if not f_black:
                del r[GR_STONES_B]
            if not f_white:
                del r[GR_STONES_W]

        img = generate_board(shape = self._img.shape, res = r, f_show_det = f_det)
        return img

    def resize_board(self, max_size = None, scale = None):
        """Resize board image and stone coordinations to new size or scale.
        See gr.utils.resize3() for parameters info"""

        def resize_stones(stones, scale):
            ret_stones = []
            for st in stones:
                st[GR_X] = int(st[GR_X] * scale[0])
                st[GR_Y] = int(st[GR_Y] * scale[1])
                st[GR_R] = int(st[GR_R] * max(scale[0],scale[1]))
                ret_stones.append(st)
            return np.array(ret_stones)

        self._img, scale = resize2(self._img, max_size)
        if not self._res is None:
            self._res[GR_STONES_B] = resize_stones(self._res[GR_STONES_B], scale)
            self._res[GR_STONES_W] = resize_stones(self._res[GR_STONES_W], scale)
            self._res[GR_SPACING] = (self._res[GR_SPACING][0] * scale[0], \
                                        self._res[GR_SPACING][1] * scale[1])
            self._res[GR_EDGES] = ((self._res[GR_EDGES][0][0] * scale[0], \
                                        self._res[GR_EDGES][0][1] * scale[1]), \
                                        (self._res[GR_EDGES][1][0] * scale[0], \
                                        self._res[GR_EDGES][1][1] * scale[1]))


    @property
    def params(self):
        """Recognition parameters"""
        return self._params

    @params.setter
    def params(self, p):
        """Recognition parameters"""
        self._params.assign(p)
        self._gen_board = False

    @property
    def param_area_mask(self):
        """Board recognition area rectangle - tuple of tuples ((x1,y1),(x2,y2)).
        Image is clipped to this rectangle during processing.
        """
        p = self._params.get('AREA_MASK')
        return list(p) if p is not None else None

    @param_area_mask.setter
    def param_area_mask(self, mask):
        # ImageMask uses flattened list, conversion required
        if mask is None:
            self._params['AREA_MASK'] = None
        else:
            m = np.array(mask).reshape((2,2)).tolist()
            self._params['AREA_MASK'] = m

    @property
    def param_board_edges(self):
        """Board edges rectangle - tuple of tuples ((x1,y1),(x2,y2)).
        Defines corners of actual board (where stones are placed upon).
        If set, automatic edges/spacing detection is skipped if favour for this parameter.
        Note that param_board_size should also be set in parameters to proper board recognition.
        Use detect_edges() to define edges and board size before processing.
        """
        m = self._params.get('BOARD_EDGES')
        return list(m) if m is not None else None

    @param_board_edges.setter
    def param_board_edges(self, edges):
        # ImageMask/Tranform use flattened list, conversion required
        if edges is None:
            self._params['BOARD_EDGES'] = None
        else:
            m = np.array(edges).reshape((2,2)).tolist()
            self._params['BOARD_EDGES'] = m

    @property
    def param_board_size(self):
        """Board size to be used for image recognition.
        Note that param_area_size should also be set in parameters to proper board recognition.
        Use detect_edges() to define edges and board size before processing.
        """
        return self._params.get('BOARD_SIZE')

    @param_board_size.setter
    def param_board_size(self, size):
        self._params['BOARD_SIZE'] = int(size) if size is not None else None

    @property
    def param_transform_rect(self):
        """Board image transformation rectangle - tuple of tuples ((x1,y1),(x2,y2))"""
        p = self._params.get('TRANSFORM')
        return list(p) if p is not None else None

    @param_transform_rect.setter
    def param_transform_rect(self, rect):
        self._params['TRANSFORM'] = rect

    @property
    def results(self):
        """Recognition results"""
        return self._res

    @property
    def image(self):
        """Board image"""
        return self._img

    @image.setter
    def image(self, im):
        """Board image"""
        self._img = im
        self._gen_board = False
        if self._src_img is None:
            self._src_img = im.copy()

    @property
    def src_image(self):
        """Board image as it was loaded"""
        return self._src_img

    @property
    def image_file(self):
        """Image file name"""
        return self._img_file

    @property
    def is_gen_board(self):
        """True if board was generated with generate()"""
        return self._gen_board

    @property
    def black_stones(self):
        """List of black stones"""
        if self._res is None:
            return None
        else:
            return self._res[GR_STONES_B]

    @property
    def white_stones(self):
        """List of white stones"""
        if self._res is None:
            return None
        else:
            return self._res[GR_STONES_W]

    @property
    def stones(self):
        """Dictionary with all stones (keys are B, W)"""
        if self._res is None:
            return None
        else:
            return { 'W': self._res[GR_STONES_W], 'B': self._res[GR_STONES_B] }

    @property
    def all_stones(self):
        """All stones on a board.
        Returns list of stones, where every stone is [x, y, a, b, r, bw]"""
        r = []
        if not self.black_stones is None:
            r.extend([list(r) + ['B'] for r in self.black_stones])
        if not self.white_stones is None:
            r.extend([list(r) + ['W'] for r in self.white_stones])
        return r

    def find_stone(self, c = None, p = None, s = None, bw = None):
        """Finds a stone at given coordinates or position
        Parameters:
            c       screen coordinates as tuple(x,y) or None
            p       stone position as tuple(a,b) or None
            s       stone position as letter and index (A10)
            bw      stone type (B/W to look for specified color or None)
        Returns;
            stone list of stone properties
            type  B/W stone type
        """
        def _find(stones):
            if c is not None:
                return find_coord(c[0], c[1], stones)
            elif p is not None:
                return find_position(p[0], p[1], stones)
            elif s is not None:
                return find_position(
                    ord(s.upper()[0]) - ord('A') + 1,
                    int(s[1:len(s)]),
                    stones)
            else:
                return None

        if self._res is None:
            return None, None

        if bw is not None:
            stone = _find(self.stones[bw])
        else:
            stone = _find(self.black_stones)
            if stone is not None:
                bw = 'B'
            else:
                stone = _find(self.white_stones)
                if not stone is None: bw = 'W'

        return stone, bw

    def find_nearby(self, p, d = 1):
        """Finds all stones near specified position.
        Parameters:
            p   board position coordinates
            d   delta
        Return: a list of stones the same as for all_stones
        """
        if p is None:
            return None
        r = []
        rg_a = range(max(p[GR_A]-d,1), min(p[GR_A]+d, self.board_size)+1)
        rg_b = range(max(p[GR_B]-d,1), min(p[GR_B]+d, self.board_size)+1)
        for s in self.all_stones:
            if not(s[GR_A] == p[GR_A] and s[GR_B] == p[GR_B]) and \
            s[GR_A] in rg_a and s[GR_B] in rg_b:
                r.extend([s])
        return r

    @property
    def debug_images(self):
        """Collection of debug images generated during image recognition"""
        if self._res is None:
            return None
        else:
            r = dict()
            for key in self._res.keys():
                if key.find("IMG_") >= 0: r[key] = self._res[key]
            return r

    @property
    def debug_info(self):
        """Collection of textual information generated during image recognition"""
        if self._res is None:
            return None
        else:
            r = dict()
            r[GR_EDGES] = self._res[GR_EDGES]
            r[GR_SPACING] = (round(self._res[GR_SPACING][0],2), \
                             round(self._res[GR_SPACING][1],2))
            r[GR_NUM_CROSS_H] = self._res[GR_NUM_CROSS_H]
            r[GR_NUM_CROSS_W] = self._res[GR_NUM_CROSS_W]
            r[GR_BOARD_SIZE] = self._res[GR_BOARD_SIZE]
            r[GR_IMAGE_SIZE] = self._res[GR_IMAGE_SIZE]
            return r

    @property
    def board_size(self):
        """Board size"""
        if self._res is None:
            p = self._params.get('BOARD_SIZE')
            return p if p is not None else DEF_BOARD_SIZE
        else:
            return self._res[GR_BOARD_SIZE]

    @property
    def board_edges(self):
        """Board edges"""
        if self._res is None:
            return self._params.get('BOARD_EDGES')
        else:
            return self._res[GR_EDGES]

    def transform_image(self, transform_rect):
        """Performs a perspective transformation"""
        if not transform_rect is None and len(transform_rect) == 4:
           logging.info('Transforming: {}'.format(transform_rect))
           self._img = four_point_transform(self._img, np.array(transform_rect))
           self._params['TRANSFORM'] = transform_rect

    def reset_image(self):
        """Revert image to original after a transformation"""
        self._img = self._src_img
        self._params['TRANSFORM'] = None
        self._params['BOARD_EDGES'] = None
        self._params['BOARD_SIZE'] = None

    @property
    def can_reset_image(self):
        """Returns True if a transformation was applied to the image.
        Use reset_image() to revert to original image"""
        return not self._img is None and np.any(self._img != self._src_img)

