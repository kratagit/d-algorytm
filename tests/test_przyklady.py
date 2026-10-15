import pytest

import buduj_przyklady


def test_examples_generator(tmp_path):
    (tmp_path / '10.json').write_text('{"components": {}}', encoding='utf-8')
    (tmp_path / '2.json').write_text('{"components": {"X1": {}}}', encoding='utf-8')
    (tmp_path / 'uklad.json').write_text('{}', encoding='utf-8')  # ignorowany - nazwa nie jest liczbą
    out = tmp_path / 'web' / 'examples.js'
    assert buduj_przyklady.buduj(str(tmp_path), str(out)) == ['2.json', '10.json']
    js = out.read_text(encoding='utf-8')
    assert js == 'const EXAMPLES = {\n    2: {"components": {"X1": {}}},\n    10: {"components": {}},\n};\n'


def test_examples_generator_rejects_invalid_json(tmp_path):
    (tmp_path / '1.json').write_text('{zepsuty', encoding='utf-8')
    with pytest.raises(ValueError):
        buduj_przyklady.generuj_examples_js(str(tmp_path))
