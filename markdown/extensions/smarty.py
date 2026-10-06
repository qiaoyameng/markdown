# Smarty extension for Python-Markdown
# ====================================

# Adds conversion of ASCII dashes, quotes and ellipses to their HTML
# entity equivalents.

# See https://Python-Markdown.github.io/extensions/smarty
# for documentation.

# Author: 2013, Dmitry Shachnev <mitya57@gmail.com>

# All changes Copyright 2013-2014 The Python Markdown Project

# License: [BSD](https://opensource.org/licenses/bsd-license.php)

# SmartyPants license:

#    Copyright (c) 2003 John Gruber <https://daringfireball.net/>
#    All rights reserved.

#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are
#    met:

#    *  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.

#    *  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.

#    *  Neither the name "SmartyPants" nor the names of its contributors
#       may be used to endorse or promote products derived from this
#       software without specific prior written permission.

#    This software is provided by the copyright holders and contributors "as
#    is" and any express or implied warranties, including, but not limited
#    to, the implied warranties of merchantability and fitness for a
#    particular purpose are disclaimed. In no event shall the copyright
#    owner or contributors be liable for any direct, indirect, incidental,
#    special, exemplary, or consequential damages (including, but not
#    limited to, procurement of substitute goods or services; loss of use,
#    data, or profits; or business interruption) however caused and on any
#    theory of liability, whether in contract, strict liability, or tort
#    (including negligence or otherwise) arising in any way out of the use
#    of this software, even if advised of the possibility of such damage.


# `smartypants.py` license:

#    `smartypants.py` is a derivative work of SmartyPants.
#    Copyright (c) 2004, 2007 Chad Miller <http://web.chad.org/>

#    Redistribution and use in source and binary forms, with or without
#    modification, are permitted provided that the following conditions are
#    met:

#    *  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.

#    *  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.

#    This software is provided by the copyright holders and contributors "as
#    is" and any express or implied warranties, including, but not limited
#    to, the implied warranties of merchantability and fitness for a
#    particular purpose are disclaimed. In no event shall the copyright
#    owner or contributors be liable for any direct, indirect, incidental,
#    special, exemplary, or consequential damages (including, but not
#    limited to, procurement of substitute goods or services; loss of use,
#    data, or profits; or business interruption) however caused and on any
#    theory of liability, whether in contract, strict liability, or tort
#    (including negligence or otherwise) arising in any way out of the use
#    of this software, even if advised of the possibility of such damage.

"""
Convert ASCII dashes, quotes and ellipses to their HTML entity equivalents.

See the [documentation](https://Python-Markdown.github.io/extensions/smarty)
for details.
"""

from __future__ import annotations

from . import Extension
from ..inlinepatterns import HtmlInlineProcessor, HTML_RE
from ..treeprocessors import InlineProcessor, Treeprocessor
from ..util import Registry, BLOCK_LEVEL_ELEMENTS
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from markdown import Markdown
    from .. import inlinepatterns
    import re
    import xml.etree.ElementTree as etree

# Constants for quote education.
punctClass = r"""[!"#\$\%'()*+,-.\/:;<=>?\@\[\\\]\^_`{|}~]"""
endOfWordClass = r"[\s.,;:!?)]"
closeClass = r"[^\ \t\r\n\[\{\(\-\u0002\u0003]"

openingQuotesBase = (
    r'(\s'               # a  whitespace char
    r'|&nbsp;'           # or a non-breaking space entity
    r'|--'               # or dashes
    r'|–|—'              # or Unicode
    r'|&[mn]dash;'       # or named dash entities
    r'|&#8211;|&#8212;'  # or decimal entities
    r')'
)

substitutions = {
    'mdash': '&mdash;',
    'ndash': '&ndash;',
    'ellipsis': '&hellip;',
    'left-angle-quote': '&laquo;',
    'right-angle-quote': '&raquo;',
    'left-single-quote': '&lsquo;',
    'right-single-quote': '&rsquo;',
    'left-double-quote': '&ldquo;',
    'right-double-quote': '&rdquo;',
}


# Language-specific quote styles used by the `language` option.
#
# Each entry defines the characters used for paired double and single
# quotes, the apostrophe, the prime marks used for feet/inches and the
# spacing character the language requires inside its paired quotes
# (French requires a narrow no-break space inside its guillemets).
LANGUAGES = {
    'en': {
        'double': ('\u201c', '\u201d'),  # “ ”
        'single': ('\u2018', '\u2019'),  # ‘ ’
        'apostrophe': '\u2019',          # ’
        'primes': ('\u2032', '\u2033'),  # ′ ″
        'spacing': '',
    },
    'fr': {
        'double': ('\u00ab', '\u00bb'),  # « »
        'single': ('\u201c', '\u201d'),  # “ ”
        'apostrophe': '\u2019',          # ’
        'primes': ('\u2032', '\u2033'),  # ′ ″
        'spacing': '\u202f',             # narrow no-break space
    },
    'zh': {
        'double': ('\u201c', '\u201d'),  # “ ”
        'single': ('\u2018', '\u2019'),  # ‘ ’
        'apostrophe': '\u2019',          # ’
        'primes': ('\u2032', '\u2033'),  # ′ ″
        'spacing': '',
    },
}

