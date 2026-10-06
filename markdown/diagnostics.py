"""
Diagnostics collected while parsing Markdown.

Diagnostics describe the source document only. They are never inserted into
the serialized output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import weakref
from typing import Literal


ReferenceType = Literal['full', 'collapsed', 'short']


@dataclass(frozen=True)
class ReferenceDefinition:
    """A link reference definition accepted by the block parser."""

    label: str
    normalized_label: str
    url: str
    title: str | None
    line: int | None


@dataclass(frozen=True)
class ReferenceUse:
    """A link or image reference accepted by an inline processor."""

    label: str
    normalized_label: str
    line: int | None
    reference_type: ReferenceType
    is_image: bool


@dataclass(frozen=True)
class ReferenceDiagnostic:
    """A problem with a link reference."""

    category: Literal['unknown', 'conflict', 'unused']
    label: str
    line: int | None = None
    message: str = ''
    reference_type: ReferenceType | None = None
    is_image: bool | None = None
    definitions: tuple[ReferenceDefinition, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Return a plain dictionary suitable for JSON serialization."""
        result = {
            'category': self.category,
            'label': self.label,
            'line': self.line,
            'message': self.message,
        }
        if self.reference_type is not None:
            result['reference_type'] = self.reference_type
        if self.is_image is not None:
            result['is_image'] = self.is_image
        if self.definitions:
            result['definitions'] = [
                {
                    'label': definition.label,
                    'normalized_label': definition.normalized_label,
                    'url': definition.url,
                    'title': definition.title,
                    'line': definition.line,
                }
                for definition in self.definitions
            ]
        return result


@dataclass
class ReferenceDiagnostics:
    """Reference definitions, uses, and problems found in one conversion."""

    definitions: dict[str, list[ReferenceDefinition]] = field(default_factory=dict)
    uses: list[ReferenceUse] = field(default_factory=list)

    def reset(self) -> None:
        """Clear all collected reference information."""
        self.definitions.clear()
        self.uses.clear()

    def add_definition(
        self,
        label: str,
        normalized_label: str,
        url: str,
        title: str | None,
        line: int | None,
    ) -> None:
        """Record one accepted definition."""
        definition = ReferenceDefinition(label, normalized_label, url, title, line)
        self.definitions.setdefault(normalized_label, []).append(definition)

    def add_use(
        self,
        label: str,
        normalized_label: str,
        line: int | None,
        reference_type: ReferenceType,
        is_image: bool,
    ) -> None:
        """Record one accepted full, collapsed, or short reference."""
        self.uses.append(
            ReferenceUse(label, normalized_label, line, reference_type, is_image)
        )

    @property
    def unknown_references(self) -> list[ReferenceDiagnostic]:
        """References whose normalized label has no definition."""
        return [
            ReferenceDiagnostic(
                'unknown',
                use.label,
                use.line,
                'Unknown link reference: %r' % use.label,
                use.reference_type,
                use.is_image,
            )
            for use in self.uses
            if use.normalized_label not in self.definitions
        ]

    @property
    def conflicting_definitions(self) -> list[ReferenceDiagnostic]:
        """Definitions which collide after parser label normalization."""
        result = []
        for definitions in self.definitions.values():
            if len(definitions) > 1:
                for definition in definitions[1:]:
                    result.append(
                        ReferenceDiagnostic(
                            'conflict',
                            definition.label,
                            definition.line,
                            'Duplicate link reference definition: %r'
                            % definition.label,
                            definitions=tuple(definitions),
                        )
                    )
        return result

    @property
    def unused_definitions(self) -> list[ReferenceDiagnostic]:
        """Definitions never used by a link or image reference."""
        used = {use.normalized_label for use in self.uses}
        return [
            ReferenceDiagnostic(
                'unused',
                definitions[-1].label,
                definitions[-1].line,
                'Unused link reference definition: %r' % definitions[-1].label,
                definitions=tuple(definitions),
            )
            for label, definitions in self.definitions.items()
            if label not in used
        ]

    @property
    def problems(self) -> list[ReferenceDiagnostic]:
        """All unknown references, conflicts, and unused definitions."""
        return (
            self.unknown_references
            + self.conflicting_definitions
            + self.unused_definitions
        )

    def as_dict(self) -> dict[str, list[dict[str, object]]]:
        """Return diagnostic problems as plain dictionaries."""
        return {
            'unknown': [item.as_dict() for item in self.unknown_references],
            'conflicts': [item.as_dict() for item in self.conflicting_definitions],
            'unused': [item.as_dict() for item in self.unused_definitions],
        }


