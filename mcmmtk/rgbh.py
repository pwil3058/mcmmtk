### Copyright: Peter Williams (2012) - All rights reserved
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

'''
Implement types to represent red/green/blue data as a tuple and hue angle as a float
'''

import collections
import math
import array
import fractions

from . import utils

if __name__ == '__main__':
    import doctest
    _ = lambda x: x

def RGB_TUPLE(name):
    return collections.namedtuple(name, ["red", "green", "blue"])

# 8 bits per channel specific constants
class BPC8:
    ZERO = 0
    BITS_PER_CHANNEL = 8
    ONE = (1 << BITS_PER_CHANNEL) - 1
    TWO = ONE * 2
    THREE = ONE * 3
    SIX = ONE * 6
    TYPECODE = 'B'
    @classmethod
    def ROUND(cls, x):
        return int(x + 0.5)

# 16 bits per channel specific constants
class BPC16:
    ZERO = 0
    BITS_PER_CHANNEL = 16
    ONE = (1 << BITS_PER_CHANNEL) - 1
    TWO = ONE * 2
    THREE = ONE * 3
    SIX = ONE * 6
    TYPECODE = 'H'
    @classmethod
    def ROUND(cls, x):
        return int(x + 0.5)

# Proportion (i.e. real numbers in the range 0 to 1.0) channel constants
class PROPN_CHANNELS:
    ZERO = 0.0
    BITS_PER_CHANNEL = None
    ONE = 1.0
    TWO = ONE * 2
    THREE = ONE * 3
    SIX = ONE * 6
    TYPECODE = 'f'
    @classmethod
    def ROUND(cls, x):
        return float(x)

