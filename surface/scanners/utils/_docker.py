from datetime import datetime

import docker


class ContainerApiMonkeyMixin:
    @docker.utils.check_resource('container')
    def logs(
        self,
        container,
        stdout=True,
        stderr=True,
        stream=False,
        timestamps=False,
        tail='all',
        since=None,
        follow=None,
        until=None,
    ):
        """
        copy from docker.api.container.ContainerApiMixin.logs()
        only to patch `since=` datetime conversion...
        https://github.com/docker/docker-py/issues/2825

        TODO: would be nice to support extract stream type from multiplexer
        docker-py currently ignored skips that byte and does not return it anywhere
        when parsing the logs/stream
        """
        if follow is None:
            follow = stream
        params = {
            'stderr': stderr and 1 or 0,
            'stdout': stdout and 1 or 0,
            'timestamps': timestamps and 1 or 0,
            'follow': follow and 1 or 0,
        }
        if tail != 'all' and (not isinstance(tail, int) or tail < 0):
            tail = 'all'
        params['tail'] = tail

        if since is not None:
            if isinstance(since, datetime):
                # DA PATCH DA MONKEY MADE
                # datetime.timestamp() already (py3.3+) provides timestamp
                # (with microseconds) in UTC, no need for docker.utils
                params['since'] = since.timestamp()
            elif isinstance(since, (int, float)) and since > 0:
                params['since'] = since
            else:
                raise docker.errors.InvalidArgument(
                    'since value should be datetime or positive int, ' 'not {}'.format(type(since))
                )

        if until is not None:
            if docker.utils.version_lt(self._version, '1.35'):
                raise docker.errors.InvalidVersion('until is not supported for API version < 1.35')
            if isinstance(until, datetime):
                # DA PATCH DA MONKEY MADE
                params['until'] = until.timestamp()
            elif isinstance(until, int) and until > 0:
                params['until'] = until
            else:
                raise docker.errors.InvalidArgument(
                    'until value should be datetime or positive int, ' 'not {}'.format(type(until))
                )

        url = self._url("/containers/{0}/logs", container)
        res = self._get(url, params=params, stream=stream)
        output = self._get_result(container, stream, res)

        if stream:
            return docker.types.CancellableStream(output, res)
        else:
            return output


class OurDockerClient(docker.DockerClient):
    def __init__(self, *a, **b):
        # hardcoded API version to avoid the implicit request for version detection
        # also, version detection is done during __init__ so it fails due to the "trust_env"
        # issue mentioned below...
        # adjust if required (older dockerd or newer methods required)
        if 'version' not in b:
            b['version'] = '1.41'

        self.api = OurAPIClient(*a, **b)
        # workaround for stupid requests.Session() bug
        # to be removed once this (or similar fix) is applied https://github.com/psf/requests/pull/5210
        # more history:
        # https://github.com/psf/requests/issues/5209
        # https://github.com/docker/docker-py/issues/2433
        # we don't really care about env for docker client (at the moment)
        self.api.trust_env = False


class OurAPIClient(ContainerApiMonkeyMixin, docker.api.APIClient):
    pass
