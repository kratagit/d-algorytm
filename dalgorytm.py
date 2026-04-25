import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import json

class DAlgorithmApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Inteligentny Symulator D-Algorytmu PRO (Czysta Tabela + Don't Care)")
        self.root.geometry("1200x800")
        
        # Stan aplikacji
        self.components = {}
        self.counter = 0
        self.active_out = None
        self.dragging = None
        self.offset_x = 0
        self.offset_y = 0
        self.selected_comp = None
        
        # Stan algorytmu
        self.user_choices = {}
        self.decision_log = []
        self.algo_state = {}
        self.steps = []
        self.cols =[]

        self.setup_ui()
        self.load_user_example()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        self.paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        self.left_frame = ttk.Frame(self.paned)
        self.paned.add(self.left_frame, weight=3)
        
        self.right_frame = ttk.Frame(self.paned)
        self.paned.add(self.right_frame, weight=2)
        
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Edytuj (Zmień nazwę)", command=self.cmd_edit_comp)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Usuń element", command=self.cmd_delete_comp)
        
        self.setup_toolbar_and_canvas()
        self.setup_results_panel()

    def setup_toolbar_and_canvas(self):
        toolbar = ttk.Frame(self.left_frame, width=150)
        toolbar.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        
        btn_style = {'width': 16, 'padding': 4}
        
        ttk.Label(toolbar, text="DODAJ ELEMENT", font=("Arial", 9, "bold"), foreground="#2c3e50").pack(pady=(5,2))
        ttk.Button(toolbar, text="+ Wejście (IN)", command=lambda: self.add_comp('IN'), **btn_style).pack(pady=1)
        ttk.Button(toolbar, text="+ Węzeł", command=lambda: self.add_comp('NODE'), **btn_style).pack(pady=1)
        
        for g in['AND', 'OR', 'NAND', 'NOR', 'XOR', 'XNOR', 'NOT']:
            ttk.Button(toolbar, text=f"Bramka {g}", command=lambda t=g: self.add_comp(t), **btn_style).pack(pady=1)
            
        ttk.Separator(toolbar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        ttk.Label(toolbar, text="PLIKI", font=("Arial", 9, "bold"), foreground="#2c3e50").pack(pady=(0,2))
        ttk.Button(toolbar, text="Zapisz układ", command=self.save_workspace, **btn_style).pack(pady=1)
        ttk.Button(toolbar, text="Wczytaj układ", command=self.load_workspace, **btn_style).pack(pady=1)
        
        ttk.Separator(toolbar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        
        ttk.Label(toolbar, text="ZARZĄDZANIE", font=("Arial", 9, "bold"), foreground="#2c3e50").pack(pady=(0,2))
        ttk.Button(toolbar, text="Zbuduj Przykład", command=self.load_user_example, **btn_style).pack(pady=1)
        ttk.Button(toolbar, text="Wyczyść planszę", command=self.clear_workspace, **btn_style).pack(pady=1)
        
        info = "ŁĄCZENIE:\n1. Kliknij czerwone\n2. Kliknij niebieskie\n(Ponowne klik. usuwa)\n\nZARZĄDZANIE:\nPrawy klik na bramkę"
        ttk.Label(toolbar, text=info, foreground="gray", font=("Arial", 8)).pack(side=tk.BOTTOM, pady=10)

        self.canvas = tk.Canvas(self.left_frame, bg="#e8eaed", cursor="crosshair")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)

    def setup_results_panel(self):
        top_frame = ttk.Frame(self.right_frame)
        top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(top_frame, text="Cel:").pack(side=tk.LEFT)
        self.target_var = tk.StringVar()
        self.target_cb = ttk.Combobox(top_frame, textvariable=self.target_var, width=6, state="readonly")
        self.target_cb.pack(side=tk.LEFT, padx=3)
        
        self.fault_type_var = tk.StringVar(value="sa1")
        fault_cb = ttk.Combobox(top_frame, textvariable=self.fault_type_var, values=["sa0", "sa1"], width=4, state="readonly")
        fault_cb.pack(side=tk.LEFT, padx=3)
        
        ttk.Button(top_frame, text="Oblicz", command=lambda: self.run_algorithm(True)).pack(side=tk.RIGHT)
        
        self.show_nodes_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top_frame, text="Pokaż węzły", variable=self.show_nodes_var, command=self.update_ui).pack(side=tk.RIGHT, padx=10)

        self.tree_frame = ttk.Frame(self.right_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        self.tree = ttk.Treeview(self.tree_frame, show="headings")
        vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(column=0, row=0, sticky='nsew')
        vsb.grid(column=1, row=0, sticky='ns')
        hsb.grid(column=0, row=1, sticky='ew')
        self.tree_frame.grid_columnconfigure(0, weight=1)
        self.tree_frame.grid_rowconfigure(0, weight=1)

        self.decisions_frame = ttk.LabelFrame(self.right_frame, text="💡 Alternatywne Ścieżki / Wybory")
        self.decisions_frame.pack(fill=tk.X, padx=10, pady=10)
        self.decisions_inner = ttk.Frame(self.decisions_frame)
        self.decisions_inner.pack(fill=tk.BOTH, padx=5, pady=5)

    # --- ZAPIS I ODCZYT PLIKÓW ---
    
    def save_workspace(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")], title="Zapisz układ")
        if not file_path: return
        data = {'components': self.components, 'counter': self.counter, 'target': self.target_var.get(), 'fault_type': self.fault_type_var.get()}
        try:
            with open(file_path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
            messagebox.showinfo("Sukces", "Pomyślnie zapisano układ!")
        except Exception as e: messagebox.showerror("Błąd zapisu", f"Nie udało się zapisać pliku:\n{e}")

    def load_workspace(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")], title="Wczytaj układ")
        if not file_path: return
        try:
            with open(file_path, 'r', encoding='utf-8') as f: data = json.load(f)
            self.clear_workspace()
            self.components = data.get('components', {})
            self.counter = data.get('counter', 0)
            self.update_target_cb()
            self.target_var.set(data.get('target', ''))
            self.fault_type_var.set(data.get('fault_type', 'sa1'))
            self.redraw()
        except Exception as e: messagebox.showerror("Błąd", f"Nie udało się wczytać pliku:\n{e}")

    # --- ZARZĄDZANIE KOMPONENTAMI ---

    def add_comp(self, ctype, x=100, y=100, cid=None):
        self.counter += 1
        if not cid:
            prefix = 'X' if ctype == 'IN' else ('W' if ctype == 'NODE' else 'G')
            cid = f"{prefix}{self.counter}"
            
        self.components[cid] = {'id': cid, 'type': ctype, 'x': x, 'y': y, 'inputs':[None, None]}
        self.update_target_cb()
        self.redraw()

    def update_target_cb(self):
        targets = [c for c in self.components if self.components[c]['type'] not in ['IN']]
        self.target_cb['values'] = targets
        if targets and not self.target_var.get(): self.target_cb.current(0)

    def clear_workspace(self):
        self.components.clear()
        self.counter = 0
        self.active_out = None
        self.user_choices.clear()
        self.update_target_cb()
        self.target_var.set('')
        self.clear_results()
        self.redraw()

    def clear_results(self):
        self.tree.delete(*self.tree.get_children())
        for widget in self.decisions_inner.winfo_children(): widget.destroy()

    def load_user_example(self):
        self.clear_workspace()
        self.counter = 7
        
        comps =[
            ('IN', 50, 50, 'X8'), ('IN', 160, 100, 'X9'), ('IN', 280, 150, 'X10'), ('IN', 420, 200, 'X11'),
            ('IN', 50, 350, 'X12'), ('IN', 180, 400, 'X13'), ('IN', 320, 400, 'X14'),
            ('NOT', 120, 50, 'G0'), ('AND', 240, 75, 'G1'), ('NAND', 360, 100, 'G2'), ('OR', 500, 125, 'G3'),
            ('NOR', 150, 330, 'G4'), ('XOR', 300, 350, 'G5'), ('XNOR', 460, 350, 'G6')
        ]
        for c in comps: self.add_comp(c[0], c[1], c[2], c[3])
            
        c = self.components
        c['G0']['inputs'][0] = 'X8'; c['G1']['inputs'][0] = 'G0'; c['G1']['inputs'][1] = 'X9'
        c['G2']['inputs'][0] = 'G1'; c['G2']['inputs'][1] = 'X10'; c['G3']['inputs'][0] = 'G2'; c['G3']['inputs'][1] = 'X11'
        c['G4']['inputs'][0] = 'G3'; c['G4']['inputs'][1] = 'X12'; c['G5']['inputs'][0] = 'G4'; c['G5']['inputs'][1] = 'X13'
        c['G6']['inputs'][0] = 'G5'; c['G6']['inputs'][1] = 'X14'
        
        self.target_var.set('G3')
        self.redraw()

    # --- MENU KONTEKSTOWE ---

    def on_canvas_right_click(self, event):
        hb = self.get_hitbox(event.x, event.y)
        if hb and hb['type'] == 'comp':
            self.selected_comp = hb['id']
            self.context_menu.post(event.x_root, event.y_root)

    def cmd_edit_comp(self):
        if not self.selected_comp or self.selected_comp not in self.components: return
        old_id = self.selected_comp
        new_id = simpledialog.askstring("Edytuj", f"Nowa nazwa dla {old_id}:", parent=self.root)
        
        if new_id and new_id != old_id:
            new_id = "".join(c for c in new_id if c.isalnum() or c == '_').upper()
            if not new_id: return
            if new_id in self.components: return messagebox.showerror("Błąd", "Ta nazwa jest już zajęta!")
                
            self.components[new_id] = self.components.pop(old_id)
            self.components[new_id]['id'] = new_id
            
            for c in self.components.values():
                for i in range(len(c['inputs'])):
                    if c['inputs'][i] == old_id: c['inputs'][i] = new_id
                        
            if self.target_var.get() == old_id: self.target_var.set(new_id)
            if self.active_out == old_id: self.active_out = new_id
            
            self.update_target_cb()
            self.clear_results()
            self.redraw()

    def cmd_delete_comp(self):
        if not self.selected_comp or self.selected_comp not in self.components: return
        cid = self.selected_comp
        
        del self.components[cid]
        for c in self.components.values():
            for i in range(len(c['inputs'])):
                if c['inputs'][i] == cid: c['inputs'][i] = None
                    
        if self.active_out == cid: self.active_out = None
        if self.target_var.get() == cid: self.target_var.set('')
        
        self.update_target_cb()
        self.clear_results()
        self.redraw()

    # --- RYSOWANIE IKON BRAMEK LOGICZNYCH ---

    def redraw(self):
        self.canvas.delete("all")
        self.draw_wires()
        self.draw_components()

    def draw_components(self):
        self.hitboxes =[]
        for cid, c in self.components.items():
            x, y = c['x'], c['y']
            w, h = 60, 40
            color = "#3498db" if self.dragging == cid else "#2c3e50"
            
            self.canvas.create_rectangle(x, y-15, x+w, y+h, fill="", outline="")
            self.hitboxes.append({'type': 'comp', 'id': cid, 'x': x, 'y': y-15, 'w': w, 'h': h+15})
            
            if c['type'] == 'NODE':
                self.canvas.create_oval(x, y, x+12, y+12, fill="#2c3e50")
                self.canvas.create_text(x+6, y-10, text=cid, font=("Arial", 8, "bold"), fill="#2c3e50")
                
                ix, iy = x - 4, y + 2
                self.canvas.create_oval(ix, iy, ix+8, iy+8, fill="#3498db", outline="white")
                self.hitboxes.append({'type': 'port_in', 'id': cid, 'idx': 0, 'x': ix, 'y': iy, 'w': 8, 'h': 8})
                
                ox, oy = x + 8, y + 2
                pc = "#f1c40f" if self.active_out == cid else "#e74c3c"
                self.canvas.create_oval(ox, oy, ox+8, oy+8, fill=pc, outline="white")
                self.hitboxes.append({'type': 'port_out', 'id': cid, 'x': ox, 'y': oy, 'w': 8, 'h': 8})
                continue
                
            if c['type'] == 'IN':
                self.canvas.create_oval(x, y, x+w, y+h, fill="#e0f7fa", outline="#0097e6", width=2)
                self.canvas.create_text(x+w/2, y+20, text=cid, font=("Arial", 10, "bold"), fill="#0097e6")
                
                ox, oy = x + w - 4, y + 16
                pc = "#f1c40f" if self.active_out == cid else "#e74c3c"
                self.canvas.create_oval(ox, oy, ox+8, oy+8, fill=pc, outline="white")
                self.hitboxes.append({'type': 'port_out', 'id': cid, 'x': ox, 'y': oy, 'w': 8, 'h': 8})
                continue
                
            sx, sy = x + 10, y
            gtype = c['type']
            
            self.canvas.create_text(x+w/2, y-8, text=cid, font=("Arial", 10, "bold"), fill="#2c3e50")
            
            if gtype == 'NOT':
                self.canvas.create_line(x, sy+20, sx, sy+20, fill=color, width=2)
            else:
                self.canvas.create_line(x, sy+10, sx+8, sy+10, fill=color, width=2)
                self.canvas.create_line(x, sy+30, sx+8, sy+30, fill=color, width=2)
                
            out_start = sx + 40
            if gtype in['NAND', 'NOR', 'XNOR']: out_start = sx + 48
            elif gtype == 'NOT': out_start = sx + 38
            self.canvas.create_line(out_start, sy+20, x+60, sy+20, fill=color, width=2)
            
            if gtype in ['AND', 'NAND']:
                self.canvas.create_rectangle(sx, sy, sx+20, sy+40, fill="white", outline="")
                self.canvas.create_arc(sx, sy, sx+40, sy+40, start=-90, extent=180, fill="white", outline="")
                self.canvas.create_line(sx, sy, sx+20, sy, fill=color, width=2)
                self.canvas.create_line(sx, sy+40, sx+20, sy+40, fill=color, width=2)
                self.canvas.create_line(sx, sy, sx, sy+40, fill=color, width=2)
                self.canvas.create_arc(sx, sy, sx+40, sy+40, start=-90, extent=180, style=tk.ARC, outline=color, width=2)
                
            elif gtype in['OR', 'NOR', 'XOR', 'XNOR']:
                pts =[sx, sy, sx, sy, sx+20, sy, sx+40, sy+20, sx+40, sy+20, sx+20, sy+40, sx, sy+40, sx, sy+40, sx+10, sy+20, sx+10, sy+20]
                self.canvas.create_polygon(pts, smooth=True, fill="white", outline=color, width=2)
                if gtype in ['XOR', 'XNOR']:
                    xpts =[sx-6, sy, sx-6, sy, sx+4, sy+20, sx+4, sy+20, sx-6, sy+40, sx-6, sy+40]
                    self.canvas.create_line(xpts, smooth=True, fill=color, width=2)
            
            elif gtype == 'NOT':
                self.canvas.create_polygon(sx, sy+5, sx+30, sy+20, sx, sy+35, fill="white", outline=color, width=2)
                
            if gtype in['NAND', 'NOR', 'XNOR']:
                self.canvas.create_oval(sx+40, sy+16, sx+48, sy+24, fill="white", outline=color, width=2)
            elif gtype == 'NOT':
                self.canvas.create_oval(sx+30, sy+16, sx+38, sy+24, fill="white", outline=color, width=2)
                
            ox, oy = x + w - 4, y + 16
            pc = "#f1c40f" if self.active_out == cid else "#e74c3c"
            self.canvas.create_oval(ox, oy, ox+8, oy+8, fill=pc, outline="white")
            self.hitboxes.append({'type': 'port_out', 'id': cid, 'x': ox, 'y': oy, 'w': 8, 'h': 8})
            
            ix = x - 4
            if gtype == 'NOT':
                iy = y + 16
                self.canvas.create_oval(ix, iy, ix+8, iy+8, fill="#3498db", outline="white")
                self.hitboxes.append({'type': 'port_in', 'id': cid, 'idx': 0, 'x': ix, 'y': iy, 'w': 8, 'h': 8})
            else:
                iy1, iy2 = y + 6, y + 26
                self.canvas.create_oval(ix, iy1, ix+8, iy1+8, fill="#3498db", outline="white")
                self.canvas.create_oval(ix, iy2, ix+8, iy2+8, fill="#3498db", outline="white")
                self.hitboxes.append({'type': 'port_in', 'id': cid, 'idx': 0, 'x': ix, 'y': iy1, 'w': 8, 'h': 8})
                self.hitboxes.append({'type': 'port_in', 'id': cid, 'idx': 1, 'x': ix, 'y': iy2, 'w': 8, 'h': 8})

    def draw_wires(self):
        for cid, c in self.components.items():
            for idx, src_id in enumerate(c['inputs']):
                if src_id and src_id in self.components:
                    self.draw_bezier(src_id, cid, idx)

    def draw_bezier(self, src_id, dst_id, idx):
        src = self.components[src_id]
        dst = self.components[dst_id]
        
        x1 = src['x'] + (12 if src['type'] == 'NODE' else 60)
        y1 = src['y'] + (6 if src['type'] == 'NODE' else 20)
        
        x2 = dst['x']
        if dst['type'] == 'NODE': y2 = dst['y'] + 6
        elif dst['type'] == 'NOT': y2 = dst['y'] + 20
        else: y2 = dst['y'] + (10 if idx == 0 else 30)
        
        self.canvas.create_line(x1, y1, x1+40, y1, x2-40, y2, x2, y2, smooth=True, fill="#34495e", width=2)

    # --- OBSŁUGA ZDARZEŃ MYSZY ---

    def get_hitbox(self, x, y):
        for hb in reversed(self.hitboxes):
            if hb['x'] <= x <= hb['x']+hb['w'] and hb['y'] <= y <= hb['y']+hb['h']:
                return hb
        return None

    def on_canvas_click(self, event):
        hb = self.get_hitbox(event.x, event.y)
        
        if not hb:
            self.active_out = None
            self.redraw()
            return
            
        if hb['type'] == 'port_out':
            if self.active_out == hb['id']: self.active_out = None
            else: self.active_out = hb['id']
            self.redraw()
            
        elif hb['type'] == 'port_in':
            cid, idx = hb['id'], hb['idx']
            if self.active_out:
                if self.components[cid]['inputs'][idx] == self.active_out:
                    self.components[cid]['inputs'][idx] = None
                else:
                    self.components[cid]['inputs'][idx] = self.active_out
                self.active_out = None
                self.redraw()
                self.clear_results()
                
        elif hb['type'] == 'comp':
            self.dragging = hb['id']
            self.offset_x = event.x - self.components[hb['id']]['x']
            self.offset_y = event.y - self.components[hb['id']]['y']

    def on_canvas_drag(self, event):
        if self.dragging:
            self.components[self.dragging]['x'] = event.x - self.offset_x
            self.components[self.dragging]['y'] = event.y - self.offset_y
            self.redraw()

    def on_canvas_release(self, event):
        self.dragging = None


    # --- LOGIKA INTELIGENTNEGO D-ALGORYTMU (Z 'x' I CZYSTĄ TABELĄ) ---

    def eval_gate(self, gtype, i1, i2):
        if gtype == 'IN' or gtype == 'NODE': return i1
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

    def get_justifications(self, gtype, val):
        """Zwraca kombinacje dla 'x' (Don't care)"""
        if gtype == 'AND': return[{0:'1', 1:'1'}] if val == '1' else[{0:'0', 1:'x'}, {0:'x', 1:'0'}]
        if gtype == 'NAND': return[{0:'1', 1:'1'}] if val == '0' else[{0:'0', 1:'x'}, {0:'x', 1:'0'}]
        if gtype == 'OR': return[{0:'0', 1:'0'}] if val == '0' else[{0:'1', 1:'x'}, {0:'x', 1:'1'}]
        if gtype == 'NOR': return[{0:'0', 1:'0'}] if val == '1' else[{0:'1', 1:'x'}, {0:'x', 1:'1'}]
        if gtype == 'XOR': return[{0:'1', 1:'0'}, {0:'0', 1:'1'}] if val == '1' else[{0:'0', 1:'0'}, {0:'1', 1:'1'}]
        if gtype == 'XNOR': return[{0:'0', 1:'0'}, {0:'1', 1:'1'}] if val == '1' else[{0:'1', 1:'0'}, {0:'0', 1:'1'}]
        if gtype == 'NOT': return[{0: '0' if val=='1' else '1'}]
        if gtype == 'NODE': return [{0: val}]
        return []

    def find_valid_justifications(self, g, val):
        in0 = g['inputs'][0] if len(g['inputs']) > 0 else None
        in1 = g['inputs'][1] if len(g['inputs']) > 1 else None
        
        s0 = self.algo_state[in0] if in0 else 'x'
        s1 = self.algo_state[in1] if in1 else 'x'
        
        cands = self.get_justifications(g['type'], val)
        valid =[]
        for cand in cands:
            conflict = False
            needed = {}
            
            if 0 in cand:
                if not in0: 
                    if cand[0] != 'x': conflict = True
                else:
                    if cand[0] == 'x':
                        if s0 == 'x': needed[in0] = 'x'
                    else:
                        if s0 != 'x' and s0 != cand[0]: conflict = True
                        elif s0 == 'x': needed[in0] = cand[0]
                        
            if 1 in cand:
                if not in1:
                    if cand[1] != 'x': conflict = True
                else:
                    if cand[1] == 'x':
                        if s1 == 'x': needed[in1] = 'x'
                    else:
                        if s1 != 'x' and s1 != cand[1]: conflict = True
                        elif s1 == 'x': needed[in1] = cand[1]
                        
            if not conflict and needed not in valid:
                valid.append(needed)
        return valid

    def make_decision(self, dec_id, title, options):
        if len(options) <= 1: return 0
        selected = self.user_choices.get(dec_id, 0)
        self.decision_log.append({'id': dec_id, 'title': title, 'options': options, 'selected': selected})
        return selected

    def add_step(self, msg, delta=None, full=False):
        self.steps.append({
            's': self.algo_state.copy(),
            'delta': delta if delta is not None else {},
            'msg': msg,
            'full': full
        })

    def run_algorithm(self, is_fresh_run=False):
        if is_fresh_run: self.user_choices.clear()
        self.decision_log.clear()
        self.steps.clear()
        
        f_node = self.target_var.get()
        f_type = self.fault_type_var.get()
        if f_node not in self.components: return
        
        def sort_key(k):
            t = self.components[k]['type']
            cat = 0 if t == 'IN' else (2 if t == 'NODE' else 1)
            num = int(''.join(filter(str.isdigit, k)) or 0)
            return (cat, num)
            
        self.cols = sorted(self.components.keys(), key=sort_key)
        self.algo_state = {c: 'x' for c in self.cols}
        
        self.add_step("Stan początkowy układu", full=True)
        
        # 1. Pobudzenie
        req_h = '1' if f_type == 'sa0' else '0'
        fault_sym = 'D' if f_type == 'sa0' else '~D'
        
        valid_cands = self.find_valid_justifications(self.components[f_node], req_h)

        if not valid_cands:
            self.add_step(f"BŁĄD: Nie można wysterować {f_node} na {req_h}", full=False)
            self.update_ui()
            return
            
        opts =[{'label': ", ".join(f"{k}={v}" for k,v in cb.items()) or "Brak wymagań", 'data': cb} for cb in valid_cands]
        idx = self.make_decision(f'excite_{f_node}', f"Pobudzenie {f_node} na {req_h}", opts)
        chosen = opts[idx]['data']
        
        delta = chosen.copy()
        delta[f_node] = fault_sym
        
        for k, v in chosen.items(): 
            if v != 'x': self.algo_state[k] = v
        self.algo_state[f_node] = fault_sym
        
        self.add_step(f"Pobudzenie błędu {f_node}. Wymagane: {opts[idx]['label']}", delta=delta, full=False)

        # 2. Propagacja
        curr_node = f_node
        while True:
            next_gates =[g for g in self.components.values() if curr_node in g['inputs'] and self.algo_state[g['id']] == 'x']
            if not next_gates: break
            
            opts =[{'label': f"Przez {g['id']}", 'data': g} for g in next_gates]
            n_idx = self.make_decision(f'branch_{curr_node}', f"Rozgałęzienie z {curr_node}. Wybierz drogę:", opts)
            n_gate = opts[n_idx]['data']
            
            if n_gate['type'] in['NOT', 'NODE']:
                new_sym = ('~D' if self.algo_state[curr_node]=='D' else 'D') if n_gate['type']=='NOT' else self.algo_state[curr_node]
                self.algo_state[n_gate['id']] = new_sym
                curr_node = n_gate['id']
                self.add_step(f"Propagacja przez {n_gate['id']}. Znak zaktualizowany.", delta={n_gate['id']: new_sym}, full=False)
                continue
                
            port_idx = n_gate['inputs'].index(curr_node)
            other_inp = n_gate['inputs'][1 if port_idx==0 else 0]
            o_state = self.algo_state[other_inp] if other_inp else 'x'
            
            valid_sens =[]
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
                break
                
            opts =[{'label': f"{other_inp}={vs['val']} (wypuści {vs['sym']})", 'data': vs} for vs in valid_sens]
            s_idx = self.make_decision(f'prop_{n_gate["id"]}', f"Uczulenie {n_gate['id']}", opts)
            chosen = opts[s_idx]['data']
            
            delta = {n_gate['id']: chosen['sym']}
            if other_inp and chosen['val'] != 'x' and self.algo_state[other_inp] == 'x':
                self.algo_state[other_inp] = chosen['val']
                delta[other_inp] = chosen['val']
                
            self.algo_state[n_gate['id']] = chosen['sym']
            curr_node = n_gate['id']
            req_msg = f"{other_inp}={chosen['val']}" if (other_inp and chosen['val']!='x') else "Brak"
            self.add_step(f"Propagacja przez {n_gate['id']}. Wymagane: {req_msg}", delta=delta, full=False)

        self.add_step("Stan po propagacji (Podsumowanie)", full=True)

        # 3. Zgodność
        changed = True
        conflict = False
        while changed and not conflict:
            changed = False
            for cid in reversed(self.cols):
                val = self.algo_state[cid]
                if val in ['0', '1'] and self.components[cid]['type'] != 'IN':
                    g = self.components[cid]
                    in0, in1 = g['inputs'][0], g['inputs'][1]
                    s0 = self.algo_state[in0] if in0 else 'x'
                    s1 = self.algo_state[in1] if in1 else 'x'
                    
                    if self.eval_gate(g['type'], s0, s1) == val:
                        continue 
                        
                    valid_cands = self.find_valid_justifications(g, val)
                    
                    if not valid_cands:
                        conflict = True
                        self.add_step(f"SPRZECZNOŚĆ na {cid}", full=False)
                        break
                        
                    opts =[{'label': ", ".join(f"{k}={v}" for k,v in cb.items()) or "Spełnione", 'data': cb} for cb in valid_cands]
                    j_idx = self.make_decision(f'just_{cid}', f"Zgodność na {cid}={val}", opts)
                    chosen = opts[j_idx]['data']
                    
                    has_real_change = False
                    for k, v in chosen.items():
                        if v != 'x' and self.algo_state[k] != v:
                            self.algo_state[k] = v
                            has_real_change = True
                            changed = True
                            
                    if chosen:
                        self.add_step(f"Zgodność na {cid}={val}. Wymagane: {opts[j_idx]['label']}", delta=chosen, full=False)

        if not conflict:
            self.add_step("TEST (Stan końcowy układu)", full=True)
            
        self.update_ui()

    def update_ui(self):
        self.tree.delete(*self.tree.get_children())
        
        # Filtrowanie kolumn WĘZŁÓW
        show_nodes = self.show_nodes_var.get()
        display_cols =[c for c in self.cols if show_nodes or self.components.get(c, {}).get('type') != 'NODE']
        
        self.tree["columns"] =["Krok"] + display_cols + ["Komentarz"]
        self.tree.heading("Krok", text="Krok")
        self.tree.column("Krok", width=40, anchor="center")
        
        for c in display_cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=45, anchor="center")
            
        self.tree.heading("Komentarz", text="Komentarz")
        self.tree.column("Komentarz", width=400, anchor="w")
        
        for i, step in enumerate(self.steps):
            vals = [i+1]
            for c in display_cols:
                if step['full']:
                    v = step['s'][c]
                else:
                    v = step['delta'].get(c, '')
                vals.append(v)
            vals.append(step['msg'])
            self.tree.insert("", tk.END, values=vals)

        for widget in self.decisions_inner.winfo_children(): widget.destroy()
        
        if self.decision_log:
            for dec in self.decision_log:
                f = ttk.Frame(self.decisions_inner)
                f.pack(fill=tk.X, pady=2)
                ttk.Label(f, text=dec['title'] + ":", font=("Arial", 8)).pack(anchor=tk.W)
                
                cb = ttk.Combobox(f, values=[opt['label'] for opt in dec['options']], state="readonly")
                cb.current(dec['selected'])
                cb.pack(fill=tk.X)
                
                def on_change(event, d_id=dec['id'], box=cb):
                    self.user_choices[d_id] = box.current()
                    self.run_algorithm(False)
                    
                cb.bind("<<ComboboxSelected>>", on_change)

if __name__ == "__main__":
    root = tk.Tk()
    app = DAlgorithmApp(root)
    root.mainloop()