class RGBNG:
    def get_value(self):
        total = sum(self)
        return total / self.ONE if self.BITS_PER_CHANNEL is None else fractions.Fraction(sum(self), self.THREE)
    def converted_to(self, rgbt):
        return rgbt(*[rgbt.ROUND((chnl * rgbt.ONE) / self.ONE) for chnl in self])
    @property
    def _class_name(self):
        return repr(self.__class__)[8:-2]
    @property
    def _format_str(self):
        s = self._class_name.split('.')[-1] + "("
        if self.BITS_PER_CHANNEL is None:
            s += "red={0.red:f}, green={0.green:f}, blue={0.blue:f})"
        else:
            s += "red=0x{{0.red:0{0}X}}, green=0x{{0.green:0{0}X}}, blue=0x{{0.blue:0{0}X}})".format(self.BITS_PER_CHANNEL / 4)
        return s
    @staticmethod
    def indices_value_order(rgb):
        '''
        Return the indices in descending order by value
        >>> RGB.indices_value_order((1, 2, 3))
        (2, 1, 0)
        >>> RGB.indices_value_order((3, 2, 1))
        (0, 1, 2)
        >>> RGB.indices_value_order((3, 1, 2))
        (0, 2, 1)
        '''
        if rgb[0] > rgb[1]:
            if rgb[0] > rgb[2]:
                if rgb[1] > rgb[2]:
                    return (0, 1, 2)
                else:
                    return (0, 2, 1)
            else:
                return (2, 0, 1)
        elif rgb[1] > rgb[2]:
            if rgb[0] > rgb[2]:
                return (1, 0, 2)
            else:
                return (1, 2, 0)
        else:
            return (2, 1, 0)
    @staticmethod
    def ncomps(rgb):
        '''
        Return the number of non zero components
        >>> RGB.ncomps((0, 0, 0))
        0
        >>> RGB.ncomps((1, 2, 3))
        3
        >>> RGB.ncomps((10, 0, 3))
        2
        >>> RGB.ncomps((0, 10, 3))
        2
        >>> RGB.ncomps((0, 10, 0))
        1
        '''
        return len(rgb) - rgb.count(0)
    @classmethod
    def ncomps_and_indices_value_order(cls, rgb):
        '''
        Return the number of non zero components and indices in value order
        >>> RGB.ncomps_and_indices_value_order((0, 0, 0))
        (0, (2, 1, 0))
        >>> RGB.ncomps_and_indices_value_order((1, 2, 3))
        (3, (2, 1, 0))
        >>> RGB.ncomps_and_indices_value_order((10, 0, 3))
        (2, (0, 2, 1))
        >>> RGB.ncomps_and_indices_value_order((0, 10, 3))
        (2, (1, 2, 0))
        >>> RGB.ncomps_and_indices_value_order((0, 10, 0))
        (1, (1, 2, 0))
        '''
        return (cls.ncomps(rgb), cls.indices_value_order(rgb))
    @classmethod
    def rotated(cls, rgb, delta_hue_angle):
        """
        Return a copy of the RGB with the same value but the hue angle rotated
        by the specified amount and with the item types unchanged.
        NB chroma changes when less than 3 non zero components and in the
        case of 2 non zero components this change is undesirable and
        needs to be avoided by using a higher level wrapper function
        that is aware of item types and maximum allowed value per component.
        import utils
        >>> RGB.rotated((1, 2, 3), utils.Angle(0))
        (1, 2, 3)
        >>> RGB.rotated((1, 2, 3), utils.PI_120)
        (3, 1, 2)
        >>> RGB.rotated((1, 2, 3), -utils.PI_120)
        (2, 3, 1)
        >>> RGB.rotated((2, 0, 0), utils.PI_60)
        (1, 1, 0)
        >>> RGB.rotated((2, 0, 0), -utils.PI_60)
        (1, 0, 1)
        >>> RGB.rotated((1.0, 0.0, 0.0), utils.PI_60)
        (0.5, 0.5, 0.0)
        >>> RGB.rotated((100, 0, 0), utils.Angle(math.radians(150)))
        (0, 66, 33)
        >>> RGB.rotated((100, 0, 0), utils.Angle(math.radians(-150)))
        (0, 33, 66)
        >>> RGB.rotated((100, 100, 0), -utils.PI_60)
        (100, 50, 50)
        >>> RGB.rotated((100, 100, 10), -utils.PI_60)
        (100, 55, 55)
        """
        def calc_ks(delta_hue_angle):
            a = math.sin(delta_hue_angle)
            b = math.sin(utils.PI_120 - delta_hue_angle)
            c = a + b
            k1 = b / c
            k2 = a / c
            return (k1, k2)
        f = lambda c1, c2: cls.ROUND(rgb[c1] * k1 + rgb[c2] * k2)
        if delta_hue_angle > 0:
            if delta_hue_angle > utils.PI_120:
                k1, k2 = calc_ks(delta_hue_angle - utils.PI_120)
                return array.array(cls.TYPECODE, (f(2, 1), f(0, 2), f(1, 0)))
            else:
                k1, k2 = calc_ks(delta_hue_angle)
                return array.array(cls.TYPECODE, (f(0, 2), f(1, 0), f(2, 1)))
        elif delta_hue_angle < 0:
            if delta_hue_angle < -utils.PI_120:
                k1, k2 = calc_ks(abs(delta_hue_angle) - utils.PI_120)
                return array.array(cls.TYPECODE, (f(1, 2), f(2, 0), f(0, 1)))
            else:
                k1, k2 = calc_ks(abs(delta_hue_angle))
                return array.array(cls.TYPECODE, (f(0, 1), f(1, 2), f(2, 0)))
        else:
            return rgb

class RGB8(RGB_TUPLE("RGB8"), RGBNG, BPC8):
    def __str__(self):
        return self._format_str.format(self)
    def __repr__(self):
        return str(self)
    def get_value(self):
        return fractions.Fraction(sum(self), self.THREE)

class RGB16(RGB_TUPLE("RGB16"), RGBNG, BPC16):
    def __str__(self):
        return self._format_str.format(self)
    def __repr__(self):
        return str(self)
    def get_value(self):
        return fractions.Fraction(sum(self), self.THREE)

class RGBPN(RGB_TUPLE("RGBPN"), RGBNG, PROPN_CHANNELS):
    def __str__(self):
        return self._format_str.format(self)
    def __repr__(self):
        return str(self)
    def get_value(self):
        return sum(self) / self.THREE

