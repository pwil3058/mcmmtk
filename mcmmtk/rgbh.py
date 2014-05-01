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

from mcmmtk import utils

if __name__ == '__main__':
    import doctest
    _ = lambda x: x

# 8 bits per channel specific constants
class BPC8:
    ZERO = 0
    BITS_PER_CHANNEL = 8
    ONE = (1 << BITS_PER_CHANNEL) - 1
    TWO = ONE * 2
    THREE = ONE * 3
    SIX = ONE * 6
    TYPECODE = 'B'

# 16 bits per channel specific constants
class BPC16:
    ZERO = 0
    BITS_PER_CHANNEL = 16
    ONE = (1 << BITS_PER_CHANNEL) - 1
    TWO = ONE * 2
    THREE = ONE * 3
    SIX = ONE * 6
    TYPECODE = 'H'

class RGBNG:
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
        f = lambda c1, c2: int((rgb[c1] * k1 + rgb[c2] * k2) + 0.5)
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

class RGB8(RGBNG, BPC8):
    pass

class RGB16(RGBNG, BPC16):
    pass

class HueNG(collections.namedtuple('Hue', ['io', 'other', 'angle'])):
    @classmethod
    def from_angle(cls, angle):
        if math.isnan(angle):
            return cls(io=None, other=cls.ONE, angle=angle)
        assert abs(angle) <= math.pi
        def calc_other(oa):
            scale = math.sin(oa) / math.sin(utils.PI_120 - oa)
            return int(cls.ONE * scale + 0.5)
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
        return cls(io=io, other=other, angle=utils.Angle(angle))
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
        result = array.array(self.TYPECODE, [0, 0, 0])
        result[self.io[0]] = self.ONE
        result[self.io[1]] = self.other
        return result
    def rgb_with_total(self, req_total):
        '''
        return the RGB for this hue with the specified component total
        NB if requested value is too big for the hue the returned value
        will deviate towards the weakest component on its way to white.
        Return: a tuple with proportion components of the same type
        as our rgb
        '''
        if math.isnan(self.angle):
            val = int((req_total + 0.5) / 3)
            return array.array(self.TYPECODE, (val, val, val))
        cur_total = self.ONE + self.other
        shortfall = req_total - cur_total
        result = array.array(self.TYPECODE, [0, 0, 0])
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
        return self.rgb_with_total(int(value * max(self.rgb) * 3 + 0.5))
    def get_chroma_correction(self):
        if math.isnan(self.angle):
            return 1.0
        a = self.ONE
        b = self.other
        if a == b or b == 0: # avoid floating point inaccuracies near 1
            return 1.0
        return a / math.sqrt(a * a + b * b - a * b)
    def is_grey(self):
        return math.isnan(self.angle)

class Hue8(HueNG, BPC8):
    pass

class Hue16(HueNG, BPC16):
    pass

SIN_60 = math.sin(utils.PI_60)
SIN_120 = math.sin(utils.PI_120)
COS_120 = -0.5 # math.cos(utils.PI_120) is slightly out

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

if __name__ == '__main__':
    doctest.testmod()
