"""Streaming parser for compressed PubMed baseline/update XML records.

`parse_file` yields one normalized dictionary at a time rather than collecting a
whole shard in memory, which is important on an 8 GB laptop. DeleteCitation
records are emitted as delete operations for a future downstream upsert/delete
stage. This parser does not download shards, filter the corpus, persist Parquet,
or update Elasticsearch/Qdrant by itself.
"""

import gzip
from collections.abc import Iterator
from pathlib import Path

from lxml import etree  # type: ignore[import-untyped]

KEEP = {"PubmedArticle", "DeleteCitation"}


def _txt(el) -> str:
    """Flatten nested XML text safely; absent elements become an empty string."""
    return "".join(el.itertext()).strip() if el is not None else ""


def parse_file(path: Path) -> Iterator[dict]:
    """Yield normalized article upserts and PMID tombstones from one `.xml.gz` file.

    Article abstracts retain their section labels when available. Each processed
    XML element is cleared promptly to cap parser memory while streaming shards.
    """
    with gzip.open(path, "rb") as fh:
        for _, el in etree.iterparse(fh, events=("end",), huge_tree=True):
            if el.tag not in KEEP:
                continue
            if el.tag == "DeleteCitation":
                for p in el.findall("PMID"):
                    yield {"op": "delete", "pmid": _txt(p)}
            else:
                mc = el.find("MedlineCitation")
                art = mc.find("Article")
                parts = []
                for at in art.findall("Abstract/AbstractText"):
                    label = at.get("Label")
                    parts.append(f"{label}: {_txt(at)}" if label else _txt(at))
                
                year = (art.findtext("Journal/JournalIssue/PubDate/Year")
                        or (art.findtext("Journal/JournalIssue/PubDate/MedlineDate") or "")[:4])
                
                yield {
                    "op": "upsert",
                    "pmid": _txt(mc.find("PMID")),
                    "title": _txt(art.find("ArticleTitle")),
                    "abstract": " ".join(p for p in parts if p),
                    "year": int(year) if year.isdigit() else None,
                    "journal": art.findtext("Journal/Title"),
                    "language": art.findtext("Language"),
                    "mesh": [_txt(x) for x in mc.findall("MeshHeadingList/MeshHeading/DescriptorName")],
                }
            # Clear element from memory to protect your 8GB RAM
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]