# Tags whose content must never take part in quote substitution
# (code, raw HTML and the like).
QUOTE_SKIP_TAGS = frozenset({'pre', 'code', 'kbd', 'samp', 'script', 'style', 'textarea'})

# Characters after which a quote is assumed to open rather than close.
QUOTE_OPENING_CHARS = '([{<-\u2013\u2014\u2018\u2019\u201c\u201d\u00ab\u2039'

# Spacing characters which may already separate a quote from its content.
QUOTE_SPACING_CHARS = '\u202f\u00a0'


# Special case if the very first character is a quote
# followed by punctuation at a non-word-break. Close the quotes by brute force:
singleQuoteStartRe = r"^'(?=%s\B)" % punctClass
doubleQuoteStartRe = r'^"(?=%s\B)' % punctClass

# Special case for double sets of quotes, e.g.:
#   <p>He said, "'Quoted' words in a larger quote."</p>
doubleQuoteSetsRe = r""""'(?=\w)"""
singleQuoteSetsRe = r"""'"(?=\w)"""
doubleQuoteSetsRe2 = r'(?<=%s)\'"' % closeClass
singleQuoteSetsRe2 = r"(?<=%s)\"'" % closeClass

# Special case for decade abbreviations (the '80s):
decadeAbbrRe = r"(?<!\w)'(?=\d{2}s)"

# Get most opening double quotes:
openingDoubleQuotesRegex = r'%s"(?=\w)' % openingQuotesBase

# Double closing quotes:
closingDoubleQuotesRegex = r'"(?=\s)'
closingDoubleQuotesRegex2 = r'(?<=%s)"' % closeClass

# Get most opening single quotes:
openingSingleQuotesRegex = r"%s'(?=\w)" % openingQuotesBase

# Single closing quotes:
closingSingleQuotesRegex = r"(?<=%s)'(?!\s|s\b|\d)" % closeClass
closingSingleQuotesRegex2 = r"'(\s|s\b)"

# All remaining quotes should be opening ones
remainingSingleQuotesRegex = r"'"
remainingDoubleQuotesRegex = r'"'

HTML_STRICT_RE = HTML_RE + r'(?!\>)'


class SubstituteTextPattern(HtmlInlineProcessor):
    def __init__(self, pattern: str, replace: Sequence[int | str | etree.Element], md: Markdown):
        """ Replaces matches with some text. """
        HtmlInlineProcessor.__init__(self, pattern)
        self.replace = replace
        self.md = md

    def handleMatch(self, m: re.Match[str], data: str) -> tuple[str, int, int]:
        result = ''
        for part in self.replace:
            if isinstance(part, int):
                result += m.group(part)
            else:
                result += self.md.htmlStash.store(part)
        return result, m.start(0), m.end(0)


class QuoteState:
    """ Tracks open quotes and the preceding character within one block of inline content. """

    def __init__(self):
        self.stack: list[str] = []
        self.last_char: str = ''


