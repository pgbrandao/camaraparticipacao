from django.conf import settings

def get_api_params(initial_date, final_date):
    return 'initial_date={}&final_date={}'.format(
        initial_date.strftime(settings.STRFTIME_SHORT_DATE_FORMAT),
        final_date.strftime(settings.STRFTIME_SHORT_DATE_FORMAT)
    )
