from django.contrib.admin.sites import site
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone


def _clean_field(fieldname):
    # For things like ('time', DateRangeFilter)
    if isinstance(fieldname, tuple):
        fieldname = fieldname[0]
    # Custom field... we will just skip them...
    if not isinstance(fieldname, str):
        return None
    # Remove = from fields
    if fieldname[0] == "=":
        fieldname = fieldname[1:]
    return fieldname


def _method_factory(model_class, model_admin):
    def method_tester(test_case: TestCase):
        # Test the filters and searchfields
        for fieldname in list(model_admin.list_filter) + list(model_admin.search_fields):
            fieldname = _clean_field(fieldname)
            if not fieldname:
                continue
            try:
                try:
                    # validate that filter can be executed for fieldname, don't care about result
                    test_case.assertIsInstance(model_class.objects.filter(**{fieldname: "1"}).count(), int)
                except ValidationError:
                    # Datetime fields?
                    test_case.assertIsInstance(
                        model_class.objects.filter(**{fieldname: timezone.now()}).count(),
                        int,
                    )
            except Exception as e:
                test_case.fail(f"{model_admin} search field test failed - {e}")

    return method_tester


class AdminMeta(type):
    def __init__(cls, *args, **kwargs):
        for model_class, model_admin in site._registry.items():
            setattr(
                cls,
                f'test_{str(model_admin).replace(".", "_")}',
                _method_factory(model_class, model_admin),
            )


class Test(TestCase, metaclass=AdminMeta):
    """
    ## Context

    Metaclass and dynamic test method generation is bad (in principle) for lack of test clarity.
    In this case, dynamic was already in place within a single method which prevent proper test result output:
    * print would always show up
    * if we remove print, when method failed we didn't know which model_admin was bad

    Creating a method per model_admin allows result output to be controlled by the testrunner (verbosity 1 displays only dots,
    2 will display each model_admin as method) and parseable by test result tools
    """

    pass