class HueNG(collections.namedtuple('Hue', ['io', 'other', 'angle', 'chroma_correction'])):
    @classmethod
    def from_angle(cls, angle):
        if math.isnan(angle):
            return cls(io=None, other=cls.ONE, angle=angle, chroma_correction=1.0)
        assert abs(angle) <= math.pi
        def calc_other(oa):
            scale = math.sin(oa) / math.sin(utils.PI_120 - oa)
            return cls.ROUND(cls.ONE * scale)
        aha = abs(angle)
        if aha <= utils.PI_60:
            other = calc_other(aha)
            io = (0, 1, 2) if angle >= 0 else (0, 2, 1)
        elif aha <= utils.PI_120:
            other = calc_other(utils.PI_120 - aha)
            io = (1, 0, 2) if angle >= 0 else (2, 0, 1)
        else:
            other = calc_other(aha - utils.PI_120)
            io = (1, 2, 0) if angle >= 0 else (2, 1, 0)
        a = cls.ONE
        b = other
        # avoid floating point inaccuracies near 1
        cc = 1.0 if a == b or b == 0 else a / math.sqrt(a * a + b * b - a * b)
        return cls(io=io, other=other, angle=utils.Angle(angle), chroma_correction=cc)
    @classmethod
    def from_rgb(cls, rgb):
        return cls.from_angle(XY.from_rgb(rgb).get_angle())
    def __eq__(self, other):
        if math.isnan(self.angle):
            return math.isnan(other.angle)
        return self.angle.__eq__(other.angle)
    def __ne__(self, other):
        return not self.__eq__(other.angle)
    def __lt__(self, other):
        if math.isnan(self.angle):
            return not math.isnan(other.angle)
        return self.angle.__lt__(other.angle)
    def __le__(self, other):
        return self.__lt__(other.angle) or self.__eq__(other.angle)
    def __gt__(self, other):
        return not self.__le__(other.angle)
    def __ge__(self, other):
        return not self.__lt__(other.angle)
    def __sub__(self, other):
        diff = self.angle - other.angle
        if diff > math.pi:
            diff -= math.pi * 2
        elif diff < -math.pi:
            diff += math.pi * 2
        return diff
    @property
    def rgb(self):
        if math.isnan(self.angle):
            return array.array(self.TYPECODE, (self.ONE, self.ONE, self.ONE))
        result = array.array(self.TYPECODE, [self.ZERO, self.ZERO, self.ZERO])
        result[self.io[0]] = self.ONE
        result[self.io[1]] = self.other
        return result
    def max_chroma_value(self):
        mct = self.ONE + self.other
        return mct / self.THREE if self.BITS_PER_CHANNEL is None else fractions.Fraction(mct, self.THREE)
    def max_chroma_for_total(self, total):
        if math.isnan(self.angle):
            return min(1.0, float(total) /self.ONE)
        mct = self.ONE + self.other
        if mct > total:
            return total / mct
        else:
            angle = self.angle if self.io[0] == 0 else (self.angle - utils.PI_120 if self.io[0] == 1 else self.angle + utils.PI_120)
            return ((self.THREE - total) / (2.0 * math.cos(angle))) * self.chroma_correction
    def max_chroma_for_value(self, value):
        return self.max_chroma_for_total(value * self.THREE)
    def rgb_with_total(self, req_total):
        '''
        return the RGB for this hue with the specified component total
        NB if requested value is too big for the hue the returned value
        will deviate towards the weakest component on its way to white.
        Return: a tuple with proportion components of the same type
        as our rgb
        '''
        if math.isnan(self.angle):
            val = self.ROUND(req_total / 3.0)
            return array.array(self.TYPECODE, (val, val, val))
        cur_total = self.ONE + self.other
        shortfall = req_total - cur_total
        result = array.array(self.TYPECODE, [self.ZERO, self.ZERO, self.ZERO])
        if shortfall == 0:
            result[self.io[0]] = self.ONE
            result[self.io[1]] = self.other
        elif shortfall < 0:
            result[self.io[0]] = self.ONE * req_total / cur_total
            result[self.io[1]] = self.other * req_total / cur_total
        else:
            result[self.io[0]] = self.ONE
            # it's simpler two work out the weakest component first
            result[self.io[2]] = (shortfall * self.ONE) / (2 * self.ONE - self.other)
            result[self.io[1]] = self.other + shortfall - result[self.io[2]]
        return result
    def rgb_with_value(self, value):
        '''
        return the RGB for this hue with the specified value
        NB if requested value is too big for the hue the returned value
        will deviate towards the weakest component on its way to white.
        Return: a tuple with proportion components of the same type
        as our rgb
        '''
        return self.rgb_with_total(self.ROUND(value * max(self.rgb) * 3))
    def is_grey(self):
        return math.isnan(self.angle)
    def rotated_by(self, delta_angle):
        return self.__class__.from_angle(self.angle + delta_angle)
    def get_xy_for_chroma(self, chroma):
        assert chroma > 0 and chroma <= 1.0
        hypot = chroma * self.ONE / self.chroma_correction
        return XY(hypot * math.cos(self.angle), hypot * math.sin(self.angle))

