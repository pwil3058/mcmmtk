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

import string
import bisect
import math

# Allow possessives and hyphenated words
DELIMITERS = string.whitespace + string.punctuation.replace("'", '').replace('-', '')

def find_start_last_word(text, before=None):
    index = before if before is not None and before < len(text) else len(text)
    while index > 0:
        index -= 1
        if text[index] in DELIMITERS:
            return index + 1
    return index

def replace_last_word(text, new_word, before=None):
    """
    Return a new string with the last word replaced by the new word.
    """
    index = find_start_last_word(text=text, before=before)
    tail = text[before:] if before is not None else ''
    return text[:index] + new_word + tail

def extract_words(text):
    words = []
    index = 0
    inword = False
    start = None
    while index < len(text):
        if inword:
            if text[index] in DELIMITERS:
                words.append(text[start:index])
                start = None
                inword = False
        elif text[index] not in DELIMITERS:
            inword = True
            start = index
        index += 1
    if start is not None:
        words.append(text[start:])
    return words

def contains(somelist, arg):
    index = bisect.bisect_left(somelist, arg)
    return index != len(somelist) and somelist[index] == arg

def create_flag_generator(next_flag_num=0):
    """
    Create a new flag generator
    """
    while True:
        yield 2 ** next_flag_num
        next_flag_num += 1

class Angle(float):
    """
    A wrapper around float type to represent hue_angles incorporating the
    restrictions that apply to hue_angles.
    """
    def __new__(cls, value):
        """
        >>> Angle(2)
        Angle(2.0)
        >>> Angle(4)
        Traceback (most recent call last):
        AssertionError
        """
        #Make sure the value is between -pi and pi
        assert value >= -math.pi and value <= math.pi
        return float.__new__(cls, value)
    def __repr__(self):
        '''
        >>> Angle(2).__repr__()
        'Angle(2.0)'
        '''
        return '{0}({1})'.format(self.__class__.__name__, float.__repr__(self))
    @classmethod
    def normalize(cls, angle):
        """
        >>> Angle.normalize(2)
        Angle(2.0)
        >>> Angle.normalize(4)
        Angle(-2.2831853071795862)
        >>> Angle.normalize(-4)
        Angle(2.2831853071795862)
        >>> Angle.normalize(Angle(2))
        Traceback (most recent call last):
        AssertionError
        """
        assert not isinstance(angle, Angle)
        if angle > math.pi:
            return cls(angle - 2 * math.pi)
        elif angle < -math.pi:
            return cls(angle + 2 * math.pi)
        return cls(angle)
    def __neg__(self):
        """
        Change sign while maintaining type
        >>> -Angle(2)
        Angle(-2.0)
        >>> -Angle(-2)
        Angle(2.0)
        """
        return type(self)(float.__neg__(self))
    def __abs__(self):
        """
        Get absolate value while maintaining type
        >>> abs(-Angle(2))
        Angle(2.0)
        >>> abs(Angle(-2))
        Angle(2.0)
        """
        return type(self)(float.__abs__(self))
    def __add__(self, other):
        """
        Do addition and normalize the result
        >>> Angle(2) + 2
        Angle(-2.2831853071795862)
        >>> Angle(2) + 1
        Angle(3.0)
        """
        return self.normalize(float.__add__(self, other))
    def __radd__(self, other):
        """
        Do addition and normalize the result
        >>> 2.0 + Angle(2)
        Angle(-2.2831853071795862)
        >>> 1.0 + Angle(2)
        Angle(3.0)
        >>> 1 + Angle(2)
        Angle(3.0)
        """
        return self.normalize(float.__radd__(self, other))
    def __sub__(self, other):
        """
        Do subtraction and normalize the result
        >>> Angle(2) - 1
        Angle(1.0)
        >>> Angle(2) - 6
        Angle(2.2831853071795862)
        """
        return self.normalize(float.__sub__(self, other))
    def __rsub__(self, other):
        """
        Do subtraction and normalize the result
        >>> 1 - Angle(2)
        Angle(-1.0)
        >>> 6 - Angle(2)
        Angle(-2.2831853071795862)
        """
        return self.normalize(float.__rsub__(self, other))
    def __mul__(self, other):
        """
        Do multiplication and normalize the result
        >>> Angle(1) * 4
        Angle(-2.2831853071795862)
        >>> Angle(1) * 2.5
        Angle(2.5)
        """
        return self.normalize(float.__mul__(self, other))
PI_0 = Angle(0.0)
PI_30 = Angle(math.pi / 6)
PI_60 = Angle(math.pi / 3)
PI_90 = Angle(math.pi / 2)
PI_120 = PI_60 * 2
PI_150 = PI_30 * 5
PI_180 = Angle(math.pi)

def gcd(*args):
    if len(args) == 0:
        return None
    elif len(args) == 1:
        return args[0]
    L = list(args)
    while len(L) > 1:
        a = L[len(L) - 2]
        b = L[len(L) - 1]
        L = L[:len(L) - 2]
        while a:
            a, b = b % a, a
        L.append(b)
    return abs(b)
