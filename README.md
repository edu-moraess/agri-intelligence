# ARQTECH AGRI INTELLIGENCE

Fundação de engenharia para uma plataforma modular de inteligência agrícola, sob a identidade ArqTech Labs. O primeiro domínio operacional planejado é **Crop Intelligence — Planting Quality & Emergence Monitoring**.

Esta versão implementa somente a Fase 0: arquitetura, contratos, governança, documentação e validação estrutural. Não contém modelos treinados, datasets, pesos, inferência ou métricas de desempenho.

## Princípios

- Separar observações diretas, predições, medições derivadas, estimativas estatísticas, interpretações agronômicas e recomendações.
- Preservar proveniência, método, incerteza e referência espacial.
- Nunca converter pixel em distância física sem escala ou transformação válida.
- Tratar lacunas visuais como evidência para investigação, não como falha agronômica confirmada.
- Manter contratos independentes de YOLO, SAHI, sensor, cultura ou dataset.

## Estado atual

| Item | Estado |
|---|---|
| Repositório e branch principal | Implementado |
| Pacote Python tipado | Implementado |
| Contratos de observação e predição | Implementado |
| Guardas de geometria e CRS | Fundação explícita |
| Auditoria de dataset | Interface sem download |
| Modelos e inferência | Planejados, não implementados |
| Geoprocessamento avançado | Planejado, não implementado |

## Uso local

```bash
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/validate_environment.py
PYTHONPATH=src python3 scripts/audit_dataset.py --help
```

Nenhum comando da Fase 0 baixa dados, pesos ou dependências externas.

## Roadmap

0. Fundação e governança (este repositório)
1. Data engine: descoberta, proveniência e validação de anotações
2. Crop perception: detecção/segmentação e avaliação em espaço de imagem
3. Geometria agrícola: linhas, espaçamento e lacunas
4. Inteligência geoespacial: ortomosaicos, CRS e exportações GIS
5. Inteligência multimodal
6. Suporte à decisão agrícola validado

Consulte [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/ARCHITECTURE_REVIEW.md`](docs/ARCHITECTURE_REVIEW.md) e [`docs/ROADMAP.md`](docs/ROADMAP.md).
