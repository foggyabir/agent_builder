import logging

class UtilBase:
    def __init__(self) -> None:
        self.logger = logging.getLogger(name=self.__class__.__name__)