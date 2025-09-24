from datetime import datetime


def logger():
    return f'[{__current_time()}:]\n'


def __current_time():
    return datetime.now().strftime("%Y.%m.%d %H:%M:%S.%f")[:-3]