class Hue8(HueNG, BPC8):
    pass

class Hue16(HueNG, BPC16):
    pass

class HuePN(HueNG, PROPN_CHANNELS):
    pass

SIN_60 = math.sin(utils.PI_60)
SIN_120 = math.sin(utils.PI_120)
COS_120 = -0.5 # math.cos(utils.PI_120) is slightly out

class FRGB(RGB_TUPLE("FRGB")):
    def converted_to(self, rgbt):
        return rgbt(*[rgbt.ROUND(c) for c in self])

class XY(collections.namedtuple('XY', ['x', 'y'])):
    X_VECTOR = (1.0, COS_120, COS_120)
    Y_VECTOR = (0.0, SIN_120, -SIN_120)
    @classmethod
    def from_rgb(cls, rgb):
        """
        Return an XY instance derived from the specified rgb.
        >>> XY.from_rgb((100, 0, 0))
        XY(x=Fraction(100, 1), y=Fraction(0, 1))
        """
        x = sum(cls.X_VECTOR[i] * rgb[i] for i in range(3))
        y = sum(cls.Y_VECTOR[i] * rgb[i] for i in range(1, 3))
        return cls(x=x, y=y)
    def get_angle(self):
        if self.x == 0.0 and self.y == 0.0:
            return float('nan')
        else:
            return math.atan2(self.y, self.x)
    def get_hypot(self):
        """
        Return the hypotenuse as an instance of Fraction
        >>> XY.from_rgb((100, 0, 0)).get_hypot()
        Fraction(100, 1)
        >>> round(XY.from_rgb((100, 100, 100)).get_hypot())
        0.0
        >>> round(XY.from_rgb((0, 100, 0)).get_hypot())
        100.0
        >>> round(XY.from_rgb((0, 0, 100)).get_hypot())
        100.0
        >>> round(XY.from_rgb((0, 100, 100)).get_hypot())
        100.0
        >>> round(XY.from_rgb((0, 100, 50)).get_hypot())
        87.0
        """
        return math.hypot(self.x, self.y)
    def get_frgb(self):
        # get the RGB values for this XY point as floating point numbers
        # the scale of these will be the same as those of self
        a = self.x / COS_120
        b = self.y / SIN_120
        if self.y > 0.0:
            if a > b:
                return FRGB(red=0.0, green=((a + b) / 2), blue=((a - b) / 2))
            else:
                return FRGB(red=(self.x - b * COS_120), green=b, blue=0.0)
        elif self.y < 0.0:
            if a > -b:
                return FRGB(red=0.0, green=((a + b) / 2), blue=((a - b) / 2))
            else:
                return FRGB(red=(self.x + b * COS_120), green=0.0, blue=-b)
        elif self.x < 0.0:
            ha = a / 2
            return FRGB(red=0.0, green=ha, blue=ha)
        else:
            return FRGB(red=self.x, green=0.0, blue=0.0)

