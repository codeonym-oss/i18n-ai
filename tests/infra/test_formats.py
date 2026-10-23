"""The locale file formats: what is read, and a target written the way its source is."""

import json
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from i18n_ai.domain.exports.locale import KeyPath, SourceFile
from i18n_ai.infra.adapters.filesystem.formats import FORMATS, format_of, load_document
from i18n_ai.infra.adapters.filesystem.formats.arb_format import ArbFormat
from i18n_ai.infra.adapters.filesystem.formats.po_format import PoFormat
from i18n_ai.infra.adapters.filesystem.formats.xliff_format import XliffFormat
from i18n_ai.infra.adapters.filesystem.formats.yaml_format import YamlFormat

yaml = YamlFormat()
arb = ArbFormat()
po = PoFormat()

POT = """\
# The app's messages.
#, fuzzy
msgid ""
msgstr ""
"Project-Id-Version: app 1.0\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language: \\n"
"Content-Type: text/plain; charset=CHARSET\\n"
"Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;\\n"

#. The button that saves the profile
#: profile.py:3
msgid "Save"
msgstr ""

#: list.py:9
#, python-format
msgid "%(n)d file"
msgid_plural "%(n)d files"
msgstr[0] ""
msgstr[1] ""

msgctxt "month"
msgid "May"
msgstr ""

#~ msgid "Gone"
#~ msgstr "Parti"
"""

RU_FORMS = (
    "nplurals=4; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || "
    "n%100>14) ? 1 : n%10==0 || (n%10>=5 && n%10<=9) || (n%100>=11 && n%100<=14)? 2 : 3);"
)
# The three forms long-standing Russian catalogs have
RU_OLD_FORMS = (
    "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || "
    "n%100>=20) ? 1 : 2);"
)

RU = """\
msgid ""
msgstr ""
"Language: ru\\n"
"Plural-Forms: RU_FORMS\\n"

# Ours
msgid "Save"
msgstr "Сохранить"

msgid "%(n)d file"
msgid_plural "%(n)d files"
msgstr[0] "%(n)d файл"
msgstr[1] "%(n)d файла"
msgstr[2] "%(n)d файлов"
msgstr[3] "%(n)d файла"

#, fuzzy
msgctxt "month"
msgid "May"
msgstr "Мая"

msgid "Kept"
msgstr "Оставлен"
""".replace("RU_FORMS", RU_FORMS)

ARB = """\
{
    "@@locale": "en",
    "@@x-team": "web",
    "title": "Notes",
    "@title": {"description": "The app's name"},
    "count": "{n, plural, one{# note} other{# notes}}",
    "@count": {"placeholders": {"n": {"type": "int"}}}
}
"""

SOURCE = """\
# The shop's messages
shop:
  title: "Acme"   # shown in the tab
  empty: 'Nothing here'
  intro: |
    Welcome.
    Take a look.
  item_one: One item
  item_other: Many items
  limit: 0x10
  tags:
    - new
    - sale
"""


def source(tmp_path: Path, text: str, name: str = "en.yml", key: str | None = None) -> SourceFile:
    path = tmp_path / name
    path.write_bytes(text.encode())
    return SourceFile(PurePosixPath(name), path, None, root_key=key)


def translated(text: str) -> str:
    return f"<{text}>"


def test_yaml_is_read_as_plain_values(tmp_path: Path) -> None:
    content = yaml.read(source(tmp_path, SOURCE).path)

    assert content["shop"]["title"] == "Acme"
    assert type(content["shop"]["title"]) is str
    assert content["shop"]["intro"] == "Welcome.\nTake a look.\n"
    assert content["shop"]["limit"] == 16
    assert content["shop"]["tags"] == ["new", "sale"]


def test_yaml_1_2_keeps_no_a_key(tmp_path: Path) -> None:
    content = yaml.read(source(tmp_path, "no:\n  yes: Ja\n1: one\n").path)

    assert content == {"no": {"yes": "Ja"}, "1": "one"}


