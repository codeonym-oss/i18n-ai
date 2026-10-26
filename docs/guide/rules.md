# The rules

Every translation is checked before it is written. One that breaks a rule is **rejected**, and
sent back to the model with the problem, until it passes or runs out of attempts
(`--max-attempts`, 3 by default). One that bends a rule is **kept, with a warning**.

## Rejected

A translation is rejected when it:

- is empty or missing;
- loses, adds or alters a placeholder, counted as often as it appears;
- breaks ICU MessageFormat, drops a plural's explicit selector (`=0`), changes a select's options,
  or changes the placeholders inside a plural's or select's branches;
- hides an argument behind an ICU apostrophe (`l'{count}`); the model is told to write `’`;
- in Laravel's locales, gives a pipe plural another number of forms than the target's
  (`pipe-forms`), or changes the ranges of its forms (`pipe-ranges`).

The placeholders it knows:

| Syntax | Used by |
|---|---|
| `{{name}}`, `{{count, number}}` | i18next, Vue, Angular, Handlebars |
| `{name}`, `{n, number}`, `{n, plural, …}`, `{x, select, …}` | ICU MessageFormat (FormatJS, next-intl), vue-i18n |
| `%{name}` | Rails, Polyglot |
| `%s`, `%d`, `%1$s`, `%(name)s` | printf |
| `$t(key)` | i18next nesting |
| `@:key`, `@.lower:key` | vue-i18n linked messages |
| `<b>`, `</b>`, `<0/>`, `<br/>` | HTML and component tags (Trans, rich text) |
| `<x1/>`, `<g2>…</g2>` | XLIFF's inline elements, as i18n-ai numbers them |
| `:name`, `:Name`, `:NAME` | Laravel, in its own locales only; the case may change |

## Kept, with a warning

- An ICU plural lacks some of the target's plural categories.
- A message is left as in the source (a brand name, `OK`).

## Plurals

A plural family takes the **target's** CLDR categories. i18next's `item_one` and `item_other`
become six keys in Arabic (`item_zero` … `item_many`, `item_other`) and one in Japanese
(`item_other`). So does a nested family, Rails' `item: {one: …, other: …}`: an object whose keys
are all plural categories, `other` among them. Its `zero` is kept in every language, since Rails
shows it for a count of 0. Rails itself reads only `zero`, `one` and `other`; the other forms
(Arabic's `two`, `few`, `many`) are read when the app has the
[rails-i18n](https://github.com/svenfuchs/rails-i18n) gem's plural rules, which it turns on by
default. A category the source lacks is translated from its `other` form. A form
may show the count or not: Russian's `one` is also 21, so it needs `{{count}}` (or `%{count}`)
where English's does not.

A Laravel pipe plural (`one apple|:count apples`) is one message whose forms the target's are:
as many as Laravel's own table gives the language, each told to the model by the counts it is
for. Its placeholders are compared over the whole message: each of the source's is in one form
or more, and none is new. See [Your framework](frameworks.md#laravel).

## Whitespace

Leading and trailing whitespace is copied from the source, whatever the model answers.

## When a message never passes

It keeps its source text, so that its document is whole, and is listed at the end. Such a file is
**partial**. With `--strict`, a partial file is not written at all, and the run exits with 1.

The run also records it in `.i18n-ai-fallbacks.json`, in the directory the targets are written
to: the file, the message's key, the rules it broke and the model's last answer. The next run
translates a recorded message again, rather than keeping its source text as a translation, and
takes it off the record once it passes. Commit the record with your locales, so that every clone
and CI run knows which messages are still in their source text. A tree with no fallbacks left has
no record.

Messages that fell back before the record existed are not in it: `--overwrite` translates them
again.

## Existing translations

A target's existing translation is kept when it passes the same rules, and is not sent to the
model. A broken one, such as a French `{{nom}}` for `{{name}}`, is translated again.
