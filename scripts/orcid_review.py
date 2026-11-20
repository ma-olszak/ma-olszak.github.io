#!/usr/bin/env python3
"""Build a review report from public ORCID records without editing the site."""

import argparse
from collections import defaultdict
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

import yaml


ORCID = "0000-0001-8920-5309"
WORKS_URL = f"https://pub.orcid.org/v3.0/{ORCID}/works"
PUBLICATIONS = Path(__file__).resolve().parents[1] / "_publications"
DOI = re.compile(r'10\.\d{4,9}/[^\s<>"\']+', re.IGNORECASE)


def normalise_doi(value):
    value = unquote(value).strip().lower()
    value = re.sub(r"^(?:doi:\s*|https?://(?:dx\.)?doi\.org/)", "", value)
    return value if DOI.fullmatch(value) else None


def normalise_text(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", value))


def existing_publications():
    by_doi = defaultdict(set)
    by_put_code = defaultdict(set)
    titles = {}
    for path in sorted(PUBLICATIONS.glob("*.md")):
        _, header, _ = path.read_text(encoding="utf-8").split("---", 2)
        fields = yaml.safe_load(header)
        titles[path.name] = normalise_text(fields["title"])
        for field in ("doi", "paperurl", "citation"):
            for match in DOI.findall(unquote(str(fields.get(field, "")))):
                doi = match.rstrip(".,;")
                doi = doi.rstrip(")") if doi.count(")") > doi.count("(") else doi
                by_doi[doi.lower()].add(path.name)
        for value in fields.get("related_dois", []):
            doi = normalise_doi(value)
            if doi:
                by_doi[doi].add(path.name)
        for put_code in fields.get("orcid_put_codes", []):
            by_put_code[put_code].add(path.name)
    return by_doi, by_put_code, titles


def get_json(url):
    request = Request(
        url, headers={"Accept": "application/json", "User-Agent": "ma-olszak.github.io ORCID review"}
    )
    with urlopen(request, timeout=12) as response:
        return json.load(response)


def orcid_value(value):
    return (value or {}).get("value")


def collect_candidates(groups):
    candidates = defaultdict(list)
    for group in groups:
        summaries = group["work-summary"]
        group_key = min(summary["put-code"] for summary in summaries)
        for summary in summaries:
            identifiers = (summary.get("external-ids") or {}).get("external-id") or []
            dois = {
                normalise_doi(identifier["external-id-value"])
                for identifier in identifiers
                if identifier["external-id-type"].lower() == "doi"
                and identifier.get("external-id-relationship") == "self"
            } - {None}
            source = summary.get("source") or {}
            record = {
                "group": group_key,
                "put_code": summary["put-code"],
                "title": orcid_value((summary.get("title") or {}).get("title")),
                "type": summary.get("type"),
                "year": orcid_value((summary.get("publication-date") or {}).get("year")),
                "venue": orcid_value(summary.get("journal-title")),
                "source": orcid_value(source.get("source-name")),
            }
            for key in sorted(dois) or [f"orcid-group:{group_key}"]:
                candidates[key].append(record)
    return candidates


def crossref_metadata(doi):
    try:
        record = get_json("https://api.crossref.org/works/" + quote(doi, safe="/"))["message"]
    except HTTPError as error:
        if error.code == 404:
            return None
        raise
    authors = record.get("author") or []
    date = record.get("published-print") or record.get("published") or {}
    return {
        "doi": record["DOI"],
        "title": next(iter(record.get("title") or []), None),
        "authors": [
            author.get("name") or " ".join(
                filter(None, (author.get("given"), author.get("family")))
            )
            for author in authors
        ],
        "author_orcids": [author["ORCID"] for author in authors if author.get("ORCID")],
        "venue": next(iter(record.get("container-title") or []), None),
        "type": record.get("type"),
        "year": (date.get("date-parts") or [[None]])[0][0],
        "url": record.get("URL"),
    }


def similar_title(title, other):
    return bool(title and other and SequenceMatcher(None, title, other).ratio() >= 0.90)


def build_report(payload):
    by_doi, by_put_code, existing_titles = existing_publications()
    groups = payload["group"]
    candidates = collect_candidates(groups)
    titles = {
        key: {normalise_text(record["title"] or "") for record in records}
        for key, records in candidates.items()
    }
    group_keys = defaultdict(set)
    for key, records in candidates.items():
        for record in records:
            group_keys[record["group"]].add(key)

    entries = []
    for key, records in sorted(candidates.items()):
        doi = normalise_doi(key)
        doi_matches = by_doi.get(doi, set())
        orcid_matches = set().union(*(by_put_code[record["put_code"]] for record in records))
        entry = {
            "key": key,
            "doi": doi,
            "status": "already_listed" if doi_matches or orcid_matches else "needs_review",
            "existing_doi_matches": sorted(doi_matches),
            "existing_orcid_matches": sorted(orcid_matches),
            "orcid_records": records,
        }
        if entry["status"] == "needs_review":
            entry["possible_existing_matches"] = sorted(
                filename for filename, other in existing_titles.items()
                if any(similar_title(title, other) for title in titles[key])
            )
            related = set().union(*(group_keys[record["group"]] for record in records))
            related.update(
                other_key for other_key, other_titles in titles.items()
                if any(similar_title(title, other) for title in titles[key] for other in other_titles)
            )
            entry["possible_related_candidates"] = sorted(related - {key})
            entry["crossref"] = crossref_metadata(doi) if doi else None
        entries.append(entry)

    return {
        "orcid": ORCID,
        "source": WORKS_URL,
        "orcid_groups": len(groups),
        "orcid_records": sum(len(group["work-summary"]) for group in groups),
        "entries": entries,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.suffix != ".json" or args.output.resolve().is_relative_to(PUBLICATIONS.resolve()):
        parser.error("Write a JSON report outside _publications.")
    try:
        report = build_report(get_json(WORKS_URL))
    except (OSError, URLError, ValueError, TypeError, KeyError) as error:
        print(f"ORCID review failed: {error}", file=sys.stderr)
        return 1
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    already_listed = sum(entry["status"] == "already_listed" for entry in report["entries"])
    print(f"{already_listed} already listed, {len(report['entries']) - already_listed} to review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
