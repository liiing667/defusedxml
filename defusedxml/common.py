# defusedxml
#
# Copyright (c) 2013-2020 by Christian Heimes <christian@python.org>
# Licensed to PSF under a Contributor Agreement.
# See https://www.python.org/psf/license for licensing details.
"""Common constants, exceptions and helper functions
"""
import sys
import xml.parsers.expat

PY3 = True

# Fail early when pyexpat is not installed correctly
if not hasattr(xml.parsers.expat, "ParserCreate"):
    raise ImportError("pyexpat")  # pragma: no cover


class DefusedXmlException(ValueError):
    """Base exception"""

    def __repr__(self):
        return str(self)


class DTDForbidden(DefusedXmlException):
    """Document type definition is forbidden"""

    def __init__(self, name, sysid, pubid):
        super().__init__()
        self.name = name
        self.sysid = sysid
        self.pubid = pubid

    def __str__(self):
        tpl = "DTDForbidden(name='{}', system_id={!r}, public_id={!r})"
        return tpl.format(self.name, self.sysid, self.pubid)


class EntitiesForbidden(DefusedXmlException):
    """Entity definition is forbidden"""

    def __init__(self, name, value, base, sysid, pubid, notation_name):
        super().__init__()
        self.name = name
        self.value = value
        self.base = base
        self.sysid = sysid
        self.pubid = pubid
        self.notation_name = notation_name

    def __str__(self):
        tpl = "EntitiesForbidden(name='{}', system_id={!r}, public_id={!r})"
        return tpl.format(self.name, self.sysid, self.pubid)


class ExternalReferenceForbidden(DefusedXmlException):
    """Resolving an external reference is forbidden"""

    def __init__(self, context, base, sysid, pubid):
        super().__init__()
        self.context = context
        self.base = base
        self.sysid = sysid
        self.pubid = pubid

    def __str__(self):
        tpl = "ExternalReferenceForbidden(system_id='{}', public_id={})"
        return tpl.format(self.sysid, self.pubid)


class NotSupportedError(DefusedXmlException):
    """The operation is not supported"""


class DepthExceeded(DefusedXmlException):
    """The nesting depth of an element exceeds the configured limit"""

    def __init__(self, depth, max_depth):
        super().__init__()
        self.depth = depth
        self.max_depth = max_depth

    def __str__(self):
        return (
            "DepthExceeded(depth={}, max_depth={})".format(
                self.depth, self.max_depth
            )
        )


class NodesExceeded(DefusedXmlException):
    """The number of element nodes exceeds the configured limit"""

    def __init__(self, count, max_nodes):
        super().__init__()
        self.count = count
        self.max_nodes = max_nodes

    def __str__(self):
        return (
            "NodesExceeded(count={}, max_nodes={})".format(
                self.count, self.max_nodes
            )
        )


def _normalize_limit(limit):
    """Normalize a depth/node budget argument.

    ``None`` or any non-positive value disables the limit.  Positive
    integers are returned as-is.
    """
    if limit is None:
        return 0
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer or None, got %r" % type(limit))
    if limit <= 0:
        return 0
    return limit


class _ElementBudget:
    """Track element nesting depth and total element node count.

    A ``max_depth`` of 0 disables the depth check, a ``max_nodes`` of 0
    disables the node count check.
    """

    __slots__ = ("depth", "count", "max_depth", "max_nodes")

    def __init__(self, max_depth=0, max_nodes=0):
        self.depth = 0
        self.count = 0
        self.max_depth = _normalize_limit(max_depth)
        self.max_nodes = _normalize_limit(max_nodes)

    def start(self):
        """Account for a newly opened element and enforce the budgets."""
        self.depth += 1
        self.count += 1
        if self.max_depth and self.depth > self.max_depth:
            raise DepthExceeded(self.depth, self.max_depth)
        if self.max_nodes and self.count > self.max_nodes:
            raise NodesExceeded(self.count, self.max_nodes)

    def end(self):
        """Account for a closed element."""
        self.depth -= 1


def _apply_defusing(defused_mod):
    assert defused_mod is sys.modules[defused_mod.__name__]
    stdlib_name = defused_mod.__origin__
    __import__(stdlib_name, {}, {}, ["*"])
    stdlib_mod = sys.modules[stdlib_name]
    stdlib_names = set(dir(stdlib_mod))
    for name, obj in vars(defused_mod).items():
        if name.startswith("_") or name not in stdlib_names:
            continue
        setattr(stdlib_mod, name, obj)
    return stdlib_mod
