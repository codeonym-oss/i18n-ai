# Changelog

## [0.4.0](https://github.com/codeonym-oss/i18n-ai/compare/v0.3.0...v0.4.0) (2026-11-04)


### Features

* fallback intents to list, set, retry and accept ([#33](https://github.com/codeonym-oss/i18n-ai/issues/33)) ([#47](https://github.com/codeonym-oss/i18n-ai/issues/47)) ([e020671](https://github.com/codeonym-oss/i18n-ai/commit/e020671cabf17023628326fc213ab5d67f1955fb))
* open a full-screen TUI by default, starting with its setup screen ([#30](https://github.com/codeonym-oss/i18n-ai/issues/30)) ([#37](https://github.com/codeonym-oss/i18n-ai/issues/37)) ([3d271ba](https://github.com/codeonym-oss/i18n-ai/commit/3d271ba6067ad4922021133cbeb84665eea51756))
* plan a TUI run as a files × locales grid, with single cells turned off ([#31](https://github.com/codeonym-oss/i18n-ai/issues/31)) ([#38](https://github.com/codeonym-oss/i18n-ai/issues/38)) ([a1ec720](https://github.com/codeonym-oss/i18n-ai/commit/a1ec720318b276096882b3452d916c4aaf04d8ea))
* record the fallbacks, and translate them again ([#29](https://github.com/codeonym-oss/i18n-ai/issues/29)) ([#35](https://github.com/codeonym-oss/i18n-ai/issues/35)) ([8287930](https://github.com/codeonym-oss/i18n-ai/commit/82879300abfa327445ab8bfd7e317678ec39c2b5))
* review the fallbacks in the TUI ([#33](https://github.com/codeonym-oss/i18n-ai/issues/33)) ([#48](https://github.com/codeonym-oss/i18n-ai/issues/48)) ([adadda6](https://github.com/codeonym-oss/i18n-ai/commit/adadda6544eb0b4592a8d915680ce7fcb36fd1fa))
* watch a TUI run live, retries and failures included ([#32](https://github.com/codeonym-oss/i18n-ai/issues/32)) ([#39](https://github.com/codeonym-oss/i18n-ai/issues/39)) ([a9fc741](https://github.com/codeonym-oss/i18n-ai/commit/a9fc7418eec2f5d78d664041538401801fba29c6))


### Documentation

* close the full-screen TUI story ([#15](https://github.com/codeonym-oss/i18n-ai/issues/15)) ([#49](https://github.com/codeonym-oss/i18n-ai/issues/49)) ([597cfad](https://github.com/codeonym-oss/i18n-ai/commit/597cfadd7540b47a635ae5857aec3335dcb806b8))


### Build

* **deps-dev:** bump the dev-tools group with 3 updates ([#41](https://github.com/codeonym-oss/i18n-ai/issues/41)) ([3d24276](https://github.com/codeonym-oss/i18n-ai/commit/3d24276820c979ec0ca80ebea55b815f242ed19d))
* **deps:** bump langchain from 1.4.6 to 1.4.7 ([#42](https://github.com/codeonym-oss/i18n-ai/issues/42)) ([5ae274b](https://github.com/codeonym-oss/i18n-ai/commit/5ae274bfefc03858363199d03bd6d7d4e84438ad))
* **deps:** bump langchain-core from 1.6.12 to 1.7.0 ([#43](https://github.com/codeonym-oss/i18n-ai/issues/43)) ([3615012](https://github.com/codeonym-oss/i18n-ai/commit/3615012335be13688e4550af30aa79ea63158c60))
* **deps:** bump langgraph from 1.2.16 to 1.2.18 ([#44](https://github.com/codeonym-oss/i18n-ai/issues/44)) ([44202cb](https://github.com/codeonym-oss/i18n-ai/commit/44202cbe05ecd2b45203467205b0561169b04cf5))
* raise the example manifests' dependency floors past known vulnerabilities ([#50](https://github.com/codeonym-oss/i18n-ai/issues/50)) ([#51](https://github.com/codeonym-oss/i18n-ai/issues/51)) ([79b7edf](https://github.com/codeonym-oss/i18n-ai/commit/79b7edfcb8186ecaa84e9e0c0ba7fb88f620e882))

## [0.3.0](https://github.com/codeonym-oss/i18n-ai/compare/v0.2.0...v0.3.0) (2026-10-23)


### Features

* translate Laravel's JSON locales, keeping their :name placeholders ([#17](https://github.com/codeonym-oss/i18n-ai/issues/17)) ([#27](https://github.com/codeonym-oss/i18n-ai/issues/27)) ([63e1615](https://github.com/codeonym-oss/i18n-ai/commit/63e161584aba5c1ebc34402a6b013360098608e3))

## [0.2.0](https://github.com/codeonym-oss/i18n-ai/compare/v0.1.0...v0.2.0) (2026-10-23)


### Features

* ask for whatever a run is missing, at a terminal ([#13](https://github.com/codeonym-oss/i18n-ai/issues/13)) ([#18](https://github.com/codeonym-oss/i18n-ai/issues/18)) ([b521c51](https://github.com/codeonym-oss/i18n-ai/commit/b521c51fa5680e4474594266e26999e667fcba67))
* detect the project's i18n library and preset its tree ([#17](https://github.com/codeonym-oss/i18n-ai/issues/17)) ([#24](https://github.com/codeonym-oss/i18n-ai/issues/24)) ([2a5774f](https://github.com/codeonym-oss/i18n-ai/commit/2a5774ff475ab577268372ac3b97644d85e426b7))
* keep provider API keys in the system keyring ([#14](https://github.com/codeonym-oss/i18n-ai/issues/14)) ([#19](https://github.com/codeonym-oss/i18n-ai/issues/19)) ([acea45f](https://github.com/codeonym-oss/i18n-ai/commit/acea45f6dda96297b8fb8c9d18c073668c5e9c99))
* read and write Flutter's ARB locales ([#16](https://github.com/codeonym-oss/i18n-ai/issues/16)) ([#21](https://github.com/codeonym-oss/i18n-ai/issues/21)) ([233a65d](https://github.com/codeonym-oss/i18n-ai/commit/233a65d0a0b788a325be2ec1a1717b2ba2de9c44))
* read and write gettext PO catalogs ([#16](https://github.com/codeonym-oss/i18n-ai/issues/16)) ([#22](https://github.com/codeonym-oss/i18n-ai/issues/22)) ([efd03dd](https://github.com/codeonym-oss/i18n-ai/commit/efd03dd415f2a909d524b0639fa1c9f0a420b41f))
* read and write XLIFF 1.2 and 2.0 files ([#16](https://github.com/codeonym-oss/i18n-ai/issues/16)) ([#23](https://github.com/codeonym-oss/i18n-ai/issues/23)) ([3c68407](https://github.com/codeonym-oss/i18n-ai/commit/3c68407b824913ddf688aa981d9f30da386bb328))
* read and write YAML locales ([#16](https://github.com/codeonym-oss/i18n-ai/issues/16)) ([#20](https://github.com/codeonym-oss/i18n-ai/issues/20)) ([9ffa586](https://github.com/codeonym-oss/i18n-ai/commit/9ffa586f89dc420d150730f4e31ca38487147908))


### Build

* **deps-dev:** update uv-build requirement from &lt;0.13,&gt;=0.8.22 to &gt;=0.8.22,&lt;0.14 in the dev-tools group ([#3](https://github.com/codeonym-oss/i18n-ai/issues/3)) ([fd8c906](https://github.com/codeonym-oss/i18n-ai/commit/fd8c9068a2f941111da8751466f8ae9628b220c6))

## 0.1.0 (2026-10-22)


### Features

* generate locales with LangGraph agents through any LangChain provider ([#5](https://github.com/codeonym-oss/i18n-ai/issues/5)) ([#9](https://github.com/codeonym-oss/i18n-ai/issues/9)) ([e3d01a5](https://github.com/codeonym-oss/i18n-ai/commit/e3d01a5461c667cfa56c97ad5bfcfb704f78ff92))
* precheck a locale tree with i18n-ai scan ([#4](https://github.com/codeonym-oss/i18n-ai/issues/4)) ([#8](https://github.com/codeonym-oss/i18n-ai/issues/8)) ([a738b75](https://github.com/codeonym-oss/i18n-ai/commit/a738b75de4cb89e9df8110702b5259fe813c55c9))
* the locale domain, with placeholders, schemas and the rules ([#2](https://github.com/codeonym-oss/i18n-ai/issues/2)) ([#7](https://github.com/codeonym-oss/i18n-ai/issues/7)) ([32f4860](https://github.com/codeonym-oss/i18n-ai/commit/32f48604b03bfe3e9da1e3d8161e99ff3334e16f))


### Documentation

* the guide, the command reference and the architecture ([#6](https://github.com/codeonym-oss/i18n-ai/issues/6)) ([#10](https://github.com/codeonym-oss/i18n-ai/issues/10)) ([d0b5e92](https://github.com/codeonym-oss/i18n-ai/commit/d0b5e9239aa2a2b0a89042a003f6bfec0acd0949))


### Build

* set up the project with the codeonym-oss tooling ([5b651e9](https://github.com/codeonym-oss/i18n-ai/commit/5b651e9c456323b3c4188d117d9cc7881a01ac24))
