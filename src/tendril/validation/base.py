#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2016-2019 Chintalagiri Shashank
#
# This file is part of tendril.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Tendril Validation Base (:mod:`tendril.validation.base`)
========================================================
"""

from copy import copy
from colorama import Style
from colorama import Fore

from tendril.utils import terminal
from tendril.utils import log
logger = log.get_logger(__name__, log.DEFAULT)


class ValidatableBase(object):
    def __init__(self, vctx=None):
        self._validated = False
        self._validation_context = vctx or ValidationContext(self.__class__.__name__)
        self._validation_errors = ErrorCollector()

    @property
    def ident(self):
        return '<unidentifiable {0}>'.format(self.__class__.__name__)

    @ident.setter
    def ident(self, value):
        raise NotImplementedError

    def _validate(self):
        raise NotImplementedError

    def validate(self):
        if not self._validated:
            logger.debug("Validating {0}".format(self.ident))
            self._validate()

    @property
    def validation_errors(self):
        if not self._validated:
            self._validate()
        return self._validation_errors


class ValidationContext(object):
    def __init__(self, mod, locality=None):
        self.mod = mod
        self.locality = locality

    def __repr__(self):
        if self.locality:
            return '/'.join([self.mod, self.locality])
        else:
            return self.mod

    def render(self):
        if self.locality:
            return self.locality
        else:
            return self.mod

    def child(self, locality):
        if self.locality:
            locality = '/'.join([self.locality, locality])
        cctx = copy(self)
        cctx.locality = locality
        return cctx


class ValidationPolicy(object):
    def __init__(self, context, is_error=True):
        self.context = context
        self.is_error = is_error


class ValidationError(Exception):
    msg = "Validation Error"

    def __init__(self, policy):
        self._policy = policy
        self.detail = None

    @property
    def policy(self):
        return self._policy

    def render(self):
        return {
            'is_error': self.policy.is_error,
            'group': self.msg,
            'headline': self._policy.context.render(),
            'detail': self.detail,
        }

    def __str__(self):
        rd = self.render()
        return "{0}\n\t{1}\n\t{2}".format(
            rd['group'], rd['headline'], rd['detail']
        )


class ErrorCollector(ValidationError):
    def __init__(self):
        self._errors = []

    def add(self, e):
        if isinstance(e, ErrorCollector):
            for error in e.errors:
                self._errors.append(error)
        else:
            self._errors.append(e)

    @property
    def errors(self):
        return self._errors

    @property
    def terrors(self):
        return len(self._errors)

    @property
    def derrors(self):
        return [x for x in self._errors if x.policy.is_error]

    @property
    def dwarnings(self):
        return [x for x in self._errors if not x.policy.is_error]

    @property
    def nerrors(self):
        return len(self.derrors)

    @property
    def nwarnings(self):
        return len(self.dwarnings)

    @staticmethod
    def _group_errors(errors):
        rval = {}
        for error in errors:
            etype = error['group']
            if etype in rval.keys():
                rval[etype].append(error)
            else:
                rval[etype] = [error]
        return rval

    @property
    def errors_by_type(self):
        lerrors = [x.render() for x in self.derrors]
        return self._group_errors(lerrors)

    @property
    def warnings_by_type(self):
        lwarnings = [x.render() for x in self.dwarnings]
        return self._group_errors(lwarnings)

    def __repr__(self):
        rval = 'Collected Errors:\n'
        for e in self._errors:
            rval += '  {0}\n'.format(repr(e))
        return rval

    def _render_cli_group(self, g):
        for idx, i in enumerate(g):
            if 'detail_core' in i.keys():
                detail = i['detail_core']
            else:
                detail = i['detail']
            print("{0}.{1} : {2}"
                  "".format(idx + 1, i['headline'], detail))

    def render_cli(self, name):
        width = terminal.get_terminal_width()
        hline = '-' * width
        print(hline + Style.BRIGHT)
        titleformat = "{0:<" + str(width - 13) + "} {1:>2} {2}"
        print(titleformat.format(name, self.terrors, 'ALERTS') + Style.NORMAL)
        if self.nerrors:
            print(Fore.RED + hline)
            print(titleformat.format('', self.nerrors, 'ERRORS'))
            for n, g in self.errors_by_type.items():
                print(hline + Style.BRIGHT)
                print(titleformat.format(n, len(g), 'INSTANCES') + Style.NORMAL)
                self._render_cli_group(g)
        if self.nwarnings:
            print(Fore.YELLOW + hline)
            print(titleformat.format('', self.nwarnings, 'WARNINGS'))
            for n, g in self.warnings_by_type.items():
                print(hline + Style.BRIGHT)
                print(titleformat.format(n, len(g), 'INSTANCES') + Style.NORMAL)
                self._render_cli_group(g)
        print(Fore.RESET + Style.BRIGHT + hline + Style.NORMAL)
