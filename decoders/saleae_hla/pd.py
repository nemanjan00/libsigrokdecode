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

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from fractions import Fraction

import sigrokdecode as srd

from . import saleae as _saleae
from .saleae import analyzers as _analyzers, data as _data

# Logic 2 extensions import these by their Saleae names.
sys.modules.setdefault('saleae', _saleae)
sys.modules.setdefault('saleae.analyzers', _analyzers)
sys.modules.setdefault('saleae.data', _data)

from .saleae.analyzers import AnalyzerFrame, HighLevelAnalyzer
from .saleae.data import SaleaeTime

UART_PTYPES = ('STARTBIT', 'PARITYBIT', 'STOPBIT', 'INVALID STARTBIT',
               'INVALID STOPBIT', 'PARITY ERROR', 'BREAK', 'FRAME', 'IDLE')
SPI_PTYPES = ('CS-CHANGE', 'BITS', 'TRANSFER')

class Ann:
    FRAME, ERROR = range(2)

class HlaError(Exception):
    pass

def word_bytes(value, bits):
    '''A word as Saleae analyzers deliver it: bytes, most significant first.'''
    if value is None:
        return b''
    return value.to_bytes(max(1, (bits + 7) // 8), 'big')

def format_value(value):
    if isinstance(value, (bytes, bytearray)):
        return ' '.join('0x{:02X}'.format(b) for b in value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value)

def load_hla(path, name):
    '''Find the HighLevelAnalyzer class of a Logic 2 extension.

    path is an extension directory (with extension.json) or a single .py
    file; name picks one analyzer when there are several: the extension
    name from extension.json, or the class name.
    '''
    path = os.path.expanduser(path)
    if os.path.isdir(path):
        manifest = os.path.join(path, 'extension.json')
        if not os.path.exists(manifest):
            raise HlaError('no extension.json in {}'.format(path))
        with open(manifest) as f:
            hlas = [(n, e['entryPoint']) for n, e in
                    json.load(f).get('extensions', {}).items()
                    if e.get('type') == 'HighLevelAnalyzer']
        if not hlas:
            raise HlaError('{} has no HighLevelAnalyzer'.format(manifest))
        for ext_name, entry in hlas:
            if not name or name in (ext_name, entry.split('.')[-1]):
                break
        else:
            raise HlaError('no analyzer {!r} in {} (has: {})'.format(
                name, manifest, ', '.join(n for n, _ in hlas)))
        module_name, class_name = entry.rsplit('.', 1)
        module = import_file(os.path.join(path, module_name + '.py'))
        if not hasattr(module, class_name):
            raise HlaError('{} has no class {}'.format(module.__file__, class_name))
        return getattr(module, class_name)

    module = import_file(path)
    classes = [c for c in vars(module).values() if isinstance(c, type) and
               issubclass(c, HighLevelAnalyzer) and c is not HighLevelAnalyzer]
    if name:
        classes = [c for c in classes if c.__name__ == name]
    if not classes:
        raise HlaError('no HighLevelAnalyzer {}in {}'.format(
            repr(name) + ' ' if name else '', path))
    return classes[0]

def import_file(path):
    if not os.path.exists(path):
        raise HlaError('{} not found'.format(path))
    directory = os.path.dirname(os.path.abspath(path))
    # Extensions may import their own helper modules.
    if directory not in sys.path:
        sys.path.insert(0, directory)
    module_name = 'saleae_hla_ext_{}'.format(abs(hash(os.path.abspath(path))))
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def parse_settings(cls, text):
    '''"name=value; name2=value2" to the settings dict of an HLA class.'''
    settings = {}
    by_name = {s.name: s for s in cls._settings()}
    for item in filter(None, (i.strip() for i in text.split(';'))):
        name, sep, value = item.partition('=')
        name, value = name.strip(), value.strip()
        if not sep or name not in by_name:
            raise HlaError('unknown setting {!r} (settings: {})'.format(
                name, ', '.join(by_name) or 'none'))
        settings[name] = by_name[name].parse(value)
    return settings

class Decoder(srd.Decoder):
    api_version = 3
    id = 'saleae_hla'
    name = 'Saleae HLA'
    longname = 'Saleae Logic 2 High Level Analyzer'
    desc = 'Runs a Saleae Logic 2 High Level Analyzer extension.'
    license = 'gplv2+'
    inputs = ['uart', 'i2c', 'spi']
    outputs = []
    tags = ['Util']
    options = (
        {'id': 'extension', 'desc': 'Extension directory or .py file',
            'default': ''},
        {'id': 'analyzer', 'desc': 'Analyzer name (if the extension has several)',
            'default': ''},
        {'id': 'settings', 'desc': 'Settings (name=value; ...)', 'default': ''},
        {'id': 'uart_dir', 'desc': 'UART direction to analyze', 'default': 'RX',
            'values': ('RX', 'TX')},
        {'id': 'cs_polarity', 'desc': 'SPI CS# polarity', 'default': 'active-low',
            'values': ('active-low', 'active-high')},
    )
    annotations = (
        ('frame', 'HLA frame'),
        ('error', 'HLA error'),
    )
    annotation_rows = (
        ('frames', 'Frames', (Ann.FRAME,)),
        ('errors', 'Errors', (Ann.ERROR,)),
    )

    def __init__(self):
        self.reset()

    def reset(self):
        self.samplerate = None
        self.hla = None
        self.protocol = None
        self.failed = False
        self.pending = None      # I2C address/data byte waiting for its ACK
        self.uart_bits = {}      # UART data bits of the frame being received
        self.uart_error = {}
        self.spi_bits = 8

    def metadata(self, key, value):
        if key == srd.SRD_CONF_SAMPLERATE:
            self.samplerate = value

    def start(self):
        self.out_ann = self.register(srd.OUTPUT_ANN)
        self.t0 = SaleaeTime(datetime.now(timezone.utc))
        if not self.options['extension']:
            raise HlaError('set the "extension" option to a Logic 2 extension')
        cls = load_hla(self.options['extension'], self.options['analyzer'])
        self.hla = cls(parse_settings(cls, self.options['settings']))
        self.result_types = getattr(self.hla, 'result_types', {}) or {}

    def time(self, sample):
        if not self.samplerate:
            raise HlaError('the samplerate is needed to give frames a time')
        return self.t0 + _data.SaleaeTimeDelta(Fraction(sample, self.samplerate))

    def sample(self, time):
        return round((time - self.t0)._s * self.samplerate)

    def text(self, frame):
        data = frame.data or {}
        fmt = self.result_types.get(frame.type, {}).get('format')
        if not fmt:
            values = ', '.join('{}: {}'.format(k, format_value(v)) for k, v in data.items())
            return '{}: {}'.format(frame.type, values) if values else frame.type

        def field(match):
            key = (match.group(1) or match.group(2)).strip()
            if key == 'type':
                return frame.type
            if key.startswith('data.'):
                key = key[5:]
            return format_value(data.get(key, ''))
        # Logic 2 formats are Mustache-like: {{data.x}}, or {{{data.x}}}.
        return re.sub(r'\{\{\{(.*?)\}\}\}|\{\{(.*?)\}\}', field, fmt)

    def feed(self, ftype, ss, es, data=None):
        '''Pass one input frame to the HLA and put out what it returns.'''
        if self.failed:
            return
        frame = AnalyzerFrame(ftype, self.time(ss), self.time(es), data)
        try:
            result = self.hla.decode(frame)
        except Exception as e:
            # Report once, then stop feeding the extension.
            self.failed = True
            self.put(ss, es, self.out_ann, [Ann.ERROR,
                     ['{}: {}'.format(type(e).__name__, e), 'Error']])
            return
        if result is None:
            return
        for out in (result if isinstance(result, (list, tuple)) else [result]):
            # Annotation texts become C strings: a NUL would cut them off.
            text = self.text(out).replace('\0', '\\0')
            self.put(self.sample(out.start_time), self.sample(out.end_time),
                     self.out_ann, [Ann.FRAME, [text, out.type]])

    def detect(self, data):
        if len(data) == 2:
            return 'i2c'
        ptype = data[0]
        if ptype in UART_PTYPES or (ptype == 'DATA' and isinstance(data[2], tuple)):
            return 'uart'
        if ptype in SPI_PTYPES or ptype == 'DATA':
            return 'spi'
        return None

    def decode(self, ss, es, data):
        if self.protocol is None:
            self.protocol = self.detect(data)
            if self.protocol is None:
                return
        getattr(self, 'decode_' + self.protocol)(ss, es, data)

    # Async Serial: 'data' frames, with 'error' when the frame was invalid.
    def decode_uart(self, ss, es, data):
        ptype, rxtx, pdata = data
        if rxtx != (0 if self.options['uart_dir'] == 'RX' else 1):
            return
        if ptype == 'DATA':
            self.uart_bits[rxtx] = len(pdata[1])
        elif ptype == 'PARITY ERROR':
            self.uart_error[rxtx] = 'parity error'
        elif ptype == 'INVALID STOPBIT':
            self.uart_error.setdefault(rxtx, 'framing error')
        elif ptype == 'FRAME':
            value, valid = pdata
            fields = {'data': word_bytes(value, self.uart_bits.get(rxtx, 8))}
            error = self.uart_error.pop(rxtx, None)
            if not valid:
                fields['error'] = error or 'framing error'
            self.feed('data', ss, es, fields)

    # I2C: 'start', 'address' and 'data' (each with its ACK), 'stop'.
    def decode_i2c(self, ss, es, data):
        ptype, pdata = data
        if ptype in ('START', 'START REPEAT', 'STOP'):
            self.flush_i2c()
            self.feed('stop' if ptype == 'STOP' else 'start', ss, es)
        elif ptype in ('ADDRESS READ', 'ADDRESS WRITE'):
            self.flush_i2c()
            self.pending = ('address', ss, {'address': bytes([pdata & 0x7f]),
                                            'read': ptype == 'ADDRESS READ'})
        elif ptype in ('DATA READ', 'DATA WRITE'):
            self.flush_i2c()
            self.pending = ('data', ss, {'data': bytes([pdata])})
        elif ptype in ('ACK', 'NACK') and self.pending:
            ftype, pss, fields = self.pending
            self.pending = None
            fields['ack'] = ptype == 'ACK'
            self.feed(ftype, pss, es, fields)

    def flush_i2c(self):
        # A byte without its ACK/NACK bit (e.g. the capture ended).
        if self.pending:
            ftype, pss, fields = self.pending
            self.pending = None
            fields.update(ack=False, error='missing ACK')
            self.feed(ftype, pss, pss, fields)

    # SPI: 'enable'/'disable' on CS# changes, 'result' for every word.
    def decode_spi(self, ss, es, data):
        ptype, d1, d2 = data
        if ptype == 'CS-CHANGE':
            if d1 is None or d2 is None:
                return
            active = 0 if self.options['cs_polarity'] == 'active-low' else 1
            self.feed('enable' if d2 == active else 'disable', ss, es)
        elif ptype == 'BITS':
            bits = d1 if d1 is not None else d2
            self.spi_bits = len(bits) if bits else 8
        elif ptype == 'DATA':
            # Like Logic 2: no key for a data line that isn't connected.
            fields = {}
            if d1 is not None:
                fields['mosi'] = word_bytes(d1, self.spi_bits)
            if d2 is not None:
                fields['miso'] = word_bytes(d2, self.spi_bits)
            self.feed('result', ss, es, fields)