class LanguageQuoteTreeprocessor(Treeprocessor):
    """
    Replace straight quotes with the paired quotes of a specific language.

    Unlike the classic SmartyPants regexes, this processor keeps track of
    opened quotes so that nested quotes and language-specific spacing are
    handled correctly. Quote state carries over inline elements such as
    emphasis, but is reset at every block-level (paragraph) boundary. The
    content of code-like elements, link targets, HTML attributes and raw
    (stashed) content never takes part in the substitution. As only straight
    ASCII quotes are replaced, text which already contains the correct
    typographic punctuation is left untouched.
    """

    def __init__(self, md: Markdown, language: str):
        self.md = md
        self.lang = LANGUAGES[language]

    def run(self, root: etree.Element) -> None:
        self._walk(root, None)

    def _walk(self, el: etree.Element, state: QuoteState | None) -> None:
        if state is None or el.tag in BLOCK_LEVEL_ELEMENTS:
            # Reset the quote state at every block-level (paragraph) boundary.
            state = QuoteState()
        if el.text:
            el.text = self._convert(str(el.text), state)
        for child in el:
            if child.tag in QUOTE_SKIP_TAGS:
                # Code and raw content are skipped, but their last character
                # still provides context for a quote which follows them.
                self._track_last_char(child, state)
            else:
                self._walk(child, state)
            if child.tail:
                child.tail = self._convert(child.tail, state)

    def _track_last_char(self, el: etree.Element, state: QuoteState) -> None:
        text = ''.join(el.itertext()).rstrip()
        if text:
            state.last_char = text[-1]

    def _convert(self, text: str, state: QuoteState) -> str:
        lang = self.lang
        spacing = lang['spacing']
        out: list[str] = []
        prev = state.last_char
        i = 0
        n = len(text)
        while i < n:
            ch = text[i]
            if ch != '"' and ch != "'":
                out.append(ch)
                prev = ch
                i += 1
                continue
            nxt = text[i+1] if i + 1 < n else ''
            nxt2 = text[i+2] if i + 2 < n else ''
            if ch == '"':
                if prev.isdigit() and not (state.stack and state.stack[-1] == 'double'):
                    # Inch mark after a number, e.g. `6'2"`.
                    out.append(lang['primes'][1])
                    prev = lang['primes'][1]
                elif (state.stack and state.stack[-1] == 'double'
                      and prev and not prev.isspace() and prev not in QUOTE_OPENING_CHARS):
                    if spacing and prev not in QUOTE_SPACING_CHARS:
                        out.append(spacing)
                    out.append(lang['double'][1])
                    prev = lang['double'][1]
                    state.stack.pop()
                else:
                    out.append(lang['double'][0])
                    if spacing and nxt not in QUOTE_SPACING_CHARS:
                        out.append(spacing)
                    prev = lang['double'][0]
                    state.stack.append('double')
            else:
                if prev.isdigit() and nxt.isdigit():
                    # Foot mark between digits, e.g. `6'2"`.
                    out.append(lang['primes'][0])
                    prev = lang['primes'][0]
                elif prev.isdigit() and nxt.isalpha():
                    # Possessive of a number, e.g. `1960's`.
                    out.append(lang['apostrophe'])
                    prev = lang['apostrophe']
                elif prev.isdigit() and not (state.stack and state.stack[-1] == 'single'):
                    # Foot mark after a number, e.g. `6'`.
                    out.append(lang['primes'][0])
                    prev = lang['primes'][0]
                elif prev.isalpha() and nxt.isalpha():
                    # Apostrophe within a word, e.g. `don't`, `l'arbre`.
                    out.append(lang['apostrophe'])
                    prev = lang['apostrophe']
                elif (not prev or prev.isspace() or prev in QUOTE_OPENING_CHARS) \
                        and nxt.isdigit() and nxt2.isdigit():
                    # Decade abbreviation, e.g. `'80s`.
                    out.append(lang['apostrophe'])
                    prev = lang['apostrophe']
                elif (state.stack and state.stack[-1] == 'single'
                      and prev and not prev.isspace() and prev not in QUOTE_OPENING_CHARS):
                    out.append(lang['single'][1])
                    prev = lang['single'][1]
                    state.stack.pop()
                else:
                    out.append(lang['single'][0])
                    prev = lang['single'][0]
                    state.stack.append('single')
            i += 1
        state.last_char = prev
        return ''.join(out)


