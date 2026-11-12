from __future__ import print_function

import io
import os
import sys
import unittest
import warnings
from unittest import mock

from xml.etree import ElementTree as orig_elementtree
from xml.etree.ElementTree import Element as ElementBeforeImport
from xml.sax.saxutils import XMLGenerator
from xml.sax import SAXParseException
from pyexpat import ExpatError

from defusedxml import (
    ElementTree,
    minidom,
    pulldom,
    sax,
    xmlrpc,
    expatreader,
    expatbuilder,
)
from defusedxml import defuse_stdlib
from defusedxml import (
    DepthExceeded,
    DTDForbidden,
    EntitiesForbidden,
    ExternalReferenceForbidden,
    NodesExceeded,
    NotSupportedError,
    DefusedXmlException,
)

from xml.etree.ElementTree import Element as ElementAfterImport

if sys.version_info < (3, 7):
    warnings.filterwarnings("once", category=DeprecationWarning)


with warnings.catch_warnings(record=True) as cetree_warnings:
    warnings.simplefilter("always")
    from defusedxml import cElementTree


try:
    import gzip
except ImportError:
    gzip = None


try:
    with warnings.catch_warnings(record=True) as lxml_warnings:
        from defusedxml import lxml
    from lxml import etree as lxml_etree

    LXML3 = lxml.LXML3
except ImportError:
    lxml = None
    lxml_etree = None
    LXML3 = False
    lxml_warnings = None


warnings.filterwarnings("always", category=DeprecationWarning, module=r"defusedxml\..*")


HERE = os.path.dirname(os.path.abspath(__file__))

# prevent web access
# based on Debian's rules, Port 9 is discard
os.environ["http_proxy"] = "http://127.0.9.1:9"
os.environ["https_proxy"] = os.environ["http_proxy"]
os.environ["ftp_proxy"] = os.environ["http_proxy"]


class DefusedTestCase(unittest.TestCase):
    content_binary = False

    xml_dtd = os.path.join(HERE, "xmltestdata", "dtd.xml")
    xml_external = os.path.join(HERE, "xmltestdata", "external.xml")
    xml_external_file = os.path.join(HERE, "xmltestdata", "external_file.xml")
    xml_quadratic = os.path.join(HERE, "xmltestdata", "quadratic.xml")
    xml_simple = os.path.join(HERE, "xmltestdata", "simple.xml")
    xml_simple_ns = os.path.join(HERE, "xmltestdata", "simple-ns.xml")
    xml_bomb = os.path.join(HERE, "xmltestdata", "xmlbomb.xml")
    xml_bomb2 = os.path.join(HERE, "xmltestdata", "xmlbomb2.xml")
    xml_cyclic = os.path.join(HERE, "xmltestdata", "cyclic.xml")
    xml_dtd_element = os.path.join(HERE, "xmltestdata", "dtd_element.xml")
    xml_schema_include = os.path.join(HERE, "xmltestdata", "schema-include.xsd")

    def get_content(self, xmlfile):
        mode = "rb" if self.content_binary else "r"
        with io.open(xmlfile, mode) as f:
            data = f.read()
        return data


