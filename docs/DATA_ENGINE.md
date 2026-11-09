# Phase 1 — Data Engine

Esta fase adiciona a primeira camada operacional para inventariar e auditar datasets locais. O núcleo não baixa dados, não instala dependências, não desserializa formatos não confiáveis e não executa modelos.

## Componentes

- `data/contracts.py`: contratos tipados, estados de licença e consistência entre assets e splits.
- `data/inventory.py`: SHA-256 em chunks e leitura limitada de cabeçalhos PNG/JPEG. Caminhos relativos são resolvidos sob a raiz selecionada; symlinks são rejeitados ou ignorados na descoberta recursiva.
- `data/annotations.py`: validação de IDs, referências de imagem, classes, dimensões e bounding boxes com valores numéricos finitos.
- `data/leakage.py`: hashes exatos, grupos de origem e integridade das referências dos splits.
- `data/manifest.py`: manifesto JSON determinístico gravado por substituição atômica no mesmo diretório.

## Política de adoção e licença

O estado `verified` identifica uma licença revisada, mas não basta isoladamente para liberar adoção. O gate também exige confirmação explícita de direitos de redistribuição, uso comercial e revisão das obrigações de atribuição. Projetos com outros requisitos devem ampliar a política antes de liberar datasets.

A aprovação técnica do manifesto não equivale a autorização jurídica. A revisão deve se referir à distribuição exata e à versão efetivamente utilizada.

## MSDD: estado de evidência

O artigo publicado em *Agronomy* informa 3.152 imagens, 163.921 objetos, classes single/double/triple e aquisição UAV entre 2019 e 2022 em Columbia, Missouri [1]. A página da distribuição `Project-AgML/maize_seedling_msdd_detection` declara licença `unknown`, apresenta conversão automática para Parquet e campos como `flight_date`, `source_video`, `split` e `objects` [2].

Por isso, o MSDD permanece **BLOCKED para adoção**. O artigo não comprova direitos da distribuição Parquet, e nenhuma licença de outra cópia foi transferida. Nenhum arquivo do dataset foi baixado.

## Limitações conhecidas

- A leitura de cabeçalho não substitui decodificação integral nem validação semântica da imagem.
- Hash exato não detecta imagens quase duplicadas.
- Grupos compartilhados entre splits indicam risco, não provam leakage.
- Os contratos espaciais validam metadados, mas não aplicam transformações GIS.
- O gate de licença é uma política técnica conservadora; não substitui revisão jurídica.
- A gravação atômica reduz risco de arquivo parcial, mas não elimina todos os riscos de concorrência ou alterações maliciosas do diretório.

## Uso

```bash
PYTHONPATH=src python3 scripts/build_manifest.py /caminho/local --dataset-id exemplo --output artifacts/example_manifest.json
```

O resultado continua com licença `pending_review` até que origem, direitos de redistribuição, uso comercial e atribuição sejam revisados com evidências adequadas.

## Referências

[1]: https://doi.org/10.3390/agronomy16161605 "Maize Seedling Detection Dataset (MSDD), Agronomy"
[2]: https://huggingface.co/datasets/Project-AgML/maize_seedling_msdd_detection "Project-AgML MSDD dataset card"
