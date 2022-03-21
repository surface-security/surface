from django.db.models import Aggregate, CharField


class GroupConcat(Aggregate):
    """
    aggregate function to use GROUP_CONCAT for mysql (src: https://stackoverflow.com/a/40478702)
    hacked to seamlessly support both MySQL (GROUP_CONCAT) and PostgreSQL (ARRAY_AGG)

    for PostgreSQL, it will convert the array field to string, so the output is the same as GROUP_CONCAT.
    Using array_to_string(ARRAY_AGG) instead of STRING_AGG due to type conversion.
    Those that want to leverage ARRAYFIELD, just use https://docs.djangoproject.com/en/4.0/ref/contrib/postgres/aggregates/#arrayagg
    """

    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s%(ordering)s%(separator)s)'

    def __init__(self, expression, distinct=False, ordering=None, separator=',', **extra):
        # save for `as_postgresql`
        self._separator = separator
        super().__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            ordering=' ORDER BY %s' % ordering if ordering is not None else '',
            separator=' SEPARATOR "%s"' % separator,
            output_field=CharField(),
            **extra,
        )

    def as_postgresql(self, compiler, connection):
        '''
        function = 'ARRAY_AGG'
        template = '%(function)s(%(distinct)s%(expressions)s %(ordering)s)'
        allow_distinct = True
        '''
        self.template = f"array_to_string(%(function)s(%(distinct)s%(expressions)s %(ordering)s),'{self._separator}')"
        return super().as_sql(compiler, connection, function='ARRAY_AGG')
