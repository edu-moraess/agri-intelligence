# Phase 1 — Data Engine

Esta fase adiciona a primeira camada operacional para inventariar e auditar datasets locais. O núcleo não baixa dados, não instala dependências, não desserializa formatos não confiáveis e não executa modelos.

## Componentes

`data/contracts.py` define contratos tipados e independentes de frameworks para fonte, licença, versão, assets, schema de anotação, splits, aquisição, manifesto e resultado de auditoria. Uma licença que não esteja em `verified` mantém `adoption_blocked=True`.

`data/inventory.py` calcula SHA-256 em chunks e lê somente cabeçalhos PNG/JPEG quando possível. Dimensões e canais observados no arquivo são separados de metadados declarados; ausência permanece ausência.

`data/annotations.py` valida registros de bounding boxes sem assumir que máscaras existam. `data/leakage.py` identifica hashes repetidos entre splits e grupos de origem compartilhados entre splits. Grupo compartilhado é um alerta de possível leakage, não prova de leakage.

`data/manifest.py` serializa manifestos JSON determinísticos. `scripts/build_manifest.py` é um comando local; exige um diretório já existente e não possui código de download.

## MSDD: estado de evidência

O artigo publicado em *Agronomy* informa 3.152 imagens, 163.921 objetos, classes single/double/triple e aquisição UAV entre 2019 e 2022 em Columbia, Missouri [1]. A página da distribuição `Project-AgML/maize_seedling_msdd_detection` declara licença `unknown`, apresenta 3.15k linhas, conversão automática para Parquet e campos como `flight_date`, `source_video`, `split` e `objects` [2]. A página não comprova direitos de redistribuição, uso comercial ou que a conversão tenha a mesma licença do material original.

Por isso, o MSDD é um **candidato bloqueado para adoção**. O repositório registra evidência pública, mas não transfere automaticamente a licença do artigo ou de outra cópia. Nenhum arquivo do dataset foi baixado.

## Limites

O inventário local não valida conteúdo semântico que não esteja no arquivo, não transforma coordenadas geográficas, não infere CRS/GSD/affine transform e não prova qualidade agronômica. GSD sozinho pode não representar rotação, escala variável ou distorções de uma ortofoto. Uma auditoria futura deve registrar a proveniência dos splits originais antes de qualquer redivisão.

## Uso

```bash
PYTHONPATH=src python3 scripts/build_manifest.py /caminho/local --dataset-id exemplo --output artifacts/example_manifest.json
```

O resultado continuará com licença `pending_review` até que a origem e os direitos sejam revisados por evidência adequada.

## Referências

[1]: https://doi.org/10.3390/agronomy16161605 "Maize Seedling Detection Dataset (MSDD), Agronomy"
[2]: https://huggingface.co/datasets/Project-AgML/maize_seedling_msdd_detection "Project-AgML MSDD dataset card"