class SmartyExtension(Extension):
    """ Add Smarty to Markdown. """
    def __init__(self, **kwargs):
        self.config = {
            'smart_quotes': [True, 'Educate quotes'],
            'smart_angled_quotes': [False, 'Educate angled quotes'],
            'smart_dashes': [True, 'Educate dashes'],
            'smart_ellipses': [True, 'Educate ellipses'],
            'substitutions': [{}, 'Overwrite default substitutions'],
            'language': ['', "Language used for quote substitution: 'en', 'fr' or 'zh'. "
                             "If not set, the classic SmartyPants quote substitution is used."],
        }
        """ Default configuration options. """
        super().__init__(**kwargs)
        self.substitutions: dict[str, str] = dict(substitutions)
        self.substitutions.update(self.getConfig('substitutions', default={}))

    def _addPatterns(
        self,
        md: Markdown,
        patterns: Sequence[tuple[str, Sequence[int | str | etree.Element]]],
        serie: str,
        priority: int,
    ):
        for ind, pattern in enumerate(patterns):
            pattern += (md,)
            pattern = SubstituteTextPattern(*pattern)
            name = 'smarty-%s-%d' % (serie, ind)
            self.inlinePatterns.register(pattern, name, priority-ind)

    def educateDashes(self, md: Markdown) -> None:
        emDashesPattern = SubstituteTextPattern(
            r'(?<!-)---(?!-)', (self.substitutions['mdash'],), md
        )
        enDashesPattern = SubstituteTextPattern(
            r'(?<!-)--(?!-)', (self.substitutions['ndash'],), md
        )
        self.inlinePatterns.register(emDashesPattern, 'smarty-em-dashes', 50)
        self.inlinePatterns.register(enDashesPattern, 'smarty-en-dashes', 45)

    def educateEllipses(self, md: Markdown) -> None:
        ellipsesPattern = SubstituteTextPattern(
            r'(?<!\.)\.{3}(?!\.)', (self.substitutions['ellipsis'],), md
        )
        self.inlinePatterns.register(ellipsesPattern, 'smarty-ellipses', 10)

    def educateAngledQuotes(self, md: Markdown) -> None:
        leftAngledQuotePattern = SubstituteTextPattern(
            r'\<\<', (self.substitutions['left-angle-quote'],), md
        )
        rightAngledQuotePattern = SubstituteTextPattern(
            r'\>\>', (self.substitutions['right-angle-quote'],), md
        )
        self.inlinePatterns.register(leftAngledQuotePattern, 'smarty-left-angle-quotes', 40)
        self.inlinePatterns.register(rightAngledQuotePattern, 'smarty-right-angle-quotes', 35)

    def educateQuotes(self, md: Markdown) -> None:
        lsquo = self.substitutions['left-single-quote']
        rsquo = self.substitutions['right-single-quote']
        ldquo = self.substitutions['left-double-quote']
        rdquo = self.substitutions['right-double-quote']
        patterns = (
            (singleQuoteStartRe, (rsquo,)),
            (doubleQuoteStartRe, (rdquo,)),
            (doubleQuoteSetsRe, (ldquo + lsquo,)),
            (singleQuoteSetsRe, (lsquo + ldquo,)),
            (doubleQuoteSetsRe2, (rsquo + rdquo,)),
            (singleQuoteSetsRe2, (rdquo + rsquo,)),
            (decadeAbbrRe, (rsquo,)),
            (openingSingleQuotesRegex, (1, lsquo)),
            (closingSingleQuotesRegex, (rsquo,)),
            (closingSingleQuotesRegex2, (rsquo, 1)),
            (remainingSingleQuotesRegex, (lsquo,)),
            (openingDoubleQuotesRegex, (1, ldquo)),
            (closingDoubleQuotesRegex, (rdquo,)),
            (closingDoubleQuotesRegex2, (rdquo,)),
            (remainingDoubleQuotesRegex, (ldquo,))
        )
        self._addPatterns(md, patterns, 'quotes', 30)

    def extendMarkdown(self, md):
        """ Register the processors.

        | Class Instance                                                              | Registry                                                         | Name   | Priority |
        | --------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------ | :------: |
        | [`markdown.treeprocessors.InlineProcessor`][markdown.treeprocessors.InlineProcessor] | [`treeprocessors`][markdown.treeprocessors.build_treeprocessors] | `smarty` | `6` |
        | [`markdown.inlinepatterns.HtmlInlineProcessor`][markdown.inlinepatterns.HtmlInlineProcessor] | [`inlinepatterns`][markdown.inlinepatterns.build_inlinepatterns] | `html` | `90` |

        The `HtmlInlineProcessor` , above, is only used if the `smart_angled_quotes` option is enabled.

        A [`LanguageQuoteTreeprocessor`][markdown.extensions.smarty.LanguageQuoteTreeprocessor]
        is registered as `smarty-language-quotes` with priority `7` if the `language` option is set,
        in which case it replaces the classic quote substitution patterns.

        The `InlineProcessor`, above, is a separate instance from the `InlineProcessor` used for
        standard inline parsing. It contains a collection of inline patterns dependent upon the
        various configuration options.

        """
        # flake8: noqa: E501 263-265
        configs = self.getConfigs()
        self.inlinePatterns: Registry[inlinepatterns.InlineProcessor] = Registry()
        if configs['smart_ellipses']:
            self.educateEllipses(md)
        language = configs['language']
        if language and language not in LANGUAGES:
            raise ValueError(
                "Unknown smarty language: %r. Expected one of: %s."
                % (language, ', '.join(sorted(LANGUAGES)))
            )
        if configs['smart_quotes']:
            if language:
                md.treeprocessors.register(
                    LanguageQuoteTreeprocessor(md, language), 'smarty-language-quotes', 7
                )
            else:
                self.educateQuotes(md)
        if configs['smart_angled_quotes']:
            self.educateAngledQuotes(md)
            # Override `HTML_RE` from `inlinepatterns.py` so that it does not
            # process tags with duplicate closing quotes.
            md.inlinePatterns.register(HtmlInlineProcessor(HTML_STRICT_RE, md), 'html', 90)
        if configs['smart_dashes']:
            self.educateDashes(md)
        inlineProcessor = InlineProcessor(md)
        inlineProcessor.inlinePatterns = self.inlinePatterns
        md.treeprocessors.register(inlineProcessor, 'smarty', 6)
        md.ESCAPED_CHARS.extend(['"', "'"])


def makeExtension(**kwargs):  # pragma: no cover
    return SmartyExtension(**kwargs)