class BaseTests(DefusedTestCase):
    module = None
    dtd_external_ref = False

    external_ref_exception = ExternalReferenceForbidden
    cyclic_error = None
    iterparse = None

    def test_simple_parse(self):
        self.parse(self.xml_simple)
        self.parseString(self.get_content(self.xml_simple))
        if self.iterparse:
            self.iterparse(self.xml_simple)

    def test_simple_parse_ns(self):
        self.parse(self.xml_simple_ns)
        self.parseString(self.get_content(self.xml_simple_ns))
        if self.iterparse:
            self.iterparse(self.xml_simple_ns)

    def test_entities_forbidden(self):
        self.assertRaises(EntitiesForbidden, self.parse, self.xml_bomb)
        self.assertRaises(EntitiesForbidden, self.parse, self.xml_quadratic)
        self.assertRaises(EntitiesForbidden, self.parse, self.xml_external)

        self.assertRaises(EntitiesForbidden, self.parseString, self.get_content(self.xml_bomb))
        self.assertRaises(
            EntitiesForbidden, self.parseString, self.get_content(self.xml_quadratic)
        )
        self.assertRaises(
            EntitiesForbidden, self.parseString, self.get_content(self.xml_external)
        )

        if self.iterparse:
            self.assertRaises(EntitiesForbidden, self.iterparse, self.xml_bomb)
            self.assertRaises(EntitiesForbidden, self.iterparse, self.xml_quadratic)
            self.assertRaises(EntitiesForbidden, self.iterparse, self.xml_external)

    def test_entity_cycle(self):
        self.assertRaises(self.cyclic_error, self.parse, self.xml_cyclic, forbid_entities=False)

    def test_dtd_forbidden(self):
        self.assertRaises(DTDForbidden, self.parse, self.xml_bomb, forbid_dtd=True)
        self.assertRaises(DTDForbidden, self.parse, self.xml_quadratic, forbid_dtd=True)
        self.assertRaises(DTDForbidden, self.parse, self.xml_external, forbid_dtd=True)
        self.assertRaises(DTDForbidden, self.parse, self.xml_dtd, forbid_dtd=True)

        self.assertRaises(
            DTDForbidden, self.parseString, self.get_content(self.xml_bomb), forbid_dtd=True
        )
        self.assertRaises(
            DTDForbidden, self.parseString, self.get_content(self.xml_quadratic), forbid_dtd=True
        )
        self.assertRaises(
            DTDForbidden, self.parseString, self.get_content(self.xml_external), forbid_dtd=True
        )
        self.assertRaises(
            DTDForbidden, self.parseString, self.get_content(self.xml_dtd), forbid_dtd=True
        )

        if self.iterparse:
            self.assertRaises(DTDForbidden, self.iterparse, self.xml_bomb, forbid_dtd=True)
            self.assertRaises(DTDForbidden, self.iterparse, self.xml_quadratic, forbid_dtd=True)
            self.assertRaises(DTDForbidden, self.iterparse, self.xml_external, forbid_dtd=True)
            self.assertRaises(DTDForbidden, self.iterparse, self.xml_dtd, forbid_dtd=True)

    def test_dtd_with_external_ref(self):
        if self.dtd_external_ref:
            self.assertRaises(self.external_ref_exception, self.parse, self.xml_dtd)
        else:
            self.parse(self.xml_dtd)

    def test_external_ref(self):
        self.assertRaises(
            self.external_ref_exception, self.parse, self.xml_external, forbid_entities=False
        )

    def test_external_file_ref(self):
        content = self.get_content(self.xml_external_file)
        if isinstance(content, bytes):
            here = HERE.encode(sys.getfilesystemencoding())
            content = content.replace(b"/PATH/TO", here)
        else:
            content = content.replace("/PATH/TO", HERE)
        self.assertRaises(
            self.external_ref_exception, self.parseString, content, forbid_entities=False
        )

    def test_allow_expansion(self):
        self.parse(self.xml_bomb2, forbid_entities=False)
        self.parseString(self.get_content(self.xml_bomb2), forbid_entities=False)

    def test_dtd_element(self):
        self.parse(self.xml_dtd_element)


class TestDefusedElementTree(BaseTests):
    module = ElementTree

    # etree doesn't do external ref lookup
    # external_ref_exception = ElementTree.ParseError

    cyclic_error = ElementTree.ParseError

    def parse(self, xmlfile, **kwargs):
        tree = self.module.parse(xmlfile, **kwargs)
        return self.module.tostring(tree.getroot())

    def parseString(self, xmlstring, **kwargs):
        tree = self.module.fromstring(xmlstring, **kwargs)
        return self.module.tostring(tree)

    def parseStringList(self, sequence, **kwargs):
        tree = self.module.fromstringlist(sequence, **kwargs)
        return self.module.tostring(tree)

    def iterparse(self, source, **kwargs):
        return list(self.module.iterparse(source, **kwargs))

    def test_html_arg(self):
        with warnings.catch_warnings(record=True) as w:
            self.module.XMLParse(html=0)
        self.assertEqual(len(w), 1)
        self.assertIs(w[0].category, DeprecationWarning)
        with self.assertRaises(TypeError):
            self.module.XMLParse(html=1)

    def test_aliases(self):
        parser = self.module.DefusedXMLParser
        assert self.module.XMLTreeBuilder is parser
        assert self.module.XMLParser is parser
        assert self.module.XMLParse is parser

    def test_fromstringlist(self):
        seq = ["<root>", '<tag id="one" />', '<tag id="two" />', "</root>"]
        tree = self.module.fromstringlist(seq)
        result = self.module.tostring(tree)
        self.assertEqual(result, "".join(seq).encode("utf-8"))

    def test_import_order(self):
        from xml.etree import ElementTree as second_elementtree

        self.assertIs(orig_elementtree, second_elementtree)

    def test_orig_parseerror(self):
        # https://github.com/tiran/defusedxml/issues/63
        self.assertIs(self.module.ParseError, orig_elementtree.ParseError)
        try:
            self.parseString("invalid")
        except Exception as e:
            self.assertIsInstance(e, orig_elementtree.ParseError)
            self.assertIsInstance(e, self.module.ParseError)

    def test_etree_element(self):
        tree = tree = self.module.parse(self.xml_simple)
        root = tree.getroot()
        root.append(orig_elementtree.Element("module-import"))
        root.append(ElementBeforeImport("before-import"))
        root.append(ElementAfterImport("after-import"))
        s = orig_elementtree.tostring(root)
        self.assertEqual(s.count(b"import"), 3, s)


