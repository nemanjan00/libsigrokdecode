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
Runs a Saleae Logic 2 High Level Analyzer (HLA) extension on top of the
uart, i2c or spi decoder.

The lower decoder's output is turned into the frames Logic 2's own analyzers
produce (Async Serial 'data'; I2C 'start', 'address', 'data', 'stop'; SPI
'enable', 'result', 'disable'), passed to the extension's decode(), and the
frames it returns are shown as annotations, using its result_types formats.

Options:
 - extension: path of the extension directory (with extension.json), or of
   a single .py file containing a HighLevelAnalyzer subclass.
 - analyzer: which analyzer to run if the extension has several (its name
   in extension.json, or the class name).
 - settings: the extension's settings as "name=value; name2=value2".
   Unset settings get a default (empty string, 0 or the first choice).
 - uart_dir: which UART direction feeds the extension.
 - cs_polarity: SPI chip select polarity, for 'enable'/'disable'.
'''

from .pd import Decoder
