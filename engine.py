# engine.py
# D-algorytm: pobudzenie źródła błędu -> propagacja błędu -> badanie zgodności stanów.
# Po każdym przypisaniu wykonywana jest implikacja w D-algebrze (wartości wynikające z ustalonych linii).
# Wartości linii: '0', '1', 'D' (zdatny 1 / błędny 0), '~D' (zdatny 0 / błędny 1), 'x' (nieustalona).
import itertools
from functools import lru_cache

D_PAIRS = {'0': (0, 0), '1': (1, 1), 'D': (1, 0), '~D': (0, 1)}
D_NAMES = {pair: name for name, pair in D_PAIRS.items()}
D_VALUES = ('D', '~D')
LOGIC = {
    'AND': lambda b: int(all(b)), 'OR': lambda b: int(any(b)),
    'NAND': lambda b: 1 - int(all(b)), 'NOR': lambda b: 1 - int(any(b)),
    'XOR': lambda b: sum(b) % 2, 'XNOR': lambda b: 1 - sum(b) % 2,
    'NOT': lambda b: 1 - b[0], 'NODE': lambda b: b[0], 'IN': lambda b: b[0],
}
NON_CONTROLLING = {'AND': '1', 'NAND': '1', 'OR': '0', 'NOR': '0'}


@lru_cache(maxsize=None)
def d_eval(gtype, values):
    """Wartość bramki w D-algebrze; 'x' na wejściu może być dowolną z wartości 0, 1, D, ~D."""
    results = set()
    for combo in itertools.product(*[list(D_PAIRS) if v == 'x' else [v] for v in values]):
        good = LOGIC[gtype]([D_PAIRS[v][0] for v in combo])
        bad = LOGIC[gtype]([D_PAIRS[v][1] for v in combo])
        results.add(D_NAMES[(good, bad)])
        if len(results) > 1: return 'x'
    return results.pop()


