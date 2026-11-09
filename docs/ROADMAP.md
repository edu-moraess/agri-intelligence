# Roadmap

## Fase 0 — Fundação
Concluída neste repositório: contratos, arquitetura, governança e validação estrutural.

## Fase 1 — Data engine
Fundação implementada nesta branch: contratos de dataset, inventário local com SHA-256 e cabeçalhos de imagem, manifesto JSON, auditoria de bounding boxes e verificações conservadoras de leakage. O MSDD permanece `BLOCKED` até a verificação da licença da distribuição, direitos de redistribuição, proveniência da conversão Parquet e splits originais. Consulte `artifacts/msdd_candidate_audit.json`.

## Fase 2 — Crop perception
Adicionar adaptadores de detecção/segmentação, tiled inference e avaliação em espaço de imagem.

## Fase 3 — Geometria agrícola
Reconstruir linhas quando suportado pelos dados, estimar espaçamento com referência válida e separar gap observado de falha confirmada.

## Fases 4–6
Geoespacial, multimodalidade e suporte à decisão somente após validação científica de cada etapa.
