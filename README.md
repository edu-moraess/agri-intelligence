# ARQTECH AGRI INTELLIGENCE

Fundação de engenharia para uma plataforma modular de inteligência agrícola, sob a identidade ArqTech Labs. O primeiro domínio operacional é **Crop Intelligence — Planting Quality & Emergence Monitoring**.

## Objetivo

Transformar imagens e ortofotos agrícolas em evidências visuais e espaciais rastreáveis para apoiar a análise da qualidade do plantio: detecção de plântulas/plantas, reconstrução de linhas, espaçamento e identificação de lacunas visuais. Interpretações agronômicas e recomendações exigem validação própria e não são inferidas automaticamente.

## Estado do projeto

| Fase | Escopo | Estado |
|---|---|---|
| 0 — Foundation & Governance | Arquitetura, contratos, governança e validação estrutural | Concluída e integrada |
| 1 — Data Engine | Proveniência, licenças, inventário, manifestos, auditoria de anotações, leakage e contratos espaciais | Concluída e integrada |
| 2 — Crop Vision Engine | Contratos, Image I/O, tiling, detector adapter, pós-processamento e avaliação em espaço de imagem | 2.0–2.3 integradas; 2.4 em implementação; experimento real pendente |
| 3 — Spatial Intelligence | Reconstrução de linhas, geometria, coordenadas, distâncias e mapas georreferenciados | Planejada |
| 4 — Agricultural Analytics | Estande, densidade, espaçamento, falhas observadas e indicadores agronômicos validados | Planejada |
| 5 — Operational Interface | Ingestão operacional, visualização, mapas, comparação de levantamentos e relatórios | Planejada |

### Estado detalhado da Fase 2

- 2.0 — Perception Contracts: integrada.
- 2.1 — Image I/O + Tiling: integrada.
- 2.2 — Detector Adapter: integrada.
- 2.3 — Image-space Postprocessing: integrada.
- 2.4 — Evaluation Framework: em implementação; validação com fixtures sintéticas.
- 2.5 — Primeiro experimento real: pendente de fonte licenciada, ground truth auditado e protocolo aprovado.

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
- [Auditoria de prontidão da Fase 2](docs/PHASE_2_READINESS_AUDIT.md)
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
