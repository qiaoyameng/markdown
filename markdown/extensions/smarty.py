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

import re

from . import Extension
from ..inlinepatterns import HtmlInlineProcessor, HTML_RE
from ..treeprocessors import InlineProcessor, Treeprocessor
from ..util import (
    Registry,
    HTML_PLACEHOLDER_RE,
    INLINE_PLACEHOLDER_RE,
    STX,
    ETX,
)
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from markdown import Markdown
    from .. import inlinepatterns
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
    'apostrophe': '&rsquo;',
    'prime': '&prime;',
    'double-prime': '&Prime;',
}

languageSettings = {
    'en': {},
    'zh': {},
    'fr': {
        'left-single-quote': '&lsaquo;&nbsp;',
        'right-single-quote': '&nbsp;&rsaquo;',
        'left-double-quote': '&laquo;&nbsp;',
        'right-double-quote': '&nbsp;&raquo;',
    },
}

ESCAPED_CHAR_RE = re.compile(re.escape(STX) + r'\d+' + re.escape(ETX))


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


class LanguageQuoteTreeprocessor(Treeprocessor):
    """ Pair straight quotes using the typographic rules of a language. """

    skipped_tags = {'code', 'script', 'style'}

    def __init__(self, md: Markdown, substitutions: dict[str, str], language: str):
        self.md = md
        self.substitutions = substitutions
        self.language = language

    def run(self, root):
        self._walk_element(root, _QuoteState(), root.tag not in self.skipped_tags)

    def _walk_element(self, element, state, active):
        if element.text:
            element.text = self._process_text(element.text, state, active)
        for child in element:
            is_block = self.md.is_block_level(child.tag)
            if is_block:
                child_state = _QuoteState()
                self._walk_element(
                    child, child_state, active and child.tag not in self.skipped_tags
                )
                if child.tail:
                    child.tail = self._process_text(child.tail, child_state, active)
                state = _QuoteState()
            else:
                self._walk_element(
                    child, state, active and child.tag not in self.skipped_tags
                )
            if child.tail and not is_block:
                child.tail = self._process_text(child.tail, state, active)

    def _process_text(self, text, state, active):
        if not active:
            return text

        result = []
        index = 0
        for match in re.finditer(
            r'%s|%s|%s' % (
                HTML_PLACEHOLDER_RE.pattern,
                INLINE_PLACEHOLDER_RE.pattern,
                ESCAPED_CHAR_RE.pattern,
            ),
            text
        ):
            if match.start() > index:
                self._process_plain_text(text[index:match.start()], state, result)
            inline_match = INLINE_PLACEHOLDER_RE.fullmatch(match.group(0))
            if inline_match:
                node_id = int(inline_match.group(1))
                node = self.md.treeprocessors['inline'].stashed_nodes.get(node_id)
                if getattr(node, 'tag', None) in self.skipped_tags:
                    result.append(match.group(0))
                    index = match.end()
                    continue
            result.append(match.group(0))
            index = match.end()
        if index < len(text):
            self._process_plain_text(text[index:], state, result)
        return ''.join(result)

    def _process_plain_text(self, text, state, result):
        index = 0
        while index < len(text):
            char = text[index]
            if char not in ('"', "'"):
                result.append(char)
                state.previous = char
                index += 1
                continue

            quote_type = self._get_quote_type(char, text, index, state)
            if quote_type is None:
                result.append(char)
                state.previous = char
                index += 1
                continue

            if self.language == 'fr' and char == '"':
                if quote_type == 'open' and index + 1 < len(text) and text[index + 1].isspace():
                    index += 1
                elif quote_type == 'close' and result and result[-1].isspace():
                    result.pop()

            result.append(self.md.htmlStash.store(self._get_replacement(char, quote_type)))
            self._update_state(char, quote_type, state)
            index += 1

    def _get_quote_type(self, char, text, index, state):
        previous = state.previous
        following = text[index + 1] if index + 1 < len(text) else ''
        after = text[index + 2] if index + 2 < len(text) else ''
        following_word = following.isalnum() or following in ('_',)

        if char in state.stack:
            return 'close'

        if char == "'":
            if previous.isdigit() and not (
                following == 's' and (not after or not after.isalnum())
            ):
                return 'prime'
            if self._is_apostrophe(previous, text, index):
                return 'apostrophe'
        elif previous.isdigit():
            return 'double-prime'

        if char == "'":
            if previous.isalnum() and not (not following and previous.isdigit()):
                return 'apostrophe'
            if following.isdigit() and self._is_decade(text, index):
                return 'apostrophe'
            if following_word and (not previous or not previous.isalnum()):
                return 'open'
            return None

        return 'open'

    def _is_apostrophe(self, previous, text, index):
        following = text[index + 1] if index + 1 < len(text) else ''
        after = text[index + 2] if index + 2 < len(text) else ''
        if previous.isalnum() and following.isalnum():
            return True
        if previous.isalnum() and following == 's' and (not after or not after.isalnum()):
            return True
        if previous in ('"', "'") and following == 's' and (not after or not after.isalnum()):
            return True
        if previous.isdigit() and following == 's':
            return True
        if not previous.isalnum() and following == 'n' and after == "'":
            return True
        if following.isdigit() and self._is_decade(text, index):
            return True
        return False

    def _is_decade(self, text, index):
        return (
            index + 4 <= len(text)
            and text[index + 1:index + 3].isdigit()
            and text[index + 3] == 's'
            and (index + 4 == len(text) or not text[index + 4].isalnum())
        )

    def _get_replacement(self, char, quote_type):
        if quote_type == 'apostrophe':
            return self.substitutions['apostrophe']
        if quote_type == 'prime':
            return self.substitutions['prime']
        if quote_type == 'double-prime':
            return self.substitutions['double-prime']

        direction = 'left' if quote_type == 'open' else 'right'
        kind = 'single' if char == "'" else 'double'
        return self.substitutions[f'{direction}-{kind}-quote']

    def _update_state(self, char, quote_type, state):
        if quote_type == 'open':
            state.stack.append(char)
            state.previous = char
        elif quote_type == 'close' and char in state.stack:
            while state.stack:
                item = state.stack.pop()
                if item == char:
                    break
            state.previous = char
        else:
            state.previous = char