SourceLineMap = list[tuple[int, int | None]]


@dataclass
class _SourceContext:
    text: str
    line_map: SourceLineMap


class ReferenceTracker(ReferenceDiagnostics):
    """Reference event collector with parser source locations."""

    def __init__(self, enabled: bool = False):
        super().__init__()
        self.enabled = enabled
        self.source_line_map: list[int | None] | None = None
        self.trusted_preprocessors: set[str] = set()
        self.trusted_preprocessors.update([
            'normalize_whitespace',
            'html_block',
            'fenced_code_block',
            'meta',
        ])
        self._contexts: list[_SourceContext] = []
        self._inline_sources: weakref.WeakKeyDictionary[
            object, dict[str, SourceLineMap]
        ] = weakref.WeakKeyDictionary()

    def reset(self) -> None:
        super().reset()
        self.source_line_map = None
        self._contexts.clear()
        self._inline_sources.clear()

    def reset_document_sources(self, lines: list[str]) -> None:
        """Initialize source locations for preprocessed document lines."""
        source_line_map = self.source_line_map
        if source_line_map is None or len(source_line_map) < len(lines):
            source = list(range(1, len(lines) + 1))
        else:
            source = list(source_line_map[:len(lines)])
            if len(source) < len(lines):
                source.extend([None] * (len(lines) - len(source)))

        text = '\n'.join(lines)
        line_map: SourceLineMap = [
            (position, source[index])
            for index, position in enumerate(_line_starts(text))
        ]
        self._contexts = [_SourceContext(text, line_map)]

    def preprocessor_changed_lines(
        self,
        name: str,
        old_lines: list[str],
        new_lines: list[str],
    ) -> None:
        """
        Track line origins after a preprocessor.

        Known preprocessors preserve one-to-one line correspondence. Other
        extensions may generate content, whose source is intentionally left
        unknown rather than guessed by index.
        """
        current = self.source_line_map
        if current is None:
            current = list(range(1, len(old_lines) + 1))

        if name == 'meta':
            first_new = 0
            if len(new_lines) < len(old_lines):
                first_new = len(old_lines) - len(new_lines)
            self.source_line_map = current[first_new:first_new + len(new_lines)]
        elif name in self.trusted_preprocessors and len(current) == len(old_lines):
            if len(new_lines) <= len(current):
                self.source_line_map = current[:len(new_lines)]
            else:
                extra = len(new_lines) - len(current)
                self.source_line_map = current + current[-1:] * extra
        else:
            self.source_line_map = [None] * len(new_lines)

    def push_text(self, text: str, line_map: SourceLineMap | None = None) -> None:
        """Push source context for a block about to be parsed."""
        if line_map is None:
            line_map = self._align_text(text)
        self._contexts.append(_SourceContext(text, line_map))

    def pop_text(self) -> None:
        """Remove the most recently pushed source context."""
        self._contexts.pop()

    def has_document_context(self) -> bool:
        """Return whether root document source locations are initialized."""
        return bool(self._contexts)

    def current_text(self) -> str | None:
        """Return the text of the current parser source context."""
        return self._contexts[-1].text if self._contexts else None

    def line_for_text(self, text: str, offset: int) -> int | None:
        """Return the original line for an offset in a parser text fragment."""
        line_map = self._align_text(text)
        return _resolve_line(line_map, offset)

    def attach_text(
        self,
        element: object,
        attribute: str,
        text: str,
        prepend: bool = False,
    ) -> None:
        """Attach source locations to inline element text or tail."""
        mapped = self._align_text(text)
        existing = self._inline_sources.setdefault(element, {}).get(attribute)
        if not existing:
            self._inline_sources[element][attribute] = mapped
            return

        if prepend:
            new_text = getattr(element, attribute, '') or ''
            boundary = len(new_text) + 1
            mapped = [(position, line) for position, line in mapped]
            mapped.extend((boundary + position, line) for position, line in existing)
        else:
            old_text = getattr(element, attribute, '') or ''
            boundary = len(old_text) + 1
            mapped = existing + [
                (boundary + position, line) for position, line in mapped
            ]
        self._inline_sources[element][attribute] = mapped

    def line_for_inline(
        self,
        element: object,
        attribute: str,
        offset: int,
    ) -> int | None:
        """Return the source line for an offset in tracked inline text."""
        line_map = self._inline_sources.get(element, {}).get(attribute)
        if line_map is None:
            return None
        return _resolve_line(line_map, offset)

    def attach_relative_text(
        self,
        element: object,
        attribute: str,
        fragment: str,
        parent_element: object,
        parent_attribute: str,
        parent_offset: int,
    ) -> None:
        """Map a generated inline fragment relative to its parent text."""
        parent_map = self._inline_sources.get(parent_element, {}).get(parent_attribute)
        if parent_map is None:
            self._inline_sources.setdefault(element, {})[attribute] = [
                (position, None) for position in _line_starts(fragment)
            ]
            return

        line_map: SourceLineMap = []
        for position in _line_starts(fragment):
            line_map.append(
                (position, _resolve_line(parent_map, parent_offset + position))
            )
        self._inline_sources.setdefault(element, {})[attribute] = line_map

    def _align_text(self, text: str) -> SourceLineMap:
        if not self._contexts:
            return []

        context = self._contexts[-1]
        if text == context.text:
            return list(context.line_map)

        parent_lines = context.text.split('\n')
        child_lines = text.split('\n')
        cursor = 0
        result: SourceLineMap = []

        for child_index, child_line in enumerate(child_lines):
            child_start = sum(len(line) + 1 for line in child_lines[:child_index])
            stripped = child_line.lstrip(' ')
            indent = len(child_line) - len(stripped)
            match_position = self._find_line(parent_lines, child_line, cursor)
            if match_position is not None:
                parent_line = context.text.count('\n', 0, match_position)
                source_line = _resolve_line(context.line_map, match_position)
                if source_line is not None and child_line:
                    source_text = parent_lines[parent_line]
                    line_offset = source_text.find(child_line)
                    if line_offset < 0:
                        line_offset = source_text.find(stripped)
                        if line_offset >= 0:
                            line_offset += indent
                    if line_offset > 0:
                        source_line = _resolve_line(
                            context.line_map, match_position + line_offset
                        )
                result.append((child_start, source_line))
                cursor = match_position + len(child_line)
            elif stripped:
                result.append((child_start, None))

        return result

    @staticmethod
    def _find_line(lines: list[str], child_line: str, cursor: int) -> int | None:
        cursor_line = 0
        position = 0
        stripped = child_line.lstrip(' ')

        while position < cursor and cursor_line < len(lines):
            position += len(lines[cursor_line]) + 1
            cursor_line += 1

        for line in lines[cursor_line:]:
            if line == child_line or (stripped and stripped in line):
                return position
            position += len(line) + 1
        return None


def _line_starts(text: str) -> list[int]:
    starts = [0]
    starts.extend(position + 1 for position, char in enumerate(text) if char == '\n')
    return starts


def _resolve_line(line_map: SourceLineMap, offset: int) -> int | None:
    line = None
    for position, mapped_line in line_map:
        if position > offset:
            break
        line = mapped_line
    return line