class TestDefusedcElementTree(TestDefusedElementTree):
    module = cElementTree

    def test_celementtree_warnings(self):
        self.assertTrue(cetree_warnings)
        self.assertEqual(cetree_warnings[0].category, DeprecationWarning)
        self.assertIn("tests.py", cetree_warnings[0].filename)


class TestDefusedMinidom(BaseTests):
    module = minidom

    cyclic_error = ExpatError

    iterparse = None

    def parse(self, xmlfile, **kwargs):
        doc = self.module.parse(xmlfile, **kwargs)
        return doc.toxml()

    def parseString(self, xmlstring, **kwargs):
        doc = self.module.parseString(xmlstring, **kwargs)
        return doc.toxml()


class TestDefusedMinidomWithParser(TestDefusedMinidom):
    cyclic_error = SAXParseException
    dtd_external_ref = True

    def parse(self, xmlfile, **kwargs):
        doc = self.module.parse(xmlfile, parser=expatreader.create_parser(**kwargs), **kwargs)
        return doc.toxml()

    def parseString(self, xmlstring, **kwargs):
        doc = self.module.parseString(
            xmlstring, parser=expatreader.create_parser(**kwargs), **kwargs
        )
        return doc.toxml()


class TestDefusedPulldom(BaseTests):
    module = pulldom

    cyclic_error = SAXParseException

    dtd_external_ref = True

    def parse(self, xmlfile, **kwargs):
        events = self.module.parse(xmlfile, **kwargs)
        return list(events)

    def parseString(self, xmlstring, **kwargs):
        events = self.module.parseString(xmlstring, **kwargs)
        return list(events)


class TestDefusedSax(BaseTests):
    module = sax

    cyclic_error = SAXParseException

    content_binary = True
    dtd_external_ref = True

    def parse(self, xmlfile, **kwargs):
        with io.StringIO() as result:
            handler = XMLGenerator(result)
            self.module.parse(xmlfile, handler, **kwargs)
            return result.getvalue()

    def parseString(self, xmlstring, **kwargs):
        with io.StringIO() as result:
            handler = XMLGenerator(result)
            self.module.parseString(xmlstring, handler, **kwargs)
            return result.getvalue()

    def test_exceptions(self):
        with self.assertRaises(EntitiesForbidden) as ctx:
            self.parse(self.xml_bomb)
        msg = "EntitiesForbidden(name='a', system_id=None, public_id=None)"
        self.assertEqual(str(ctx.exception), msg)
        self.assertEqual(repr(ctx.exception), msg)

        with self.assertRaises(ExternalReferenceForbidden) as ctx:
            self.parse(self.xml_external, forbid_entities=False)
        msg = (
            "ExternalReferenceForbidden"
            "(system_id='http://www.w3schools.com/xml/note.xml', public_id=None)"
        )
        self.assertEqual(str(ctx.exception), msg)
        self.assertEqual(repr(ctx.exception), msg)

        with self.assertRaises(DTDForbidden) as ctx:
            self.parse(self.xml_bomb, forbid_dtd=True)
        msg = "DTDForbidden(name='xmlbomb', system_id=None, public_id=None)"
        self.assertEqual(str(ctx.exception), msg)
        self.assertEqual(repr(ctx.exception), msg)


