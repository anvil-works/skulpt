# CPython 3.14.3 tokenize research

The useful reuse boundary is the Python `tokenize.py` wrapper around a Skulpt implementation of `_tokenize.TokenizerIter`, backed by the new TypeScript lexer. CPython already shares its lexer between compilation and public tokenization, with an explicit mode for the latter. Reusing the C extension itself would require the CPython runtime APIs it calls. Porting that extension's small adapter contract is a much smaller task. This recommendation follows from the pinned [Python wrapper](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L472-L506), [native adapter](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c), and [readline implementation](https://github.com/python/cpython/blob/v3.14.3/Parser/tokenizer/readline_tokenizer.c).

## Version boundary

The available sibling checkout is the 3.13 maintenance branch at
`ef5bc9ec9b25c66181fd51f2dbbf861e79bf3be4`, rather than the target release.
Implementation claims below use pinned CPython `v3.14.3` sources instead.

Compared with local 3.13 HEAD, 3.14.3 adds template-string handling in the lexer and untokenizer, moves encoding-cookie matching to bytes, and validates the consumed encoding-detection lines using the selected codec, including null-byte rejection. Copying the sibling wrapper would therefore preserve the wrong target behavior. The pinned [tokenize.py](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py) and [token.py](https://github.com/python/cpython/blob/v3.14.3/Lib/token.py) are the sources to port.

## Public contract

- `tokenize(readline)` consumes bytes lines, detects an encoding, replays the consumed lines, yields an initial `ENCODING` token, and delegates to the native iterator. `generate_tokens(readline)` consumes strings and yields no `ENCODING`. Empty input and `StopIteration` terminate reading. Both produce an iterator of `TokenInfo(type, string, start, end, line)`, a named tuple whose `exact_type` maps generic `OP` through `EXACT_TOKEN_TYPES`. See [TokenInfo](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L47-L60) and [entry points](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L472-L506).
- Public positions use Unicode character columns, not C UTF-8 byte offsets. The native adapter converts byte positions, returns source text, and adjusts trailing tokens and implicit newlines. A JavaScript adapter must not accidentally expose UTF-16 code-unit columns for astral characters. See [native position conversion and tuple assembly](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c#L195-L352).
- `detect_encoding` reads at most two lines, returns the codec and consumed bytes, supports a BOM and coding cookie, defaults to UTF-8, and reports codec conflicts or unknown codecs as `SyntaxError`. A BOM makes detection return `utf-8-sig`; `tokenize` strips it and emits `utf-8`. `open` wraps the file using that detected codec. See [encoding helpers](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L349-L470).
- `untokenize` accepts token pairs or full five-field records. Pairs use a compatibility path that reconstructs spacing; full records use their positions and indentation. The guarantee concerns token types and strings, not identical source spacing. It returns bytes when an encoding token occurs, otherwise text. Its f-string and t-string paths reconstruct doubled braces, so string concatenation is insufficient. See [untokenizer](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L165-L346).

`token.py` is straightforward generated data plus three predicates. In 3.14.3 it includes `EXCLAMATION=54`, `OP=55`, `FSTRING_START/MIDDLE/END=59/60/61`, `TSTRING_START/MIDDLE/END=62/63/64`, `COMMENT=65`, `NL=66`, `ERRORTOKEN=67`, `ENCODING=68`, `N_TOKENS=69`, and `NT_OFFSET=256`. It exports `EXACT_TOKEN_TYPES` and `tok_name`. Local 3.13 instead assigns `COMMENT=62`, `NL=63`, `ERRORTOKEN=64`, `ENCODING=65`; mixing these constants silently corrupts streams. See [pinned constants](https://github.com/python/cpython/blob/v3.14.3/Lib/token.py) and [grammar tokens](https://github.com/python/cpython/blob/v3.14.3/Grammar/Tokens).

## Native adapter and lexer modes

The effective constructor is `_tokenize.TokenizerIter(readline, *, extra_tokens, encoding=...)`. Omitting encoding takes strings: despite the generated signature's displayed UTF-8 default, the C default is `NULL`. Supplying an encoding takes bytes. The iterator yields plain five-tuples; `tokenize.py` creates `TokenInfo` with `_make`. See [constructor](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c#L44-L86), [input validation](https://github.com/python/cpython/blob/v3.14.3/Parser/tokenizer/readline_tokenizer.c#L10-L73), and [wrapper](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L581-L594).

`extra_tokens=True` changes more than the set of emitted tokens:

- It retains comments and non-significant newlines, preserves indentation strings, normalizes exact operator codes to `OP`, and adjusts final token positions and newline spellings. See [lexer](https://github.com/python/cpython/blob/v3.14.3/Parser/lexer/lexer.c#L615-L827) and [adapter](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c#L305-L346).
- It bypasses identifier validity checks, relaxes end-of-number validation and leading-zero rejection, and suppresses some unmatched/mismatched bracket errors. See [identifier and number checks](https://github.com/python/cpython/blob/v3.14.3/Parser/lexer/lexer.c#L304-L370), [leading zeros](https://github.com/python/cpython/blob/v3.14.3/Parser/lexer/lexer.c#L960-L985), and [brackets](https://github.com/python/cpython/blob/v3.14.3/Parser/lexer/lexer.c#L1300-L1365).

Consequently, converting a compiler stream after scanning cannot reproduce public tokenization: omitted comments cannot be recovered and rejected input cannot be recovered by changing token codes. Use the shared lexer with the correct mode. Public tokenization is also not a syntax validator. The documented contract only covers syntactically valid Python, and explicitly leaves behavior on invalid Python undefined. See the [official documentation warning](https://docs.python.org/3.14/library/tokenize.html).

## Errors worth preserving

The C adapter raises exceptions when scanning yields `ERRORTOKEN`; the Python wrapper does not normally expose that sentinel as a token. The wrapper catches exact `SyntaxError`, converts it to `TokenError(message, (lineno, offset))`, and rewrites unterminated triple-quoted-string messages to `EOF in multi-line string`. Subclasses such as `IndentationError` and `TabError` pass through unchanged. Keep lexer error class, message, and coordinates available so the public adapter can perform this conversion without changing compiler diagnostics. See [native error mapping](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c#L88-L179), [iterator error handling](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c#L245-L261), and [Python conversion](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L570-L594).

Useful native diagnostics include incomplete multiline input, invalid tokens, unmatched dedents, mixed tabs/spaces, excess indentation, and bad line continuations. Wrong callback return types raise `TypeError`; encoding detection has its own `SyntaxError` path before native iteration. These are separate paths that an adapter must preserve. The pinned bytes reader decodes with the selected codec using `replace`; do not assume every later invalid byte raises a decoding error. See [native mapping](https://github.com/python/cpython/blob/v3.14.3/Python/Python-tokenize.c#L88-L179), [readline decoding](https://github.com/python/cpython/blob/v3.14.3/Parser/tokenizer/readline_tokenizer.c#L10-L47), and [encoding detection](https://github.com/python/cpython/blob/v3.14.3/Lib/tokenize.py#L359-L455).


## Skulpt migration findings

In this study's Skulpt base, `src/lib/tokenize.js` exposes only `tokenize`.
It eagerly returns a list of plain five-tuples, accepts decoded strings from a
callback, and inserts an `ENCODING` token labelled `UTF-8`. It does not implement
CPython's bytes-reader contract, `TokenInfo`, `generate_tokens`, `untokenize`, or
encoding detection. Existing tests use this text-reader extension, so replacing
it with a strict bytes-only API would break currently supported behavior.

A wholesale copy of CPython's Python wrapper would also fail immediately:
`src/lib/io.py` and `src/lib/codecs.py` are unsupported-module stubs. Implementing
those modules is outside the tokenizer migration. Prefer a focused wrapper over
the new scanner, following CPython's token and diagnostic contracts.

The lean parser at `67428dc` already exports `scan` and `tokenize` with
`extraTokens: true` by default. Its existing lexer fixtures use CPython's native
`_tokenize.TokenizerIter`. The additional script in this PR checks the public
`tokenize.generate_tokens` path directly against CPython 3.14.3:

```sh
node support/run/check-tokenize-migration.mjs /path/to/skulpt-parser/dist-core/index.js
```

All 12 targeted token-stream comparisons passed, including empty input, comments,
implicit newlines, Unicode character columns, indentation, CRLF, f-strings and
template strings. This verifies token names, strings, positions and source lines;
it does not verify a Python wrapper, token numbers, streaming callbacks, encoding,
or complete public-module compatibility.

The script also reports three diagnostic probes. Unclosed parentheses have the
same message but require conversion from the core's `SyntaxError` to `TokenError`.
An unterminated triple-quoted string needs CPython's public compatibility message
`EOF in multi-line string`. Indentation failures retain `IndentationError`.
Keep that public compatibility translation separate from parser diagnostics so
the IDE can continue displaying the more descriptive parser error.

Token constants must migrate together with the public module. For example,
Skulpt currently uses `OP = 53` and `ENCODING = 59`, while CPython 3.14.3 uses
55 and 68. The new scanner uses symbolic token names, so the wrapper can map to
a generated 3.14 token table without putting numeric IDs in the lexer. Preserve
legacy numeric tables while the old parser remains available.

## What removing the old tokenizer actually requires

`src/tokenize.js` also defines `Sk.token.isIdentifier`, used by `str.isidentifier`,
and `Sk.token.setupTokens`, invoked during `Sk.configure`. Those dependencies
must be moved or replaced before removing the module. The existing identifier
helper normalizes with NFKC and uses old Unicode category regexes; changing it
needs direct CPython checks for identifier edge cases.

Removing the tokenizer will not remove the entire old Unicode table dependency.
`src/str.js` imports the same tables for printable and decimal-character checks.
Any size estimate that assumes all of `support/polyfills/Unicode.js` disappears
would overstate the saving. No additional size saving was measured in this study.

The current core `scan(source)` emits tokens lazily but takes the complete source
string. It does not yet provide CPython's incremental `readline` behavior. Using
it avoids constructing a token list, but source buffering and callback timing
remain explicit differences to address or document.

## Proposed implementation order

1. Add a CPython-shaped wrapper over core `scan` in the opt-in runtime path.
   Start with decoded text, `generate_tokens`, `TokenInfo`, `exact_type`, matching
   token constants and error translation. Preserve the existing text-reader
   `tokenize` extension for current Skulpt callers and bounded Python 2 syntax.
2. Add the standard bytes-reader path and encoding handling only to the extent
   supported by Skulpt's existing byte-decoding facilities. Do not claim full
   CPython `tokenize` support until encoding/BOM/cookie and callback behavior are
   tested. Treat `untokenize` and file-opening convenience separately.
3. Move identifier/configuration helpers out of the old tokenizer, verify Python
   string behavior and the existing token module tests, then remove the old lexer
   from the replacement artifact. Rebuild and report the actual size delta.

This recommendation reuses CPython's lexer/public-wrapper division. It does not
require another tokenizer implementation, a compiler rewrite, or broader codec
and file-I/O work before testing the first adapter.

Local implementation references: [tokenize module](../src/lib/tokenize.js),
[token module](../src/lib/token.js), [token constants](../src/token.js),
[legacy tokenizer](../src/tokenize.js), [string implementation](../src/str.js),
[configuration](../src/env.js), [existing tests](../test/unit/test_tokenize.py),
[io stub](../src/lib/io.py), [codecs stub](../src/lib/codecs.py).
New lexer references: [core exports](https://github.com/anvil-works/skulpt-parser/blob/67428dc/src/python314/core.ts)
and [scanner](https://github.com/anvil-works/skulpt-parser/blob/67428dc/src/python314/lexer/tokenizer.ts).
