# Roadmap — ARQTECH AGRI INTELLIGENCE

O projeto evolui de engenharia de dados para percepção visual, geometria agrícola e inteligência geoespacial, mantendo evidência e incerteza rastreáveis.

## Fase 0 — Foundation & Governance

**Estado: concluída e integrada à `main`.**

Arquitetura modular, contratos fundamentais, separação entre observação/predição/medição/interpretação, governança e validação estrutural.

## Fase 1 — Data Engine

**Estado: concluída e integrada à `main`.**

Contratos de fonte/licença/versão/asset/schema/split/manifesto/aquisição/auditoria; inventário local SHA-256; inspeção limitada de cabeçalhos; manifesto determinístico e atômico; auditoria de bounding boxes; integridade de IDs/referências; leakage por grupos; contratos espaciais tipados.

O MSDD permanece **BLOCKED** até verificação da licença da distribuição exata, direitos de redistribuição, uso comercial, atribuição e proveniência/equivalência da conversão Parquet. Não realizar download ou adoção enquanto bloqueado.

## Fase 2 — Crop Vision Engine

**Estado: planejamento técnico documentado; implementação não iniciada.**

Escopo inicial em espaço de imagem:
1. Readiness de dados, classes, licença e protocolo experimental.
2. Image I/O e validação determinística.
3. Tiling com transformação tile → imagem original.
4. Adaptador de detector independente de backend.
5. Pós-processamento e deduplicação.
6. Avaliação com ground truth auditado, splits por grupos de aquisição e métricas reproduzíveis.

A primeira entrega será detecção. Segmentação depende de máscaras aprovadas e fica fora do primeiro incremento. Consulte [PHASE_2_VISION_PLAN.md](PHASE_2_VISION_PLAN.md).

## Fase 3 — Agricultural Geometry

Reconstruir linhas quando suportado pelos dados, estimar espaçamento somente com referência espacial válida e separar lacuna visual observada de falha agronômica confirmada.

## Fase 4 — Geospatial Intelligence

Integração geoespacial de ortomosaicos, CRS, GSD, transformações, mapas e exportações GIS, com validação de precisão e proveniência.

## Fase 5 — Multimodal Intelligence

Pontos de extensão para integrar sensores e fontes complementares, com sincronização, calibração, qualidade e incerteza explícitas.

## Fase 6 — Validated Decision Support

Indicadores agronômicos e suporte à decisão somente após validação científica, avaliação em campo e limites de uso documentados.

## Gates transversais

- Sem downloads de datasets/pesos ou treinamento/inferência sem autorização explícita.
- Sem promoção de métrica experimental a capacidade operacional sem validação.
- Sem conversão pixel → distância física sem escala/transformação válida.
- Testes determinísticos e validator oficial em cada fase.
- Validação manual no Colab; não adicionar GitHub Actions.
- Cada fase trabalha em branch própria; integração à `main` exige revisão, evidência e autorização.
