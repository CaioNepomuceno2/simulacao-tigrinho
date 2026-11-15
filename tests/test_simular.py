"""Testes rápidos: a tabela de prêmios, o RTP exato e a reprodutibilidade (mesma semente, mesmo resultado)."""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

import simular

PASTA = Path(__file__).resolve().parents[1]


def grade(*simbolos):
    return np.array([simbolos], dtype=np.uint8)


def test_uma_linha_de_rojao_paga_a_tabela_sobre_a_aposta_por_linha():
    # linha de cima: rojão, rojão, rojão (5x a aposta por linha = 5 × 1/5 da aposta total); nada mais ganha
    total, cheia = simular.pagar(grade(5, 5, 5, 6, 4, 3, 3, 4, 6))
    assert total[0] == 1.0 and not cheia[0]


def test_curinga_substitui_qualquer_simbolo():
    total, _ = simular.pagar(grade(0, 5, 5, 6, 4, 3, 3, 4, 6))
    assert total[0] == 1.0


def test_tela_cheia_multiplica_por_10():
    total, cheia = simular.pagar(grade(*[6] * 9))  # 9 laranjas: 5 linhas × 3 ÷ 5 = 3, vezes 10
    assert cheia[0] and total[0] == 30.0


def test_premio_maximo_e_2500_vezes_a_aposta():
    total, _ = simular.pagar(grade(*[0] * 9))  # 9 curingas: 5 linhas × 250 ÷ 5 = 250, vezes 10
    assert total[0] == 2500.0


def test_fita_e_rtp_do_modelo():
    contagens, rtp, _ = simular.montar_fita()
    assert contagens.tolist() == [1, 1, 12, 63, 96, 231, 596]
    assert round(rtp * 100, 5) == 97.09262
    assert round(0.9681 / rtp, 6) == 0.997089  # fator que leva o modelo aos 96,81% do mundo "tigrinho"


def test_rtp_exato_bate_com_sorteio():
    contagens, rtp, _ = simular.montar_fita()
    fita = np.repeat(np.arange(7, dtype=np.uint8), contagens)
    rng = np.random.default_rng(1)
    medias = [simular.pagar(fita[rng.integers(0, 1000, size=(500_000, 9))])[0].mean() for _ in range(4)]
    assert abs(np.mean(medias) - rtp) < 0.02


def rodar(saida):
    return subprocess.run([sys.executable, "-X", "utf8", str(PASTA / "simular.py"), str(saida), "--jogadores", "300",
                           "--giros", "400", "--amostra", "20"], capture_output=True, text=True, encoding="utf-8",
                          check=True)


def test_mesma_semente_mesmo_resultado_e_retomavel(tmp_path):
    rodar(tmp_path / "a")
    rodar(tmp_path / "b")
    a = json.loads((tmp_path / "a" / "resultados.json").read_text(encoding="utf-8"))
    b = json.loads((tmp_path / "b" / "resultados.json").read_text(encoding="utf-8"))
    for chave in ("marcos", "final", "giros_tigrinho", "estrategia_dobrar_tigrinho"):
        assert a[chave] == b[chave]
    assert "já existe" in rodar(tmp_path / "a").stdout
