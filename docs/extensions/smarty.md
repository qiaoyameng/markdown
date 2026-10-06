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

Language modes
--------------

Set the `language` option to `en`, `zh`, or `fr` to use language-specific
quotation rules. BCP 47 region tags such as `zh-CN` and `fr-FR` are also
accepted. When a language is enabled, quote pairing is tracked through normal
inline emphasis, but the state resets at paragraph and other block boundaries.
Code spans, code blocks, link destinations, link titles, HTML attributes, and
stashed raw HTML never participate in quote replacement.

| Language | Outer quotes | Inner quotes | Spacing |
| -------- | ------------ | ------------ | ------- |
| `en`     | `“ ”`        | `‘ ’`        | none |
| `zh`     | `“ ”`        | `‘ ’`        | none |
| `fr`     | `« »`        | `‹ ›`        | non-breaking space inside each quote |

```python
markdown.markdown(
    'She said, "Read the **manual** and run `import "os"` first."',
    extensions=['smarty'],
    extension_configs={'smarty': {'language': 'en'}}
)
# <p>She said, &ldquo;Read the <strong>manual</strong> and run
# <code>import "os"</code> first.&rdquo;</p>

markdown.markdown(
    '她说："请先阅读**手册**，再运行 `import "os"`。"',
    extensions=['smarty'],
    extension_configs={'smarty': {'language': 'zh-CN'}}
)
# <p>她说：&ldquo;请先阅读<strong>手册</strong>，再运行
# <code>import "os"</code>。&rdquo;</p>

markdown.markdown(
    'Elle a dit : "Lisez le **manuel** et exécutez `import "os"`."',
    extensions=['smarty'],
    extension_configs={'smarty': {'language': 'fr-FR'}}
)
# <p>Elle a dit : &laquo;&nbsp;Lisez le <strong>manuel</strong> et
# exécutez <code>import "os"</code>.&nbsp;&raquo;</p>
```

In language modes, apostrophes are converted to `&rsquo;`, while foot and
inch marks after numbers are converted to `&prime;` and `&Prime;`. For
example, `It's the '80s and 5'10"` becomes
`It&rsquo;s the &rsquo;80s and 5&prime;10&Prime;`.

Language modes only convert ASCII quote marks. Text that already contains the
correct Unicode or entity punctuation is left unchanged when converted again.
When `language` is not set, the legacy SmartyPants quote heuristics remain in
use and language-specific pairing is disabled.

!!! tip
    This extension re-implements the Python [SmartyPants]
    library by integrating it into the markdown parser.
    Integrating the conversion into the parser means quote pairing can follow
    inline elements while still skipping code and stashed raw HTML. It will
    also not try to work on highlighted code blocks (using the [CodeHilite]
    Extension) like the third party library has been known to do.

[SmartyPants]: https://pythonhosted.org/smartypants/
[CodeHilite]: code_hilite.md

Usage
-----

See [Extensions](index.md) for general extension usage. Use `smarty` as the
name of the extension.

See the [Library Reference](../library.md#extensions) for information about
configuring extensions.

The following options are provided to configure the output:

Option                | Default value | Description
------                | ------------- | -----------
`language`            | disabled (`''`)  | language-specific quote rules: `en`, `zh`, or `fr`
`smart_dashes`        | `True`        | whether to convert dashes
`smart_quotes`        | `True`        | whether to convert straight quotes
`smart_angled_quotes` | `False`       | whether to convert angled quotes
`smart_ellipses`      | `True`        | whether to convert ellipses
`substitutions`       | `{}`          | overwrite default substitutions

A trivial example:

```python
markdown.markdown(some_text, extensions=['smarty'])
```

Further reading
---------------

SmartyPants extension is based on the original SmartyPants implementation
by John Gruber. Please read its [documentation][1] for details.

[1]: https://daringfireball.net/projects/smartypants/
