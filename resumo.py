"""Imprime os números do vídeo a partir de um resultados.json gerado pelo simular.py.

Uso:
  uv run python resumo.py                      # resultados/A_grade/resultados.json
  uv run python resumo.py resultados/B_moderado/resultados.json
"""
import json
import sys


def br(x, casas=1):
    """Número no formato brasileiro (vírgula decimal, ponto de milhar)."""
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def main():
    caminho = sys.argv[1] if len(sys.argv) > 1 else "resultados/A_grade/resultados.json"
    r = json.load(open(caminho, encoding="utf-8"))
    n, s0 = r["jogadores"], r["saldo_inicial"]
    depositado = n * s0
    t, j = r["marcos"]["tigrinho"], r["marcos"]["justo"]
    g = r["giros_tigrinho"]
    print(f"{br(n, 0)} jogadores, R$ {br(s0, 0)} cada, R$ {br(r['aposta'], 0)} por giro, semente {r['semente']}")
    print(f"Modelo: {r['modelo']['tipo']}; RTP do mundo tigrinho: 96,81%\n")

    print("Depois de 100 giros")
    print(f"  no lucro (tigrinho): {br(t['100']['pct_no_lucro'])}%")
    print("Depois de 1.000 giros")
    print(f"  a casa ficou com {br(t['1000']['casa_pct_do_depositado'])}% do dinheiro depositado "
          f"(máquina justa: {br(j['1000']['casa_pct_do_depositado'])}%)")
    voltas = t["1000"]["apostado_total"] / depositado
    print(f"  cada real depositado foi apostado {br(voltas)} vezes; a casa ficou com "
          f"{br(t['1000']['casa_pct_do_apostado'], 2)}% de cada aposta")
    print("Depois de 20.000 giros")
    print(f"  no lucro: {br(t['20000']['pct_no_lucro'] * n / 100, 0)} no tigrinho × "
          f"{br(j['20000']['pct_no_lucro'] * n / 100, 0)} na máquina justa")
    print(f"  a casa ficou com {br(t['20000']['casa_pct_do_depositado'])}% "
          f"(máquina justa: {br(j['20000']['casa_pct_do_depositado'])}%)")
    f = r["final"]["tigrinho"]
    print(f"  estiveram no lucro em algum momento e depois zeraram: {br(f['pct_estiveram_no_lucro_e_zeraram'])}%")

    if "jogador_mediano" in r:
        m = r["jogador_mediano"]
        print("\nJogador do meio da fila (tigrinho)")
        print(f"  pico de R$ {br(m['pico'], 2)} no giro {br(m['giro_do_pico'], 0)}, {br(m['giros_no_lucro'], 0)} giros "
              f"no lucro, zerou no giro {br(m['giros_ate_zerar'], 0)}")

    d = r["estrategia_dobrar_tigrinho"]
    print("\nEstratégia \"paro quando dobrar\" (tigrinho)")
    print(f"  dobraram: {br(d['pct_dobraram'])}%; zeraram antes: {br(d['pct_zeraram'])}%")
    print("\nGiros")
    print(f"  pagaram algo: {br(g['pct_giros_com_premio'])}%; desses, pagaram menos que a aposta: "
          f"{br(g['pct_premios_menores_que_aposta'])}% (\"falsa vitória\")")


if __name__ == "__main__":
    main()