def test_a_target_keeps_the_source_comments_order_and_quoting(tmp_path: Path) -> None:
    like = source(tmp_path, SOURCE)
    content: dict[str, Any] = {
        "shop": {
            "title": "Acmé",
            "empty": "Rien ici",
            "intro": "Bienvenue.\nRegardez.\n",
            "item_one": "Un article",
            "item_many": "Beaucoup d'articles",
            "item_other": "Des articles",
            "limit": 16,
            "tags": ["nouveau", "soldes"],
        }
    }

    yaml.write(tmp_path / "fr.yml", content, like, None)

    assert (tmp_path / "fr.yml").read_text(encoding="utf-8") == (
        "# The shop's messages\n"
        "shop:\n"
        '  title: "Acmé"   # shown in the tab\n'
        "  empty: 'Rien ici'\n"
        "  intro: |\n"
        "    Bienvenue.\n"
        "    Regardez.\n"
        "  item_one: Un article\n"
        "  item_many: Beaucoup d'articles\n"
        "  item_other: Des articles\n"
        "  limit: 0x10\n"
        "  tags:\n"
        "    - nouveau\n"
        "    - soldes\n"
    )


def test_a_key_the_target_drops_is_gone(tmp_path: Path) -> None:
    like = source(tmp_path, "a: A\nb: B\n")

    yaml.write(tmp_path / "ja.yml", {"b": "ビー"}, like, None)

    assert (tmp_path / "ja.yml").read_text(encoding="utf-8") == "b: ビー\n"


def test_a_rooted_file_is_rooted_at_its_locale(tmp_path: Path) -> None:
    like = source(tmp_path, "# Rails' locales\n\nen:\n  hello: Hello\n", key="en")

    yaml.write(tmp_path / "fr.yml", {"hello": "Bonjour"}, like, "fr")

    assert (tmp_path / "fr.yml").read_text(
        encoding="utf-8"
    ) == "# Rails' locales\n\nfr:\n  hello: Bonjour\n"


def test_an_existing_target_keeps_its_other_keys(tmp_path: Path) -> None:
    like = source(tmp_path, "en:\n  hello: Hello\n", key="en")
    (tmp_path / "fr.yml").write_text("fr:\n  hello: Salut\nfr-CA:\n  hello: Allo\n")

    yaml.write(tmp_path / "fr.yml", {"hello": "Bonjour"}, like, "fr")

    assert (tmp_path / "fr.yml").read_text(
        encoding="utf-8"
    ) == "fr:\n  hello: Bonjour\nfr-CA:\n  hello: Allo\n"


def test_a_bundle_takes_the_new_locale_last(tmp_path: Path) -> None:
    like = source(tmp_path, "en:\n  hello: Hello # greeting\n", "i18n.yml", key="en")

    yaml.write(like.path, {"hello": "Hallo"}, like, "de")

    assert (
        like.path.read_text(encoding="utf-8")
        == "en:\n  hello: Hello # greeting\nde:\n  hello: Hallo # greeting\n"
    )


@pytest.mark.parametrize(
    ("text", "written"),
    [
        ("a:\n    b: B\n    c:\n    - x\n", "a:\n    b: <B>\n    c:\n    - <x>\n"),
        ("a:\n  c:\n    - x\n", "a:\n  c:\n    - <x>\n"),
        ("---\na: A\n", "---\na: <A>\n"),
    ],
)
def test_the_indent_and_the_start_are_kept(tmp_path: Path, text: str, written: str) -> None:
    like = source(tmp_path, text)
    content = _map(yaml.read(like.path), translated)

    yaml.write(tmp_path / "fr.yml", content, like, None)

    assert (tmp_path / "fr.yml").read_text(encoding="utf-8") == written


@pytest.mark.parametrize("name", ["en.json", "en.yml"])
def test_the_line_endings_are_kept(tmp_path: Path, name: str) -> None:
    text = '{\r\n  "a": "A"\r\n}\r\n' if name.endswith(".json") else "a: A\r\n"
    like = source(tmp_path, text, name)
    adapter = format_of(like.path)
    assert adapter is not None

    adapter.write(tmp_path / f"fr{like.path.suffix}", {"a": "B"}, like, None)

    written = (tmp_path / f"fr{like.path.suffix}").read_bytes()
    assert written.count(b"\r\n") == text.count("\r\n")
    assert b"\n" not in written.replace(b"\r\n", b"")


def test_invalid_yaml_says_why(tmp_path: Path) -> None:
    path = source(tmp_path, "a: [\n").path

    document, error = load_document(path, yaml)

    assert document is None
    assert error is not None
    assert error.startswith("not valid YAML: ")


def test_an_empty_file_is_no_document(tmp_path: Path) -> None:
    document, error = load_document(source(tmp_path, "").path, yaml)

    assert document is None
    assert error == "its top level is nothing, not an object"


