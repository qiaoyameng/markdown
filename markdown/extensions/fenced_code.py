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

from dataclasses import dataclass, field
import re
import xml.etree.ElementTree as etree
from . import Extension
from ..blockprocessors import BlockProcessor, BlockQuoteProcessor
from ..postprocessors import Postprocessor
from ..preprocessors import Preprocessor
from ..treeprocessors import Treeprocessor
from .codehilite import CodeHilite, CodeHiliteExtension, parse_hl_lines
from .attr_list import get_attrs_and_remainder, AttrListExtension
from ..util import parseBoolValue
from ..serializers import _escape_attrib_html
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:  # pragma: no cover
    from markdown import Markdown


FENCE_MARKER = '\u0000fenced-code-fence\u0000'
EMPTY_QUOTE_MARKER = '\u0000fenced-code-empty-quote\u0000'
EMPTY_LIST_MARKER = '\u0000fenced-code-empty-list\u0000'


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

        config = self.getConfigs()
        preprocessor = FencedBlockPreprocessor(md, config)
        block_processor = FencedBlockProcessor(md, preprocessor)
        self.block_processor = block_processor
        blank_line_preprocessor = FencedListBlankLinePreprocessor(md)

        md.preprocessors.register(blank_line_preprocessor, 'fenced_code_list_blank_lines', 31)
        md.preprocessors.register(preprocessor, 'fenced_code_block', 25)
        md.treeprocessors.register(FenceFinishingTreeprocessor(md, block_processor), 'fenced_code_block', 25)
        md.postprocessors.register(FenceMarkerPostprocessor(md), 'fenced_code_fence_marker', 25)
        md.parser.blockprocessors.register(block_processor, 'fenced_code_block', 95)
        md.parser.blockprocessors.register(
            FencedBlockQuoteProcessor(md.parser, block_processor),
            'quote',
            20
        )

    def reset(self) -> None:
        self.block_processor.reset()


class FencedBlockPreprocessor(Preprocessor):
    """ Find and extract fenced code blocks. """

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

        text = "\n".join(lines)
        index = 0
        while 1:
            m = self.FENCED_BLOCK_RE.search(text, index)
            if m:
                lang, id, classes, config = None, '', [], {}
                if m.group('attrs'):
                    attrs, remainder = get_attrs_and_remainder(m.group('attrs'))
                    if remainder:  # Does not have correctly matching curly braces, so the syntax is invalid.
                        index = m.end('attrs')  # Explicitly skip over this, to prevent an infinite loop.
                        continue
                    id, classes, config = self.handle_attrs(attrs)
                    if len(classes):
                        lang = classes.pop(0)
                else:
                    if m.group('lang'):
                        lang = m.group('lang')
                    if m.group('hl_lines'):
                        # Support `hl_lines` outside of `attrs` for backward-compatibility
                        config['hl_lines'] = parse_hl_lines(m.group('hl_lines'))

                code = self.render_code(m.group('code'), lang, id, classes, config)
                placeholder = self.md.htmlStash.store(code)
                text = f'{text[:m.start()]}\n{placeholder}\n{text[m.end():]}'
                # Continue from after the replaced text in the next iteration.
                index = m.start() + 1 + len(placeholder)
            else:
                break
        return text.split("\n")

    def render_code(
        self,
        code: str,
        lang: str | None,
        id: str,
        classes: list[str],
        config: dict[str, Any]
    ) -> str:
        """ Render fenced code content using top-level fence behavior. """
        if self.codehilite_conf and self.codehilite_conf['use_pygments'] and config.get('use_pygments', True):
            local_config = self.codehilite_conf.copy()
            local_config.update(config)
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


@dataclass
class PendingFence:
    parent: etree.Element
    path: list[etree.Element]
    fence: str
    marker_depth: int
    lang: str | None
    id: str
    classes: list[str]
    config: dict[str, Any]
    code_lines: list[str] = field(default_factory=list)


