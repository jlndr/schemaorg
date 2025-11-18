#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Import standard python libraries

from __future__ import annotations
import collections
from typing import Optional, List
import glob
import logging
import os
import traceback
import re
import sys


# Import schema.org libraries
if not os.getcwd() in sys.path:
    sys.path.insert(1, os.getcwd())

import software
import software.util.schemaglobals as schemaglobals
import software.SchemaTerms.sdoterm as sdoterm
import software.SchemaTerms.sdotermsource as sdotermsource
import software.SchemaTerms.localmarkdown as localmarkdown

log = logging.getLogger(__name__)

INCLUDE_RE = re.compile(R"---\s+([^.]+)\.md")
SECTION_SEPARATOR = "---"


class collaborator(object):
    """Wrapper for the collaboration meta-data."""

    COLLABORATORS: Dict[str, collaborator] = {}
    CONTRIBUTORS: Dict[str, collaborator] = {}

    def __init__(self, ref: str, desc: Optional[str] = None) -> None:
        self.ref = ref
        self.urirel = os.path.join("/docs", "collab", ref)
        self.uri = schemaglobals.HOMEPAGE + self.urirel
        self.docurl = self.urirel
        self.terms = None
        self.contributor = False
        self.img = self.code = self.title = self.url = None
        self.description = ""
        self.acknowledgement = ""
        self._parseDesc(desc)

        collaborator.COLLABORATORS[self.ref] = self
        log.debug(f"Created collaborator for '{ref}'")

    def __str__(self) -> str:
        return (
            f"<collaborator ref: {self.ref} uri: {self.uri} contributor: {self.contributor} img: '{self.img}' title: '{self.title}' url: 'self.url'>"
        )

    def _parseDesc(self, desc: Optional[str]) -> None:
        """Parses data from the pseudo-markdown format.

        Args:
          desc: content of the file, typically found at the path data/collab/*.md
        """
        if not desc:
            return
        section = 0
        attributes = {}
        lines_by_section = collections.defaultdict(list)
        section_selector = ""

        for line in desc.splitlines():
            if line.startswith(SECTION_SEPARATOR):
                section += 1
            if section == 1:
                if line.startswith(SECTION_SEPARATOR):
                    continue
                key, value = line.split(":", maxsplit=1)
                attributes[key.strip()] = value.strip()
                continue
            if section > 1:
                include_match = re.search(INCLUDE_RE, line)
                if include_match:
                    section_selector = include_match.groups(0)[0]
                    continue
                lines_by_section[section_selector].append(line)

        self.url = attributes.get("url")
        self.title = attributes.get("title")
        self.img = attributes.get("img")
        attributes.pop("url")
        attributes.pop("title")
        attributes.pop("img")
        if attributes:
            log.warning(
                f"Unknown attributes found in collaborator file {self.urirel}: {attributes}"
            )

        description_lines = lines_by_section["DescriptionText"]
        acknowledgement_lines = lines_by_section["AcknowledgementText"]
        lines_by_section.pop("DescriptionText")
        lines_by_section.pop("AcknowledgementText")

        if lines_by_section:
            log.warning(
                f"Unknown sections found in collaborator file {self.urirel}: {lines_by_section}"
            )

        self.description = localmarkdown.Markdown.parseLines(description_lines)
        self.acknowledgement = localmarkdown.Markdown.parseLines(acknowledgement_lines)

    def isContributor(self) -> bool:
        return self.contributor

    def getTerms(self) -> List[sdoterm.SdoTerm]:
        if not self.contributor:
            return []
        if not self.terms:
            self.terms = sdotermsource.SdoTermSource.getAcknowledgedTerms(self.uri)
        return self.terms

    @classmethod
    def getCollaborator(cls, ref: str) -> Optional[collaborator]:
        cls.loadCollaborators()
        key = os.path.basename(ref)
        coll = cls.COLLABORATORS.get(key, None)
        if not coll:
            log.warning(f"No collaborator for '{ref}'")
        return coll

    @classmethod
    def getContributor(cls, ref: str) -> Optional[collaborator]:
        key = os.path.basename(ref)
        cls.loadContributors()
        cont = cls.CONTRIBUTORS.get(key, None)
        if not cont:
            log.warning(f"No contributor for '{ref}'")
        return cont

    @classmethod
    def createCollaborator(cls, file_path: str) -> Optional[collaborator]:
        code = os.path.basename(file_path)
        ref, _ = os.path.splitext(code)
        try:
            with open(file_path, "r", encoding="utf-8") as file_handle:
                desc = file_handle.read()
            return cls(ref, desc=desc)
        except OSError as e:
            log.error(f"Error loading colaborator source: {e}")
            return None

    @classmethod
    def loadCollaborators(cls) -> None:
        if not len(cls.COLLABORATORS):
            for file_path in glob.glob("data/collab/*.md"):
                cls.createCollaborator(file_path)
            log.info(f"Loaded {len(cls.COLLABORATORS)} collaborators")

    @classmethod
    def createContributor(cls, ref: str) -> None:
        key = os.path.basename(ref)
        coll = cls.getCollaborator(key)
        if coll:
            coll.contributor = True
            cls.CONTRIBUTORS[key] = coll

    @classmethod
    def loadContributors(cls) -> None:
        if not len(cls.CONTRIBUTORS):
            cls.loadCollaborators()
            query = """
            SELECT distinct ?val WHERE {
                    [] schema:contributor ?val.
            }"""
            res = sdotermsource.SdoTermSource.query(query)
            for row in res:
                cls.createContributor(row.val)
            log.info(f"Loaded {len(cls.CONTRIBUTORS)} contributors")

    @classmethod
    def collaborators(cls) -> List[collaborator]:
        cls.loadCollaborators()
        return list(cls.COLLABORATORS.values())

    @classmethod
    def contributors(cls) -> List[collaborator]:
        cls.loadContributors()
        return list(cls.CONTRIBUTORS.values())