@unittest.skipUnless(lxml is not None, "test requires lxml")
class TestDefusedLxml(BaseTests):
    module = lxml

    cyclic_error = getattr(lxml_etree, "XMLSyntaxError", None)

    content_binary = True

    def parse(self, xmlfile, **kwargs):
        try:
            tree = self.module.parse(xmlfile, **kwargs)
        except lxml_etree.XMLSyntaxError:
            self.skipTest("lxml detects entity reference loop")
        return self.module.tostring(tree)

    def parseString(self, xmlstring, **kwargs):
        try:
            tree = self.module.fromstring(xmlstring, **kwargs)
        except lxml_etree.XMLSyntaxError:
            self.skipTest("lxml detects entity reference loop")
        return self.module.tostring(tree)

    if not LXML3:

        def test_entities_forbidden(self):
            self.assertRaises(NotSupportedError, self.parse, self.xml_bomb)

        def test_dtd_with_external_ref(self):
            self.assertRaises(NotSupportedError, self.parse, self.xml_dtd)

    def test_external_ref(self):
        pass

    def test_external_file_ref(self):
        pass

    def test_restricted_element1(self):
        try:
            tree = self.module.parse(self.xml_bomb, forbid_dtd=False, forbid_entities=False)
        except lxml_etree.XMLSyntaxError:
            self.skipTest("lxml detects entityt reference loop")
        root = tree.getroot()
        self.assertEqual(root.text, None)

        self.assertEqual(list(root), [])
        self.assertEqual(root.getchildren(), [])
        self.assertEqual(list(root.iter()), [root])
        self.assertEqual(list(root.iterchildren()), [])
        self.assertEqual(list(root.iterdescendants()), [])
        self.assertEqual(list(root.itersiblings()), [])
        self.assertEqual(list(root.getiterator()), [root])
        self.assertEqual(root.getnext(), None)

    def test_restricted_element2(self):
        try:
            tree = self.module.parse(self.xml_bomb2, forbid_dtd=False, forbid_entities=False)
        except lxml_etree.XMLSyntaxError:
            self.skipTest("lxml detects entityt reference loop")
        root = tree.getroot()
        bomb, tag = root
        self.assertEqual(root.text, "text")

        self.assertEqual(list(root), [bomb, tag])
        self.assertEqual(root.getchildren(), [bomb, tag])
        self.assertEqual(list(root.iter()), [root, bomb, tag])
        self.assertEqual(list(root.iterchildren()), [bomb, tag])
        self.assertEqual(list(root.iterdescendants()), [bomb, tag])
        self.assertEqual(list(root.itersiblings()), [])
        self.assertEqual(list(root.getiterator()), [root, bomb, tag])
        self.assertEqual(root.getnext(), None)
        self.assertEqual(root.getprevious(), None)

        self.assertEqual(list(bomb.itersiblings()), [tag])
        self.assertEqual(bomb.getnext(), tag)
        self.assertEqual(bomb.getprevious(), None)
        self.assertEqual(tag.getnext(), None)
        self.assertEqual(tag.getprevious(), bomb)

    def test_xpath_injection(self):
        # show XPath injection vulnerability
        xml = """<root><tag id="one" /><tag id="two"/></root>"""
        expr = "one' or @id='two"
        root = lxml.fromstring(xml)

        # insecure way
        xp = "tag[@id='%s']" % expr
        elements = root.xpath(xp)
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements, list(root))

        # proper and safe way
        xp = "tag[@id=$idname]"
        elements = root.xpath(xp, idname=expr)
        self.assertEqual(len(elements), 0)
        self.assertEqual(elements, [])

        elements = root.xpath(xp, idname="one")
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements, list(root)[:1])

    def test_lxml_warnings(self):
        self.assertTrue(lxml_warnings)
        self.assertEqual(lxml_warnings[0].category, DeprecationWarning)
        self.assertIn("tests.py", lxml_warnings[0].filename)

    def test_lxml_schema_include(self):
        # attempt to trigger network ops and error
        with mock.patch.dict(os.environ):
            os.environ.pop("no_proxy", None)
            os.environ["http_proxy"] = "http://proxy.invalid:3128"
            os.environ["https_proxy"] = "http://proxy.invalid:3128"

            doc = self.module.fromstring("<root>true</root>")

            schema = lxml_etree.XMLSchema(file=self.xml_schema_include)
            schema.validate(doc)

            schema_etree = self.module.parse(self.xml_schema_include)
            lxml_etree.XMLSchema(etree=schema_etree)
            schema.validate(doc)