class FencedBlockProcessor(BlockProcessor):
    """ Process fenced code blocks inside list items and blockquotes. """

    FENCE_RE = re.compile(
        r'^(?P<indent>[ ]{0,3})(?P<fence>(?P<char>[`~])(?P=char){2,})(?P<info>.*?)(?P<marker>'
        + r'(?:' + re.escape(FENCE_MARKER) + r')*)?$'
    )

    def __init__(self, md: Markdown, preprocessor: FencedBlockPreprocessor):
        super().__init__(md.parser)
        self.md = md
        self.preprocessor = preprocessor
        self.reset()

    def reset(self) -> None:
        self.pending: PendingFence | None = None

    def test(self, parent: etree.Element, block: str) -> bool:
        if self.pending is not None:
            if parent is self.pending.parent:
                return True
            if not self.block_belongs_to_pending(parent, block):
                self.finish_pending()
            return False

        if parent.tag not in ('li', 'blockquote'):
            return False

        lines = block.split('\n')
        first_line = next((line for line in lines if line.strip()), '')
        match = self.match_fence(first_line)
        return match is not None and (
            len(match.group('indent')) <= 3 and
            (not match.group('info').strip() or self.parse_info(match.group('info')) is not None)
        )

    def run(self, parent: etree.Element, blocks: list[str]) -> None:
        if self.pending is None:
            block = blocks.pop(0)
            lines = block.split('\n')
            index = next(i for i, line in enumerate(lines) if line.strip())
            match = self.match_fence(lines[index])
            if match is None:
                blocks.insert(0, block)
                return
            parsed = self.parse_info(match.group('info'))
            if parsed is None or len(match.group('indent')) > 3:
                blocks.insert(0, block)
                return
            lang, id, classes, config = parsed

            before = '\n'.join(lines[:index])
            if before:
                self.parser.parseBlocks(parent, [before])

            remaining = lines[index + 1:]
            close_index, remaining = self.find_close(remaining, match)
            if close_index is None:
                self.pending = PendingFence(
                    parent=parent,
                    fence=match.group('fence'),
                    marker_depth=self.marker_depth(match),
                    lang=lang,
                    id=id,
                    classes=classes,
                    config=config,
                    path=self.get_path(parent),
                    code_lines=self.clean_code_lines(remaining)
                )
                return

            code_lines = self.clean_code_lines(self.preserve_blank_lines(remaining[:close_index]))
            after = remaining[close_index + 1:]
            self.store_code(parent, code_lines, lang, id, classes, config)
            if after:
                blocks.insert(0, '\n'.join(after).lstrip('\n'))
            return

        pending = self.pending
        block = blocks.pop(0)
        lines = block.split('\n')
        close_index, remaining = self.find_close(
            lines,
            fence=pending.fence,
            marker_depth=pending.marker_depth
        )
        if close_index is None:
            if pending.parent.tag == 'li' and lines and self.lines_belong_to_list(lines):
                pending.code_lines.append('')
            pending.code_lines.extend(self.clean_code_lines(lines))
            return

        pending.code_lines.extend(
            self.clean_code_lines(self.preserve_blank_lines(lines[:close_index]))
        )
        code_lines = pending.code_lines
        parent = pending.parent
        lang = pending.lang
        id = pending.id
        classes = pending.classes
        config = pending.config
        self.pending = None
        self.store_code(parent, code_lines, lang, id, classes, config)

        after = remaining[close_index + 1:]
        if after:
            blocks.insert(0, '\n'.join(after).lstrip('\n'))

    def finish_pending(self) -> None:
        if self.pending is None:
            return
        pending = self.pending
        self.pending = None
        self.store_code(
            pending.parent,
            pending.code_lines,
            pending.lang,
            pending.id,
            pending.classes,
            pending.config
        )

    def get_path(self, element: etree.Element) -> list[etree.Element]:
        def find(parent: etree.Element) -> list[etree.Element] | None:
            if parent is element:
                return [parent]
            for child in parent:
                path = find(child)
                if path is not None:
                    return [parent, *path]
            return None

        path = find(self.parser.root)
        return path if path is not None else [element]

    def block_belongs_to_pending(self, parent: etree.Element, block: str) -> bool:
        pending = self.pending
        if pending is None:
            return False
        try:
            index = next(i for i, element in enumerate(pending.path) if element is parent)
        except StopIteration:
            return False

        remaining = pending.path[index + 1:]
        first_line = next((line for line in block.split('\n') if line.strip()), '')
        prefix_pattern = ''
        for element in remaining:
            if element.tag == 'blockquote':
                prefix_pattern += r'[ ]{0,3}>[ ]?'
            elif element.tag == 'li':
                prefix_pattern += r'[ ]+'
        return re.match(prefix_pattern, first_line) is not None

    def match_fence(
        self,
        line: str,
        fence: str | None = None,
        marker_depth: int | None = None
    ) -> re.Match[str] | None:
        match = self.FENCE_RE.match(line)
        if match is None:
            return None
        if fence is not None and match.group('fence') != fence:
            return None
        if marker_depth is not None and self.marker_depth(match) != marker_depth:
            return None
        return match

    def find_close(
        self,
        lines: list[str],
        match: re.Match[str] | None = None,
        fence: str | None = None,
        marker_depth: int = 0
    ) -> tuple[int | None, list[str]]:
        if match is not None:
            fence = match.group('fence')
            marker_depth = self.marker_depth(match)
        for index, line in enumerate(lines):
            close_match = self.match_fence(line, fence=fence, marker_depth=marker_depth)
            if close_match is not None and not close_match.group('info').strip():
                return index, lines
        return None, lines

    def parse_info(self, info: str) -> tuple[str | None, str, list[str], dict[str, Any]] | None:
        info = info.strip()
        if not info:
            return None, '', [], {}
        if info.startswith('{'):
            attrs, remainder = get_attrs_and_remainder(info[1:-1].strip())
            if remainder:
                return None
            id, classes, config = self.preprocessor.handle_attrs(attrs)
            lang = classes.pop(0) if classes else None
            return lang, id, classes, config

        parts = info.split(None, 1)
        lang = parts[0]
        if not re.fullmatch(r'\.?[\w#.+-]*', lang):
            return None
        config = {}
        if len(parts) > 1:
            hl_lines_match = re.fullmatch(
                r'hl_lines=(?P<quote>"|\')(?P<hl_lines>.*?)(?P=quote)[ ]*',
                parts[1]
            )
            if hl_lines_match is None:
                return None
            config['hl_lines'] = parse_hl_lines(hl_lines_match.group('hl_lines'))
        return lang.lstrip('.'), '', [], config

    def clean_code_lines(self, lines: list[str]) -> list[str]:
        cleaned = []
        for line in lines:
            if not line.strip() or line.strip() == EMPTY_LIST_MARKER:
                cleaned.append('')
                continue
            while line.endswith(FENCE_MARKER):
                line = line[:-len(FENCE_MARKER)]
            if line == EMPTY_QUOTE_MARKER:
                line = ''
            cleaned.append(line)
        return cleaned

    def marker_depth(self, match: re.Match[str]) -> int:
        return len(match.group('marker') or '') // len(FENCE_MARKER)

    def lines_belong_to_list(self, lines: list[str]) -> bool:
        return bool(next((line for line in lines if line.strip()), ''))

    def preserve_blank_lines(self, lines: list[str]) -> list[str]:
        return ['' if not line.strip() else line for line in lines]

    def store_code(
        self,
        parent: etree.Element,
        code_lines: list[str],
        lang: str | None,
        id: str,
        classes: list[str],
        config: dict[str, Any]
    ) -> None:
        code = '\n'.join(code_lines)
        if code:
            code += '\n'
        rendered = self.preprocessor.render_code(code, lang, id, classes, config)
        placeholder = self.md.htmlStash.store(rendered)
        paragraph = etree.SubElement(parent, 'p')
        paragraph.text = placeholder


