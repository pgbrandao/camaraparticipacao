from django.conf import settings
from calendar import monthrange
def get_api_params(initial_date, final_date):
    return 'initial_date={}&final_date={}'.format(
        initial_date.strftime(settings.STRFTIME_SHORT_DATE_FORMAT),
        final_date.strftime(settings.STRFTIME_SHORT_DATE_FORMAT)
    )

def period_humanized(initial_date, final_date):
    if  initial_date.year == final_date.year and \
        initial_date.month == final_date.month and \
        initial_date.day == 1 and \
        final_date.day == monthrange(final_date.year, final_date.month)[1]:
        return initial_date.strftime('%B %Y')
    elif initial_date.year == final_date.year and \
        initial_date.month == 1 and final_date.month == 12 and \
        initial_date.day == 1 and final_date.year == 31:
        return initial_date.strftime('%Y')
    else:
        return '{}-{}'.format(
            initial_date.strftime(settings.STRFTIME_SHORT_DATE_FORMAT),
            final_date.strftime(settings.STRFTIME_SHORT_DATE_FORMAT)
        )
