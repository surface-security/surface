import os
from abc import ABCMeta


class BaseParser(metaclass=ABCMeta):
    name = None
    label = None

    __CACHE__ = {}
    CHOICES = []

    @classmethod
    def __init_subclass__(cls):
        # register subclasses
        _n = cls.get_name()
        if _n in BaseParser.__CACHE__:
            raise ValueError('Duplicated function key', _n)
        BaseParser.__CACHE__[_n] = (cls.get_label(), cls)
        # need to use variable instead of @property so it can be referenced by model field choices
        # and still be modified *after*
        BaseParser.CHOICES.append((_n, cls.get_label()))
        return super().__init_subclass__()

    @classmethod
    def get_name(cls):
        return cls.name or f"{cls.__module__.split('.', 1)[0]}.{cls.__name__}"

    @classmethod
    def get_label(cls):
        return cls.label or cls.get_name()

    def __init__(self, rootbox, scanner, timestamp, filepath):
        self.scanner = scanner
        self.rootbox = rootbox
        self.timestamp = timestamp
        self.filepath = filepath
        self.parse(self.rootbox, self.scanner, self.timestamp, self.filepath)
        self.__raw_results()

    def parse(self, rootbox, scanner, timestamp, filepath):
        """
        Parse the scanner results with the scanner parser
        default behavior does nothing so results are simply stored in RawResults
        """

    def __raw_results(self):
        """
        handler for raw results
        :return:
        """
        for _sf in os.listdir(self.filepath):
            target = os.path.join(self.filepath, _sf)
            if os.path.isfile(target):
                self.save_results(_sf, target)
            # :hammer!! support for baseline_browser results organised in folders, can be improved!
            elif os.path.isdir(target):
                for _file in os.listdir(target):
                    self.save_results(_file, os.path.join(target, _file))

    def save_results(self, name, file_src):
        from scanners import models

        with open(file_src) as f:
            models.RawResult(file_name=name, rootbox=self.rootbox, scanner=self.scanner, raw_results=f.read()).save()


def query(key):
    return BaseParser.__CACHE__.get(key, (None, BaseParser))[1]
