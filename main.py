import sys
import traceback
import ctypes

def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    ctypes.windll.user32.MessageBoxW(0, f"Aplikacja napotkała błąd:\n\n{error_msg}", "Błąd Krytyczny", 0x10)
    sys.exit(1)

sys.excepthook = global_exception_handler

import eel
import os
from engine import DAlgorithmEngine

# 1. Zabezpieczenie dla PyInstaller (na wypadek gdybyś kiedyś do niego wrócił)
if hasattr(sys, '_MEIPASS'):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    
web_folder = os.path.join(base_path, 'web')

# 2. Mówimy Eelowi, gdzie znajduje się folder z naszym interfejsem
eel.init(web_folder)

@eel.expose
def run_d_algorithm(components, target_node, fault_type, user_choices):
    engine = DAlgorithmEngine(components, target_node, fault_type, user_choices)
    result = engine.run()
    return result

import eel.chrome
import eel.edge

if __name__ == '__main__':
    # 3. Wykrywamy dostępną przeglądarkę, by uniknąć błędu braku Chrome'a
    if eel.chrome.find_path():
        mode = 'chrome'
    elif eel.edge.find_path():
        mode = 'edge'
    else:
        mode = 'default'

    # 4. Uruchamiamy aplikację w odpowiednim trybie
    eel.start('index.html', size=(1300, 850), port=0, mode=mode)