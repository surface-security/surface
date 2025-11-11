import json
import logging

from scanners import models, utils
from slackbot.base import MessageProcessor

logger = logging.getLogger(__name__)


class ScannersProcessor(MessageProcessor):
    def handle(self, message, user=None, channel=None, ts=None, raw=None):
        if channel and channel[0] == 'D' and 'scanners' in message.lower():
            if self.user_has_perm(user, 'scanners.check_scanners'):
                try:
                    out = utils.check_scanners(models.Rootbox.objects.filter(active=True))
                    for r in out:
                        self.post_message(
                            channel=channel, text=f'*{r[0]}*\n```{json.dumps(r[1], indent=4)}```', thread_ts=ts
                        )
                except Exception:
                    logging.exception('checking scanners on slack')
                    self.post_message(
                        channel=channel, text=':exclamation: an error occurred (and logged)', thread_ts=ts
                    )
            else:
                self.web.reactions_add(name='alert', channel=channel, timestamp=ts)
            return self.PROCESSED
