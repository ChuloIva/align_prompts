"""
Seed concepts for Semantic Gravity Mapping.

This module defines 200 niche concepts across 20 diverse domains.
These serve as starting points for BFS expansion of the semantic graph.

The concepts are intentionally "niche" to avoid early convergence to
common words like "life", "thing", or "system". Each domain contributes
10 specific concepts that are characteristic of that field.
"""

from typing import List, Dict

# 20 domains × 10 concepts each = 200 total seeds
DOMAINS: Dict[str, List[str]] = {
    'quantum_physics': [
        'entanglement',
        'superposition',
        'decoherence',
        'qubit',
        'wavefunction',
        'uncertainty',
        'tunneling',
        'spin',
        'fermion',
        'boson'
    ],

    'medieval_history': [
        'feudalism',
        'crusade',
        'monastery',
        'charter',
        'vassal',
        'trebuchet',
        'guild',
        'knight',
        'serf',
        'fief'
    ],

    'anime': [
        'shonen',
        'mecha',
        'isekai',
        'tsundere',
        'seinen',
        'chibi',
        'otaku',
        'mangaka',
        'doujin',
        'cosplay'
    ],

    'molecular_gastronomy': [
        'spherification',
        'emulsion',
        'gelification',
        'sous-vide',
        'foam',
        'caviar',
        'deconstruction',
        'nitrogen',
        'texture',
        'umami'
    ],

    'philosophy': [
        'phenomenology',
        'epistemology',
        'ontology',
        'nihilism',
        'existentialism',
        'solipsism',
        'determinism',
        'dialectic',
        'metaphysics',
        'virtue'
    ],

    'immunology': [
        'antibody',
        'cytokine',
        'lymphocyte',
        'macrophage',
        'antigen',
        'interferon',
        'histamine',
        'complement',
        'phagocytosis',
        'inflammation'
    ],

    'music_theory': [
        'counterpoint',
        'cadence',
        'modulation',
        'fugue',
        'tritone',
        'syncopation',
        'timbre',
        'harmonic',
        'overtone',
        'polyrhythm'
    ],

    'gothic_architecture': [
        'buttress',
        'gargoyle',
        'vault',
        'spire',
        'tracery',
        'rose-window',
        'nave',
        'transept',
        'clerestory',
        'pinnacle'
    ],

    'norse_mythology': [
        'Ragnarok',
        'Valhalla',
        'Yggdrasil',
        'Valkyrie',
        'Midgard',
        'Asgard',
        'Fenrir',
        'Mjolnir',
        'rune',
        'Jotun'
    ],

    'organic_chemistry': [
        'carbocation',
        'nucleophile',
        'electrophile',
        'resonance',
        'chirality',
        'aromatic',
        'alkyne',
        'ester',
        'ketone',
        'peptide'
    ],

    'politics': [
        'gerrymandering',
        'filibuster',
        'caucus',
        'lobby',
        'referendum',
        'bicameral',
        'sovereignty',
        'impeachment',
        'veto',
        'coalition'
    ],

    'computer_science': [
        'polymorphism',
        'recursion',
        'heap',
        'stack',
        'algorithm',
        'encryption',
        'compiler',
        'thread',
        'mutex',
        'pointer'
    ],

    'psychology': [
        'cognition',
        'schema',
        'conditioning',
        'neurosis',
        'ego',
        'repression',
        'bias',
        'stimulus',
        'behavior',
        'perception'
    ],

    'law': [
        'plaintiff',
        'tort',
        'jurisdiction',
        'litigation',
        'statute',
        'precedent',
        'affidavit',
        'subpoena',
        'injunction',
        'arraignment'
    ],

    'linguistics': [
        'morpheme',
        'phoneme',
        'syntax',
        'semantics',
        'pragmatics',
        'dialect',
        'lexicon',
        'inflection',
        'conjugation',
        'etymology'
    ],

    'physics': [
        'momentum',
        'inertia',
        'friction',
        'velocity',
        'acceleration',
        'torque',
        'gravity',
        'magnetism',
        'thermodynamics',
        'photon'
    ],

    'body': [
        'tendon',
        'ligament',
        'cartilage',
        'neuron',
        'hormone',
        'enzyme',
        'metabolism',
        'circulation',
        'respiration',
        'mitosis'
    ],

    'relationships': [
        'intimacy',
        'attachment',
        'boundary',
        'communication',
        'empathy',
        'trust',
        'conflict',
        'compromise',
        'codependency',
        'reciprocity'
    ],

    'nature': [
        'ecosystem',
        'biodiversity',
        'symbiosis',
        'pollination',
        'photosynthesis',
        'migration',
        'hibernation',
        'predator',
        'prey',
        'habitat'
    ],

    'religion': [
        'pilgrimage',
        'scripture',
        'sacrament',
        'prophet',
        'deity',
        'ritual',
        'prayer',
        'meditation',
        'salvation',
        'divinity'
    ]
}


def get_all_seeds() -> List[str]:
    """
    Returns all 200 seed words as a flat list.

    Returns:
        List of 200 seed concept strings

    Example:
        >>> seeds = get_all_seeds()
        >>> len(seeds)
        200
        >>> 'entanglement' in seeds
        True
    """
    return [word for words in DOMAINS.values() for word in words]


def get_seeds_by_domain(domain: str) -> List[str]:
    """
    Returns 10 seeds for a specific domain.

    Args:
        domain: Domain name (e.g., 'quantum_physics', 'anime')

    Returns:
        List of 10 seed concepts for that domain

    Raises:
        KeyError: If domain name is not recognized

    Example:
        >>> physics_seeds = get_seeds_by_domain('quantum_physics')
        >>> len(physics_seeds)
        10
        >>> 'superposition' in physics_seeds
        True
    """
    return DOMAINS[domain]


def get_domain_names() -> List[str]:
    """
    Returns list of all domain names.

    Returns:
        List of 20 domain name strings

    Example:
        >>> domains = get_domain_names()
        >>> 'quantum_physics' in domains
        True
    """
    return list(DOMAINS.keys())


def get_seeds_with_metadata() -> List[Dict[str, str]]:
    """
    Returns seeds with their domain metadata.

    Useful for tracking which domain each seed came from
    during graph analysis.

    Returns:
        List of dicts with 'word' and 'domain' keys

    Example:
        >>> seeds = get_seeds_with_metadata()
        >>> seeds[0]
        {'word': 'entanglement', 'domain': 'quantum_physics'}
    """
    seeds_with_meta = []
    for domain, words in DOMAINS.items():
        for word in words:
            seeds_with_meta.append({
                'word': word,
                'domain': domain
            })
    return seeds_with_meta


# Validation: Ensure exactly 200 seeds
assert len(get_all_seeds()) == 200, "Must have exactly 200 seed concepts"
assert len(DOMAINS) == 20, "Must have exactly 20 domains"
assert all(len(words) == 10 for words in DOMAINS.values()), "Each domain must have exactly 10 concepts"
