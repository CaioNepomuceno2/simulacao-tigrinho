"""Simulação de 10 mil jogadores num caça-níquel de teste, para o vídeo do tigrinho do canal Experimento Neural.

NÃO é o código do Fortune Tiger. É um caça-níquel de teste 3x3 com 5 linhas, a mesma tabela de prêmios que os
sites de análise divulgam (curinga 250, lingote 100, jade 25, saco 10, envelope 8, rojão 5, laranja 3, pagos sobre a
aposta por linha = aposta/5) e o multiplicador x10 de tela cheia. Os PESOS dos símbolos são INVENTADOS (fita
virtual de 1.000 posições, símbolo mais caro = mais raro), porque os do jogo real não são públicos.

Três mundos com os MESMOS giros (mesma semente, mesmos símbolos); só muda quanto a máquina paga
(prêmios multiplicados por k = RTP_alvo / RTP_do_modelo):
  justo     100,00%  (devolve tudo, em média)
  tigrinho   96,81%  (RTP teórico do certificado Gaming Associates, 26/04/2022, versão 1.3.0.3)
  piso       85,00%  (mínimo teórico da Portaria SPA/MF 1.207/2024, Anexo I, item 28)

Uso:
  uv run python simular.py <pasta_saida> [--jogadores 10000] [--giros 20000] [--modelo grade|generico|moderado]
Retomável: se <pasta_saida>/resultados.json existe, não roda de novo.
"""
import argparse
import json
import os
import time

import numpy as np

SEMENTE = 20261113
NOMES = ["curinga", "lingote", "jade", "saco", "envelope", "rojao", "laranja"]
PREMIO = np.array([250, 100, 25, 10, 8, 5, 3], dtype=np.float64)  # sobre a aposta por linha
LINHAS = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 4, 8), (6, 4, 2)]
FITA = 1000
MUNDOS = {"justo": 1.0, "tigrinho": 0.9681, "piso": 0.85}
SALDO0 = 100.0
APOSTA = 1.0
MARCOS = [10, 25, 50, 100, 200, 300, 500, 1000, 2000, 3000, 5000, 10000, 20000]


def rtp_exato(p):
    """RTP exato (em fração da aposta total) para probabilidades p por posição (posições independentes)."""
    w = p[0]
    e_linha = PREMIO[0] * w ** 3
    extra = PREMIO[0] * w ** 9
    for s in range(1, 7):
        q = p[s] + w
        e_linha += PREMIO[s] * (q ** 3 - w ** 3)
        so_s = (q ** 9 - w ** 9) - (w ** 3 * q ** 6 - w ** 9)
        extra += PREMIO[s] * so_s + PREMIO[0] * (w ** 3 * q ** 6 - w ** 9)
    # 5 linhas, cada uma paga PREMIO * aposta/5 -> média de 1 linha = soma/5; tela cheia multiplica por 10 (+9x)
    return e_linha + 9 * extra


def montar_fita():
    """Procura contagens inteiras (fita de 1.000) com RTP mais perto de 96,81%, símbolo caro = raro."""
    melhor = None
    for alfa in np.linspace(0.3, 2.5, 2201):
        bruto = PREMIO ** (-alfa)
        c = np.maximum(1, np.round(FITA * bruto / bruto.sum())).astype(int)
        c[-1] += FITA - c.sum()
        if c[-1] < 1:
            continue
        r = rtp_exato(c / FITA)
        if melhor is None or abs(r - 0.9681) < abs(melhor[1] - 0.9681):
            melhor = (c, r, float(alfa))
    return melhor


def pagar(sim):
    """sim: (n, 9) uint8 -> pagamento em múltiplos da aposta total."""
    total = np.zeros(sim.shape[0], dtype=np.float64)
    for a, b, c in LINHAS:
        x, y, z = sim[:, a], sim[:, b], sim[:, c]
        s = np.maximum(np.maximum(x, y), z)
        ganha = ((x == 0) | (x == s)) & ((y == 0) | (y == s)) & ((z == 0) | (z == s))
        total += np.where(ganha, PREMIO[s], 0.0)
    total /= 5.0
    s9 = sim.max(axis=1)
    cheia = np.all((sim == 0) | (sim == s9[:, None]), axis=1)
    total[cheia] *= 10.0
    return total, cheia


