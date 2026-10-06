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

Copyright 2007-2023 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

License: BSD (see LICENSE.md for details).

Python-Markdown Reference Diagnostics Tests
===========================================

Tests of the reference diagnostics collected while parsing.
"""

import unittest
import xml.etree.ElementTree as etree

import markdown
from markdown.diagnostics import (
    UNKNOWN_REFERENCE,
    CONFLICTING_DEFINITION,
    UNUSED_DEFINITION,
    ReferenceDiagnosticsError,
)
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class TestReferenceDiagnostics(unittest.TestCase):
    """ Tests of the reference diagnostics collected while parsing. """

    def setUp(self):
        """ Create instance of Markdown. """
        self.md = markdown.Markdown()

    def diagnostics(self, kind):
        """ Return the diagnostics of the given kind from the last conversion. """
        return [d for d in self.md.reference_diagnostics if d.kind == kind]

    def testNoDiagnosticsForCleanDocument(self):
        """ A document with matching references has no diagnostics. """
        output = self.md.convert('[text][ref]\n\n[ref]: /url\n')
        self.assertEqual(output, '<p><a href="/url">text</a></p>')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testUnknownReference(self):
        """ An unknown reference is reported with its source line. """
        output = self.md.convert('Some [missing] link.\n')
        self.assertEqual(output, '<p>Some [missing] link.</p>')
        diagnostics = self.diagnostics(UNKNOWN_REFERENCE)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].label, 'missing')
        self.assertEqual(diagnostics[0].line, 1)

    def testUnknownFullReference(self):
        """ An unknown full reference reports the label in the second set of brackets. """
        self.md.convert('A [text][typo] here.\n')
        diagnostics = self.diagnostics(UNKNOWN_REFERENCE)
        labels = [d.label for d in diagnostics]
        self.assertIn('typo', labels)
        # The parser falls back to trying the text as a shortcut reference.
        self.assertIn('text', labels)
        self.assertTrue(all(d.line == 1 for d in diagnostics))

    def testUnknownImageReference(self):
        """ An unknown image reference is reported. """
        self.md.convert('![alt][img]\n')
        diagnostics = self.diagnostics(UNKNOWN_REFERENCE)
        labels = [d.label for d in diagnostics]
        self.assertIn('img', labels)
        # The parser falls back to trying the alt text as a shortcut image reference.
        self.assertIn('alt', labels)
        self.assertTrue(all(d.line == 1 for d in diagnostics))

    def testLabelNormalizationCaseAndWhitespace(self):
        """ References match definitions regardless of case and whitespace. """
        text = (
            '[one][MY LABEL] and [two][my  label] and [My Label] and ![alt][my\nlabel].\n'
            '\n'
            '[My Label]: /url\n'
        )
        output = self.md.convert(text)
        self.assertEqual(
            output,
            '<p><a href="/url">one</a> and <a href="/url">two</a> and '
            '<a href="/url">My Label</a> and <img alt="alt" src="/url" />.</p>'
        )
        self.assertEqual(self.md.reference_diagnostics, [])

    def testCollapsedReference(self):
        """ A collapsed reference uses its own text as the label. """
        output = self.md.convert('[My Label][]\n\n[my label]: /url\n')
        self.assertEqual(output, '<p><a href="/url">My Label</a></p>')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testConflictingDefinitions(self):
        """ Definitions which normalize to the same label are reported. """
        output = self.md.convert('[My Label]: /first\n\n[MY LABEL]: /second\n\n[use][my label]\n')
        # Output is unchanged: the parser keeps its existing behavior.
        self.assertEqual(output, '<p><a href="/second">use</a></p>')
        diagnostics = self.diagnostics(CONFLICTING_DEFINITION)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].label, 'my label')
        self.assertEqual(diagnostics[0].line, 3)
        self.assertIn('line 1', diagnostics[0].message)

    def testUnusedDefinition(self):
        """ A definition which is never referenced is reported with its line. """
        output = self.md.convert('[used]: /a\n[unused]: /b\n\n[link][used]\n')
        self.assertEqual(output, '<p><a href="/a">link</a></p>')
        diagnostics = self.diagnostics(UNUSED_DEFINITION)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(diagnostics[0].label, 'unused')
        self.assertEqual(diagnostics[0].line, 2)

    def testNestedLinkText(self):
        """ Nested markup in link text does not confuse label matching. """
        output = self.md.convert('[*em* [inner](http://example.com)][ref]\n\n[ref]: /url\n')
        self.assertEqual(
            output,
            '<p><a href="/url"><em>em</em> <a href="http://example.com">inner</a></a></p>'
        )
        self.assertEqual(self.md.reference_diagnostics, [])

    def testCodeSpansAreIgnored(self):
        """ Pseudo-references in code spans are not reported. """
        output = self.md.convert('`[not a ref][missing]`\n')
        self.assertEqual(output, '<p><code>[not a ref][missing]</code></p>')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testCodeBlocksAreIgnored(self):
        """ Pseudo-references in code blocks are not reported. """
        output = self.md.convert('    [not a ref]: /url\n    [text][missing]\n')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testEscapedBracketsAreIgnored(self):
        """ Escaped brackets are not treated as references. """
        output = self.md.convert('\\[not a ref\\] and \\!\\[not an image\\]\n')
        self.assertEqual(output, '<p>[not a ref] and ![not an image]</p>')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testRawHtmlIsIgnored(self):
        """ Pseudo-references in raw HTML blocks are not reported. """
        output = self.md.convert('<div>\n[not a ref][missing]\n</div>\n')
        self.assertEqual(output, '<div>\n[not a ref][missing]\n</div>')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testNoWarningsInOutput(self):
        """ Diagnostics are never inserted into the HTML output. """
        output = self.md.convert('[missing] and [unused]: /url\n')
        self.assertNotIn('warning', output.lower())
        self.assertNotIn('diagnostic', output.lower())
        self.assertEqual(output, '<p>[missing] and [unused]: /url</p>')
        self.assertNotEqual(self.md.reference_diagnostics, [])

    def testResetClearsDiagnostics(self):
        """ Resetting the parser clears collected diagnostics. """
        self.md.convert('[missing]\n')
        self.assertNotEqual(self.md.reference_diagnostics, [])
        self.md.reset()
        self.assertEqual(self.md.reference_diagnostics, [])
        self.md.convert('[ok][ref]\n\n[ref]: /url\n')
        self.assertEqual(self.md.reference_diagnostics, [])

    def testStrictReferencesRaises(self):
        """ Strict mode raises an error containing the diagnostics. """
        md = markdown.Markdown(strict_references=True)
        with self.assertRaises(ReferenceDiagnosticsError) as cm:
            md.convert('[missing]\n')
        self.assertEqual(len(cm.exception.diagnostics), 1)
        self.assertEqual(cm.exception.diagnostics[0].kind, UNKNOWN_REFERENCE)
        self.assertEqual(cm.exception.diagnostics[0].label, 'missing')

    def testStrictReferencesCleanDocument(self):
        """ Strict mode does not raise when there are no diagnostics. """
        md = markdown.Markdown(strict_references=True)
        self.assertEqual(md.convert('[ok][ref]\n\n[ref]: /url\n'), '<p><a href="/url">ok</a></p>')

    def testStrictReferencesDefaultOff(self):
        """ Strict mode is off by default and output is unchanged. """
        self.assertEqual(markdown.markdown('[missing]\n'), '<p>[missing]</p>')


class InjectTreeprocessor(Treeprocessor):
    """ Insert generated content which contains a reference. """

    def run(self, root):
        p = etree.SubElement(root, 'p')
        p.text = 'Generated [text][ghost] content.'


class InjectExtension(Extension):
    """ Register a treeprocessor which generates content with a reference. """

    def extendMarkdown(self, md):
        md.treeprocessors.register(InjectTreeprocessor(md), 'inject', 30)


class TestGeneratedContentDiagnostics(unittest.TestCase):
    """ Tests of diagnostics for content not present in the source document. """

    def testGeneratedContentHasUnknownSource(self):
        """ References in extension-generated content have no line number. """
        md = markdown.Markdown(extensions=[InjectExtension()])
        output = md.convert('Real [missing] here.\n')
        self.assertEqual(
            output,
            '<p>Real [missing] here.</p>\n<p>Generated [text][ghost] content.</p>'
        )
        by_label = {d.label: d for d in md.reference_diagnostics}
        self.assertEqual(by_label['missing'].line, 1)
        self.assertIsNone(by_label['ghost'].line)


if __name__ == '__main__':
    unittest.main()
