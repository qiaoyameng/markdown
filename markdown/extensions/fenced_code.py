# Fenced Code Extension for Python Markdown
# =========================================

# This extension adds Fenced Code Blocks to Python-Markdown.

# See https://Python-Markdown.github.io/extensions/fenced_code_blocks
# for documentation.

# Original code Copyright 2007-2008 [Waylan Limberg](https://github.com/waylan).

# All changes Copyright 2008-2014 The Python Markdown Project

# License: [BSD](https://opensource.org/licenses/bsd-license.php)

"""
This extension adds Fenced Code Blocks to Python-Markdown.

See the [documentation](https://Python-Markdown.github.io/extensions/fenced_code_blocks)
for details.
"""

from __future__ import annotations

import re
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Iterable

from . import Extension
from ..preprocessors import Preprocessor
from .codehilite import CodeHilite, CodeHiliteExtension, parse_hl_lines
from .attr_list import get_attrs_and_remainder, AttrListExtension
from ..util import parseBoolValue
from ..serializers import _escape_attrib_html

if TYPE_CHECKING:  # pragma: no cover
    from markdown import Markdown


class FencedCodeExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            'lang_prefix': ['language-', 'Prefix prepended to the language. Default: "language-"']
        }
        """ Default configuration options. """
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        """
        Register the processor.

        | Class Instance                                                              | Registry                                                         | Name   | Priority |
        | --------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------ | :------: |
        | [`FencedBlockPreprocessor`][markdown.extensions.fenced_code.FencedBlockPreprocessor] | [`blockprocessors`][markdown.blockprocessors.build_block_parser] | `fenced_code_block` | `25` |

        """
        # flake8: noqa: E501 50-52
        md.registerExtension(self)

        md.preprocessors.register(FencedBlockPreprocessor(md, self.getConfigs()), 'fenced_code_block', 25)


