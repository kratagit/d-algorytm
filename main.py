import eel
import os
import sys
from engine import DAlgorithmEngine

# 1. Ten magiczny fragment znajduje prawdziwą ścieżkę do plików (nawet gdy jesteśmy spakowani w .exe)
base_path = os.path.dirname(os.path.abspath(__file__))
web_folder = os.path.join(base_path, 'web')

# 2. Mówimy Eelowi, gdzie znajduje się folder z naszym interfejsem
eel.init(web_folder)

@eel.expose
def run_d_algorithm(components, target_node, fault_type, user_choices):
    engine = DAlgorithmEngine(components, target_node, fault_type, user_choices)
    result = engine.run()
    return result

if __name__ == '__main__':
    # 3. Uruchamiamy aplikację
    eel.start('index.html', size=(1300, 850), port=0)