def test_arb_is_read_without_its_metadata(tmp_path: Path) -> None:
    content = arb.read(source(tmp_path, ARB, "app_en.arb").path)

    assert content == {"title": "Notes", "count": "{n, plural, one{# note} other{# notes}}"}


def test_an_arb_description_is_its_messages_note(tmp_path: Path) -> None:
    path = source(tmp_path, ARB, "app_en.arb").path

    document, _ = load_document(path, arb)

    assert document is not None
    assert document.notes == {KeyPath(("title",)): "The app's name"}


def test_an_arb_target_names_its_locale_and_keeps_its_own_metadata(tmp_path: Path) -> None:
    like = source(tmp_path, ARB, "app_en.arb")
    target = tmp_path / "app_fr.arb"
    target.write_text('{"@@locale": "fr", "title": "Old", "@title": {"description": "Le nom"}}')

    arb.write(target, {"title": "Notes", "count": "{n, plural, other{# notes}}"}, like, None, "fr")

    written = json.loads(target.read_text(encoding="utf-8"))
    assert list(written) == ["@@locale", "@@x-team", "title", "@title", "count"]
    assert written["@@locale"] == "fr"
    assert written["@title"] == {"description": "Le nom"}  # its own, not the source's
    assert target.read_text(encoding="utf-8").startswith('{\n    "@@locale"')  # the source's indent


def test_an_arb_target_without_locale_in_its_source_gets_none(tmp_path: Path) -> None:
    like = source(tmp_path, '{"a": "A"}', "app_en.arb")

    arb.write(tmp_path / "app_de.arb", {"a": "Ah"}, like, None, "de")

    assert json.loads((tmp_path / "app_de.arb").read_text(encoding="utf-8")) == {"a": "Ah"}


def test_a_po_source_is_its_msgids(tmp_path: Path) -> None:
    content = po.read(source(tmp_path, POT, "app.pot").path, source=True)

    assert content == {
        "Save": "Save",
        "%(n)d file": {"one": "%(n)d file", "other": "%(n)d files"},
        "month\x04May": "May",
    }


def test_a_po_translation_is_its_msgstrs(tmp_path: Path) -> None:
    path = source(tmp_path, RU, "ru.po").path

    assert po.read(path) == {
        "Save": "Сохранить",
        "%(n)d file": {
            "one": "%(n)d файл",
            "few": "%(n)d файла",
            "many": "%(n)d файлов",
            "other": "%(n)d файла",
        },
        "Kept": "Оставлен",
    }  # the fuzzy one is not a translation


def test_a_po_translation_keeps_its_own_numbering_of_forms(tmp_path: Path) -> None:
    text = RU.replace(RU_FORMS, RU_OLD_FORMS).replace('msgstr[3] "%(n)d файла"\n', "")
    path = source(tmp_path, text, "ru.po").path

    assert po.read(path)["%(n)d file"] == {
        "one": "%(n)d файл",
        "few": "%(n)d файла",
        "many": "%(n)d файлов",
    }


def test_po_plurals_numbered_unreadably_are_not_read(tmp_path: Path) -> None:
    text = RU.replace(RU_FORMS, "nplurals=4; plural=(n ? ;")

    assert "%(n)d file" not in po.read(source(tmp_path, text, "ru.po").path)


def test_po_notes_are_the_comments_and_the_context(tmp_path: Path) -> None:
    assert po.notes(source(tmp_path, POT, "app.pot").path) == {
        KeyPath(("Save",)): "The button that saves the profile",
        KeyPath(("month\x04May",)): "context: month",
    }


def test_a_new_po_translation_is_the_template_filled(tmp_path: Path) -> None:
    like = source(tmp_path, POT, "app.pot")
    content = {
        "Save": "حفظ",
        "%(n)d file": {c: f"{c} %(n)d" for c in ("zero", "one", "two", "few", "many", "other")},
        "month\x04May": "مايو",
    }

    po.write(tmp_path / "ar.po", content, like, None, "ar")

    written = (tmp_path / "ar.po").read_text(encoding="utf-8")
    assert written.startswith("# The app's messages.\nmsgid")  # no longer fuzzy
    assert '"Last-Translator: i18n-ai\\n"' in written
    assert '"Language-Team: Arabic\\n"' in written
    assert '"Language: ar\\n"' in written
    assert '"Plural-Forms: nplurals=6; plural=' in written
    assert "charset=UTF-8" in written
    assert (
        '#. The button that saves the profile\n#: profile.py:3\nmsgid "Save"\nmsgstr "حفظ"'
        in written
    )
    assert 'msgstr[0] "zero %(n)d"\n' in written
    assert 'msgstr[5] "other %(n)d"\n' in written
    assert 'msgctxt "month"\nmsgid "May"\nmsgstr "مايو"' in written
    assert po.read(tmp_path / "ar.po")["%(n)d file"]["few"] == "few %(n)d"


