# -*- coding: utf-8 -*-
"""
Python Markdown

A Python implementation of John Gruber's Markdown.

Documentation: https://python-markdown.github.io/
GitHub: https://github.com/Python-Markdown/markdown/
PyPI: https://pypi.org/project/Markdown/

Started by Manfred Stienstra (http://www.dwerg.net/).
Maintained for a few years by Yuri Takhteyev (http://www.freewisdom.org).
Currently maintained by Waylan Limberg (https://github.com/waylan),
Dmitry Shachnev (https://github.com/mitya57) and Isaac Muse (https://github.com/facelessuser).

Copyright 2007-2022 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).
"""

from markdown import Markdown
from markdown.test_tools import TestCase


class TestSmarty(TestCase):

    default_kwargs = {'extensions': ['smarty']}

    def test_basic(self):
        self.assertMarkdownRenders(
            "It's fun. What's fun?",
            '<p>It&rsquo;s fun. What&rsquo;s fun?</p>'
        )
        self.assertMarkdownRenders(
            '"Isn\'t this fun"? --- she said...',
            '<p>&ldquo;Isn&rsquo;t this fun&rdquo;? &mdash; she said&hellip;</p>'
        )
        self.assertMarkdownRenders(
            '"\'Quoted\' words in a larger quote."',
            '<p>&ldquo;&lsquo;Quoted&rsquo; words in a larger quote.&rdquo;</p>'
        )
        self.assertMarkdownRenders(
            '\'Quoted "words" in a larger quote.\'',
            '<p>&lsquo;Quoted &ldquo;words&rdquo; in a larger quote.&rsquo;</p>'
        )
        self.assertMarkdownRenders(
            '"Quoted words at the \'end.\'"',
            '<p>&ldquo;Quoted words at the &lsquo;end.&rsquo;&rdquo;</p>'
        )
        self.assertMarkdownRenders(
            '\'Quoted words at the "end."\'',
            '<p>&lsquo;Quoted words at the &ldquo;end.&rdquo;&rsquo;</p>'
        )
        self.assertMarkdownRenders(
            '(He replied, "She said \'Hello.\'")',
            '<p>(He replied, &ldquo;She said &lsquo;Hello.&rsquo;&rdquo;)</p>'
        )
        self.assertMarkdownRenders(
            '<span>He replied, "She said \'Hello.\'"</span>',
            '<p><span>He replied, &ldquo;She said &lsquo;Hello.&rsquo;&rdquo;</span></p>'
        )
        self.assertMarkdownRenders(
            '"quoted" text and **bold "quoted" text**',
            '<p>&ldquo;quoted&rdquo; text and <strong>bold &ldquo;quoted&rdquo; text</strong></p>'
        )
        self.assertMarkdownRenders(
            "'quoted' text and **bold 'quoted' text**",
            '<p>&lsquo;quoted&rsquo; text and <strong>bold &lsquo;quoted&rsquo; text</strong></p>'
        )
        self.assertMarkdownRenders(
            'em-dashes (---) and ellipes (...)',
            '<p>em-dashes (&mdash;) and ellipes (&hellip;)</p>'
        )
        self.assertMarkdownRenders(
            '"[Link](http://example.com)" --- she said.',
            '<p>&ldquo;<a href="http://example.com">Link</a>&rdquo; &mdash; she said.</p>'
        )
        self.assertMarkdownRenders(
            '"Ellipsis within quotes..."',
            '<p>&ldquo;Ellipsis within quotes&hellip;&rdquo;</p>'
        )
        self.assertMarkdownRenders(
            "*Custer*'s Last Stand",
            "<p><em>Custer</em>&rsquo;s Last Stand</p>"
        )

    def test_years(self):
        self.assertMarkdownRenders("1440--80's", '<p>1440&ndash;80&rsquo;s</p>')
        self.assertMarkdownRenders("1440--'80s", '<p>1440&ndash;&rsquo;80s</p>')
        self.assertMarkdownRenders("1440---'80s", '<p>1440&mdash;&rsquo;80s</p>')
        self.assertMarkdownRenders("1960's", '<p>1960&rsquo;s</p>')
        self.assertMarkdownRenders("one two '60s", '<p>one two &rsquo;60s</p>')
        self.assertMarkdownRenders("'60s", '<p>&rsquo;60s</p>')

    def test_wrapping_line(self):
        text = (
            "A line that 'wraps' with\n"
            "*emphasis* at the beginning of the next line."
        )
        html = (
            '<p>A line that &lsquo;wraps&rsquo; with\n'
            '<em>emphasis</em> at the beginning of the next line.</p>'
        )
        self.assertMarkdownRenders(text, html)

    def test_escaped(self):
        self.assertMarkdownRenders(
            'Escaped \\-- ndash',
            '<p>Escaped -- ndash</p>'
        )
        self.assertMarkdownRenders(
            '\\\'Escaped\\\' \\"quotes\\"',
            '<p>\'Escaped\' "quotes"</p>'
        )
        self.assertMarkdownRenders(
            'Escaped ellipsis\\...',
            '<p>Escaped ellipsis...</p>'
        )
        self.assertMarkdownRenders(
            '\'Escaped \\"quotes\\" in real ones\'',
            '<p>&lsquo;Escaped "quotes" in real ones&rsquo;</p>'
        )
        self.assertMarkdownRenders(
            '\\\'"Real" quotes in escaped ones\\\'',
            "<p>'&ldquo;Real&rdquo; quotes in escaped ones'</p>"
        )

    def test_escaped_attr(self):
        self.assertMarkdownRenders(
            '![x\"x](x)',
            '<p><img alt="x&quot;x" src="x" /></p>'
        )

    def test_code_spans(self):
        self.assertMarkdownRenders(
            'Skip `"code" -- --- \'spans\' ...`.',
            '<p>Skip <code>"code" -- --- \'spans\' ...</code>.</p>'
        )

    def test_code_blocks(self):
        text = (
            '    Also skip "code" \'blocks\'\n'
            '    foo -- bar --- baz ...'
        )
        html = (
            '<pre><code>Also skip "code" \'blocks\'\n'
            'foo -- bar --- baz ...\n'
            '</code></pre>'
        )
        self.assertMarkdownRenders(text, html)

    def test_horizontal_rule(self):
        self.assertMarkdownRenders('--- -- ---', '<hr />')


