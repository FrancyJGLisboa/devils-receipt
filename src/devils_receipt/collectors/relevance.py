"""Shared token-overlap relevance scoring for the bleed guard (§3 #5).

Ported from last30days/relevance.py. The scoring math, the synonym/low-signal
sets, and the two load-bearing constants (``RELEVANCE_FLOOR``, ``MIN_ON_TOPIC``)
are preserved VERBATIM — they are the contract the bleed-guard test consumes.
The only change vs the reference is the tokenizer: the commodity roster is an
English ag/energy/macro domain, so the CJK segmentation path is dropped in
favour of a stdlib ``\\w+`` tokenizer. (70% in the GOAL is a RATIO of items
scoring >= RELEVANCE_FLOOR, NOT a competing relevance constant.)
"""

import re
from typing import List, Optional, Set

# Stopwords for relevance computation (common English words that dilute token overlap)
STOPWORDS = frozenset({
    'the', 'a', 'an', 'to', 'for', 'how', 'is', 'in', 'of', 'on',
    'and', 'with', 'from', 'by', 'at', 'this', 'that', 'it', 'my',
    'your', 'i', 'me', 'we', 'you', 'what', 'are', 'do', 'can',
    'its', 'be', 'or', 'not', 'no', 'so', 'if', 'but', 'about',
    'all', 'just', 'get', 'has', 'have', 'was', 'will',
})

# Shared relevance-ranking thresholds. RELEVANCE_FLOOR: posts below this are
# off-topic; the zero-overlap tail is dropped when anything relevant remains.
# MIN_ON_TOPIC: how many posts must clear the soft floor before it is applied
# wholesale. REUSED VERBATIM — do not retune.
RELEVANCE_FLOOR = 0.1
MIN_ON_TOPIC = 5


# Synonym groups for relevance scoring (bidirectional expansion). Commodity
# domain: tie common ticker/abbreviation variants to their long forms so a
# "soybean" query still scores a "soy" headline, etc.
SYNONYMS = {
    'soy': {'soybean', 'soybeans'},
    'soybean': {'soy', 'soybeans'},
    'soybeans': {'soy', 'soybean'},
    'corn': {'maize'},
    'maize': {'corn'},
    'wheat': {'grain'},
    'crude': {'oil', 'wti', 'brent'},
    'oil': {'crude'},
    'natgas': {'natural', 'gas', 'lng'},
    'fed': {'fomc', 'federal'},
    'usd': {'dollar'},
    'opec': {'opec+'},
    'cot': {'cftc'},
    'wasde': {'usda'},
}

# Generic query words that should not carry relevance on their own. The
# commodity-context trade/news words (export, sales, report, demand, supply, …)
# are the load-bearing addition over the reference: a topic like "corn export
# sales" must score on the ENTITY (corn), never on "export"/"sales", or items
# about Apple/Ukraine/weapons exports bleed in. See §3 #5.
LOW_SIGNAL_QUERY_TOKENS = frozenset({
    'advice', 'best', 'chance', 'chances', 'compare', 'comparison',
    'differences', 'explain', 'guide', 'guides', 'how', 'latest', 'news',
    'odds', 'opinion', 'opinions', 'prediction', 'predictions', 'probability',
    'probabilities', 'rate', 'review', 'reviews', 'thoughts', 'tip', 'tips',
    'tutorial', 'tutorials', 'update', 'updates', 'use', 'using', 'versus',
    'vs', 'worth', 'market', 'markets', 'price', 'prices',
    # commodity-context generics — never an entity on their own
    'export', 'exports', 'sale', 'sales', 'report', 'reports', 'demand',
    'supply', 'data', 'futures', 'trade', 'trading', 'season', 'outlook',
    'forecast', 'reaction', 'cut', 'cuts', 'ban', 'record', 'high', 'low',
})

_WORD_RE = re.compile(r"\w+")


def tokenize(text: str) -> Set[str]:
    """Lowercase, strip punctuation, remove stopwords, drop single-char tokens.

    Expands tokens with synonyms for better cross-domain matching.
    """
    words = _WORD_RE.findall(text.lower())
    tokens = {w for w in words if w not in STOPWORDS and len(w) > 1}
    expanded = set(tokens)
    for t in tokens:
        if t in SYNONYMS:
            expanded.update(SYNONYMS[t])
    return expanded


def _normalize_phrase(text: str) -> str:
    """Normalize text for phrase containment checks."""
    return ' '.join(re.sub(r'[^\w\s]', ' ', text.lower()).split())


def token_overlap_relevance(
    query: str,
    text: str,
    hashtags: Optional[List[str]] = None,
) -> float:
    """Compute a query-centric relevance score between 0.0 and 1.0.

    The score combines query coverage, informative-token coverage, a small
    precision term, and an exact-phrase bonus. Generic tokens alone are capped
    below typical relevance filter thresholds.
    """
    q_tokens = tokenize(query)

    combined = text
    if hashtags:
        combined = f"{text} {' '.join(hashtags)}"
    t_tokens = tokenize(combined)

    if hashtags:
        for tag in hashtags:
            tag_lower = tag.lower()
            for qt in q_tokens:
                if qt in tag_lower and qt != tag_lower:
                    t_tokens.add(qt)

    if not q_tokens:
        return 0.5  # Neutral fallback for empty/stopword-only queries

    overlap_tokens = q_tokens & t_tokens
    overlap = len(overlap_tokens)
    if overlap == 0:
        return 0.0

    informative_q_tokens = {t for t in q_tokens if t not in LOW_SIGNAL_QUERY_TOKENS} or q_tokens

    coverage = overlap / len(q_tokens)
    informative_overlap = len(informative_q_tokens & t_tokens) / len(informative_q_tokens)
    precision_denominator = min(len(t_tokens), len(q_tokens) + 4) or 1
    precision = overlap / precision_denominator

    phrase_bonus = 0.0
    normalized_query = _normalize_phrase(query)
    normalized_text = _normalize_phrase(combined)
    if normalized_query:
        contained = normalized_query in normalized_text
        if contained:
            phrase_bonus = 0.12 if len(normalized_query.split()) > 1 else 0.16

    base = (
        0.55 * (coverage ** 1.35) +
        0.25 * informative_overlap +
        0.20 * precision
    )

    # ENTITY GATE: if the query has informative (entity) tokens and NONE of them
    # appear in the item, the item is off-topic regardless of how many generic
    # tokens ("export", "sales") it shares. Return 0.0 (below RELEVANCE_FLOOR) so
    # the surfacing filter drops it — this is what stops Apple/Ukraine/weapons
    # "export" items bleeding into a "corn export sales" query (§3 #5).
    if informative_q_tokens and not (informative_q_tokens & t_tokens):
        return 0.0

    return round(min(1.0, base + phrase_bonus), 2)