def test_an_existing_po_translation_keeps_its_own(tmp_path: Path) -> None:
    like = source(tmp_path, POT, "app.pot")
    target = source(tmp_path, RU, "ru.po").path

    po.write(target, {"Save": "Сохранить", "month\x04May": "мая"}, like, None, "ru")

    written = target.read_text(encoding="utf-8")
    assert "plural=(n%10==1" in written  # its own Plural-Forms
    assert '# Ours\nmsgid "Save"' in written
    assert 'msgid "Kept"\nmsgstr "Оставлен"' in written
    assert '"PO-Revision-Date: ' in written
    assert "fuzzy" not in written
    assert 'msgstr "мая"' in written


def test_an_existing_po_translation_is_written_in_its_own_forms(tmp_path: Path) -> None:
    like = source(tmp_path, POT, "app.pot")
    text = RU.replace(RU_FORMS, RU_OLD_FORMS).replace('msgstr[3] "%(n)d файла"\n', "")
    target = source(tmp_path, text, "ru.po").path
    forms = {"one": "один", "few": "несколько", "many": "много", "other": "дробь"}

    po.write(target, {"%(n)d file": forms}, like, None, "ru")

    written = target.read_text(encoding="utf-8")
    assert RU_OLD_FORMS.split(";")[0] in written  # nplurals=3, kept
    assert 'msgstr[0] "один"\nmsgstr[1] "несколько"\nmsgstr[2] "много"\n' in written
    assert "msgstr[3]" not in written


def test_invalid_po_says_why(tmp_path: Path) -> None:
    document, error = load_document(source(tmp_path, 'msgid "a"\nmsgstr\n', "en.po").path, po)

    assert document is None
    assert error is not None
    assert error.startswith("not valid PO: ")


xliff = XliffFormat()
# A machine's translation, for review
REVIEW = '<target state="needs-review-translation" state-qualifier="mt-suggestion">'

HI = (
    'Hi <ph id="0" disp="{{ name }}"/>, see <pc id="1" dispStart="&lt;a&gt;" dispEnd="&lt;/a&gt;">'
    'the <pc id="2">news</pc></pc> &amp; more.'
)
XLIFF_2 = f"""<?xml version='1.0' encoding='utf-8'?>
<xliff xmlns="urn:oasis:names:tc:xliff:document:2.0" version="2.0" srcLang="en">
  <!-- exported -->
  <file id="f">
    <unit id="hi" name="home.hi">
      <notes>
        <note category="description">On the home page</note>
        <note category="location">home.html:3</note>
      </notes>
      <segment>
        <source>{HI}</source>
      </segment>
    </unit>
    <unit id="two">
      <segment id="a"><source>One.</source><target>Un.</target></segment>
      <segment id="b" state="initial"><source>Two.</source><target>Two.</target></segment>
    </unit>
    <unit id="code" translate="no"><segment><source>x</source></segment></unit>
  </file>
</xliff>
"""


def test_an_xliff_source_gives_its_tags_as_numbered_tags(tmp_path: Path) -> None:
    path = source(tmp_path, XLIFF_2, "messages.xlf").path

    assert xliff.read(path, source=True) == {
        "hi": "Hi <x1/>, see <g2>the <g3>news</g3></g2> & more.",
        "two#a": "Un.",  # a source locale's own text
        "two#b": "Two.",
    }
    assert xliff.read(path) == {"two#a": "Un."}  # an initial target is no translation
    assert xliff.notes(path) == {
        KeyPath(("hi",)): (
            "key: home.hi; description: On the home page; "
            "tags: <x1/> is {{ name }}, <g2>…</g2> is <a>…</a>"
        )
    }