class TestElementBudget(unittest.TestCase):
    """Depth and node count budgets across all stdlib facades."""

    depth = 60
    width = 60

    deep_xml = (
        b"<root>" + b"".join(b"<a>" for _ in range(depth))
        + b"x" + b"".join(b"</a>" for _ in range(depth)) + b"</root>"
    )
    wide_xml = b"<root>" + b"<a/>" * width + b"</root>"
    boundary_xml = b"<r><a><b/></a></r>"  # depth 3, 3 elements

    def assertExceeded(self, exc, expected_type, limit, value):
        self.assertIsInstance(exc, expected_type)
        self.assertIsInstance(exc, DefusedXmlException)
        self.assertIsInstance(exc, ValueError)
        if expected_type is DepthExceeded:
            self.assertEqual(exc.max_depth, limit)
            self.assertEqual(exc.depth, value)
        else:
            self.assertEqual(exc.max_nodes, limit)
            self.assertEqual(exc.count, value)

    def test_exceptions(self):
        exc = DepthExceeded(11, 10)
        self.assertEqual(str(exc), "DepthExceeded(depth=11, max_depth=10)")
        self.assertEqual(repr(exc), str(exc))
        exc = NodesExceeded(6, 5)
        self.assertEqual(str(exc), "NodesExceeded(count=6, max_nodes=5)")
        self.assertEqual(repr(exc), str(exc))

    def test_invalid_limit(self):
        self.assertRaises(
            TypeError, ElementTree.DefusedXMLParser, max_depth="10"
        )
        self.assertRaises(
            TypeError, ElementTree.DefusedXMLParser, max_nodes=2.5
        )
        # bool is rejected even though it is an int subclass
        self.assertRaises(
            TypeError, ElementTree.DefusedXMLParser, max_depth=True
        )

    def test_defaults_unlimited(self):
        # no budget configured: deeply nested and wide docs parse fine
        ElementTree.fromstring(self.deep_xml)
        ElementTree.fromstring(self.wide_xml)
        minidom.parseString(self.deep_xml)
        minidom.parseString(self.wide_xml)
        list(pulldom.parseString(self.deep_xml.decode()))
        list(pulldom.parseString(self.wide_xml.decode()))
        buf = io.StringIO()
        sax.parseString(self.deep_xml, XMLGenerator(buf))
        # explicit zero / None disable the limits as well
        ElementTree.fromstring(self.deep_xml, max_depth=0, max_nodes=None)
        minidom.parseString(self.wide_xml, max_depth=None, max_nodes=0)

    def test_boundary_accepted(self):
        ElementTree.fromstring(self.boundary_xml, max_depth=3, max_nodes=3)
        minidom.parseString(self.boundary_xml, max_depth=3, max_nodes=3)
        expatbuilder.parseString(
            self.boundary_xml, namespaces=False, max_depth=3, max_nodes=3
        )
        list(
            pulldom.parseString(
                self.boundary_xml.decode(), max_depth=3, max_nodes=3
            )
        )
        buf = io.StringIO()
        sax.parseString(
            self.boundary_xml, XMLGenerator(buf), max_depth=3, max_nodes=3
        )

    def test_elementtree_depth(self):
        with self.assertRaises(DepthExceeded) as ctx:
            ElementTree.fromstring(self.deep_xml, max_depth=10)
        self.assertExceeded(ctx.exception, DepthExceeded, 10, 11)

        with self.assertRaises(DepthExceeded) as ctx:
            ElementTree.fromstringlist(
                [self.deep_xml[:40], self.deep_xml[40:]], max_depth=10
            )
        self.assertExceeded(ctx.exception, DepthExceeded, 10, 11)

        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".xml") as f:
            f.write(self.deep_xml)
            f.flush()
            with self.assertRaises(DepthExceeded):
                ElementTree.parse(f.name, max_depth=10)

    def test_elementtree_nodes(self):
        with self.assertRaises(NodesExceeded) as ctx:
            ElementTree.fromstring(self.wide_xml, max_nodes=5)
        # root + five <a/> elements trigger the breach on element six
        self.assertExceeded(ctx.exception, NodesExceeded, 5, 6)

    def test_iterparse_incremental_depth(self):
        stream = io.BytesIO(self.deep_xml)
        iterator = ElementTree.iterparse(
            stream, events=("start", "end"), max_depth=10
        )
        with self.assertRaises(DepthExceeded) as ctx:
            list(iterator)
        self.assertExceeded(ctx.exception, DepthExceeded, 10, 11)

    def test_iterparse_incremental_nodes(self):
        # The exception must surface while pulling events, before the whole
        # document has been materialized.
        stream = io.BytesIO(b"<root>" + b"<a/>" * 1000 + b"</root>")
        iterator = ElementTree.iterparse(stream, max_nodes=7)
        pulled = 0
        with self.assertRaises(NodesExceeded) as ctx:
            for _ in iterator:
                pulled += 1
        self.assertExceeded(ctx.exception, NodesExceeded, 7, 8)
        # only a handful of end events can have been produced
        self.assertLess(pulled, 100)

    def test_iterparse_chunked_feed(self):
        # Feed data in small pieces to prove the check is incremental.
        class Chunked:
            def __init__(self, data, size=16):
                self.data = data
                self.size = size

            def read(self, n=-1):
                chunk, self.data = self.data[: self.size], self.data[self.size :]
                return chunk

        iterator = ElementTree.iterparse(
            Chunked(self.deep_xml), max_depth=10
        )
        with self.assertRaises(DepthExceeded):
            list(iterator)

    def test_minidom_depth_and_nodes(self):
        with self.assertRaises(DepthExceeded) as ctx:
            minidom.parseString(self.deep_xml, max_depth=10)
        self.assertExceeded(ctx.exception, DepthExceeded, 10, 11)
        with self.assertRaises(NodesExceeded) as ctx:
            minidom.parseString(self.wide_xml, max_nodes=5)
        self.assertExceeded(ctx.exception, NodesExceeded, 5, 6)

    def test_minidom_no_namespaces(self):
        with self.assertRaises(DepthExceeded):
            expatbuilder.parseString(
                self.deep_xml, namespaces=False, max_depth=10
            )
        with self.assertRaises(NodesExceeded):
            expatbuilder.parseString(
                self.wide_xml, namespaces=False, max_nodes=5
            )

    def test_minidom_with_sax_parser(self):
        stream = io.StringIO(self.deep_xml.decode())
        parser = expatreader.create_parser()
        with self.assertRaises(DepthExceeded):
            minidom.parse(stream, parser=parser, bufsize=1, max_depth=10)

    def test_pulldom_depth_and_nodes(self):
        with self.assertRaises(DepthExceeded) as ctx:
            list(pulldom.parseString(self.deep_xml.decode(), max_depth=10))
        self.assertExceeded(ctx.exception, DepthExceeded, 10, 11)
        with self.assertRaises(NodesExceeded) as ctx:
            list(pulldom.parseString(self.wide_xml.decode(), max_nodes=5))
        self.assertExceeded(ctx.exception, NodesExceeded, 5, 6)

    def test_sax_depth_and_nodes(self):
        def run(data, **kwargs):
            buf = io.StringIO()
            sax.parseString(data, XMLGenerator(buf), **kwargs)

        with self.assertRaises(DepthExceeded) as ctx:
            run(self.deep_xml, max_depth=10)
        self.assertExceeded(ctx.exception, DepthExceeded, 10, 11)
        with self.assertRaises(NodesExceeded) as ctx:
            run(self.wide_xml, max_nodes=5)
        self.assertExceeded(ctx.exception, NodesExceeded, 5, 6)

    def test_parser_set_budget(self):
        parser = expatreader.create_parser()
        parser.set_budget(max_depth=10)
        with self.assertRaises(DepthExceeded):
            list(pulldom.parseString(self.deep_xml.decode(), parser))

    def test_forbid_paths_still_work(self):
        # existing forbid_* behavior must not regress when budgets are set
        with self.assertRaises(DTDForbidden):
            ElementTree.fromstring(
                self.get_bomb_bytes(), forbid_dtd=True, max_depth=100
            )
        with self.assertRaises(EntitiesForbidden):
            ElementTree.fromstring(
                self.get_bomb_bytes(), max_depth=100, max_nodes=1000
            )
        with self.assertRaises(DTDForbidden):
            minidom.parseString(
                self.get_bomb_bytes(), forbid_dtd=True, max_depth=100
            )

    @staticmethod
    def get_bomb_bytes():
        with io.open(
            os.path.join(HERE, "xmltestdata", "xmlbomb.xml"), "rb"
        ) as f:
            return f.read()