# Modelo B (robustez): não tem grade nem tabela do jogo; só uma distribuição de prêmios mais volátil e com menos
# acertos (30% dos giros pagam algo). Serve para conferir se as conclusões dependem dos pesos inventados do modelo A.
# O primeiro B (com prêmio de 2500x) tinha cauda tão pesada que 10.000 jogadores não bastaram para as contas de
# dinheiro convergirem (o mundo justo mostrou a casa com +13%, onde a teoria dá 0). O B usado no vídeo é o
# "moderado": mesmo acerto de 30%, prêmio máximo de 250x.
GEN_VALORES = np.array([0.4, 0.6, 1.0, 1.6, 2.0, 5.0, 10.0, 25.0, 50.0, 100.0, 250.0, 2500.0])
GEN_ACERTO = 0.30


def montar_generico():
    """Pesos q_j ∝ valor^-beta, com beta escolhido (bisseção) para o RTP do modelo dar 96,81% sem reescalar."""
    def rtp(beta):
        w = GEN_VALORES ** -beta
        return float((GEN_ACERTO * w / w.sum() * GEN_VALORES).sum())
    lo, hi = 0.5, 3.0  # rtp cai quando beta sobe
    for _ in range(200):
        mid = (lo + hi) / 2
        if rtp(mid) > 0.9681:
            lo = mid
        else:
            hi = mid
    w = GEN_VALORES ** -lo
    q = GEN_ACERTO * w / w.sum()
    return q, float((q * GEN_VALORES).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("saida")
    ap.add_argument("--jogadores", type=int, default=10000)
    ap.add_argument("--giros", type=int, default=20000)
    ap.add_argument("--amostra", type=int, default=300, help="trajetórias guardadas para os quadros")
    ap.add_argument("--modelo", choices=["grade", "generico", "moderado"], default="grade")
    ap.add_argument("--pontos-saldo", type=int, default=0, help="guarda o saldo de todos em N pontos (simulador)")
    ap.add_argument("--giros-grade", type=int, default=0, help="guarda as grades 3x3 da amostra nos N 1ºs giros")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    destino = os.path.join(a.saida, "resultados.json")
    if os.path.exists(destino):
        print("já existe:", destino)
        return

    t0 = time.time()
    if a.modelo == "grade":
        contagens, rtp_modelo, alfa = montar_fita()
        fita = np.repeat(np.arange(7, dtype=np.uint8), contagens)
        print("fita:", dict(zip(NOMES, contagens.tolist())), "RTP do modelo:", round(rtp_modelo * 100, 4), "%")
    else:
        global GEN_VALORES
        if a.modelo == "moderado":
            GEN_VALORES = GEN_VALORES[GEN_VALORES <= 250.0]
        gq, rtp_modelo = montar_generico()
        gcum = np.cumsum(gq)
        contagens, alfa = np.zeros(7, dtype=int), float("nan")
        print("genérico: acerto", GEN_ACERTO, "RTP do modelo:", round(rtp_modelo * 100, 4), "%")
    k = {m: alvo / rtp_modelo for m, alvo in MUNDOS.items()}

    rng = np.random.default_rng(SEMENTE)
    n, g = a.jogadores, a.giros
    saldo = {m: np.full(n, SALDO0) for m in MUNDOS}
    vivo = {m: np.ones(n, dtype=bool) for m in MUNDOS}
    apostado = {m: np.zeros(n) for m in MUNDOS}
    pico = {m: np.full(n, SALDO0) for m in MUNDOS}
    giro_zerou = {m: np.full(n, -1, dtype=np.int64) for m in MUNDOS}
    esteve_lucro = {m: np.zeros(n, dtype=bool) for m in MUNDOS}
    # estratégia "paro quando dobrar" (só no mundo tigrinho): congela quem chega a 200
    dobrou = np.zeros(n, dtype=bool)
    saldo_dobra = np.full(n, SALDO0)
    vivo_dobra = np.ones(n, dtype=bool)
    apostado_dobra = np.zeros(n)

    amostra = np.arange(min(a.amostra, n))
    traj = {m: np.zeros((len(amostra), g + 1), dtype=np.float32) for m in MUNDOS}
    for m in MUNDOS:
        traj[m][:, 0] = SALDO0

    # estatísticas de giro (mundo tigrinho, todos os giros sorteados, independentes do saldo)
    giros_total = 0
    giros_premio = 0          # pagou algo (> 0)
    giros_menos_que_aposta = 0  # pagou algo, mas menos que a aposta ("perda disfarçada de ganho")
    giros_cheia = 0
    seca = np.zeros(n, dtype=np.int64)  # giros seguidos sem prêmio, por jogador (sequência de sorteios)
    apos_seca = {10: [0, 0], 20: [0, 0], 30: [0, 0]}  # [giros após >= N sem prêmio, desses quantos pagaram]
    marcos = {m: {} for m in MUNDOS}
    # séries por giro (todos os jogadores), para os contadores vivos do vídeo; não mexem no sorteio
    CAMPOS = ["pct_no_lucro", "pct_zerados", "casa_pct_depositado", "saldo_mediano", "saldo_medio",
              "pct_estiveram_no_lucro"]
    series = {m: np.zeros((len(CAMPOS), g + 1), dtype=np.float32) for m in MUNDOS}
    for m in MUNDOS:
        series[m][:, 0] = [0.0, 0.0, 0.0, SALDO0, SALDO0, 0.0]
    # para o simulador na tela: saldo de TODOS os jogadores em pontos escolhidos (mais densos no começo) e as grades
    # 3x3 reais sorteadas para os jogadores da amostra nos primeiros giros (a máquina na tela mostra o sorteio real)
    pontos = np.unique(np.round(np.linspace(0, 1, max(2, a.pontos_saldo)) ** 2 * g).astype(int)) \
        if a.pontos_saldo else np.array([], dtype=int)
    saldos = {m: np.zeros((len(pontos), n), dtype=np.float16) for m in MUNDOS}
    for m in MUNDOS:
        if len(pontos):
            saldos[m][0] = SALDO0
    giros_grade = min(a.giros_grade, g) if a.modelo == "grade" else 0
    grades = np.zeros((len(amostra), giros_grade, 9), dtype=np.uint8)

    for i in range(1, g + 1):
        if a.modelo == "grade":
            sim = fita[rng.integers(0, FITA, size=(n, 9))]
            base, cheia = pagar(sim)
        else:
            u = rng.random(n)
            idx = np.searchsorted(gcum, u, side="right")
            base = np.where(idx < len(GEN_VALORES), GEN_VALORES[np.minimum(idx, len(GEN_VALORES) - 1)], 0.0)
            cheia = base >= 2500.0
        pagou = base > 0
        giros_total += n
        giros_premio += int(pagou.sum())
        giros_menos_que_aposta += int((pagou & (base * k["tigrinho"] < APOSTA)).sum())
        giros_cheia += int(cheia.sum())
        for lim in apos_seca:
            sel = seca >= lim
            apos_seca[lim][0] += int(sel.sum())
            apos_seca[lim][1] += int((sel & pagou).sum())
        seca = np.where(pagou, 0, seca + 1)

        for m in MUNDOS:
            v = vivo[m] & (saldo[m] >= APOSTA)
            saldo[m] = np.where(v, saldo[m] - APOSTA + base * k[m], saldo[m])
            apostado[m] += np.where(v, APOSTA, 0.0)
            pico[m] = np.maximum(pico[m], saldo[m])
            esteve_lucro[m] |= saldo[m] > SALDO0
            zerou_agora = vivo[m] & (saldo[m] < APOSTA)
            giro_zerou[m][zerou_agora] = i
            vivo[m] &= saldo[m] >= APOSTA
            traj[m][:, i] = saldo[m][amostra]
            s = saldo[m]
            series[m][:, i] = [100 * (s > SALDO0).mean(), 100 * (~vivo[m]).mean(),
                               100 * (n * SALDO0 - s.sum()) / (n * SALDO0), np.median(s), s.mean(),
                               100 * esteve_lucro[m].mean()]
            if len(pontos):
                kk = np.searchsorted(pontos, i)
                if kk < len(pontos) and pontos[kk] == i:
                    saldos[m][kk] = np.minimum(s, 60000).astype(np.float16)
        if i <= giros_grade:
            grades[:, i - 1, :] = sim[amostra]
        # estratégia dobrar
        vd = vivo_dobra & (saldo_dobra >= APOSTA)
        saldo_dobra = np.where(vd, saldo_dobra - APOSTA + base * k["tigrinho"], saldo_dobra)
        apostado_dobra += np.where(vd, APOSTA, 0.0)
        chegou = vd & (saldo_dobra >= 2 * SALDO0)
        dobrou |= chegou
        vivo_dobra &= (saldo_dobra >= APOSTA) & ~chegou

        if i in MARCOS:
            for m in MUNDOS:
                s = saldo[m]
                marcos[m][i] = {
                    "pct_no_lucro": round(100 * float((s > SALDO0).mean()), 2),
                    "pct_zerados": round(100 * float((~vivo[m]).mean()), 2),
                    "saldo_mediano": round(float(np.median(s)), 2),
                    "saldo_medio": round(float(s.mean()), 2),
                    "apostado_total": round(float(apostado[m].sum()), 2),
                    "casa_ficou_com": round(float(n * SALDO0 - s.sum()), 2),
                    "casa_pct_do_apostado": round(100 * float((n * SALDO0 - s.sum()) / apostado[m].sum()), 3),
                    "casa_pct_do_depositado": round(100 * float((n * SALDO0 - s.sum()) / (n * SALDO0)), 2),
                }
            print(f"giro {i}: " + " | ".join(f"{m} lucro {marcos[m][i]['pct_no_lucro']}% zerados "
                                             f"{marcos[m][i]['pct_zerados']}%" for m in MUNDOS),
                  f"({time.time() - t0:.0f} s)", flush=True)

    res = {
        "o_que_e": __doc__.strip().splitlines()[0],
        "semente": SEMENTE, "jogadores": n, "giros_max": g, "saldo_inicial": SALDO0, "aposta": APOSTA,
        "data": time.strftime("%Y-%m-%d"),
        "modelo": {"tipo": a.modelo,
                   "generico": ({"valores": GEN_VALORES.tolist(), "acerto": GEN_ACERTO}
                                if a.modelo != "grade" else None),
                   "fita_contagens": dict(zip(NOMES, contagens.tolist())), "fita_tamanho": FITA,
                   "alfa_peso": round(alfa, 4), "rtp_modelo_exato_pct": round(rtp_modelo * 100, 5),
                   "fator_premio": {m: round(v, 6) for m, v in k.items()},
                   "premios_por_linha": dict(zip(NOMES, PREMIO.tolist()))},
        "giros_tigrinho": {
            "giros_sorteados": giros_total,
            "pct_giros_com_premio": round(100 * giros_premio / giros_total, 3),
            "pct_premios_menores_que_aposta": round(100 * giros_menos_que_aposta / max(1, giros_premio), 2),
            "pct_giros_tela_cheia": round(100 * giros_cheia / giros_total, 4),
            "pct_premio_apos_seca": {str(lim): round(100 * v[1] / max(1, v[0]), 3) for lim, v in apos_seca.items()},
            "n_apos_seca": {str(lim): v[0] for lim, v in apos_seca.items()},
        },
        "marcos": {m: {str(i): v for i, v in d.items()} for m, d in marcos.items()},
        "final": {},
        "estrategia_dobrar_tigrinho": {
            "pct_dobraram": round(100 * float(dobrou.mean()), 2),
            "pct_zeraram": round(100 * float((~dobrou & ~vivo_dobra).mean()), 2),
            "pct_ainda_jogando": round(100 * float((~dobrou & vivo_dobra).mean()), 2),
            "saldo_medio_final": round(float(saldo_dobra.mean()), 2),
            "apostado_medio": round(float(apostado_dobra.mean()), 2),
            "casa_pct_do_apostado": round(100 * float((n * SALDO0 - saldo_dobra.sum()) / apostado_dobra.sum()), 3),
        },
    }
    for m in MUNDOS:
        z = giro_zerou[m]
        zer = z[z > 0]
        res["final"][m] = {
            "pct_zerados": round(100 * float((z > 0).mean()), 2),
            "giros_ate_zerar_mediana": int(np.median(zer)) if len(zer) else None,
            "giros_ate_zerar_p10": int(np.percentile(zer, 10)) if len(zer) else None,
            "giros_ate_zerar_p90": int(np.percentile(zer, 90)) if len(zer) else None,
            "apostado_ate_zerar_mediana": round(float(np.median(apostado[m][z > 0])), 2) if len(zer) else None,
            "apostado_ate_zerar_media": round(float(apostado[m][z > 0].mean()), 2) if len(zer) else None,
            "pct_estiveram_no_lucro_e_zeraram": round(100 * float((esteve_lucro[m] & (z > 0)).mean()), 2),
            "pct_estiveram_no_lucro": round(100 * float(esteve_lucro[m].mean()), 2),
            "pico_mediano_dos_que_zeraram": round(float(np.median(pico[m][z > 0])), 2) if len(zer) else None,
            "pct_pico_acima_de_200_e_zeraram": round(100 * float(((pico[m] >= 200) & (z > 0)).mean()), 2),
        }
    # jogador mediano (mundo tigrinho): dentro da amostra, o que zerou mais perto da mediana de giros
    zt = giro_zerou["tigrinho"][amostra]
    med = res["final"]["tigrinho"]["giros_ate_zerar_mediana"]
    cand = np.where(zt > 0)[0]
    if len(cand) and med:
        j = int(cand[np.argmin(np.abs(zt[cand] - med))])
        tr = traj["tigrinho"][j, : zt[j] + 1]
        res["jogador_mediano"] = {"indice_na_amostra": j, "giros_ate_zerar": int(zt[j]),
                                  "pico": round(float(tr.max()), 2), "giro_do_pico": int(tr.argmax()),
                                  "giros_no_lucro": int((tr > SALDO0).sum()),
                                  "maior_premio_num_giro": round(float(np.max(np.diff(tr) + APOSTA)), 2)}
    res["segundos"] = round(time.time() - t0, 1)
    np.savez_compressed(os.path.join(a.saida, "trajetorias.npz"), **{m: traj[m] for m in MUNDOS})
    np.savez_compressed(os.path.join(a.saida, "series.npz"), campos=np.array(CAMPOS),
                        **{m: series[m] for m in MUNDOS})
    if len(pontos):
        np.savez_compressed(os.path.join(a.saida, "saldos.npz"), pontos=pontos, **{m: saldos[m] for m in MUNDOS})
    if giros_grade:
        np.savez_compressed(os.path.join(a.saida, "grades.npz"), grades=grades,
                            premio=PREMIO, nomes=np.array(NOMES), fator=np.array([k["tigrinho"]]))
    tmp = destino + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, destino)
    print(json.dumps({k2: res[k2] for k2 in ("modelo", "giros_tigrinho", "final", "estrategia_dobrar_tigrinho",
                                              "jogador_mediano") if k2 in res}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
