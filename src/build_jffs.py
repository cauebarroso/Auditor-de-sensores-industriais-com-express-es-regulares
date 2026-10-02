import os
import xml.etree.ElementTree as ET
import xml.dom.minidom

class Automaton:
    def __init__(self):
        self.states = []
        self.transitions = []
        self.state_counter = 0

    def add_state(self, x, y, initial=False, final=False):
        sid = self.state_counter
        self.states.append({'id': sid, 'x': float(x), 'y': float(y), 'initial': initial, 'final': final})
        self.state_counter += 1
        return sid

    def add_transition(self, fro, to, read):
        self.transitions.append({'from': fro, 'to': to, 'read': read})

    def save(self, filename):
        out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "diagramas_jflap"))
        os.makedirs(out_dir, exist_ok=True)
        filepath = os.path.join(out_dir, filename)

        root = ET.Element("structure")
        ET.SubElement(root, "type").text = "fa"
        automaton = ET.SubElement(root, "automaton")
        for s in self.states:
            state = ET.SubElement(automaton, "state", id=str(s['id']), name=f"q{s['id']}")
            ET.SubElement(state, "x").text = str(s['x'])
            ET.SubElement(state, "y").text = str(s['y'])
            if s['initial']:
                ET.SubElement(state, "initial")
            if s['final']:
                ET.SubElement(state, "final")
        for t in self.transitions:
            trans = ET.SubElement(automaton, "transition")
            ET.SubElement(trans, "from").text = str(t['from'])
            ET.SubElement(trans, "to").text = str(t['to'])
            ET.SubElement(trans, "read").text = t['read'] if t['read'] else ""
        
        xmlstr = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml(indent="	")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xmlstr)

def chain(a, start_id, chars, dx=60, dy=0, final=False):
    curr = start_id
    cx = a.states[curr]['x']
    cy = a.states[curr]['y']
    for i, ch in enumerate(chars):
        cx += dx
        cy += dy
        is_final = final if i == len(chars) - 1 else False
        nxt = a.add_state(cx, cy, final=is_final)
        a.add_transition(curr, nxt, ch)
        curr = nxt
    return curr

# ER-02: Telemetria
def build_er02():
    a = Automaton()
    q0 = a.add_state(100, 300, initial=True)
    q_sen = chain(a, q0, "SEN-LL")
    
    q_l3 = a.add_state(a.states[q_sen]['x']+50, a.states[q_sen]['y']-50)
    q_m = a.add_state(a.states[q_sen]['x']+100, a.states[q_sen]['y'])
    a.add_transition(q_sen, q_l3, "L")
    a.add_transition(q_l3, q_m, "")
    a.add_transition(q_sen, q_m, "")
    
    q_base = chain(a, q_m, "-DDDD:")
    
    # 3 Branches
    t_start = chain(a, q_base, "TEMP=", dy=-150)
    u_start = chain(a, q_base, "UMID=", dy=0)
    p_start = chain(a, q_base, "PRES=", dy=150)
    
    # TEMP
    t_minus = a.add_state(a.states[t_start]['x']+50, a.states[t_start]['y'])
    a.add_transition(t_start, t_minus, "-")
    a.add_transition(t_start, t_minus, "")
    t_num = a.add_state(a.states[t_minus]['x']+50, a.states[t_minus]['y'])
    a.add_transition(t_minus, t_num, "N") # N = Numero TEMP
    t_dec = a.add_state(a.states[t_num]['x']+50, a.states[t_num]['y'])
    a.add_transition(t_num, t_dec, ".")
    t_dec2 = a.add_state(a.states[t_dec]['x']+50, a.states[t_dec]['y'])
    a.add_transition(t_dec, t_dec2, "D")
    
    t_end = a.add_state(a.states[t_dec2]['x']+50, a.states[t_dec2]['y'])
    a.add_transition(t_num, t_end, "")
    a.add_transition(t_dec2, t_end, "")
    chain(a, t_end, "C", final=True)
    
    # UMID
    u_num = a.add_state(a.states[u_start]['x']+50, a.states[u_start]['y'])
    a.add_transition(u_start, u_num, "M") # M = Numero UMID
    u_dec = a.add_state(a.states[u_num]['x']+50, a.states[u_num]['y'])
    a.add_transition(u_num, u_dec, ".")
    u_dec2 = a.add_state(a.states[u_dec]['x']+50, a.states[u_dec]['y'])
    a.add_transition(u_dec, u_dec2, "D")
    
    u_end = a.add_state(a.states[u_dec2]['x']+50, a.states[u_dec2]['y'])
    a.add_transition(u_num, u_end, "")
    a.add_transition(u_dec2, u_end, "")
    chain(a, u_end, "%", final=True)
    
    # PRES
    p_num = a.add_state(a.states[p_start]['x']+50, a.states[p_start]['y'])
    a.add_transition(p_start, p_num, "P") # P = Numero PRES
    chain(a, p_num, "hPa", final=True)
    
    a.save("ER-02.jff")

