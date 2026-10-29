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
The High Level Analyzer classes of the Saleae Logic 2 extension API
(saleae.analyzers), written from Saleae's public documentation.
'''

__all__ = ['HighLevelAnalyzer', 'AnalyzerFrame', 'StringSetting',
           'NumberSetting', 'ChoicesSetting', 'ValidationError']


class ValidationError(RuntimeError):
    pass


class Setting:
    def __init__(self, *, label=None):
        self.label = label
        self.name = None

    def validate(self, value):
        pass

    def default(self):
        raise NotImplementedError

    def parse(self, text):
        '''Convert a setting given as text (sigrok option) to its value.'''
        return text


class StringSetting(Setting):
    '''A text input.'''

    def validate(self, value):
        if not isinstance(value, str):
            raise ValidationError(f'{self.name}: must be a string')

    def default(self):
        return ''


class NumberSetting(Setting):
    '''A numeric input, optionally limited to [min_value, max_value].'''

    def __init__(self, *, min_value=None, max_value=None, **kwargs):
        super().__init__(**kwargs)
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValidationError('min_value cannot be greater than max_value')
        self.min_value = min_value
        self.max_value = max_value

    def validate(self, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(f'{self.name}: must be a number')
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f'{self.name}: less than {self.min_value}')
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f'{self.name}: greater than {self.max_value}')

    def default(self):
        if self.min_value is not None and self.min_value > 0:
            return self.min_value
        if self.max_value is not None and self.max_value < 0:
            return self.max_value
        return 0

    def parse(self, text):
        value = float(text)
        return int(value) if value.is_integer() else value


class ChoicesSetting(Setting):
    '''A choice from a list of strings.'''

    def __init__(self, choices, **kwargs):
        super().__init__(**kwargs)
        for choice in choices:
            if not isinstance(choice, str):
                raise ValidationError('choices must be strings')
        self.choices = list(choices)

    def validate(self, value):
        if value not in self.choices:
            raise ValidationError(f'{self.name}: {value!r} is not one of {self.choices}')

    def default(self):
        return self.choices[0] if self.choices else ''


class _HighLevelAnalyzerMeta(type):
    # Logic 2 constructs an HLA as Class(settings): the settings are checked
    # and set as attributes, then __init__ runs without arguments.
    def __call__(cls, settings=None, *args, **kwargs):
        obj = cls.__new__(cls)
        for setting in cls._settings():
            if settings is None or setting.name not in settings:
                value = setting.default()
            else:
                value = settings[setting.name]
            setting.validate(value)
            setattr(obj, setting.name, value)
        obj.__init__(*args, **kwargs)
        return obj


class HighLevelAnalyzer(metaclass=_HighLevelAnalyzerMeta):
    '''Base class for HLAs: settings as class attributes, result_types, decode().'''

    result_types = {}

    @classmethod
    def _settings(cls):
        found = []
        for klass in reversed(cls.__mro__):
            for name, value in vars(klass).items():
                if isinstance(value, Setting):
                    value.name = name
                    if value.label is None:
                        value.label = ' '.join(w[:1].upper() + w[1:]
                                               for w in name.split('_') if w)
                    found = [s for s in found if s.name != name] + [value]
        return found

    def decode(self, frame):
        return None


class AnalyzerFrame:
    '''One frame: a type name, a time span and a data dictionary.'''

    def __init__(self, type, start_time, end_time, data=None):
        self.type = type
        self.start_time = start_time
        self.end_time = end_time
        self.data = data

    def __repr__(self):
        return (f'AnalyzerFrame({self.type!r}, {self.start_time!r}, '
                f'{self.end_time!r}, {self.data!r})')
