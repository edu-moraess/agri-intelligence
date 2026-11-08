# ADR-0003: Guardas para medição espacial

- **Problema:** pixels não são metros sem escala ou transformação.
- **Decisão:** exigir GSD ou transformação validada antes de distância métrica.
- **Alternativas:** assumir escala fixa; rejeitada por produzir falsa precisão.
- **Validação:** testes cobrem erro quando a referência está ausente.
