from slowapi import Limiter
from slowapi.util import get_remote_address

from quiz_clash.services.fake_quiz import FAKE_QUIZ

limiter = Limiter(key_func=get_remote_address, enabled=not FAKE_QUIZ)