class DAlgorithmEngine:
    def __init__(self, components, target_node, fault_type, user_choices):
        self.components = components
        self.target_node = target_node
        self.fault_type = fault_type
        self.user_choices = user_choices

        self.decision_log = []
        self.algo_state = {}
        self.steps = []
        self.cols = []
        self.implied = []

    def resolve_name(self, cid):
        c = self.components.get(cid)
        while c and c['type'] == 'NODE':
            cid = c['inputs'][0]
            c = self.components.get(cid)
        return cid

    def pins(self, cid):
        c = self.components[cid]
        return c['inputs'][:1] if c['type'] in ('NOT', 'NODE') else c['inputs']

    def eval_values(self, gtype, values):
        return d_eval(gtype, tuple(values))

    def eval_line(self, cid):
        return self.eval_values(self.components[cid]['type'], [self.algo_state[i] if i else 'x' for i in self.pins(cid)])

    def assign_state(self, k, v, delta):
        if self.algo_state.get(k) == v: return False
        if self.algo_state.get(k) not in ['x', None] and v not in ['x', None]: return True
        self.algo_state[k] = v
        if delta is not None: delta[k] = v
        conflict = False
        c = self.components.get(k)
        if c and c['type'] == 'NODE':
            in0 = c['inputs'][0]
            if in0:
                if self.assign_state(in0, v, delta): conflict = True
        for cid, comp in self.components.items():
            if comp['type'] == 'NODE' and comp['inputs'][0] == k:
                if self.assign_state(cid, v, delta): conflict = True
        return conflict

    def requirement_options(self, cid, val):
        """Minimalne przypisania nieustalonych wejść bramki cid, przy których daje ona val.

        Dla linii 0/1 to pierwotne sześciany z materiałów (Tabela 5); linia, do której może dotrzeć błąd,
        może dodatkowo przyjąć D lub ~D (np. XOR(D, ~D) = 1). Wymaganie na węźle dotyczy jego źródła,
        a dwa wejścia z tej samej linii dostają tę samą wartość.
        """
        lines = [self.resolve_name(p) if p else None for p in self.pins(cid)]
        free = sorted({l for l in lines if l and self.algo_state[l] == 'x'}, key=self.cols.index)
        found = []
        for combo in itertools.product(*[['x', '0', '1'] + (list(D_VALUES) if l in self.cone else []) for l in free]):
            chosen = dict(zip(free, combo))
            values = [chosen.get(l, self.algo_state[l]) if l else 'x' for l in lines]
            if self.eval_values(self.components[cid]['type'], values) == val:
                found.append({l: v for l, v in chosen.items() if v != 'x'})
        minimal = [f for f in found if not any(o != f and o.items() <= f.items() for o in found)]
        return sorted(minimal, key=lambda f: (sum(v in D_VALUES for v in f.values()), len(f), [self.cols.index(l) for l in f]))

    def imply(self, delta):
        """Implikacja w przód. Zwraca opis sprzeczności albo None; nowe wartości dopisuje do self.implied."""
        changed = True
        while changed:
            changed = False
            for cid in self.gates:
                val = self.eval_line(cid)
                if val == 'x': continue
                if cid == self.target_node:
                    if val != self.good_target:
                        return f"SPRZECZNOŚĆ na {cid}! Wejścia bramki dają {val}, a pobudzenie błędu wymaga {self.good_target}."
                    continue
                cur = self.algo_state[cid]
                if cur == val: continue
                if cur != 'x' or self.assign_state(cid, val, delta):
                    return f"SPRZECZNOŚĆ na {cid}! Wymagane {cid}={cur}, a z wartości wejść wynika {cid}={val}."
                self.implied.append(cid)
                changed = True
        return None

    def make_decision(self, dec_id, title, options):
        if len(options) <= 1: return 0
        selected = self.user_choices.get(dec_id, 0)
        if not 0 <= selected < len(options): selected = 0
        self.decision_log.append({'id': dec_id, 'title': title, 'options': options, 'selected': selected})
        return selected

    def add_step(self, msg, delta=None, full=False):
        if self.implied and not full:
            msg += " Implikacja: " + ", ".join(f"{g}={self.algo_state[g]}" for g in self.implied) + "."
        self.implied = []
        self.steps.append({'s': self.algo_state.copy(), 'delta': delta if delta is not None else {}, 'msg': msg, 'full': full})

    def conflict_step(self, msg, line, delta=None):
        self.add_step(msg, delta={**(delta or {}), line: 'ERR'})

    def requirements_label(self, needed, empty):
        return ", ".join(f"{k}={v}" for k, v in needed.items()) or empty

    def apply(self, needed, delta):
        """Przypisuje wymagane wartości i wykonuje implikację. Zwraca opis sprzeczności albo None."""
        for k, v in needed.items():
            if self.assign_state(k, v, delta):
                return f"SPRZECZNOŚĆ na {k}! Linia ma już inną wartość niż wymagane {k}={v}."
        return self.imply(delta)

    def sort_key(self, k):
        t = self.components[k]['type']
        cat = 0 if t == 'IN' else (2 if t == 'NODE' else 1)
        num = int(''.join(filter(str.isdigit, k)) or 0)
        return (cat, num)

    def prepare(self):
        """Stan początkowy: kolumny tabeli, kolejność topologiczna bramek, wyjścia i zasięg błędu."""
        self.cols = sorted(self.components.keys(), key=self.sort_key)
        self.algo_state = {c: 'x' for c in self.cols}
        self.gates, seen = [], set()

        def visit(c):
            if c in seen: return
            seen.add(c)
            for i in self.components[c]['inputs']:
                if i in self.components: visit(i)
            if self.components[c]['type'] not in ('IN', 'NODE'): self.gates.append(c)
        for c in self.cols: visit(c)
        used = {i for c in self.components for i in self.pins(c) if i}
        self.outputs = [c for c in self.cols if c not in used and self.components[c]['type'] != 'IN']
        self.cone, changed = {self.target_node}, True
        while changed:
            new = {c for c in self.components if c not in self.cone and any(i in self.cone for i in self.pins(c) if i)}
            self.cone |= new
            changed = bool(new)
        self.good_target = '1' if self.fault_type == 'sa0' else '0'

    def run(self):
        if self.target_node not in self.components:
            return self._get_result()
        self.prepare()
        self.add_step("Stan początkowy układu", full=True)

        # 1. Pobudzenie źródła błędu
        fault_sym = 'D' if self.fault_type == 'sa0' else '~D'
        cubes = self.requirement_options(self.target_node, self.good_target)
        if not cubes:
            self.add_step(f"BŁĄD: Nie można wysterować {self.target_node} na {self.good_target}", full=False)
            return self._get_result()
        opts = [{'label': self.requirements_label(cb, "Brak wymagań"), 'data': cb} for cb in cubes]
        idx = self.make_decision(f'excite_{self.target_node}', f"Pobudzenie błędu: {self.target_node} na {self.good_target}", opts)
        delta = {}
        self.assign_state(self.target_node, fault_sym, delta)
        conflict = self.apply(opts[idx]['data'], delta)
        if conflict:
            self.conflict_step(conflict, self.target_node, delta)
            return self._get_result()
        self.add_step(f"Pobudzenie błędu: {self.target_node}. Wymagane: {opts[idx]['label']}", delta=delta)

        # 2. Propagacja błędu z D-granicy (bramek z błędem na wejściu i nieustalonym wyjściem)
        while not any(self.algo_state[o] in D_VALUES for o in self.outputs):
            frontier = [g for g in self.gates if g != self.target_node and self.algo_state[g] == 'x'
                        and any(i and self.algo_state[i] in D_VALUES for i in self.pins(g))]
            if not frontier:
                self.conflict_step("SPRZECZNOŚĆ: błąd nie może dotrzeć do wyjścia – pusta D-granica "
                                   "(żadna bramka nie ma błędu na wejściu i nieustalonego wyjścia).", self.target_node)
                return self._get_result()
            # Kilka ścieżek naraz uzyskuje się, wybierając kolejno kolejne bramki z D-granicy.
            frontier.sort(key=self.sort_key)
            opts = [{'label': f"Przez {g} ({self.components[g]['type']})", 'data': g} for g in frontier]
            p_idx = self.make_decision(f"branch_{'_'.join(frontier)}", "Propagacja błędu. Wybierz drogę:", opts)
            g = opts[p_idx]['data']
            gtype, delta, needed = self.components[g]['type'], {}, {}
            if None in self.pins(g):
                self.conflict_step(f"SPRZECZNOŚĆ (Blokada propagacji) na {g}! Wejście bramki nie jest podłączone.", g)
                return self._get_result()
            for inp in self.pins(g):
                s = self.algo_state[inp]
                if s in D_VALUES: continue
                if gtype in NON_CONTROLLING:
                    if s not in ('x', NON_CONTROLLING[gtype]):
                        self.conflict_step(f"SPRZECZNOŚĆ (Blokada propagacji) na {g}! Wejście {self.resolve_name(inp)} ma stan '{s}', "
                                           f"który blokuje przepuszczenie błędu.", g)
                        return self._get_result()
                    if s == 'x': needed[self.resolve_name(inp)] = NON_CONTROLLING[gtype]
                elif gtype in ('XOR', 'XNOR') and s == 'x':
                    values = [self.algo_state[i] for i in self.pins(g)]
                    side = []
                    for v in ('0', '1'):
                        out = self.eval_values(gtype, [v if i == inp else values[n] for n, i in enumerate(self.pins(g))])
                        side.append({'label': f"{self.resolve_name(inp)}={v} (wypuści {out})", 'data': v})
                    s_idx = self.make_decision(f'prop_{g}', f"Propagacja błędu przez {g}", side)
                    needed[self.resolve_name(inp)] = side[s_idx]['data']
            conflict = self.apply(needed, delta)
            if conflict:
                self.conflict_step(conflict, g, delta)
                return self._get_result()
            if self.algo_state[g] not in D_VALUES:
                self.conflict_step(f"SPRZECZNOŚĆ (Blokada propagacji) na {g}! Przy tych wartościach wejść błąd nie przechodzi "
                                   f"({g}={self.algo_state[g]}).", g, delta)
                return self._get_result()
            delta.setdefault(g, self.algo_state[g])
            if g in self.implied: self.implied.remove(g)
            self.add_step(f"Propagacja błędu przez {g} ({gtype}). Wymagane: {self.requirements_label(needed, 'Brak')}", delta=delta)

        self.add_step("Stan po propagacji (Podsumowanie)", full=True)

        # 3. Badanie zgodności: każda ustalona wartość musi wynikać z wejść bramki
        while True:
            cid = next((c for c in reversed(self.cols) if c in self.gates and c != self.target_node
                        and self.algo_state[c] != 'x' and self.eval_line(c) == 'x'), None)
            if cid is None: break
            val, g = self.algo_state[cid], self.components[cid]
            cubes = self.requirement_options(cid, val)
            if not cubes:
                inputs = ", ".join(f"{self.resolve_name(i) if i else 'Brak'}={self.algo_state.get(self.resolve_name(i), 'x') if i else 'x'}"
                                   for i in self.pins(cid))
                self.conflict_step(f"SPRZECZNOŚĆ na {cid}={val}! Bramka {g['type']} ma na wejściach: {inputs}. "
                                   f"Funkcja logiczna bramki wyklucza taki wynik.", cid)
                return self._get_result()
            opts = [{'label': self.requirements_label(cb, "Gotowe"), 'data': cb} for cb in cubes]
            j_idx = self.make_decision(f'just_{cid}', f"Badanie zgodności stanu na {cid}={val}", opts)
            delta = {}
            conflict = self.apply(opts[j_idx]['data'], delta)
            if conflict:
                self.conflict_step(conflict, cid, delta)
                return self._get_result()
            self.add_step(f"Badanie zgodności stanu na {cid}={val}. Wymagane: {opts[j_idx]['label']}", delta=delta)

        self.add_step("TEST (Stan końcowy układu)", full=True)
        return self._get_result()

    def _get_result(self):
        return {
            'cols': self.cols,
            'steps': self.steps,
            'decision_log': self.decision_log
        }
