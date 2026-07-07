import config
from gui import MainWindow
from sent_log import SentLog
from sms_sender import HostedSmsSender, MockSmsSender


def build_sender():
    if config.HOSTEDSMS_EMAIL and config.HOSTEDSMS_PASSWORD:
        return HostedSmsSender(config.HOSTEDSMS_EMAIL, config.HOSTEDSMS_PASSWORD, config.HOSTEDSMS_SENDER)
    return MockSmsSender()


def main():
    sender = build_sender()
    is_mock = isinstance(sender, MockSmsSender)
    sent_log = SentLog()
    window = MainWindow(sender=sender, sent_log=sent_log, is_mock=is_mock)
    window.mainloop()


if __name__ == "__main__":
    main()