class TestSmartyAngledQuotes(TestCase):

    default_kwargs = {
        'extensions': ['smarty'],
        'extension_configs': {
            'smarty': {
                'smart_angled_quotes': True,
            },
        },
    }

    def test_angled_quotes(self):
        self.assertMarkdownRenders(
            '<<hello>>',
            '<p>&laquo;hello&raquo;</p>'
        )
        self.assertMarkdownRenders(
            'Кавычки-<<ёлочки>>',
            '<p>Кавычки-&laquo;ёлочки&raquo;</p>'
        )
        self.assertMarkdownRenders(
            'Anführungszeichen->>Chevrons<<',
            '<p>Anführungszeichen-&raquo;Chevrons&laquo;</p>'
        )


class TestSmartyCustomSubstitutions(TestCase):

    default_kwargs = {
        'extensions': ['smarty'],
        'extension_configs': {
            'smarty': {
                'smart_angled_quotes': True,
                'substitutions': {
                    'ndash': '\u2013',
                    'mdash': '\u2014',
                    'ellipsis': '\u2026',
                    'left-single-quote': '&sbquo;',  # `sb` is not a typo!
                    'right-single-quote': '&lsquo;',
                    'left-double-quote': '&bdquo;',
                    'right-double-quote': '&ldquo;',
                    'left-angle-quote': '[',
                    'right-angle-quote': ']',
                },
            },
        },
    }

    def test_custom_substitutions(self):
        text = (
            '<< The "Unicode char of the year 2014"\n'
            "is the 'mdash': ---\n"
            "Must not be confused with 'ndash'  (--) ... >>"
        )
        html = (
            '<p>[ The &bdquo;Unicode char of the year 2014&ldquo;\n'
            'is the &sbquo;mdash&lsquo;: \u2014\n'
            'Must not be confused with &sbquo;ndash&lsquo;  (\u2013) \u2026 ]</p>'
        )
        self.assertMarkdownRenders(text, html)