class XmlRpcTarget(object):
    def __init__(self):
        self._data = []

    def __str__(self):
        return "".join(self._data)

    def xml(self, encoding, standalone):
        pass

    def start(self, tag, attrs):
        self._data.append("<%s>" % tag)

    def data(self, text):
        self._data.append(text)

    def end(self, tag):
        self._data.append("</%s>" % tag)


class TestXmlRpc(DefusedTestCase):
    module = xmlrpc

    def parse(self, xmlfile, **kwargs):
        target = XmlRpcTarget()
        parser = self.module.DefusedExpatParser(target, **kwargs)
        data = self.get_content(xmlfile)
        parser.feed(data)
        parser.close()
        return target

    def parse_unpatched(self, xmlfile):
        target = XmlRpcTarget()
        parser = self.module.ExpatParser(target)
        data = self.get_content(xmlfile)
        parser.feed(data)
        parser.close()
        return target

    def test_xmlrpc(self):
        self.assertRaises(EntitiesForbidden, self.parse, self.xml_bomb)
        self.assertRaises(EntitiesForbidden, self.parse, self.xml_quadratic)
        self.parse(self.xml_dtd)
        self.assertRaises(DTDForbidden, self.parse, self.xml_dtd, forbid_dtd=True)

    # def test_xmlrpc_unpatched(self):
    #    for fname in (self.xml_external,  self.xml_dtd):
    #        print(self.parse_unpatched(fname))

    def test_monkeypatch(self):
        try:
            xmlrpc.monkey_patch()
        finally:
            xmlrpc.unmonkey_patch()


