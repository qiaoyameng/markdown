---
title: SmartyPants Extension
---

SmartyPants
===========

Summary
-------

The SmartyPants extension converts ASCII dashes, quotes and ellipses to
their HTML entity equivalents.

ASCII symbol | Replacements    | HTML Entities       | Substitution Keys
------------ | --------------- | ------------------- | ----------------------------------------
`'`          | &lsquo; &rsquo; | `&lsquo;` `&rsquo;` | `'left-single-quote'`, `'right-single-quote'`
`"`          | &ldquo; &rdquo; | `&ldquo;` `&rdquo;` | `'left-double-quote'`, `'right-double-quote'`
`<< >>`      | &laquo; &raquo; | `&laquo;` `&raquo;` | `'left-angle-quote'`, `'right-angle-quote'`
`...`        | &hellip;        | `&hellip;`          | `'ellipsis'`
`--`         | &ndash;         | `&ndash;`           | `'ndash'`
`---`        | &mdash;         | `&mdash;`           | `'mdash'`

Using the configuration option 'substitutions' you can overwrite the
default substitutions. Just pass a dict mapping (a subset of) the
keys to the substitution strings.

For example, one might use the following configuration to get correct quotes for
the German language:

```python
extension_configs = {
    'smarty': {
        'substitutions': {
            'left-single-quote': '&sbquo;', # sb is not a typo!
            'right-single-quote': '&lsquo;',
            'left-double-quote': '&bdquo;',
            'right-double-quote': '&ldquo;'
        }
    }
}
```

!!! tip
    This extension re-implements the Python [SmartyPants]
    library by integrating it into the markdown parser.
    While this does not provide any additional features,
    it does offer a few advantages. Notably, it will not
    try to work on highlighted code blocks (using the
    [CodeHilite] Extension) like the third party library
    has been known to do.

[SmartyPants]: https://pythonhosted.org/smartypants/
[CodeHilite]: code_hilite.md

!!! info "Note"

    This extension is in __maintenance mode__.  We will continue to fix bugs
    and keep it up-to-date with the core parser, but no new features or
    changes in behavior will be made. If you need a feature that this
    extension does not offer, then you have three options (1) find an
    existing [third-party extension] which meets your needs, (2) [build your
    own extension], or (3) fork this extension (pursuant to its licensing
    requirements) and maintain it as a third-party extension.

[third-party extension]: index.md#third-party-extensions
[build your own extension]: api.md

Usage
-----

See [Extensions](index.md) for general extension usage. Use `smarty` as the
name of the extension.

See the [Library Reference](../library.md#extensions) for information about
configuring extensions.

The following options are provided to configure the output:

Option                | Default value | Description
------                | ------------- | -----------
`smart_dashes`        | `True`        | whether to convert dashes
`smart_quotes`        | `True`        | whether to convert straight quotes
`smart_angled_quotes` | `False`       | whether to convert angled quotes
`smart_ellipses`      | `True`        | whether to convert ellipses
`substitutions`       | `{}`          | overwrite default substitutions
`language`            | `''`          | language used for quote substitution (`'en'`, `'fr'` or `'zh'`); if empty, the classic SmartyPants substitution is used

A trivial example:

```python
markdown.markdown(some_text, extensions=['smarty'])
```

Language-specific quotes
------------------------

By default, quotes are educated using the classic SmartyPants rules, which
assume English typography. If the same document needs to be published in
multiple languages, set the `language` option to `'en'`, `'fr'` or `'zh'` to
get the paired quotes, nested quotes and spacing characters that the language
requires:

Language | Double quotes | Single (nested) quotes | Spacing
-------- | ------------- | ---------------------- | -------
`en`     | `“…”`         | `‘…’`                  | none
`fr`     | `«…»`         | `“…”`                  | narrow no-break space (`U+202F`) inside `«` and `»`
`zh`     | `“…”`         | `‘…’`                  | none

```python
markdown.markdown(some_text, extensions=['smarty'],
                  extension_configs={'smarty': {'language': 'fr'}})
```

In language mode the quote state is tracked explicitly: an opened quote stays
open across inline elements such as emphasis, and is closed by the next
matching quote. The state is reset at every paragraph boundary. The content
of code spans and code blocks, link targets, HTML attributes and raw
(stashed) HTML never takes part in the substitution. Apostrophes
(`don't`, `l'arbre`), decade abbreviations (`'80s`) and feet/inches marks in
numbers (`6'2"` becomes `6′2″`) are kept distinct from real quotes. Only
straight ASCII quotes are replaced, so text which already contains the
correct typographic punctuation passes through unchanged.

Short examples (quotes around a bold word, and code within quotes):

```text
"Hello **world**"            →  “Hello <strong>world</strong>”          (en)
"Use `make` now"             →  “Use <code>make</code> now”             (en)

"Bonjour **monde**"          →  « Bonjour <strong>monde</strong> »      (fr)
"lance `ls` ici"             →  « lance <code>ls</code> ici »           (fr)

"你好 **世界**"               →  “你好 <strong>世界</strong>”            (zh)
"运行 `python` 吧"            →  “运行 <code>python</code> 吧”           (zh)
```

(The French examples use a narrow no-break space inside the guillemets.)

Further reading
---------------

SmartyPants extension is based on the original SmartyPants implementation
by John Gruber. Please read its [documentation][1] for details.

[1]: https://daringfireball.net/projects/smartypants/