class RGBManipulator(object):
    def __init__(self, rgb=None, ONE=None):
        self.set_rgb(rgb if rgb is not None else (0.0, 0.0, 0.0), ONE)
    def set_rgb(self, rgb, ONE=None):
        if isinstance(rgb, RGBNG):
            rgb = [float(c) / rgb.ONE for c in rgb]
        elif ONE is not None:
            rgb = [float(c) / ONE for c in rgb]
        self.__set_rgb(RGBPN(*rgb))
        self.__last_hue = self.hue
    def __set_rgb(self, rgb):
        self.__rgb = rgb
        self.value = self.__rgb.get_value()
        self.xy = XY.from_rgb(self.__rgb)
        self.__base_rgb = self.xy.get_frgb().converted_to(RGBPN)
        self.hue = HuePN.from_angle(self.xy.get_angle())
        self.chroma = min(self.xy.get_hypot() * self.hue.chroma_correction, 1.0)
    def _min_value_for_current_HC(self):
        return self.__base_rgb.get_value()
    def _max_value_for_current_HC(self):
        return self.__base_rgb.get_value() + 1.0 - max(self.__base_rgb)
    def get_rgb(self, rgbt=None):
        if rgbt is None:
            return self.__rgb
        else:
            return rgbt(*[rgbt.ROUND(c * rgbt.ONE) for c in self.__rgb])
    def _set_from_value(self, new_value):
        new_chroma = self.hue.max_chroma_for_value(new_value)
        new_base_rgb = self.hue.get_xy_for_chroma(new_chroma).get_frgb().converted_to(RGBPN)
        delta = new_value - new_base_rgb.get_value()
        self.__set_rgb(RGBPN(*[c + delta for c in new_base_rgb]))
    def _set_from_chroma(self, new_chroma):
        ratio = new_chroma / self.chroma
        new_base_rgb = XY(*[c * ratio for c in self.xy]).get_frgb().converted_to(RGBPN)
        delta = min(1.0 - max(new_base_rgb), self.value - new_base_rgb.get_value())
        if delta > 0.0:
            self.__set_rgb(RGBPN(*[c + delta for c in new_base_rgb]))
        else:
            self.__set_rgb(new_base_rgb)
    def decr_value(self, deltav):
        if self.value <= 0.0:
            return False
        new_value = max(0.0, self.value - deltav)
        min_value = self._min_value_for_current_HC()
        if new_value == 0.0:
            self.__set_rgb(RGBPN(0.0, 0.0, 0.0))
        elif new_value < min_value:
            self._set_from_value(new_value)
        else:
            delta = new_value - min_value
            self.__set_rgb(RGBPN(*[c + delta for c in self.__base_rgb]))
        return True
    def incr_value(self, deltav):
        if self.value >= 1.0:
            return False
        new_value = min(1.0, self.value + deltav)
        max_value = self._max_value_for_current_HC()
        if new_value >= 1.0:
            self.__set_rgb(RGBPN(1.0, 1.0, 1.0))
        elif new_value > max_value:
            self._set_from_value(new_value)
        else:
            delta = new_value - self._min_value_for_current_HC()
            self.__set_rgb(RGBPN(*[c + delta for c in self.__base_rgb]))
        return True
    def decr_chroma(self, deltac):
        if self.chroma <= 0.0:
            return False
        self._set_from_chroma(max(0.0, self.chroma - deltac))
        return True
    def incr_chroma(self, deltac):
        if self.chroma >= 1.0:
            return False
        if self.hue.is_grey():
            if self.value <= 0.0 or self.value >= 1.0:
                if self.__last_hue.is_grey():
                    # any old hue will do
                    new_base_rgb = HuePN.from_angle(0.5).get_xy_for_chroma(deltac).get_frgb().converted_to(RGBPN)
                else:
                    new_base_rgb = self.__last_hue.get_xy_for_chroma(deltac).get_frgb().converted_to(RGBPN)
                if self.value <= 0.0:
                    self.__set_rgb(new_base_rgb)
                else:
                    delta = 1.0 - max(new_base_rgb)
                    self.__set_rgb(RGBPN(*[c + delta for c in new_base_rgb]))
            else:
                max_chroma = self.__last_hue.max_chroma_for_value(self.value)
                new_chroma = min(deltac, max_chroma)
                if self.__last_hue.is_grey():
                    # any old hue will do
                    new_base_rgb = HuePN.from_angle(0.5).get_xy_for_chroma(new_chroma).get_frgb().converted_to(RGBPN)
                else:
                    new_base_rgb = self.__last_hue.get_xy_for_chroma(new_chroma).get_frgb().converted_to(RGBPN)
                # delta should be greater than or equal to zero
                delta = self.value - new_base_rgb.get_value()
                self.__set_rgb(RGBPN(*[c + delta for c in new_base_rgb]))
            self.__last_hue = self.hue
        else:
            self._set_from_chroma(min(1.0, self.chroma + deltac))
        return True
    def rotate_hue(self, deltah):
        if self.hue.is_grey():
            return False # There is no hue to rotate
        # keep same chroma
        new_base_rgb = self.hue.rotated_by(deltah).get_xy_for_chroma(self.chroma).get_frgb().converted_to(RGBPN)
        # keep same value if possible (otherwise as close as possible)
        max_delta = 1.0 - max(new_base_rgb)
        delta = min(max_delta, self.value - new_base_rgb.get_value())
        if delta > 0.0:
            self.__set_rgb(RGBPN(*[c + delta for c in new_base_rgb]))
        else:
            self.__set_rgb(new_base_rgb)
        self.__last_hue = self.hue
        return True

if __name__ == '__main__':
    doctest.testmod()
