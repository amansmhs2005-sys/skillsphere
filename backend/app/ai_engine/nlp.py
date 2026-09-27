"""AI Recommendation module (SRS Section 4.2).

Per SRS Section 2.5, this deliberately uses a classic NLP/text-similarity
approach (TF-IDF + cosine similarity, plus frequency-based extractive
summarization) rather than a generative model — no GPU or external LLM
service is assumed to be available to a student project. Per SRS
assumption 2.7, if scikit-learn is somehow unavailable, topic detection
falls back to the same keyword search used in skills.routes.
"""
import re
from collections import Counter

from app.models.skill import Skill
from app.models.progress import Progress

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    SKLEARN_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only if sklearn is missing
    SKLEARN_AVAILABLE = False

# A short, hand-rolled stopword list so keyword extraction doesn't need an
# external corpus download (keeps the module self-contained/offline-safe).
STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "and", "or", "but", "with", "as", "at",
    "by", "from", "that", "this", "it", "its", "i", "we", "you", "he",
    "she", "they", "them", "his", "her", "their", "our", "your", "not",
    "do", "does", "did", "have", "has", "had", "can", "could", "will",
    "would", "should", "about", "into", "than", "then", "so", "if",
    "my", "me", "us", "what", "how", "when", "why", "just", "also",
}

RELEVANCE_THRESHOLD = 0.05  # below this, treat as "no confident match"


def _skill_doc(skill: Skill) -> str:
    return " ".join(filter(None, [skill.skill_name, skill.topic_name, skill.description or ""]))


def detect_topic(query_text: str):
    """REQ-6: identify the most relevant topic(s) using TF-IDF + cosine
    similarity over every registered skill/topic in the system.

    Returns a list of {skill, score} dicts, sorted by score desc, for
    every Skill row — the caller decides how many to use.
    """
    skills = Skill.query.all()
    if not skills:
        return []

    if not SKLEARN_AVAILABLE:
        # Fallback: plain keyword containment scoring (assumption 2.7).
        q = query_text.lower()
        results = []
        for s in skills:
            doc = _skill_doc(s).lower()
            score = 1.0 if any(word in doc for word in q.split()) else 0.0
            results.append({"skill": s, "score": score})
        return sorted(results, key=lambda r: r["score"], reverse=True)

    corpus = [_skill_doc(s) for s in skills]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(corpus + [query_text])
    query_vec = tfidf_matrix[-1]
    doc_vecs = tfidf_matrix[:-1]
    scores = cosine_similarity(query_vec, doc_vecs)[0]

    results = [{"skill": s, "score": float(sc)} for s, sc in zip(skills, scores)]
    return sorted(results, key=lambda r: r["score"], reverse=True)


def rank_tutors_for_topic(detected_results, top_skill: Skill):
    """REQ-7: rank tutors teaching the same (skill_name, topic_name) as
    the top detected match, using a weighted score:

        40% topic-match relevance (this tutor's own TF-IDF score)
        30% trust score
        20% completed-session count (capped, diminishing returns)
        10% availability (has at least one declared slot)

    These weights are this implementation's resolution of TBD-4 (exact
    weights "to be finalized during design"); tune the constants below
    if usage data suggests otherwise.
    """
    from app.models.request_session import RequestSession  # avoid circular import

    candidates = [
        r
        for r in detected_results
        if r["skill"].skill_name.lower() == top_skill.skill_name.lower()
        and r["skill"].topic_name.lower() == top_skill.topic_name.lower()
    ]

    ranked = []
    for r in candidates:
        skill = r["skill"]
        tutor = skill.tutor
        if tutor is None:
            continue

        relevance = r["score"]
        trust_norm = float(tutor.trust_score) / 100.0
        completed_count = RequestSession.query.filter_by(tutor_id=tutor.user_id, status="completed").count()
        sessions_norm = min(completed_count / 10.0, 1.0)
        availability_norm = 1.0 if tutor.availability_slots else 0.0

        weighted_score = (
            0.4 * relevance + 0.3 * trust_norm + 0.2 * sessions_norm + 0.1 * availability_norm
        )

        ranked.append(
            {
                "skill": skill,
                "tutor": tutor,
                "weighted_score": round(weighted_score, 4),
                "breakdown": {
                    "relevance": round(relevance, 4),
                    "trust_score": float(tutor.trust_score),
                    "completed_sessions": completed_count,
                    "has_availability": bool(tutor.availability_slots),
                },
            }
        )

    return sorted(ranked, key=lambda r: r["weighted_score"], reverse=True)