# ER-03: Comando
def build_er03():
    a = Automaton()
    q0 = a.add_state(100, 300, initial=True)
    q_cmd = chain(a, q0, "CMD ATU-LL")
    
    q_l3 = a.add_state(a.states[q_cmd]['x']+50, a.states[q_cmd]['y']-50)
    q_m = a.add_state(a.states[q_cmd]['x']+100, a.states[q_cmd]['y'])
    a.add_transition(q_cmd, q_l3, "L")
    a.add_transition(q_l3, q_m, "")
    a.add_transition(q_cmd, q_m, "")
    
    q_base = chain(a, q_m, "-DDDD ")
    
    # Branches
    b1 = chain(a, q_base, "LIGAR", dy=-100, final=True)
    b2 = chain(a, q_base, "DESLIGAR", dy=-50, final=True)
    b3 = chain(a, q_base, "ABRIR", dy=0, final=True)
    b4 = chain(a, q_base, "FECHAR", dy=50, final=True)
    b5 = chain(a, q_base, "AJUSTAR ")
    
    b5_num = a.add_state(a.states[b5]['x']+50, a.states[b5]['y']+100)
    a.add_transition(b5, b5_num, "M") # M = Num Ajuste
    chain(a, b5_num, "%", final=True)
    
    a.save("ER-03.jff")

# ER-04: IPv4
def build_er04():
    a = Automaton()
    q0 = a.add_state(100, 200, initial=True)
    q1 = a.add_state(200, 200)
    a.add_transition(q0, q1, "O") # O = Octeto
    q2 = a.add_state(300, 200)
    a.add_transition(q1, q2, ".")
    q3 = a.add_state(400, 200)
    a.add_transition(q2, q3, "O")
    q4 = a.add_state(500, 200)
    a.add_transition(q3, q4, ".")
    q5 = a.add_state(600, 200)
    a.add_transition(q4, q5, "O")
    q6 = a.add_state(700, 200)
    a.add_transition(q5, q6, ".")
    q7 = a.add_state(800, 200, final=True)
    a.add_transition(q6, q7, "O")
    
    # CIDR (opcional)
    q8 = a.add_state(900, 200)
    a.add_transition(q7, q8, "/")
    q9 = a.add_state(1000, 200, final=True)
    a.add_transition(q8, q9, "C") # C = CIDR mask
    
    a.save("ER-04.jff")

# ER-05: Alerta Log
def build_er05():
    a = Automaton()
    q0 = a.add_state(100, 300, initial=True)
    q_data = chain(a, q0, "DDDD-MM-DDTDD:DD:DD [") # MM = mes, DD = dia
    
    q_info = chain(a, q_data, "INFO]", dy=-100)
    q_warn = chain(a, q_data, "WARN]", dy=-50)
    q_err = chain(a, q_data, "ERROR]", dy=0)
    q_crit = chain(a, q_data, "CRIT]", dy=50)
    
    q_post = a.add_state(a.states[q_err]['x']+100, a.states[q_err]['y'])
    a.add_transition(q_info, q_post, "")
    a.add_transition(q_warn, q_post, "")
    a.add_transition(q_err, q_post, "")
    a.add_transition(q_crit, q_post, "")
    
    q_space = chain(a, q_post, " ")
    
    q_sen = chain(a, q_space, "SEN-", dy=-50)
    q_atu = chain(a, q_space, "ATU-", dy=50)
    q_merge = a.add_state(a.states[q_sen]['x']+50, a.states[q_space]['y'])
    a.add_transition(q_sen, q_merge, "")
    a.add_transition(q_atu, q_merge, "")
    
    q_id = chain(a, q_merge, "LL")
    q_l3 = a.add_state(a.states[q_id]['x']+50, a.states[q_id]['y']-50)
    q_m2 = a.add_state(a.states[q_id]['x']+100, a.states[q_id]['y'])
    a.add_transition(q_id, q_l3, "L")
    a.add_transition(q_l3, q_m2, "")
    a.add_transition(q_id, q_m2, "")
    
    q_fim = chain(a, q_m2, "-DDDD: ")
    q_msg = a.add_state(a.states[q_fim]['x']+100, a.states[q_fim]['y'], final=True)
    a.add_transition(q_fim, q_msg, "W") # W = Texto livre (letras, nums, espacos)
    a.add_transition(q_msg, q_msg, "W")
    
    a.save("ER-05.jff")

if __name__ == "__main__":
    build_er02()
    build_er03()
    build_er04()
    build_er05()
