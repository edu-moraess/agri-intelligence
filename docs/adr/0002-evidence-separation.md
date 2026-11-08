# ADR-0002: Separar evidência de interpretação

- **Problema:** uma detecção visual não comprova falha de emergência.
- **Decisão:** representar tipos distintos e exigir proveniência.
- **Alternativas:** retornar apenas indicadores finais; rejeitada por ocultar incerteza.
- **Validação:** contratos rejeitam identificadores vazios e preservam origem.
