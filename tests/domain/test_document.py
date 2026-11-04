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


def test_with_value_sets_a_nested_key_an_array_item_and_a_plural_form() -> None:
    document = LocaleDocument(
        {"auth": {"title": "Login"}, "steps": ["Un", "Two"], "cart": {"item_one": "Ein"}}
    )

    changed = (
        document.with_value(KeyPath(("auth", "title")), "Connexion")
        .with_value(KeyPath(("steps", 1)), "Deux")
        .with_value(KeyPath(("cart", "item_few")), "Kilka")
    )

    assert changed.content == {
        "auth": {"title": "Connexion"},
        "steps": ["Un", "Deux"],
        "cart": {"item_one": "Ein", "item_few": "Kilka"},
    }


def test_with_value_leaves_the_document_as_it_was() -> None:
    document = LocaleDocument({"auth": {"title": "Login"}})

    document.with_value(KeyPath(("auth", "title")), "Connexion")

    assert document.content == {"auth": {"title": "Login"}}
