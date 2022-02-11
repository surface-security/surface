from django.db.models import Aggregate, CharField


class GroupConcat(Aggregate):
    """
    aggregate function to use GROUP_CONCAT (mysql)
    source: https://stackoverflow.com/a/40478702
    """

    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s%(ordering)s%(separator)s)'

    def __init__(self, expression, distinct=False, ordering=None, separator=',', **extra):
        super().__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            ordering=' ORDER BY %s' % ordering if ordering is not None else '',
            separator=' SEPARATOR "%s"' % separator,
            output_field=CharField(),
            **extra,
        )
