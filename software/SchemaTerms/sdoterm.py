#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import enum
import logging
import collections
from typing import Optional, Iterable, Tuple, List, Any, Dict, Type

log = logging.getLogger(__name__)

class SdoTermType(str, enum.Enum):
    """Enumeration describing the type of an SdoTerm."""

    TYPE = "Type"
    PROPERTY = "Property"
    DATATYPE = "Datatype"
    ENUMERATION = "Enumeration"
    ENUMERATIONVALUE = "Enumerationvalue"
    REFERENCE = "Reference"

    def __str__(self):
        return self.value

class UnexpandedTermError(LookupError):
    """Term is not expanded."""


class SdoTermOrId(object):
    """Wrapper that holds a term-id or a term, or nothing."""

    def __init__(
        self, term_id: Optional[str] = None, term: Optional[SdoTerm] = None
    ) -> None:
        # Empty instance is fine.
        assert not (term_id and term), f"{term_id} {term}"
        if term:
            self._term_id = term.id
        else:
            self._term_id = term_id
        self._term = term

    @property
    def expanded(self) -> bool:
        return not self._term_id or bool(self._term)

    @property
    def id(self) -> str:
        return self._term_id

    @property
    def term(self) -> SdoTerm:
        if not self._term:
             raise UnexpandedTermError()
        return self._term

    def setId(self, term_id: str) -> None:
        self._term_id = term_id

    def setTerm(self, term: SdoTerm) -> None:
        self._term = term
        if self._term:
            self._term_id = term.id

    def __str__(self):
        if not self._term:
            return f'{self._term_id}'
        return str(self._term)

    def __bool__(self):
        return bool(self._term_id)


class SdoTermSequence(object):
    """Sequence that holds either a sequence of term-ids, or a sequence of terms.

    If it holds a sequence of terms, the sequence is said to be expanded.
    It can only be changed by replacing all the values, either with ids, or term instances.

    """
    def __init__(self):
        self._term_dict = collections.OrderedDict()

    @classmethod
    def forElements(cls, elements: Iterable[Any]) -> SdoTermSequence:
        """Convert an arbitrary sequence into a SdoTermSequence."""
        if isinstance(elements, cls):
            return elements

        sequence = cls()
        if all(map(lambda e : isinstance(e, SdoTerm), elements)):
            sequence.setTerms(elements)
            return sequence
        term_ids = []
        for element in elements:
            try:
                # This will work for both SdoTerm instances, and SdoTermOrId
                term_id = element.id
            except AttributeError:
                term_id = element
            term_ids.append(term_id)
        sequence.setIds(term_ids)
        return sequence

    @property
    def expanded(self) -> bool:
        return all(self._term_dict.values())

    @property
    def ids(self) -> Tuple[str, ...]:
        return tuple(self._term_dict.keys())

    @property
    def terms(self) -> Tuple[SdoTerm, ...]:
        if not self.expanded:
          raise UnexpandedTermError()
        return tuple(self._term_dict.values())

    def setIds(self, term_ids: Iterable[str]) -> None:
        self._term_dict.clear()
        for term_id in term_ids:
            self._term_dict[term_id] = None

    def setTerms(self, terms: Iterable[SdoTerm]) -> None:
        self._term_dict.clear()
        for term in terms:
            self._term_dict[term.id] = term

    def clear(self):
        self._term_dict.clear()

    def __bool__(self):
        return bool(self._term_dict)

    def __len__(self):
        return len(self._term_dict)

    def __contains__(self, value):
        return value in self._term_dict.keys()

    def __str__(self):
        return '[' + ','.join(map(str, self.ids)) + ']'


class SdoTerm(object):
    """Abstract superclass for various schema.org types.

    Note that the semantics of the relational fields depends on the expansion_depth.

    0: Nothing is expanded
    1: Non recursive fields are expanded
    2: All recursive fields are expanded (and are at least at level 1)

    """


    TYPE_LIKE_TYPES = frozenset(
        [SdoTermType.TYPE, SdoTermType.DATATYPE, SdoTermType.ENUMERATION]
    )

    def __init__(self, termType: SdoTermType, term_id: str, uri: str, label: str):
        if type(self) == SdoTerm:
            raise Exception("<SdoTerm> must be subclassed.")

        assert isinstance(term_id, str)
        self._expansion_depth = 0
        self.termType = termType
        self.uri = uri
        self._term_id = term_id
        self.label = label

        self.acknowledgements: List[str] = []

        self.comment = ""
        self.comments: List[str] = []

        self.examples: List[str] = []
        self.pending = False
        self.retired = False
        self.extLayer = ""
        self.sources: List[str] = []


        self.supersededBy: Optional[str] = ""
        self.supersedes: Optional[str] = ""
        self.superseded = False
        self.superPaths: List[List[str]] = []

        self._termStack = SdoTermSequence()
        self._supers = SdoTermSequence()
        self._subs = SdoTermSequence()
        self._equivalents = SdoTermSequence()


    def __str__(self):
        return ("<%s: '%s' expansion depth: %s >") % (
            self.__class__.__name__.upper(),
            self.id,
            self._expansion_depth,
        )

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id

    def markExpanded(self, depth: int) -> None:
        self._expansion_depth = depth

    def expanded(self) -> bool:
        return self._expansion_depth > 1

    @property
    def supers(self) -> SdoTermSequence:
        return self._supers

    @property
    def subs(self) -> SdoTermSequence:
        return self._subs

    @property
    def equivalents(self) -> SdoTermSequence:
        return self._equivalents

    @property
    def termStack(self) -> SdoTermSequence:
        return self._termStack

    @property
    def id(self) -> str:
        return self._term_id