@unittest.skipUnless(gzip is not None, "test requires gzip")
class TestDefusedGzip(DefusedTestCase):
    def get_gzipped(self, length):
        f = io.BytesIO()
        self.addCleanup(f.close)
        gzf = gzip.GzipFile(mode="wb", fileobj=f)
        gzf.write(b"d" * length)
        gzf.close()
        f.seek(0)
        return f

    def decode_response(self, response, limit=None, readlength=1024):
        dec = xmlrpc.DefusedGzipDecodedResponse(response, limit)
        acc = []
        while True:
            data = dec.read(readlength)
            if not data:
                break
            acc.append(data)
        return b"".join(acc)

    def test_defused_gzip_decode(self):
        data = self.get_gzipped(4096).getvalue()
        result = xmlrpc.defused_gzip_decode(data)
        self.assertEqual(result, b"d" * 4096)
        result = xmlrpc.defused_gzip_decode(data, -1)
        self.assertEqual(result, b"d" * 4096)
        result = xmlrpc.defused_gzip_decode(data, 4096)
        self.assertEqual(result, b"d" * 4096)
        with self.assertRaises(ValueError):
            result = xmlrpc.defused_gzip_decode(data, 4095)
        with self.assertRaises(ValueError):
            result = xmlrpc.defused_gzip_decode(data, 0)

    def test_defused_gzip_response(self):
        clen = len(self.get_gzipped(4096).getvalue())

        response = self.get_gzipped(4096)
        data = self.decode_response(response)
        self.assertEqual(data, b"d" * 4096)

        with self.assertRaises(ValueError):
            response = self.get_gzipped(4096)
            xmlrpc.DefusedGzipDecodedResponse(response, clen - 1)

        with self.assertRaises(ValueError):
            response = self.get_gzipped(4096)
            self.decode_response(response, 4095)

        with self.assertRaises(ValueError):
            response = self.get_gzipped(4096)
            self.decode_response(response, 4095, 8192)


def test_main():
    suite = unittest.TestSuite()
    cls = [
        TestDefusedElementTree,
        TestDefusedcElementTree,
        TestDefusedMinidom,
        TestDefusedMinidomWithParser,
        TestDefusedPulldom,
        TestDefusedSax,
        TestDefusedLxml,
        TestElementBudget,
        TestXmlRpc,
        TestDefusedGzip,
    ]
    for c in cls:
        suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(c))
    return suite


def load_tests(loader, tests, pattern):
    # BaseTests is an abstract base class without parse()/parseString()
    # implementations; exclude it from plain test discovery.
    suite = unittest.TestSuite()

    def _walk(test_suite):
        for item in test_suite:
            if isinstance(item, unittest.TestSuite):
                _walk(item)
            elif item.__class__ is not BaseTests:
                suite.addTest(item)

    _walk(tests)
    return suite


if __name__ == "__main__":
    suite = test_main()
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    # TODO: test that it actually works
    defuse_stdlib()
    sys.exit(not result.wasSuccessful())
