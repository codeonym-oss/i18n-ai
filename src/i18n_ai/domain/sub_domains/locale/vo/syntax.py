from enum import StrEnum


class MessageSyntax(StrEnum):
    """What a tree's messages mean beyond the placeholders every library shares.

    - `standard`: as i18n-ai reads every tree.
    - `laravel`: Laravel's JSON locales, whose keys are the source text, whose placeholders are
      `:name`, and whose `trans_choice` plurals are pipes: `one apple|many apples`."""

    STANDARD = "standard"
    LARAVEL = "laravel"