class TestSmartyLanguage(TestCase):

    default_kwargs = {
        'extensions': ['smarty'],
        'extension_configs': {
            'smarty': {
                'language': 'en',
            },
        },
    }

    def test_english_example(self):
        self.assertMarkdownRenders(
            'She said, "Read the **manual** and run `import "os"` first."',
            '<p>She said, &ldquo;Read the <strong>manual</strong> and run '
            '<code>import "os"</code> first.&rdquo;</p>'
        )

    def test_chinese_example(self):
        self.assertMarkdownRenders(
            '她说："请先阅读**手册**，再运行 `import "os"`。"',
            '<p>她说：&ldquo;请先阅读<strong>手册</strong>，再运行 '
            '<code>import "os"</code>。&rdquo;</p>',
            extension_configs={'smarty': {'language': 'zh-CN'}},
        )

    def test_french_example(self):
        self.assertMarkdownRenders(
            'Elle a dit : "Lisez le **manuel** et exécutez `import "os"`."',
            '<p>Elle a dit : &laquo;&nbsp;Lisez le <strong>manuel</strong> et '
            'exécutez <code>import "os"</code>.&nbsp;&raquo;</p>',
            extension_configs={'smarty': {'language': 'fr'}},
        )

    def test_nested_quotes_across_emphasis(self):
        self.assertMarkdownRenders(
            '"She said **\'hello\'**."',
            '<p>&ldquo;She said <strong>&lsquo;hello&rsquo;</strong>.&rdquo;</p>'
        )

    def test_quote_state_resets_at_paragraph_boundary(self):
        self.assertMarkdownRenders(
            '"unclosed\n\n"new paragraph"',
            '<p>&ldquo;unclosed</p>\n<p>&ldquo;new paragraph&rdquo;</p>'
        )

    def test_code_spans_and_code_blocks_are_skipped(self):
        self.assertMarkdownRenders(
            '"See `quote "x" \'y\'`."\n\n    "code" \'code\'',
            '<p>&ldquo;See <code>quote "x" \'y\'</code>.&rdquo;</p>\n'
            '<pre><code>"code" \'code\'\n</code></pre>'
        )

    def test_link_target_and_title_are_skipped(self):
        self.assertMarkdownRenders(
            '[a "b"](<http://example.com/?q="x"> "t")',
            '<p><a href="http://example.com/?q=&quot;x&quot;" title="t">'
            'a &ldquo;b&rdquo;</a></p>'
        )

    def test_html_attributes_are_skipped(self):
        self.assertMarkdownRenders(
            '<span title="q \'x\'">a "b"</span>',
            '<p><span title="q \'x\'">a &ldquo;b&rdquo;</span></p>'
        )

    def test_apostrophes_and_measurements(self):
        self.assertMarkdownRenders(
            "It's from the '80s, 5'10\", and rock 'n' roll.",
            '<p>It&rsquo;s from the &rsquo;80s, 5&prime;10&Prime;, and '
            'rock &rsquo;n&rsquo; roll.</p>'
        )

    def test_idempotent_typographic_punctuation(self):
        source = (
            'She said, &ldquo;Read the <strong>manual</strong> and run '
            '<code>import "os"</code> first.&rdquo;'
        )
        md = Markdown(**self.default_kwargs)
        output = md.convert(source)
        self.assertEqual(md.convert(output), output)

    def test_french_punctuation_is_idempotent(self):
        source = '&laquo;&nbsp;Bonjour <strong>monde</strong>&nbsp;&raquo;'
        kwargs = {
            'extensions': ['smarty'],
            'extension_configs': {'smarty': {'language': 'fr'}},
        }
        md = Markdown(**kwargs)
        output = md.convert(source)
        self.assertEqual(
            md.convert(output),
            '<p>&laquo;&nbsp;Bonjour <strong>monde</strong>&nbsp;&raquo;</p>'
        )


class TestSmartyAndToc(TestCase):

    default_kwargs = {
        'extensions': ['smarty', 'toc'],
    }

    def test_smarty_and_toc(self):
        self.assertMarkdownRenders(
            '# *Foo* --- `bar`',
            '<h1 id="foo-bar"><em>Foo</em> &mdash; <code>bar</code></h1>',
            expected_attrs={
                'toc_tokens': [
                    {
                        'level': 1,
                        'id': 'foo-bar',
                        'name': 'Foo &mdash; bar',
                        'html': '<em>Foo</em> &mdash; <code>bar</code>',
                        'data-toc-label': '',
                        'children': [],
                    },
                ],
            },
        )
