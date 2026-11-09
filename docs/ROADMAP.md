# Roadmap — ARQTECH AGRI INTELLIGENCE

O projeto evolui de engenharia de dados para percepção visual, inteligência espacial, análise agronômica e operação, mantendo evidência e incerteza rastreáveis.

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

## Fase 3 — Spatial Intelligence

Reconstruir linhas quando suportado pelos dados, associar detecções à referência espacial, validar CRS/GSD/transformações e calcular distâncias somente quando houver escala espacial válida. Produzir mapas e exportações georreferenciadas com precisão documentada.

## Fase 4 — Agricultural Analytics

Derivar densidade, estande, espaçamento, variabilidade, continuidade das linhas e lacunas observadas. Distinguir medidas e estimativas de diagnósticos agronômicos; validar indicadores com dados de campo antes de qualquer recomendação.

## Fase 5 — Operational Interface

Construir a interface para ingestão de levantamentos, execução controlada, visualização de detecções e mapas, comparação temporal/espacial, indicadores e relatórios exportáveis.

## Gates transversais

- Sem downloads de datasets/pesos ou treinamento/inferência sem autorização explícita.
- Sem promoção de métrica experimental a capacidade operacional sem validação.
- Sem conversão pixel → distância física sem escala/transformação válida.
- Testes determinísticos e validator oficial em cada fase.
- Validação manual no Colab; não adicionar GitHub Actions.
- Cada fase trabalha em branch própria; integração à `main` exige revisão, evidência e autorização.
