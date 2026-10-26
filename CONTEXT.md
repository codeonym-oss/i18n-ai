# i18n-ai

i18n-ai generates the locales of a website from the one its authors write, the source, with LLM
agents whose every message is checked before it is written.

## Locales

**Locale**:
A language, and maybe a region or script, as a tree names it: `en`, `pt-BR`, `zh_Hant`. Two codes
that differ only in case or separator are the same locale; an existing one keeps its spelling.
_Avoid_: language (for a locale), lang

**Source locale**:
The locale the others are generated from: the one asked for, else `en`, else the only one.
_Avoid_: default locale, base, reference

**Target locale**:
A locale being generated.
_Avoid_: destination, output language

**Locale tree**:
A website's locales on disk, in one of three **layouts**: a directory per locale, a file per locale,
or a bundle holding every locale under its code.
_Avoid_: locale folder, i18n dir

**Source file**:
A JSON file of the source locale. In the directory layout it is known by its path inside the
source's directory (`auth/login.json`).

**Locale document**:
The messages of one locale from one file: a JSON object whose leaves are mostly strings.
_Avoid_: translation file, resource

**Qualify**:
To be a locale document worth translating. The rules say so first, from the share of text among
its values; then the model's **classification** confirms it.
_Avoid_: validate (that is for messages), detect

## Messages

**Message**:
One string leaf of a locale document, as code shows it to a user.
_Avoid_: string, key (that is its path), entry, label

**Key path**:
Where a message sits in its document: `auth.errors.locked`, `steps[2]`.

**Placeholder**:
What a message holds for code to fill or render: `{{name}}`, `{count}`, `%{name}`, `%s`, `$t(key)`,
`<b>`. A translation keeps each one, as often as it appears.
_Avoid_: variable, interpolation (for all of them), token (in prose)

**Signature**:
A message's placeholders, and its plurals and selects, which its translation must keep.

**Plural family**:
The i18next keys of one plural, one per category: `item_one`, `item_other`. A target gets its own
categories, from CLDR.
_Avoid_: plural keys, plural forms (for the keys)

**Pipe plural**:
A Laravel message `trans_choice` splits at its pipes: `one apple|:count apples`, or with ranges,
`{0} none|[1,*] some`. A target gets the number of forms Laravel's own table gives its language.
A pipe with a space on each side and no range is text.
_Avoid_: choice string

**Message syntax**:
What a tree's messages mean beyond the placeholders every library shares: standard, or Laravel's
(the keys as the source, `:name`, pipe plurals). A preset sets it for its own locales.

**Plural category**:
CLDR's `zero`, `one`, `two`, `few`, `many`, `other`; each language uses some, always `other`.

## Generation

**Precheck**:
The scan that comes before a generation: the tree, which source files qualify, and how many
messages each target needs. Nothing is sent to a model.
_Avoid_: dry run (that is the option that stops after it), preview

**Schema**:
The shape of a target's version of a source file: the source's keys and order, its non-text values,
a **unit** for each message to translate, and the plural families with the target's categories.

**Unit**:
One message to translate in a schema, with an id the model answers with, its source text, and its
signature. A plural form is a unit of its own.

**Atom**:
The agent that translates one source file into one target locale: it extracts the schema,
translates, validates, retries, and assembles.
_Avoid_: worker, job (in prose), task

**Violation**:
A rule a translation breaks. An **error** rejects it, and it is sent back with the problem; a
**warning** keeps it, and is reported.

**Kept translation**:
A message of an existing target that passes the rules, and is not translated again.
_Avoid_: cached, reused (in prose)

**Fallback**:
The source text a message keeps when it never passed the rules, so that its document is whole. Such
a file is **partial**, unless the generation is **strict**, when it is not written.

**Fallback record**:
The fallbacks a tree's generations left, in `.i18n-ai-fallbacks.json` beside its targets, so that
the next run translates them again instead of keeping them.

## Models

**Model spec**:
`provider:model`, as LangChain's `init_chat_model` takes it.

**Provider**:
A service LangChain integrates, through a package of its own (`langchain-openai`), installed into
i18n-ai's environment when first needed.
_Avoid_: vendor, backend, LLM (for the provider)