def related_topics(top_skill: Skill, user_id: int, limit: int = 5):
    """REQ-8: suggest related topics based on the detected topic (same
    skill_name) and the learner's own search history."""
    from app.models.search_history import SearchHistory  # avoid circular import

    seen_keys = {(top_skill.skill_name.lower(), top_skill.topic_name.lower())}
    related = []

    # Same-skill siblings.
    siblings = (
        Skill.query.filter(Skill.skill_name.ilike(top_skill.skill_name))
        .filter(Skill.topic_name != top_skill.topic_name)
        .limit(limit * 2)
        .all()
    )
    for s in siblings:
        key = (s.skill_name.lower(), s.topic_name.lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        related.append({"skill_name": s.skill_name, "topic_name": s.topic_name, "reason": "same skill area"})

    # Topics from this learner's recent search history.
    if user_id and len(related) < limit:
        recent = (
            SearchHistory.query.filter_by(user_id=user_id)
            .order_by(SearchHistory.created_at.desc())
            .limit(10)
            .all()
        )
        for h in recent:
            if not h.detected_skill_id:
                continue
            s = Skill.query.get(h.detected_skill_id)
            if not s:
                continue
            key = (s.skill_name.lower(), s.topic_name.lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            related.append({"skill_name": s.skill_name, "topic_name": s.topic_name, "reason": "you also searched"})

    return related[:limit]


# ---------------------------------------------------------------
# REQ-9: session summary generation
# ---------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[a-zA-Z']+")


def _split_sentences(text: str):
    text = (text or "").strip()
    if not text:
        return []
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def extract_keywords(text: str, top_n: int = 6):
    words = [w.lower() for w in _WORD_RE.findall(text or "") if w.lower() not in STOPWORDS and len(w) > 2]
    if not words:
        return []
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_n)]


def extractive_summary(text: str, max_sentences: int = 3):
    """Classic frequency-weighted extractive summarization (a simplified
    Luhn's algorithm) — no external NLP service required."""
    sentences = _split_sentences(text)
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    word_freq = Counter(
        w.lower() for w in _WORD_RE.findall(text) if w.lower() not in STOPWORDS and len(w) > 2
    )
    if not word_freq:
        return " ".join(sentences[:max_sentences])

    scored = []
    for idx, sentence in enumerate(sentences):
        words = [w.lower() for w in _WORD_RE.findall(sentence)]
        score = sum(word_freq.get(w, 0) for w in words)
        scored.append((idx, sentence, score))

    top = sorted(scored, key=lambda x: x[2], reverse=True)[:max_sentences]
    top_in_order = sorted(top, key=lambda x: x[0])
    return " ".join(s for _, s, _ in top_in_order)


def _find_homework_sentence(text: str):
    for sentence in _split_sentences(text):
        if re.search(r"\b(homework|assignment|practice|exercise)\b", sentence, re.IGNORECASE):
            return sentence
    return None


def generate_session_summary(session) -> dict:
    """REQ-9: generate a concise session summary from the tutor's notes
    after a session is marked complete."""
    notes = session.session_notes or ""
    topic = session.topic

    summary_text = extractive_summary(notes) if notes else "No session notes were recorded."
    key_concepts = extract_keywords(notes, top_n=6)
    homework = _find_homework_sentence(notes) or "No homework was recorded for this session."

    next_topic = None
    if topic:
        candidates = related_topics(topic, session.learner_id, limit=5)
        # Prefer a related topic the learner hasn't already completed.
        pending_names = {
            p.topic.topic_name.lower()
            for p in Progress.query.filter_by(learner_id=session.learner_id, status="pending").all()
            if p.topic
        }
        next_topic = next(
            (c for c in candidates if c["topic_name"].lower() in pending_names),
            candidates[0] if candidates else None,
        )

    return {
        "topics_discussed": [f"{topic.skill_name} — {topic.topic_name}"] if topic else [],
        "key_concepts": key_concepts,
        "summary": summary_text,
        "homework": homework,
        "recommended_next_topic": next_topic,
    }
