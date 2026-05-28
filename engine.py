# engine.py
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

    def resolve_name(self, cid):
        c = self.components.get(cid)
        while c and c['type'] == 'NODE':
            cid = c['inputs'][0]
            c = self.components.get(cid)
        return cid

    def eval_gate(self, gtype, i1, i2):
        if gtype in ['IN', 'NODE']: return i1
        if gtype == 'NOT': return '0' if i1=='1' else ('1' if i1=='0' else 'x')
        
        if i1 == 'x' or (i2 == 'x' and gtype not in ['NOT', 'NODE']):
            if gtype == 'AND' and (i1 == '0' or i2 == '0'): return '0'
            if gtype == 'NAND' and (i1 == '0' or i2 == '0'): return '1'
            if gtype == 'OR' and (i1 == '1' or i2 == '1'): return '1'
            if gtype == 'NOR' and (i1 == '1' or i2 == '1'): return '0'
            return 'x'
            
        b1, b2 = (i1 == '1'), (i2 == '1')
        if gtype == 'AND': return '1' if (b1 and b2) else '0'
        if gtype == 'NAND': return '0' if (b1 and b2) else '1'
        if gtype == 'OR': return '1' if (b1 or b2) else '0'
        if gtype == 'NOR': return '0' if (b1 or b2) else '1'
        if gtype == 'XOR': return '1' if (b1 != b2) else '0'
        if gtype == 'XNOR': return '1' if (b1 == b2) else '0'
        return 'x'

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

    def get_justifications(self, gtype, val):
        if gtype == 'AND': return [{0:'1', 1:'1'}] if val == '1' else [{0:'0', 1:'x'}, {0:'x', 1:'0'}]
        if gtype == 'NAND': return [{0:'1', 1:'1'}] if val == '0' else [{0:'0', 1:'x'}, {0:'x', 1:'0'}]
        if gtype == 'OR': return [{0:'0', 1:'0'}] if val == '0' else [{0:'1', 1:'x'}, {0:'x', 1:'1'}]
        if gtype == 'NOR': return [{0:'0', 1:'0'}] if val == '1' else [{0:'1', 1:'x'}, {0:'x', 1:'1'}]
        if gtype == 'XOR': return [{0:'1', 1:'0'}, {0:'0', 1:'1'}] if val == '1' else [{0:'0', 1:'0'}, {0:'1', 1:'1'}]
        if gtype == 'XNOR': return [{0:'0', 1:'0'}, {0:'1', 1:'1'}] if val == '1' else [{0:'1', 1:'0'}, {0:'0', 1:'1'}]
        if gtype == 'NOT': return [{0: '0' if val=='1' else '1'}]
        if gtype == 'NODE': return [{0: val}]
        return []

    def make_decision(self, dec_id, title, options):
        if len(options) <= 1: return 0
        selected = self.user_choices.get(dec_id, 0)
        self.decision_log.append({'id': dec_id, 'title': title, 'options': options, 'selected': selected})
        return selected

    def add_step(self, msg, delta=None, full=False):
        self.steps.append({'s': self.algo_state.copy(), 'delta': delta if delta is not None else {}, 'msg': msg, 'full': full})

    def run(self):
        if self.target_node not in self.components: 
            return self._get_result()
        
        def sort_key(k):
            t = self.components[k]['type']
            cat = 0 if t == 'IN' else (2 if t == 'NODE' else 1)
            num = int(''.join(filter(str.isdigit, k)) or 0)
            return (cat, num)
            
        self.cols = sorted(self.components.keys(), key=sort_key)
        self.algo_state = {c: 'x' for c in self.cols}
        
        self.add_step("Stan początkowy układu", full=True)
        
        req_h = '1' if self.fault_type == 'sa0' else '0'
        fault_sym = 'D' if self.fault_type == 'sa0' else '~D'
        
        c = self.components[self.target_node]
        cands = self.get_justifications(c['type'], req_h)
        valid_cands = []
        for cand in cands:
            conflict = False; needed = {}
            for pin in [0, 1]:
                if pin in cand:
                    inp = c['inputs'][pin]
                    if not inp:
                        if cand[pin] != 'x': conflict = True
                    else:
                        real_inp = self.resolve_name(inp)
                        s_val = self.algo_state[real_inp]
                        if cand[pin] == 'x': 
                            if s_val == 'x': needed[real_inp] = 'x'
                        elif s_val != 'x' and s_val != cand[pin]: 
                            conflict = True
                        elif s_val == 'x': 
                            needed[real_inp] = cand[pin]
            if not conflict and needed not in valid_cands: valid_cands.append(needed)

        if not valid_cands:
            self.add_step(f"BŁĄD: Nie można wysterować {self.target_node} na {req_h}", full=False)
            return self._get_result()
            
        opts = [{'label': ", ".join(f"{self.resolve_name(k)}={v}" for k,v in cb.items() if v!='x') or "Brak wymagań", 'data': cb} for cb in valid_cands]
        idx = self.make_decision(f'excite_{self.target_node}', f"Pobudzenie {self.target_node} na {req_h}", opts)
        chosen = opts[idx]['data']
        
        delta = {}
        conflict = self.assign_state(self.target_node, fault_sym, delta)
        for k, v in chosen.items():
            delta[k] = v
            if v != 'x':
                if self.assign_state(k, v, delta): conflict = True
                
        self.add_step(f"Pobudzenie błędu na {self.target_node}. Wymagane: {opts[idx]['label']}", delta=delta, full=False)

        curr_node = self.target_node
        while not conflict:
            def get_driven_gates(src):
                res = []
                for g in self.components.values():
                    if src in g['inputs']:
                        if g['type'] == 'NODE': res.extend(get_driven_gates(g['id']))
                        elif self.algo_state[g['id']] == 'x': res.append((g, src))
                return res

            next_items = get_driven_gates(curr_node)
            if not next_items: break
            
            unique_items = []
            for item in next_items:
                if item not in unique_items: unique_items.append(item)
            
            opts = [{'label': f"Przez {g['id']} ({g['type']})", 'data': (g, d_src)} for g, d_src in unique_items]
            n_idx = self.make_decision(f'branch_{curr_node}', f"Błąd propaguje z {self.resolve_name(curr_node)}. Wybierz drogę:", opts)
            n_gate, direct_src = opts[n_idx]['data']
            
            if n_gate['type'] == 'NOT':
                new_sym = '~D' if self.algo_state[curr_node]=='D' else 'D'
                delta = {}
                if self.assign_state(n_gate['id'], new_sym, delta): conflict = True
                curr_node = n_gate['id']
                self.add_step(f"Propagacja przez {n_gate['id']} (NOT). Znak zaktualizowany.", delta=delta, full=False)
                continue
                
            port_idx = n_gate['inputs'].index(direct_src)
            other_inp = n_gate['inputs'][1 if port_idx==0 else 0]
            o_state = self.algo_state[other_inp] if other_inp else 'x'
            
            valid_sens = []
            for v in ['0', '1']:
                if o_state != 'x' and o_state != v: continue
                if not other_inp and v != 'x': continue 
                
                out0 = self.eval_gate(n_gate['type'], '0' if port_idx==0 else v, '0' if port_idx==1 else v)
                out1 = self.eval_gate(n_gate['type'], '1' if port_idx==0 else v, '1' if port_idx==1 else v)
                
                if out0 != out1 and out0 != 'x' and out1 != 'x':
                    h_in = '1' if self.algo_state[curr_node]=='D' else '0'
                    f_in = '0' if self.algo_state[curr_node]=='D' else '1'
                    h_out = self.eval_gate(n_gate['type'], h_in if port_idx==0 else v, h_in if port_idx==1 else v)
                    f_out = self.eval_gate(n_gate['type'], f_in if port_idx==0 else v, f_in if port_idx==1 else v)
                    valid_sens.append({'val': v, 'sym': 'D' if (h_out=='1' and f_out=='0') else '~D'})
                    
            if not valid_sens:
                self.add_step(f"BŁĄD: Blokada na {n_gate['id']}", full=False)
                conflict = True
                break
                
            opts = [{'label': f"{self.resolve_name(other_inp)}={vs['val']} (wypuści {vs['sym']})", 'data': vs} for vs in valid_sens]
            s_idx = self.make_decision(f'prop_{n_gate["id"]}', f"Uczulenie bramki {n_gate['id']}", opts)
            chosen = opts[s_idx]['data']
            
            delta = {}
            if other_inp and chosen['val'] != 'x':
                r_inp = self.resolve_name(other_inp)
                if self.assign_state(r_inp, chosen['val'], delta): conflict = True
            elif other_inp and chosen['val'] == 'x':
                r_inp = self.resolve_name(other_inp)
                delta[r_inp] = 'x'
                
            if self.assign_state(n_gate['id'], chosen['sym'], delta): conflict = True
            
            curr_node = n_gate['id']
            req_msg = f"{self.resolve_name(other_inp)}={chosen['val']}" if (other_inp and chosen['val']!='x') else "Brak"
            self.add_step(f"Propagacja przez {n_gate['id']}. Wymagane: {req_msg}", delta=delta, full=False)

        self.add_step("Stan po propagacji (Podsumowanie)", full=True)

        changed = True
        while changed and not conflict:
            changed = False
            for cid in reversed(self.cols):
                val = self.algo_state[cid]
                if val in ['0', '1'] and self.components[cid]['type'] not in ['IN', 'NODE']:
                    g = self.components[cid]
                    in0, in1 = g['inputs'][0], g['inputs'][1]
                    s0 = self.algo_state[in0] if in0 else 'x'
                    s1 = self.algo_state[in1] if in1 else 'x'
                    
                    if self.eval_gate(g['type'], s0, s1) == val: continue 
                        
                    cands = self.get_justifications(g['type'], val)
                    valid_cands = []
                    for cand in cands:
                        cfg_conflict = False; needed = {}
                        for pin in [0, 1]:
                            if pin in cand:
                                inp = g['inputs'][pin]
                                if not inp:
                                    if cand[pin] != 'x': cfg_conflict = True
                                else:
                                    real_inp = self.resolve_name(inp)
                                    s_val = self.algo_state[real_inp]
                                    if cand[pin] == 'x':
                                        if s_val == 'x': needed[real_inp] = 'x'
                                    elif s_val != 'x' and s_val != cand[pin]:
                                        cfg_conflict = True
                                    elif s_val == 'x':
                                        needed[real_inp] = cand[pin]
                        if not cfg_conflict and needed not in valid_cands: valid_cands.append(needed)
                    
                    if not valid_cands:
                        conflict = True
                        self.add_step(f"SPRZECZNOŚĆ przy wyliczaniu {cid}={val}", full=False)
                        break
                        
                    opts = [{'label': ", ".join(f"{self.resolve_name(k)}={v}" for k,v in cb.items() if v!='x') or "Gotowe", 'data': cb} for cb in valid_cands]
                    j_idx = self.make_decision(f'just_{cid}', f"Zgodność na {cid}={val}", opts)
                    chosen = opts[j_idx]['data']
                    
                    delta = {}
                    for k, v in chosen.items():
                        delta[k] = v
                        if v != 'x' and self.algo_state.get(k) != v:
                            if self.assign_state(k, v, delta): conflict = True
                            changed = True
                            
                    if delta:
                        self.add_step(f"Zgodność na {cid}={val}. Wymagane: {opts[j_idx]['label']}", delta=delta, full=False)

        if not conflict:
            self.add_step("TEST (Stan końcowy układu)", full=True)
            
        return self._get_result()

    def _get_result(self):
        return {
            'cols': self.cols,
            'steps': self.steps,
            'decision_log': self.decision_log
        }
