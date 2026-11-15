# Simulei 10 mil jogadores no tigrinho

Código do vídeo sobre o tigrinho do canal Experimento Neural, no YouTube.

Vídeo: *o link entra aqui quando o vídeo for publicado.*

## A pergunta

Se a máquina devolve 96,81% do que recebe, por que quase todo mundo que joga sem parar acaba sem nada?

## O que este código é, e o que não é

- **Não é o código do Fortune Tiger** nem de nenhum jogo real, e não tem relação com quem fabrica ou oferece o jogo. É
  um caça-níquel de teste 3×3 com 5 linhas, com a tabela de prêmios que os sites de análise divulgam (curinga 250,
  lingote 100, jade 25, saco 10, envelope 8, rojão 5, laranja 3, pagos sobre a aposta por linha) e o ×10 de tela cheia.
- **Os pesos dos símbolos são inventados** (fita virtual de 1.000 posições, símbolo mais caro = mais raro), porque os do
  jogo real não são públicos. Por isso existe um segundo modelo, sem grade (modelo B), para conferir se as conclusões
  dependem desses pesos.
- **Três mundos com os mesmos giros** (mesma semente, mesmos símbolos sorteados). Só muda quanto a máquina paga:

| Mundo | Devolve em média | De onde vem |
|---|---|---|
| Justo | 100% | Referência: a casa não ganha nada, em média |
| Tigrinho | 96,81% | RTP teórico do certificado do laboratório Gaming Associates, 26/04/2022, versão 1.3.0.3, certificação para o Reino Unido (o RTP simulado pelo laboratório foi 96,71%). A versão de cada site pode ser outra |
| Piso | 85% | Mínimo teórico que a Portaria SPA/MF nº 1.207/2024 (Anexo I, item 28) exigia das bets autorizadas no Brasil |

Cada jogador começa com R$ 100, aposta R$ 1 por giro e só para quando o dinheiro acaba (ou nos 20.000 giros).

## Como rodar

Com [uv](https://docs.astral.sh/uv/):

```bash
uv sync
uv run python simular.py minha_rodada                      # modelo A, ~45 s
uv run python simular.py minha_rodada_B --modelo moderado  # modelo B, ~25 s
uv run python resumo.py minha_rodada/resultados.json       # os números do vídeo
uv run pytest                                              # testes, ~3 s
```

Com pip:

```bash
python -m venv .venv
.venv\Scripts\activate        # no Linux ou no Mac: source .venv/bin/activate
pip install -r requirements.txt
python simular.py minha_rodada
python resumo.py minha_rodada/resultados.json
```

Os resultados usados no vídeo já estão em `resultados/A_grade/` e `resultados/B_moderado/`. A simulação é retomável:
se a pasta de saída já tem um `resultados.json`, ela não roda de novo. Para rodar do zero, use outra pasta.

## Semente e reprodutibilidade

Semente **20261113**. A mesma semente gera os mesmos números (um teste confere isso). Os resultados deste repositório
foram gerados em 15/11/2026 com Python 3.12 e NumPy 2.5.4, e batem com os da rodada usada no vídeo.

## Resultado (modelo A: 10.000 jogadores)

| | Justo (100%) | Tigrinho (96,81%) | Piso (85%) |
|---|---|---|---|
| No lucro depois de 100 giros | 46,1% | 39,4% | 25,2% |
| No lucro depois de 1.000 giros | 46,6% | 33,6% | 4,1% |
| Zerados depois de 1.000 giros | 27,5% | 38,7% | 83,9% |
| A casa ficou com, depois de 1.000 giros (do dinheiro depositado) | −0,2% | 26,5% | 88,1% |
| No lucro depois de 20.000 giros | 17,8% (1.782 pessoas) | 1,7% (169 pessoas) | 0% |
| A casa ficou com, depois de 20.000 giros | −0,7% | 93,2% | 99,4% |
| Estiveram no lucro em algum momento e depois zeraram | 74,6% | 87,8% | 76,4% |

O que isso mostra:

- **A casa fica com uns 3 centavos de cada real apostado, mas o mesmo real é apostado muitas vezes.** Em 1.000 giros,
  cada real depositado voltou para a máquina 8,4 vezes; 8,4 × 3,15% ≈ 26,5% de todo o dinheiro.
- **Quem nunca para quebra até na máquina justa** (81,6% zerados em 20.000 giros). A diferença é para onde vai o
  dinheiro: na justa ele fica com os outros jogadores; no tigrinho, com a casa.
- **Ficar no lucro não quer dizer sair no lucro:** 87,8% estiveram à frente em algum momento e zeraram depois.
- **"Paro quando dobrar"**: 30,6% conseguiram dobrar os R$ 100; 69,5% zeraram antes.
- **Falsa vitória:** 53,8% dos prêmios pagaram menos que a aposta. A máquina comemora, mas o jogador perdeu dinheiro
  naquele giro. Esse número depende dos pesos inventados.

### Modelo B (robustez)

Sem grade nem tabela do jogo: só uma distribuição de prêmios em que 30% dos giros pagam algo, com prêmio máximo de 250×
e o mesmo RTP. No mundo tigrinho, depois de 20.000 giros, 3,2% estavam no lucro e a casa ficou com 57,8% do dinheiro
depositado (a cauda de prêmios grandes deixa mais dinheiro com poucos jogadores). Os números mudam, a conclusão não:
quem não para perde quase tudo, e a diferença entre a máquina justa e a de 96,81% vai para a casa.

## Limitações

- Os pesos dos símbolos são inventados; o modelo B existe para mostrar o que muda quando eles mudam.
- Aposta fixa de R$ 1, sem rodadas grátis nem bônus.
- Os jogadores não param por vontade própria (fora a estratégia "paro quando dobrar").
- Não modela máquina manipulada nem jogo ilegal: aqui, cada giro é independente e a máquina paga exatamente o RTP
  declarado. Num site ilegal ou manipulado, o resultado pode ser pior.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `simular.py` | A simulação (modelos A e B, três mundos, estratégia de dobrar) |
| `resumo.py` | Imprime os números do vídeo a partir de um `resultados.json` |
| `tests/test_simular.py` | Tabela de prêmios, RTP exato contra sorteio e reprodutibilidade |
| `resultados/` | Resultados da rodada do vídeo (os arquivos `.npz` de trajetórias ficam fora do repositório) |

## Licença

MIT (veja `LICENSE`).

## Aviso

Simulação educativa. Não é recomendação de aposta nem de investimento. Se o jogo virou problema, o SUS atende de graça,
nas Unidades Básicas de Saúde (UBS) e nos Centros de Atenção Psicossocial (CAPS).
