import config
from gui import MainWindow
from sent_log import SentLog
from sms_sender import ApiSmsPlSender, MockSmsSender


def build_sender():
    if config.API_SMS_PL_KEY:
        return ApiSmsPlSender(config.API_SMS_PL_KEY, config.API_SMS_PL_SENDER)
    return MockSmsSender()


def main():
    sender = build_sender()
    is_mock = isinstance(sender, MockSmsSender)
    sent_log = SentLog()
    window = MainWindow(sender=sender, sent_log=sent_log, is_mock=is_mock)
    window.mainloop()


if __name__ == "__main__":
    main()