def test_an_xliff_target_puts_the_tags_back_wherever_they_went(tmp_path: Path) -> None:
    like = source(tmp_path, XLIFF_2, "messages.xlf")
    target = tmp_path / "messages.fr.xlf"

    xliff.write(
        target,
        {"hi": "<g2><g3>Nouvelles</g3> & <g9>co</g9></g2> pour <x1/> </g2> <x2/>", "two#a": "Un."},
        like,
        None,
        "fr",
    )

    written = target.read_text(encoding="utf-8")
    assert written.startswith("<?xml version='1.0' encoding=\"UTF-8\"?>\n<xliff")
    assert 'srcLang="en" trgLang="fr"' in written
    assert "<!-- exported -->" in written
    assert (
        '<segment state="translated" subState="i18n-ai:mt">\n'
        '        <source>Hi <ph id="0" disp="{{ name }}"/>, see'
    ) in written
    assert (
        '<target><pc id="1" dispStart="&lt;a&gt;" dispEnd="&lt;/a&gt;"><pc id="2">Nouvelles</pc>'
        ' &amp; &lt;g9&gt;co&lt;/g9&gt;</pc> pour <ph id="0" disp="{{ name }}"/> &lt;/g2&gt; '
        "&lt;x2/&gt;</target>"
    ) in written
    assert '<segment id="b"><source>Two.</source></segment>' in written  # its target was English
    assert xliff.read(target) == {
        "hi": "<g2><g3>Nouvelles</g3> & <g9>co</g9></g2> pour <x1/> </g2> <x2/>",
        "two#a": "Un.",
    }


XLIFF_1 = """<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file original="a.html" source-language="en"><body>
    <trans-unit id="1"><source>A</source></trans-unit>
    <trans-unit id="2"><source>B</source><seg-source>B</seg-source></trans-unit>
  </body></file>
  <file original="b.html" source-language="en"><body>
    <trans-unit id="1"><source>C</source></trans-unit>
  </body></file>
</xliff>
"""


def test_an_existing_xliff_target_keeps_its_own_and_gets_the_new_units(tmp_path: Path) -> None:
    like = source(tmp_path, XLIFF_1, "messages.xlf")
    target = tmp_path / "messages.de.xlf"
    target.write_bytes(
        XLIFF_1.replace(
            "<source>A</source>",
            '<source>Old A</source><target state="final">Ä</target><note>kept</note>',
        )
        .replace(
            '    <trans-unit id="2">',
            '    <trans-unit id="0"><source>Z</source></trans-unit>\n    <trans-unit id="2">',
        )
        .replace("<source>C</source>", "<source>Y</source>")
        .replace('trans-unit id="1"><source>Y', 'trans-unit id="9"><source>Y')
        .replace("\n", "\r\n")
        .encode()
    )
    assert xliff.read(target) == {"a.html/1": "Ä"}

    xliff.write(target, {"a.html/1": "Ä", "a.html/2": "Bb", "b.html/1": "Cc"}, like, None, "de")

    written = target.read_bytes().decode()
    assert "\r\n" in written
    assert written.startswith("<xliff")
    assert '<source>Old A</source><target state="final">Ä</target><note>kept</note>' in written
    assert (
        "<seg-source>B</seg-source>\r\n    " + REVIEW + "Bb</target>" not in written
    )  # one line: its unit was
    assert "<source>B</source><seg-source>B</seg-source>" + REVIEW + "Bb</target>" in written
    assert xliff.read(target)["a.html/2"] == "Bb"  # a translation to review is one
    assert (
        '<body>\r\n    <trans-unit id="1"><source>C</source>' + REVIEW + "Cc</target>"
        '</trans-unit>\r\n    <trans-unit id="9">'
    ) in written
    assert written.count('target-language="de"') == 2
    assert written.index('id="0"') < written.index('id="2"')


def test_a_file_that_is_not_xliff_says_why(tmp_path: Path) -> None:
    for text, why in (("<html/>", "its root is <html>"), ("<xliff>", "not valid XLIFF: ")):
        document, error = load_document(source(tmp_path, text, "en.xlf").path, xliff)

        assert document is None
        assert error is not None
        assert why in error


def test_formats_by_extension() -> None:
    assert format_of(Path("a.YAML")) is FORMATS[yaml.format]
    assert format_of(Path("a.json")) is not None
    assert format_of(Path("app_en.arb")) is FORMATS[arb.format]
    assert format_of(Path("django.po")) is format_of(Path("messages.POT")) is FORMATS[po.format]
    assert format_of(Path("messages.fr.XLIFF")) is FORMATS[xliff.format]
    assert format_of(Path("a.properties")) is None


def _map(node: Any, change: Any) -> Any:
    if isinstance(node, dict):
        return {key: _map(value, change) for key, value in node.items()}
    if isinstance(node, list):
        return [_map(item, change) for item in node]
    return change(node) if isinstance(node, str) else node