class SdoType(SdoTerm):
    """Term that defines a schema.org type"""

    def __init__(self, term_id: str, uri: str, label: str):
        SdoTerm.__init__(self, SdoTermType.TYPE, term_id, uri, label)

        self._properties = SdoTermSequence()
        self._allproperties = SdoTermSequence()
        self._expectedTypeFor = SdoTermSequence()

    @property
    def properties(self) -> SdoTermSequence:
        return self._properties

    @property
    def allproperties(self) -> SdoTermSequence:
        return self._allproperties

    @property
    def expectedTypeFor(self) -> SdoTermSequence:
        return self._expectedTypeFor


class SdoProperty(SdoTerm):
    """Term that defines a propery of another type."""

    def __init__(self, term_id: str, uri: str, label: str):
        SdoTerm.__init__(self, SdoTermType.PROPERTY, term_id, uri, label)
        self._domainIncludes = SdoTermSequence()
        self._rangeIncludes = SdoTermSequence()
        self._inverse = SdoTermOrId()

    @property
    def domainIncludes(self) -> SdoTermSequence:
        return self._domainIncludes

    @property
    def rangeIncludes(self) -> SdoTermSequence:
        return self._rangeIncludes

    @property
    def inverse(self) -> SdoTermOrId:
        return self._inverse



class SdoDataType(SdoTerm):
    """Term that defines one of the basic data-types: Boolean, Date, Text, Number etc."""

    def __init__(self, term_id: str, uri: str, label: str):
        SdoTerm.__init__(self, SdoTermType.DATATYPE, term_id, uri, label)

        self._properties = SdoTermSequence()
        self._allproperties = SdoTermSequence()
        self._expectedTypeFor = SdoTermSequence()

    @property
    def properties(self) -> SdoTermSequence:
        return self._properties

    @property
    def allproperties(self) -> SdoTermSequence:
        return self._allproperties

    @property
    def expectedTypeFor(self) -> SdoTermSequence:
        return self._expectedTypeFor


class SdoEnumeration(SdoTerm):
    """Term that defines a schema.org enumeration."""

    def __init__(self, term_id: str, uri: str, label: str):
        SdoTerm.__init__(self, SdoTermType.ENUMERATION, term_id, uri, label)
        self._properties = SdoTermSequence()
        self._allproperties = SdoTermSequence()
        self._expectedTypeFor = SdoTermSequence()
        self._enumerationMembers = SdoTermSequence()

    @property
    def properties(self) -> SdoTermSequence:
        return self._properties

    @property
    def allproperties(self) -> SdoTermSequence:
        return self._allproperties

    @property
    def expectedTypeFor(self) -> SdoTermSequence:
        return self._expectedTypeFor

    @property
    def enumerationMembers(self) -> SdoTermSequence:
        return self._enumerationMembers


class SdoEnumerationvalue(SdoTerm):
    """Term that defines a value within a schema.org enumeration."""

    def __init__(self, term_id: str, uri: str, label: str):
        SdoTerm.__init__(self, SdoTermType.ENUMERATIONVALUE, term_id, uri, label)
        self._enumerationParent = SdoTermOrId()

    @property
    def enumerationParent(self) -> SdoTermOrId:
        return self._enumerationParent


class SdoReference(SdoTerm):
    def __init__(self, term_id: str, uri: str, label: str):
        SdoTerm.__init__(self, SdoTermType.REFERENCE, term_id, uri, label)


_TYPES_FOR_TYPES = {
    SdoTermType.TYPE : SdoType,
    SdoTermType.DATATYPE : SdoDataType,
    SdoTermType.PROPERTY : SdoProperty,
    SdoTermType.ENUMERATION : SdoEnumeration,
    SdoTermType.ENUMERATIONVALUE : SdoEnumerationvalue,
    SdoTermType.REFERENCE : SdoReference
}


def SdoTermforType(term_type : SdoTermType, **kwargs) -> SdoTerm:
    t = _TYPES_FOR_TYPES[term_type]
    return t(**kwargs)


