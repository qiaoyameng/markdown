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


class TestSmartyLanguageEn(TestCase):

    default_kwargs = {
        'extensions': ['smarty'],
        'extension_configs': {
            'smarty': {
                'language': 'en',
            },
        },
    }

    def test_quotes_around_bold(self):
        self.assertMarkdownRenders(
            '"Hello **world**"',
            '<p>\u201cHello <strong>world</strong>\u201d</p>'
        )

    def test_code_within_quotes(self):
        self.assertMarkdownRenders(
            '"Use `make` now"',
            '<p>\u201cUse <code>make</code> now\u201d</p>'
        )

    def test_nested_quotes(self):
        self.assertMarkdownRenders(
            '"she said \'hi\' to *me*"',
            '<p>\u201cshe said \u2018hi\u2019 to <em>me</em>\u201d</p>'
        )

    def test_quote_state_spans_emphasis(self):
        self.assertMarkdownRenders(
            '"a *little* test"',
            '<p>\u201ca <em>little</em> test\u201d</p>'
        )

    def test_quote_state_resets_at_paragraph(self):
        self.assertMarkdownRenders(
            '"unclosed first\n\n"second"',
            '<p>\u201cunclosed first</p>\n<p>\u201csecond\u201d</p>'
        )

    def test_apostrophes(self):
        self.assertMarkdownRenders(
            "It's the '80s, 1960's style",
            '<p>It\u2019s the \u201980s, 1960\u2019s style</p>'
        )

    def test_feet_and_inches(self):
        self.assertMarkdownRenders(
            'He is 6\'2" tall, not 5"',
            '<p>He is 6\u20322\u2033 tall, not 5\u2033</p>'
        )

    def test_code_spans_untouched(self):
        self.assertMarkdownRenders(
            'Skip `"code" and \'spans\'`.',
            '<p>Skip <code>"code" and \'spans\'</code>.</p>'
        )

    def test_link_targets_untouched(self):
        self.assertMarkdownRenders(
            '["link" text](http://example.com)',
            '<p><a href="http://example.com">\u201clink\u201d text</a></p>'
        )

    def test_html_attributes_untouched(self):
        self.assertMarkdownRenders(
            '<span title="don\'t">"hi"</span>',
            '<p><span title="don\'t">\u201chi\u201d</span></p>'
        )

    def test_escaped_quotes_untouched(self):
        self.assertMarkdownRenders(
            '\\"Escaped\\" and "real" quotes',
            '<p>"Escaped" and \u201creal\u201d quotes</p>'
        )

    def test_already_correct_punctuation(self):
        self.assertMarkdownRenders(
            '\u201cAlready \u2018correct\u2019, don\u2019t change it\u201d',
            '<p>\u201cAlready \u2018correct\u2019, don\u2019t change it\u201d</p>'
        )

    def test_invalid_language(self):
        with self.assertRaises(ValueError):
            self.assertMarkdownRenders(
                'text', '', extension_configs={'smarty': {'language': 'de'}}
            )


class TestSmartyLanguageFr(TestCase):

    default_kwargs = {
        'extensions': ['smarty'],
        'extension_configs': {
            'smarty': {
                'language': 'fr',
            },
        },
    }

    def test_quotes_around_bold(self):
        self.assertMarkdownRenders(
            '"Bonjour **monde**"',
            '<p>\u00ab\u202fBonjour <strong>monde</strong>\u202f\u00bb</p>'
        )

    def test_code_within_quotes(self):
        self.assertMarkdownRenders(
            '"lance `ls` ici"',
            '<p>\u00ab\u202flance <code>ls</code> ici\u202f\u00bb</p>'
        )

    def test_nested_quotes(self):
        self.assertMarkdownRenders(
            '"il dit \'salut\' ici"',
            '<p>\u00ab\u202fil dit \u201csalut\u201d ici\u202f\u00bb</p>'
        )

    def test_apostrophes(self):
        self.assertMarkdownRenders(
            "l'arbre d'aujourd'hui",
            '<p>l\u2019arbre d\u2019aujourd\u2019hui</p>'
        )

    def test_feet_and_inches(self):
        self.assertMarkdownRenders(
            '6\'2"',
            '<p>6\u20322\u2033</p>'
        )

    def test_quote_state_resets_at_paragraph(self):
        self.assertMarkdownRenders(
            '"premier\n\n"deuxi\u00e8me"',
            '<p>\u00ab\u202fpremier</p>\n<p>\u00ab\u202fdeuxi\u00e8me\u202f\u00bb</p>'
        )

    def test_already_correct_punctuation(self):
        self.assertMarkdownRenders(
            '\u00ab\u202fBonjour\u202f\u00bb',
            '<p>\u00ab\u202fBonjour\u202f\u00bb</p>'
        )


class TestSmartyLanguageZh(TestCase):

    default_kwargs = {
        'extensions': ['smarty'],
        'extension_configs': {
            'smarty': {
                'language': 'zh',
            },
        },
    }

    def test_quotes_around_bold(self):
        self.assertMarkdownRenders(
            '"\u4f60\u597d **\u4e16\u754c**"',
            '<p>\u201c\u4f60\u597d <strong>\u4e16\u754c</strong>\u201d</p>'
        )

    def test_code_within_quotes(self):
        self.assertMarkdownRenders(
            '"\u8fd0\u884c `python` \u5427"',
            '<p>\u201c\u8fd0\u884c <code>python</code> \u5427\u201d</p>'
        )

    def test_nested_quotes(self):
        self.assertMarkdownRenders(
            '"\u4ed6\u8bf4 \' \u4f60\u597d\' \u4e86"',
            '<p>\u201c\u4ed6\u8bf4 \u2018 \u4f60\u597d\u2019 \u4e86\u201d</p>'
        )

    def test_quote_state_resets_at_paragraph(self):
        self.assertMarkdownRenders(
            '"\u7b2c\u4e00\u6bb5\n\n"\u7b2c\u4e8c\u6bb5"',
            '<p>\u201c\u7b2c\u4e00\u6bb5</p>\n<p>\u201c\u7b2c\u4e8c\u6bb5\u201d</p>'
        )

    def test_already_correct_punctuation(self):
        self.assertMarkdownRenders(
            '\u201c\u5df2\u7ecf\u2018\u6b63\u786e\u2019\u4e86\u201d',
            '<p>\u201c\u5df2\u7ecf\u2018\u6b63\u786e\u2019\u4e86\u201d</p>'
        )
