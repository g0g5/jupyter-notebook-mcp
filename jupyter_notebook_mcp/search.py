from __future__ import annotations

import re

from .session import _require_notebook_loaded


WORD_RE = re.compile(r"\S+")


def _extract_search_snippets(
    source: str,
    keywords: list[str],
    context_words: int = 2,
) -> list[str]:
    if not source or not keywords:
        return []

    lowered_source = source.lower()
    lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
    if not lowered_keywords:
        return []

    matches: list[tuple[int, int]] = []
    for keyword in lowered_keywords:
        start = 0
        while True:
            found = lowered_source.find(keyword, start)
            if found == -1:
                break
            matches.append((found, found + len(keyword)))
            start = found + 1

    if not matches:
        return []

    word_spans = [(match.start(), match.end()) for match in WORD_RE.finditer(source)]
    if not word_spans:
        return []

    expanded_ranges: list[tuple[int, int]] = []
    for start, end in sorted(matches):
        overlapping_word_indices = [
            i
            for i, (word_start, word_end) in enumerate(word_spans)
            if not (word_end <= start or word_start >= end)
        ]
        if not overlapping_word_indices:
            continue

        left_word = max(0, overlapping_word_indices[0] - context_words)
        right_word = min(
            len(word_spans) - 1, overlapping_word_indices[-1] + context_words
        )
        expanded_ranges.append((left_word, right_word))

    if not expanded_ranges:
        return []

    merged_ranges: list[tuple[int, int]] = []
    for left_word, right_word in sorted(expanded_ranges):
        if not merged_ranges:
            merged_ranges.append((left_word, right_word))
            continue

        prev_left, prev_right = merged_ranges[-1]
        if left_word <= prev_right + 1:
            merged_ranges[-1] = (prev_left, max(prev_right, right_word))
        else:
            merged_ranges.append((left_word, right_word))

    snippets: list[str] = []
    words = [source[start:end] for start, end in word_spans]
    for left_word, right_word in merged_ranges:
        snippets.append(f"... {' '.join(words[left_word : right_word + 1])} ...")

    return snippets


def search_cells(keywords: str) -> dict[str, object]:
    nb = _require_notebook_loaded()

    parsed_keywords = keywords.split()
    if not parsed_keywords:
        return {"keywords": [], "results": []}

    lowered_keywords = [keyword.lower() for keyword in parsed_keywords]

    results: list[dict[str, object]] = []
    for index, cell in enumerate(nb.cells):
        source = str(cell.source)
        lowered_source = source.lower()
        if not all(keyword in lowered_source for keyword in lowered_keywords):
            continue

        snippets = _extract_search_snippets(source, parsed_keywords)
        results.append({"index": index, "snippets": snippets})

    return {"keywords": parsed_keywords, "results": results}
