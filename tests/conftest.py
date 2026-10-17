import os
import sys

# Silnik i skrypty z katalogu głównego oraz moduły pomocnicze testów (oracle, helpers, random_circuits)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.dirname(os.path.abspath(__file__))]
