"""The locales' public names: locale codes, trees and documents, placeholders, schemas and the
rules a translation must follow."""

from ..sub_domains import locale
from ..sub_domains.locale import *  # noqa: F403
from . import public

__all__ = public(locale)
