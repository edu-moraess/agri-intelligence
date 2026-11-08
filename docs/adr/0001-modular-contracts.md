# ADR-0001: Contratos modulares agnósticos ao modelo

- **Problema:** acoplar o núcleo a YOLO/SAHI impediria evolução para outros modelos e sensores.
- **Decisão:** usar contratos tipados de evidência e adaptadores de percepção.
- **Alternativas:** implementar diretamente um detector; rejeitada por reduzir reversibilidade.
- **Riscos:** contratos podem evoluir; mitigação via testes de contrato e versionamento.
- **Validação:** importação, testes estruturais e revisão independente.
- **Reversibilidade:** alta; adaptadores futuros podem implementar as interfaces.
