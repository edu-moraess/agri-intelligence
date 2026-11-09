# ARQTECH AGRI INTELLIGENCE

Fundação de engenharia para uma plataforma modular de inteligência agrícola, sob a identidade ArqTech Labs. O primeiro domínio operacional é **Crop Intelligence — Planting Quality & Emergence Monitoring**.

## Objetivo

Transformar imagens e ortofotos agrícolas em evidências visuais e espaciais rastreáveis para apoiar a análise da qualidade do plantio: detecção de plântulas/plantas, reconstrução de linhas, espaçamento e identificação de lacunas visuais. Interpretações agronômicas e recomendações exigem validação própria e não são inferidas automaticamente.

## Estado do projeto

| Fase | Escopo | Estado |
|---|---|---|
| 0 — Foundation & Governance | Arquitetura, contratos, governança e validação estrutural | Concluída e integrada |
| 1 — Data Engine | Proveniência, licenças, inventário, manifestos, auditoria de anotações, leakage e contratos espaciais | Concluída e integrada |
| 2 — Crop Vision Engine | Image I/O, tiling, detecção, pós-processamento e avaliação em espaço de imagem | Planejamento documentado; implementação não iniciada |
| 3 — Agricultural Geometry | Linhas, espaçamento e lacunas observadas | Planejada |
| 4 — Geospatial Intelligence | Ortoimagens, CRS, transformações e exportações GIS | Planejada |
| 5 — Multimodal Intelligence | Integração futura de sensores e fontes complementares | Planejada |
| 6 — Validated Decision Support | Indicadores e suporte à decisão validados | Planejada |

## Princípios

- Separar observações, predições, medições derivadas, estimativas estatísticas, interpretações agronômicas e recomendações.
- Preservar proveniência, método, incerteza e referência espacial.
- Nunca converter pixels em distância física sem escala ou transformação válida.
- Tratar lacunas visuais como evidência para investigação, não como falha agronômica confirmada.
- Manter contratos independentes de YOLO, SAHI, sensor, cultura ou dataset.
- Não declarar desempenho sem dados licenciados, ground truth auditado e protocolo reproduzível.

## Governança de dados

A Fase 1 está integrada à `main` no commit `14a0435a0d28673dd98c6934b66a081bfdf76820`. O MSDD permanece **BLOCKED** enquanto a licença da distribuição candidata e os direitos de uso, redistribuição e atribuição não forem verificados. Não baixar datasets ou pesos, nem iniciar treinamento/inferência, sem autorização explícita.

## Documentação principal

- [Arquitetura](docs/ARCHITECTURE.md)
- [Governança de dados](docs/DATA_GOVERNANCE.md)
- [Roadmap](docs/ROADMAP.md)
- [Plano técnico da Fase 2 — Crop Vision Engine](docs/PHASE_2_VISION_PLAN.md)
- [Revisão arquitetural](docs/ARCHITECTURE_REVIEW.md)

## Validação manual

O projeto adota validação manual no Colab. Não adicionar GitHub Actions.

Comandos documentados na base atual:

```bash
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/validate_environment.py
PYTHONPATH=src python3 scripts/audit_dataset.py --help
```

Execute os comandos no SHA/branch em avaliação e registre as saídas. Não declarar aprovação com base apenas em documentação ou execução anterior.