class FencedBlockQuoteProcessor(BlockQuoteProcessor):
    """ Preserve which quote container owns a fence line. """

    RAW_QUOTE_RE = re.compile(r'^((?:[ ]{0,3}>[ ]?)*)')

    def __init__(self, parser, fenced_block_processor: FencedBlockProcessor):
        super().__init__(parser)
        self.fenced_block_processor = fenced_block_processor

    def clean(self, line: str) -> str:
        depth = len(self.RAW_QUOTE_RE.match(line).group(1).split('>')) - 1
        if getattr(self, 'fence_depth', None) == depth and line.strip() == '>':
            return EMPTY_QUOTE_MARKER

        cleaned = super().clean(line)
        match = self.fenced_block_processor.FENCE_RE.match(cleaned)
        if match is None:
            return cleaned

        if self.fence_depth == depth and match.group('fence') == self.fence and not match.group('info').strip():
            cleaned += FENCE_MARKER * depth
            self.fence_depth = None
        elif self.fence_depth is None and (
            not match.group('info').strip() or
            self.fenced_block_processor.parse_info(match.group('info')) is not None
        ):
            cleaned += FENCE_MARKER * depth
            self.fence_depth = depth
            self.fence = match.group('fence')
        return cleaned

    def run(self, parent, blocks):
        self.fence_depth = None
        self.fence = ''
        return super().run(parent, blocks)


class FenceMarkerPostprocessor(Postprocessor):
    """ Remove fence ownership markers from any content that was not fenced. """

    def run(self, text: str) -> str:
        return (
            text.replace(FENCE_MARKER, '')
                .replace(EMPTY_QUOTE_MARKER, '')
                .replace(EMPTY_LIST_MARKER, '')
        )


class FenceFinishingTreeprocessor(Treeprocessor):
    """ Finish any fence left open at the end of its container. """

    def __init__(self, md: Markdown, block_processor: FencedBlockProcessor):
        super().__init__(md)
        self.block_processor = block_processor

    def run(self, root: etree.Element) -> None:
        self.block_processor.finish_pending()


class FencedListBlankLinePreprocessor(Preprocessor):
    """ Preserve blank lines that occur inside an indented fence. """

    FENCE_RE = re.compile(r'^(?P<indent>[ ]+)(?P<fence>(?P<char>[`~])(?P=char){2,})(?P<info>.*)$')

    def run(self, lines: list[str]) -> list[str]:
        result = []
        open_indent = None
        open_fence: tuple[str, str] | None = None
        for index, line in enumerate(lines):
            if not line.strip():
                if open_indent is not None and self.next_nonempty_line(lines, index).startswith(open_indent):
                    result.append(open_indent + EMPTY_LIST_MARKER)
                    continue
            else:
                match = self.FENCE_RE.match(line)
                if (
                    open_fence is not None and
                    match is not None and
                    match.group('fence') == open_fence[1] and
                    not match.group('info').strip()
                ):
                    open_indent = None
                    open_fence = None
                elif match is not None and open_indent is None:
                    open_indent = match.group('indent')
                    open_fence = (match.group('char'), match.group('fence'))
                elif open_indent is not None and not line.startswith(open_indent):
                    open_indent = None
                    open_fence = None
            result.append(line)
        return result

    def next_nonempty_line(self, lines: list[str], index: int) -> str:
        for line in lines[index:]:
            if line.strip():
                return line
        return ''
