import logging
import sys
import tenacity

from django.apps import apps

# Models need to be imported like this in order to avoid cyclic import issues with celery
def get_model(model_name):
    return apps.get_model(app_label='app', model_name=model_name)

logging.basicConfig(stream=sys.stderr, level=logging.ERROR)

logger = logging.getLogger(__name__)

TENACITY_ARGUMENTS = {
    'reraise': True,
    'wait': tenacity.wait_exponential(multiplier=60, max=600),
    'before_sleep': tenacity.before_sleep_log(logger, logging.ERROR, exc_info=True)
}
TENACITY_ARGUMENTS_FAST = {
    'reraise': True,
    'stop': tenacity.stop_after_attempt(5),
    'wait': tenacity.wait_exponential(multiplier=30),
    'before_sleep': tenacity.before_sleep_log(logger, logging.ERROR, exc_info=True)
}
def batch_qs(qs, batch_size=1000):
    """
    Returns a (start, end, total, queryset) tuple for each batch in the given
    queryset. Useful when memory is an issue. Picked from djangosnippets.
    """
    total = qs.count()

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield (start, end, total, qs[start:end])
