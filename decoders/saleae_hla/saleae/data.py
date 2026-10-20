##
## This file is part of the libsigrokdecode project.
##
## Copyright (C) 2026 Nemanja Nedeljkovic <nemanjan00@gmail.com>
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, see <http://www.gnu.org/licenses/>.
##

'''
The time types of the Saleae Logic 2 extension API (saleae.data), written
from Saleae's public documentation.

Times are kept as exact fractions of a second, so converting sample numbers
to times and back is exact at any samplerate.
'''

from datetime import datetime, timedelta, timezone
from fractions import Fraction
from functools import total_ordering

__all__ = ['SaleaeTime', 'SaleaeTimeDelta', 'SaleaeTimeInterval',
           'GraphTime', 'GraphTimeDelta', 'GraphTimeInterval']

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def _seconds(second=0, millisecond=0, microsecond=0, nanosecond=0, picosecond=0):
    return (Fraction(second) + Fraction(millisecond) / 10**3 +
            Fraction(microsecond) / 10**6 + Fraction(nanosecond) / 10**9 +
            Fraction(picosecond) / 10**12)


@total_ordering
class SaleaeTimeDelta:
    '''A duration. float() gives seconds.'''

    __slots__ = ('_s',)

    def __init__(self, second=0, *, millisecond=0, microsecond=0, nanosecond=0,
                 picosecond=0):
        self._s = _seconds(second, millisecond, microsecond, nanosecond, picosecond)

    @classmethod
    def _from_seconds(cls, seconds):
        delta = cls.__new__(cls)
        delta._s = Fraction(seconds)
        return delta

    def __float__(self):
        return float(self._s)

    def __add__(self, other):
        if isinstance(other, SaleaeTimeDelta):
            return SaleaeTimeDelta._from_seconds(self._s + other._s)
        if isinstance(other, SaleaeTime):
            return other + self
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, SaleaeTimeDelta):
            return SaleaeTimeDelta._from_seconds(self._s - other._s)
        return NotImplemented

    def __neg__(self):
        return SaleaeTimeDelta._from_seconds(-self._s)

    def __pos__(self):
        return self

    def __abs__(self):
        return SaleaeTimeDelta._from_seconds(abs(self._s))

    def __mul__(self, factor):
        if isinstance(factor, (int, float, Fraction)):
            return SaleaeTimeDelta._from_seconds(self._s * Fraction(factor))
        return NotImplemented

    __rmul__ = __mul__

    def __truediv__(self, other):
        if isinstance(other, SaleaeTimeDelta):
            return float(self._s / other._s)
        if isinstance(other, (int, float, Fraction)):
            return SaleaeTimeDelta._from_seconds(self._s / Fraction(other))
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, SaleaeTimeDelta):
            return self._s == other._s
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, SaleaeTimeDelta):
            return self._s < other._s
        return NotImplemented

    def __hash__(self):
        return hash(('delta', self._s))

    def __bool__(self):
        return self._s != 0

    def __repr__(self):
        return f'SaleaeTimeDelta(second={float(self._s)!r})'


@total_ordering
class SaleaeTime:
    '''A wall clock time. Subtract two to get a SaleaeTimeDelta.'''

    __slots__ = ('_s',) # seconds since the Unix epoch

    def __init__(self, datetime, *, millisecond=0, microsecond=0, nanosecond=0,
                 picosecond=0):
        if datetime.tzinfo is None:
            datetime = datetime.replace(tzinfo=timezone.utc)
        base = datetime - _EPOCH
        self._s = (Fraction(base.days * 86400 + base.seconds) +
                   Fraction(base.microseconds, 10**6) +
                   _seconds(0, millisecond, microsecond, nanosecond, picosecond))

    @classmethod
    def _from_seconds(cls, seconds):
        time = cls.__new__(cls)
        time._s = Fraction(seconds)
        return time

    def as_datetime(self):
        return _EPOCH + timedelta(microseconds=round(self._s * 10**6))

    def __add__(self, other):
        if isinstance(other, SaleaeTimeDelta):
            return SaleaeTime._from_seconds(self._s + other._s)
        return NotImplemented

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, SaleaeTime):
            return SaleaeTimeDelta._from_seconds(self._s - other._s)
        if isinstance(other, SaleaeTimeDelta):
            return SaleaeTime._from_seconds(self._s - other._s)
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, SaleaeTime):
            return self._s == other._s
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, SaleaeTime):
            return self._s < other._s
        return NotImplemented

    def __hash__(self):
        return hash(('time', self._s))

    def __repr__(self):
        return f'SaleaeTime({self.as_datetime().isoformat()})'


class SaleaeTimeInterval:
    '''The half-open interval [begin, end).'''

    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __repr__(self):
        return f'SaleaeTimeInterval({self.begin!r}, {self.end!r})'


GraphTime = SaleaeTime
GraphTimeDelta = SaleaeTimeDelta
GraphTimeInterval = SaleaeTimeInterval
