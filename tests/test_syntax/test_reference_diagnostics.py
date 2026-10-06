"""
Tests for link reference diagnostics.
"""

from __future__ import annotations

from markdown import Markdown, markdown
from markdown.test_tools import TestCase


class TestReferenceDiagnostics(TestCase):
    def test_diagnostics_are_separate_from_html(self):
        md = Markdown(strict=True)
        source = '[missing]'

        self.assertEqual(md.convert(source), '<p>[missing]</p>')
        self.assertNotIn('warning', md.convert(source).lower())
        self.assertEqual(
            [item.label for item in md.diagnostics.unknown_references],
            ['missing'],
        )

    def test_diagnostics_are_disabled_by_default(self):
        md = Markdown()

        self.assertEqual(md.convert('[missing]'), '<p>[missing]</p>')
        self.assertEqual(md.diagnostics.uses, [])
        self.assertEqual(md.diagnostics.problems, [])

    def test_shortcut_function_accepts_strict_without_changing_output(self):
        output = markdown('[missing]', strict=True)

        self.assertEqual(output, '<p>[missing]</p>')

    def test_unknown_full_and_short_image_references_have_lines(self):
        md = Markdown(strict=True)
        source = '[text][missing]\n\n![image missing]\n'

        md.convert(source)

        self.assertEqual(
            [(item.label, item.line, item.reference_type, item.is_image)
             for item in md.diagnostics.unknown_references],
            [
                ('missing', 1, 'full', False),
                ('image missing', 3, 'short', True),
            ],
        )

    def test_collapsed_reference_normalizes_case_and_whitespace(self):
        md = Markdown(strict=True)
        source = '[Case   ID][]\n\n[case\tid]: https://example.com\n'

        self.assertEqual(
            md.convert(source),
            '<p><a href="https://example.com">Case   ID</a></p>',
        )
        self.assertEqual(md.diagnostics.unknown_references, [])
        self.assertEqual(md.diagnostics.uses[0].reference_type, 'collapsed')

    def test_conflicting_and_unused_definitions_have_lines(self):
        md = Markdown(strict=True)
        source = (
            '[Same]\n\n'
            '[same]: https://one.example\n'
            '[SAME  ]: https://two.example\n'
            '[unused]: https://unused.example\n'
        )

        md.convert(source)

        conflicts = md.diagnostics.conflicting_definitions
        unused = md.diagnostics.unused_definitions
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].line, 4)
        self.assertEqual(
            [definition.line for definition in conflicts[0].definitions],
            [3, 4],
        )
        self.assertEqual(len(unused), 1)
        self.assertEqual(unused[0].label, 'unused')
        self.assertEqual(unused[0].line, 5)

    def test_nested_link_text_reports_parser_accepted_references(self):
        md = Markdown(strict=True)
        source = (
            '[outer [inner][inner]][outer]\n\n'
            '[inner]: https://inner.example\n'
            '[outer]: https://outer.example\n'
        )

        md.convert(source)

        self.assertEqual(
            [(use.label, use.line, use.reference_type) for use in md.diagnostics.uses],
            [('outer', 1, 'full'), ('inner', 1, 'short'), ('inner', 1, 'short')],
        )
        self.assertEqual(md.diagnostics.unknown_references, [])

    def test_code_escapes_and_raw_html_do_not_create_references(self):
        md = Markdown(strict=True)
        source = (
            '`[code][missing]`\n\n'
            '\\[escaped][missing]\n\n'
            '    [indented][missing]\n\n'
            '<div>\n'
            '[raw html][missing]\n'
            '</div>\n'
        )

        md.convert(source)

        self.assertEqual(md.diagnostics.uses, [])
        self.assertEqual(md.diagnostics.unknown_references, [])

    def test_extension_generated_content_without_source_is_unknown_origin(self):
        md = Markdown(strict=True, extensions=['md_in_html'])
        source = '<div markdown="block">\n[missing]\n</div>\n'

        md.convert(source)

        self.assertEqual(len(md.diagnostics.unknown_references), 1)
        self.assertIsNone(md.diagnostics.unknown_references[0].line)

    def test_preprocessor_removal_preserves_original_line_numbers(self):
        md = Markdown(strict=True, extensions=['meta'])
        source = '---\ntitle: Example\n---\n[missing]\n'

        md.convert(source)

        self.assertEqual(md.diagnostics.unknown_references[0].line, 4)
