"""Niezależna wyrocznia testów – symulacja układu w logice 0/1 i w D-algebrze.

Nie korzysta z kodu silnika. To na jej podstawie testy rozstrzygają, czy tabela
wygenerowana przez silnik jest zgodna z prawdą: czy test wykrywa usterkę, czy stany
linii zgadzają się z symulacją i czy zgłoszona sprzeczność jest rzeczywista.

Wartości linii jak w silniku: '0', '1', 'D' (zdatny 1 / błędny 0), '~D' (zdatny 0 / błędny 1), 'x'.
Bramki mogą mieć dowolną liczbę wejść (materiały używają np. 3-wejściowego OR).
"""
import itertools

LOGIC = {
    'AND': lambda v: int(all(v)), 'OR': lambda v: int(any(v)),
    'NAND': lambda v: 1 - int(all(v)), 'NOR': lambda v: 1 - int(any(v)),
    'XOR': lambda v: sum(v) % 2, 'XNOR': lambda v: 1 - sum(v) % 2,
    'NOT': lambda v: 1 - v[0], 'NODE': lambda v: v[0],
}
D_PAIRS = {'0': (0, 0), '1': (1, 1), 'D': (1, 0), '~D': (0, 1)}
D_NAMES = {pair: name for name, pair in D_PAIRS.items()}


def gate_inputs(comp):
    ins = [i for i in comp['inputs'] if i]
    return ins[:1] if comp['type'] in ('NOT', 'NODE') else ins


def simulate(comps, pis, fault=None):
    """Wartości 0/1 wszystkich linii. fault = (linia, 0|1) wymusza stan wyjścia elementu."""
    memo = {}

    def val(cid):
        if cid not in memo:
            c = comps[cid]
            if fault and cid == fault[0]: memo[cid] = fault[1]
            elif c['type'] == 'IN': memo[cid] = pis[cid]
            else: memo[cid] = LOGIC[c['type']]([val(i) for i in gate_inputs(c)])
        return memo[cid]

    return {cid: val(cid) for cid in comps}


def d_simulate(comps, pis, fault):
    """Wartości w D-algebrze: para (układ zdatny, układ z usterką) zapisana jako 0/1/D/~D."""
    good, bad = simulate(comps, pis), simulate(comps, pis, fault)
    return {cid: D_NAMES[(good[cid], bad[cid])] for cid in comps}


def d_gate(gtype, *values):
    """Operacja D-algebry dla bramki (Tabela 2 materiałów). 'x' = dowolna z wartości 0, 1, D, ~D."""
    options = [list(D_PAIRS) if v == 'x' else [v] for v in values]
    results = set()
    for combo in itertools.product(*options):
        good = LOGIC[gtype]([D_PAIRS[v][0] for v in combo])
        bad = LOGIC[gtype]([D_PAIRS[v][1] for v in combo])
        results.add(D_NAMES[(good, bad)])
    return results.pop() if len(results) == 1 else 'x'


def primary_inputs(comps):
    return sorted((c for c in comps if comps[c]['type'] == 'IN'), key=_natural)


def primary_outputs(comps):
    used = {i for c in comps.values() for i in gate_inputs(c)}
    return sorted(c for c in comps if c not in used and comps[c]['type'] != 'IN')


def fault_cone(comps, target):
    """Linie, na które może dotrzeć błąd z linii target (łącznie z nią)."""
    cone, changed = {target}, True
    while changed:
        changed = False
        for cid, c in comps.items():
            if cid not in cone and any(i in cone for i in gate_inputs(c)):
                cone.add(cid); changed = True
    return cone


def all_vectors(comps):
    pis = primary_inputs(comps)
    return [dict(zip(pis, bits)) for bits in itertools.product([0, 1], repeat=len(pis))]


def detects(comps, pis, target, stuck):
    good, bad = simulate(comps, pis), simulate(comps, pis, (target, stuck))
    return any(good[o] != bad[o] for o in primary_outputs(comps))


def is_testable(comps, target, stuck):
    return any(detects(comps, v, target, stuck) for v in all_vectors(comps))


def _natural(name):
    digits = ''.join(ch for ch in name if ch.isdigit())
    return (name.rstrip('0123456789'), int(digits) if digits else 0)


class Oracle:
    """Wszystkie wektory wejściowe wraz z wartościami linii w D-algebrze dla jednej usterki.

    Pozwala szybko sprawdzić, czy zbiór przypisań (stan z tabeli) da się zrealizować
    jakimkolwiek wektorem wejściowym.
    """

    def __init__(self, comps, target, stuck):
        self.comps, self.target, self.stuck = comps, target, stuck
        self.outputs = primary_outputs(comps)
        self.rows = [(v, d_simulate(comps, v, (target, stuck))) for v in all_vectors(comps)]
        self._cache = {}

    def matching(self, state):
        """Wektory, przy których każda przypisana linia stanu (0/1/D/~D) ma dokładnie tę wartość."""
        fixed = tuple(sorted((k, v) for k, v in state.items() if v in D_PAIRS))
        if fixed not in self._cache:
            self._cache[fixed] = [r for r in self.rows if all(r[1][k] == v for k, v in fixed)]
        return self._cache[fixed]

    def realizable(self, state, condition=None):
        return any(condition is None or condition(d) for _, d in self.matching(state))

    def tests(self):
        return [v for v, d in self.rows if any(d[o] in ('D', '~D') for o in self.outputs)]
