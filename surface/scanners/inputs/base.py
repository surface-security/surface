__CACHE__ = {}
from abc import ABCMeta


CHOICES = []


class BaseInput(metaclass=ABCMeta):
    name = None
    label = None

    __CACHE__ = {}
    CHOICES = []

    @classmethod
    def __init_subclass__(cls):
        # register subclasses
        _n = cls.get_name()
        if _n in BaseInput.__CACHE__:
            raise ValueError('Duplicated function key', _n)
        BaseInput.__CACHE__[_n] = (cls.get_label(), cls)
        # need to use variable instead of @property so it can be referenced by model field choices
        # and still be modified *after*
        BaseInput.CHOICES.append((_n, cls.get_label()))
        return super().__init_subclass__()

    @classmethod
    def get_name(cls):
        return cls.name or f"{cls.__module__.split('.', 1)[0]}.{cls.__name__}"

    @classmethod
    def get_label(cls):
        return cls.label or cls.get_name()

    def generate(self):
        """
        only method required by each BaseInput subclass that should return a list (or iterator)
        default implementation returns empty input

        :return: empty list for non-existent/inputless scanners
        """
        return []


def query(key):
    return BaseInput.__CACHE__.get(key, (None, BaseInput))[1]
