from i18n_ai.domain.exports.locale import KeyPath, LocaleDocument


def test_without_drops_the_messages_at_the_paths() -> None:
    document = LocaleDocument(
        {"auth": {"title": "Connexion", "locked": "Locked"}, "steps": ["Un", "Two", "Trois"]}
    )

    dropped = document.without([KeyPath(("auth", "locked")), KeyPath(("steps", 1))])

    assert dropped.content == {"auth": {"title": "Connexion"}, "steps": ["Un", None, "Trois"]}


def test_without_ignores_a_path_that_is_not_there() -> None:
    document = LocaleDocument({"title": "Connexion"})

    dropped = document.without([KeyPath(("missing", "deep")), KeyPath(("title", 0))])

    assert dropped.content == {"title": "Connexion"}


def test_without_leaves_the_document_as_it_was() -> None:
    document = LocaleDocument({"auth": {"locked": "Locked"}})

    document.without([KeyPath(("auth", "locked"))])

    assert document.content == {"auth": {"locked": "Locked"}}