class FencedBlockPreprocessor(Preprocessor):
    """ Find and extract fenced code blocks. """

    FENCE_OPEN_RE = re.compile(
        r'^(?P<indent>[ ]{0,3})(?P<fence>(?P<fence_char>`{3,}|~{3,}))[ ]*'
        r'(?:\{(?P<attrs>[^\n]*)\}|'
        r'(?:\.?(?P<lang>[\w#.+-]*)[ ]*)?'
        r'(?:hl_lines=(?P<quot>"|\')(?P<hl_lines>.*?)(?P=quot)[ ]*)?)?$'
    )
    LIST_ITEM_RE = re.compile(
        r'^(?P<indent>[ ]*)(?:\d+\.|[*+-])[ ]+(?=\S)'
    )
    CONTAINER_QUOTE_RE = re.compile(r'^(?P<prefix>[ ]{0,3}>[ ]?)(?P<rest>.*)$')
    FENCED_BLOCK_RE = re.compile(
        dedent(r'''
            (?P<fence>^(?:~{3,}|`{3,}))[ ]*                          # opening fence
            ((\{(?P<attrs>[^\n]*)\})|                                # (optional {attrs} or
            (\.?(?P<lang>[\w#.+-]*)[ ]*)?                            # optional (.)lang
            (hl_lines=(?P<quot>"|')(?P<hl_lines>.*?)(?P=quot)[ ]*)?) # optional hl_lines)
            \n                                                       # newline (end of opening fence)
            (?P<code>.*?)(?<=\n)                                     # the code block
            (?P=fence)[ ]*$                                          # closing fence
        '''),
        re.MULTILINE | re.DOTALL | re.VERBOSE
    )

    def __init__(self, md: Markdown, config: dict[str, Any]):
        super().__init__(md)
        self.config = config
        self.checked_for_deps = False
        self.codehilite_conf: dict[str, Any] = {}
        self.use_attr_list = False
        # List of options to convert to boolean values
        self.bool_options = [
            'linenums',
            'guess_lang',
            'noclasses',
            'use_pygments'
        ]

    def run(self, lines: list[str]) -> list[str]:
        """ Match and store Fenced Code Blocks in the `HtmlStash`. """

        # Check for dependent extensions
        if not self.checked_for_deps:
            for ext in self.md.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.getConfigs()
                if isinstance(ext, AttrListExtension):
                    self.use_attr_list = True

            self.checked_for_deps = True

        result: list[str] = []
        index = 0
        list_columns: list[int] = []
        skip_state_before_index: int | None = None
        while index < len(lines):
            line = lines[index]
            if skip_state_before_index is not None and index >= skip_state_before_index:
                skip_state_before_index = None
            if skip_state_before_index is None:
                self._update_list_columns(line, list_columns)
                context = self._get_container_context(line, list_columns)
                opener = self._parse_opener(line, context)
            else:
                opener = None
            if opener is None:
                result.append(line)
                index += 1
                continue
            closing_index = self._find_closing(lines, index + 1, opener)
            if closing_index is None:
                result.append(line)
                index += 1
                continue
            skip_state_before_index = closing_index
            code_lines = self._extract_code(lines[index + 1:closing_index], opener)
            code = self._render_code('\n'.join(code_lines), opener)
            placeholder = self.md.htmlStash.store(code)
            prefix_parts = ''.join(context['prefix_parts'])
            placeholder_line = f'{prefix_parts}{placeholder}'
            if not context['prefix_parts']:
                if result and result[-1] != '':
                    result.append('')
                result.append(placeholder_line)
                if closing_index + 1 < len(lines) and lines[closing_index + 1] != '':
                    result.append('')
            else:
                result.append(placeholder_line)
            index = closing_index + 1
        return result

    def _update_list_columns(self, line: str, list_columns: list[int]) -> None:
        context = self._get_container_context(line, list_columns)
        list_indent = context['list_indent']
        quote_prefix = context['quote_prefix']
        rest = line[context['content_column']:]
        if not rest.strip():
            return
        quote_column = len(list_indent) + len(quote_prefix)
        list_match = self.LIST_ITEM_RE.match(rest)
        if list_match is not None:
            content_column = quote_column + len(list_match.group('indent')) + self.md.tab_length
            while list_columns and list_columns[-1] >= content_column:
                list_columns.pop()
            list_columns.append(content_column)
            return

        if line.strip():
            indent_match = re.match(r'^([ ]*)', line)
            indentation = len(indent_match.group(1))
            while list_columns and indentation < list_columns[-1] and not quote_prefix:
                list_columns.pop()

    def _get_container_context(self, line: str, list_columns: list[int]) -> dict[str, Any]:
        """ Return the ordered container prefixes preceding content. """
        prefix_parts: list[str] = []
        remaining = line

        while remaining:
            indent_match = re.match(r'^([ ]+)', remaining)
            if indent_match is not None and list_columns:
                absolute_indentation = len(''.join(prefix_parts)) + len(indent_match.group(1))
                prefix_start = len(''.join(prefix_parts))
                possible_columns = [col for col in list_columns if absolute_indentation >= col]
                if possible_columns:
                    prefix_end = max(possible_columns)
                    if prefix_end > prefix_start:
                        indentation_length = prefix_end - prefix_start
                        prefix_parts.append(remaining[:indentation_length])
                        remaining = remaining[indentation_length:]
                        continue

            quote_match = self.CONTAINER_QUOTE_RE.match(remaining)
            if quote_match is not None:
                prefix_parts.append(quote_match.group('prefix'))
                remaining = quote_match.group('rest')
                continue
            break

        list_indent = ''.join(part for part in prefix_parts if part.isspace())
        quote_prefix = ''.join(part for part in prefix_parts if not part.isspace())
        return {
            'prefix_parts': prefix_parts,
            'list_indent': list_indent,
            'quote_prefix': quote_prefix,
            'content_column': len(''.join(prefix_parts)),
        }

    def _parse_opener(self, line: str, context: dict[str, Any]) -> dict[str, Any] | None:
        content = line[context['content_column']:]
        match = self.FENCE_OPEN_RE.match(content)
        if match is None:
            return None
        if not context['list_indent'] and not context['quote_prefix'] and match.group('indent'):
            # Preserve the historical rule that root-level fenced blocks cannot be indented.
            return None
        opener = {
            'context': context,
            'fence': match.group('fence'),
            'fence_char': match.group('fence_char')[0],
            'fence_length': len(match.group('fence')),
            'fence_indent': len(match.group('indent')),
            'attrs': match.group('attrs'),
            'lang': match.group('lang'),
            'hl_lines': match.group('hl_lines'),
        }
        if opener['attrs'] is not None and get_attrs_and_remainder(opener['attrs'])[1]:
            return None
        return opener

    def _find_closing(
        self, lines: list[str], start: int, opener: dict[str, Any]
    ) -> int | None:
        context = opener['context']
        closing_re = re.compile(
            r'^[ ]{0,%d}%s[ ]*$' % (opener['fence_indent'], re.escape(opener['fence']))
        )
        for index in range(start, len(lines)):
            content, is_container_line = self._get_line_content(lines[index], context)
            if is_container_line and closing_re.match(content):
                return index
            if is_container_line:
                continue
            if context['quote_prefix'] or context['list_indent']:
                break
        return None

    def _get_line_content(self, line: str, context: dict[str, Any]) -> tuple[str, bool]:
        if not line.strip():
            return '', True
        if not context['prefix_parts']:
            return line, True
        remaining = line
        for part in context['prefix_parts']:
            if part.isspace():
                indent_match = re.match(r'^([ ]+)', remaining)
                if indent_match is None or len(indent_match.group(1)) < len(part):
                    return '', False
                remaining = remaining[len(part):]
            else:
                quote_match = self.CONTAINER_QUOTE_RE.match(remaining)
                if quote_match is None:
                    return '', False
                remaining = quote_match.group('rest')
        return remaining, True

    def _extract_code(self, lines: list[str], opener: dict[str, Any]) -> list[str]:
        context = opener['context']
        removable_indent = opener['fence_indent'] + 3
        code = []
        for line in lines:
            content, is_container_line = self._get_line_content(line, context)
            if is_container_line:
                if context['prefix_parts'] and content.startswith(' '):
                    content = content[min(removable_indent, len(content) - len(content.lstrip(' '))):]
                code.append(content)
            elif not line.strip():
                code.append('')
            else:
                # A line without the full container prefix leaves the code block's container.
                break
        if code:
            code.append('')
        return code

    def _render_code(self, code: str, opener: dict[str, Any]) -> str:
        lang, id, classes, config = None, '', [], {}
        if opener['attrs'] is not None:
            attrs, remainder = get_attrs_and_remainder(opener['attrs'])
            if remainder:
                return ''
            id, classes, config = self.handle_attrs(attrs)
            if len(classes):
                lang = classes.pop(0)
        else:
            if opener['lang']:
                lang = opener['lang']
            if opener['hl_lines']:
                # Support `hl_lines` outside of `attrs` for backward-compatibility
                config['hl_lines'] = parse_hl_lines(opener['hl_lines'])

        # If `config` is not empty, then the `codehighlite` extension
        # is enabled, so we call it to highlight the code
        if self.codehilite_conf and self.codehilite_conf['use_pygments'] and config.get('use_pygments', True):
            local_config = self.codehilite_conf.copy()
            local_config.update(config)
            # Combine classes with `cssclass`. Ensure `cssclass` is at end
            # as Pygments appends a suffix under certain circumstances.
            # Ignore ID as Pygments does not offer an option to set it.
            if classes:
                local_config['css_class'] = '{} {}'.format(
                    ' '.join(classes),
                    local_config['css_class']
                )
            highliter = CodeHilite(
                code,
                lang=lang,
                style=local_config.pop('pygments_style', 'default'),
                **local_config
            )

            return highliter.hilite(shebang=False)

        id_attr = lang_attr = class_attr = kv_pairs = ''
        if lang:
            prefix = self.config.get('lang_prefix', 'language-')
            lang_attr = f' class="{prefix}{_escape_attrib_html(lang)}"'
        if classes:
            class_attr = f' class="{_escape_attrib_html(" ".join(classes))}"'
        if id:
            id_attr = f' id="{_escape_attrib_html(id)}"'
        if self.use_attr_list and config and not config.get('use_pygments', False):
            # Only assign key/value pairs to code element if `attr_list` extension is enabled, key/value
            # pairs were defined on the code block, and the `use_pygments` key was not set to `True`. The
            # `use_pygments` key could be either set to `False` or not defined. It is omitted from output.
            kv_pairs = ''.join(
                f' {k}="{_escape_attrib_html(v)}"' for k, v in config.items() if k != 'use_pygments'
            )
        code = self._escape(code)
        return f'<pre{id_attr}{class_attr}><code{lang_attr}{kv_pairs}>{code}</code></pre>'

    def handle_attrs(self, attrs: Iterable[tuple[str, str]]) -> tuple[str, list[str], dict[str, Any]]:
        """ Return tuple: `(id, [list, of, classes], {configs})` """
        id = ''
        classes = []
        configs = {}
        for k, v in attrs:
            if k == 'id':
                id = v
            elif k == '.':
                classes.append(v)
            elif k == 'hl_lines':
                configs[k] = parse_hl_lines(v)
            elif k in self.bool_options:
                configs[k] = parseBoolValue(v, fail_on_errors=False, preserve_none=True)
            else:
                configs[k] = v
        return id, classes, configs

    def _escape(self, txt: str) -> str:
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt


def makeExtension(**kwargs):  # pragma: no cover
    return FencedCodeExtension(**kwargs)