class _QuoteState:
    def __init__(self):
        self.previous = ''
        self.stack = []


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


class SmartyExtension(Extension):
    """ Add Smarty to Markdown. """
    def __init__(self, **kwargs):
        self.config = {
            'language': ['', 'Language-specific quotation rules'],
            'smart_quotes': [True, 'Educate quotes'],
            'smart_angled_quotes': [False, 'Educate angled quotes'],
            'smart_dashes': [True, 'Educate dashes'],
            'smart_ellipses': [True, 'Educate ellipses'],
            'substitutions': [{}, 'Overwrite default substitutions'],
        }
        """ Default configuration options. """
        super().__init__(**kwargs)
        language = self.getConfig('language') or None
        if language is not None:
            language = language.lower().split('-', 1)[0].split('_', 1)[0]
            if language not in languageSettings:
                raise ValueError('Unsupported language: %s' % language)
        self.substitutions: dict[str, str] = dict(substitutions)
        if language is not None:
            self.substitutions.update(languageSettings[language])
        self.substitutions.update(self.getConfig('substitutions', default={}))
        self.language = language

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

        The `InlineProcessor`, above, is a separate instance from the `InlineProcessor` used for
        standard inline parsing. It contains a collection of inline patterns dependent upon the
        various configuration options.

        """
        # flake8: noqa: E501 263-265
        configs = self.getConfigs()
        self.inlinePatterns: Registry[inlinepatterns.InlineProcessor] = Registry()
        if configs['smart_ellipses']:
            self.educateEllipses(md)
        if configs['smart_quotes'] and self.language is None:
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
        if self.language is not None and configs['smart_quotes']:
            md.treeprocessors.register(
                LanguageQuoteTreeprocessor(md, self.substitutions, self.language),
                'smarty-language-quotes',
                15,
            )
        md.treeprocessors.register(inlineProcessor, 'smarty', 6)
        md.ESCAPED_CHARS.extend(['"', "'"])


def makeExtension(**kwargs):  # pragma: no cover
    return SmartyExtension(**kwargs)
