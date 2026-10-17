"""Generator losowych układów kombinacyjnych do testów (powtarzalny – zależy tylko od ziarna).

Układy mają 2–5 wejść i 3–10 bramek wszystkich typów (rozmiar jak na zajęciach). Rozgałęzienie sygnału
jest rysowane jak w aplikacji i w programie TESTER: jeden węzeł, z którego wychodzą wszystkie gałęzie.
Rodzina „bez rekonwergencji” nie ma ścieżek, które rozchodzą się i ponownie spotykają;
rodzina „z rekonwergencją” zawsze je ma.
"""
import random

from oracle import fault_cone, gate_inputs

GATES = ['AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR', 'NOT']


def consumers(comps, sig):
    return [cid for cid, c in comps.items() if sig in gate_inputs(c)]


def has_reconvergence(comps):
    """Czy jakieś rozgałęzienie ma dwie gałęzie, które ponownie się spotykają."""
    for sig in comps:
        branches = [fault_cone(comps, c) for c in consumers(comps, sig)]
        for i in range(len(branches)):
            for j in range(i + 1, len(branches)):
                if branches[i] & branches[j]: return True
    return False


def _build(rng):
    comps, n = {}, 0

    def add(ctype, ins):
        nonlocal n
        n += 1
        cid = {'IN': 'X', 'NODE': 'W'}.get(ctype, 'G') + str(n)
        comps[cid] = {'id': cid, 'type': ctype, 'x': 0, 'y': 0, 'inputs': (ins + [None, None])[:2], 'waypoints': [[], []]}
        return cid

    nodes = {}  # sygnał -> jego węzeł rozgałęziający

    def connect(src):
        """Drugie i kolejne podłączenie do sygnału idzie przez jeden wspólny węzeł."""
        if src in nodes: return nodes[src]
        users = consumers(comps, src)
        if not users: return src
        node = nodes[src] = add('NODE', [src])
        for u in users:
            comps[u]['inputs'] = [node if i == src else i for i in comps[u]['inputs']]
        return node

    signals = [add('IN', []) for _ in range(rng.randint(2, 5))]
    for _ in range(rng.randint(3, 10)):
        gtype = rng.choice(GATES)
        unused = [s for s in signals if not consumers(comps, s)]
        pool = unused if unused and rng.random() < 0.7 else signals
        first = rng.choice(pool)
        if gtype == 'NOT':
            ins = [connect(first)]
        else:
            second = rng.choice([s for s in signals if s != first])
            ins = [connect(first), connect(second)]
            if rng.random() < 0.5: ins.reverse()
        signals.append(add(gtype, ins))
    if any(not consumers(comps, s) for s in signals if comps[s]['type'] == 'IN'): return None
    return comps


def random_circuit(seed, reconvergent):
    rng = random.Random(seed)
    while True:
        comps = _build(rng)
        if comps and has_reconvergence(comps) == reconvergent: return comps
