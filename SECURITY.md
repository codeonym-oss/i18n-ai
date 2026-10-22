# Security Policy

## Supported versions

i18n-ai is pre-1.0. Security fixes are released for the latest minor version only.

| Version         | Supported |
|-----------------|-----------|
| latest `0.x`    | ✅        |
| older           | ❌        |

## Reporting a vulnerability

Please **do not** open a public issue. Report it privately through
[GitHub private vulnerability reporting](https://github.com/codeonym-oss/i18n-ai/security/advisories/new).

Include what you found, how to reproduce it, and the affected versions. You can expect an
acknowledgement within 7 days. Once a fix is released, we publish a GitHub Security Advisory
crediting you, unless you prefer to stay anonymous.

Of particular interest:

- anything that leaks a provider's API key (from the environment or a `.env`) into the output,
  the logs (`-vv`), or the files written;
- writing outside the output directory, for example through a source file name or a bundle key;
- installing a package other than the provider's LangChain integration that LangChain names.
