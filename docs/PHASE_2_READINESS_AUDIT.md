# Auditoria de prontidão — Fase 2 (Crop Vision Engine)

**Data da auditoria:** 2026-11-09  
**Baseline auditada:** `main` — `5925a8c81442b99a20444faae90c22d312b12365`  
**Método:** leitura estática do tree, contratos, configuração, documentação e testes existentes.  
**Alterações no código:** nenhuma.  
**Downloads/instalações/treinamento/inferência:** nenhum.

## 1. Decisão executiva

**Estado geral: PARTIAL_READY — contratos sintéticos podem avançar; benchmark real permanece BLOCKED.**

A Fase 0 e a Fase 1 estão integradas. A base atual já contém contratos genéricos de evidência, validação de anotações, inventário, checksums, splits, leakage e metadados espaciais. A camada de percepção, porém, é somente um ponto de extensão mínimo.

A Fase 2 pode avançar com testes sintéticos e um fake detector, depois de formalizar os contratos de imagem, caixa, tile e execução. Não há fonte de dados real aprovada neste momento. O benchmark 2.4 fica bloqueado até seleção e verificação documental da fonte, direitos e protocolo.

## 2. Inventário técnico encontrado

| Área | Evidência existente | Lacuna para Fase 2 |
|---|---|---|
| Core | `core/contracts.py`: Provenance, Uncertainty, Observation, Prediction e DerivedMeasurement | Prediction.value é genérico; falta contrato explícito de detecção/caixa e referência à imagem/execução |
| Data Engine | `data/contracts.py`, `annotations.py`, `inventory.py`, `leakage.py`, `manifest.py` | Não há parser/adaptador de formatos de dataset nem decodificação integral de imagens |
| Perception | `perception/contracts.py`: ImageFrame e PerceptionModel | ImageFrame guarda apenas ID/largura/altura; não valida dimensões; predict recebe metadados, não pixels |
| Geometry | `geometry/coordinates.py`: espaços de coordenadas, GSD e distância | Não é necessário para detecção em espaço de imagem; preservar para fase espacial posterior |
| Geospatial | `geospatial/metadata.py` e `data/spatial.py` | Há dois contratos próximos de metadados espaciais; não duplicar nem ampliar isso na Fase 2 sem ADR |
| Evaluation | Pacote `evaluation` existe | Sem avaliador, matching, IoU, métricas ou testes de avaliação |
| Crop | Pacote `crop` existe | Sem taxonomia de cultura/classes aprovada |
| Configuração | `pyproject.toml` sem dependências de runtime; pytest é extra opcional | Nenhuma biblioteca de visão está instalada/declarada; manter backend opcional |
| Validação | `scripts/validate_environment.py` e testes unittest | Gate valida integridade estrutural, não qualidade visual nem desempenho agronômico |

### 2.1 Contrato de percepção atual

O contrato atual declara:
- `ImageFrame(image_id, width, height)`;
- `PerceptionModel.predict(frame) -> Sequence[Prediction]`.

Limitações verificadas:
- não recebe matriz/pixels ou um objeto de imagem carregado;
- não valida ID, largura ou altura;
- não define formato de pixel, canais, dtype ou orientação;
- não especifica classe, score, caixa, convenção de coordenadas ou referencial;
- não vincula predições a tile, imagem original, modelo/configuração e run manifest.

**Decisão:** preservar `Prediction` como contrato genérico de evidência e definir contratos específicos de percepção/detecção, sem quebrar o core.

### 2.2 Data Engine disponível

A validação de anotações já suporta:
- `absolute_xywh`;
- `normalized_xywh`;
- `absolute_xyxy`;
- `normalized_xyxy`.

Também verifica dimensões, IDs, referências, classes, valores finitos, caixas degeneradas e limites da imagem. O inventário calcula SHA-256 e lê cabeçalhos PNG/JPEG de forma limitada. O leakage avalia hashes e grupos como campanha, voo e vídeo.

Isso é uma boa base de auditoria, mas não substitui decoder, parser de formato, avaliação de predições ou split experimental aprovado.

### 2.3 Pontos que exigem cuidado

1. `data/spatial.py` e `geospatial/metadata.py` têm responsabilidades parcialmente sobrepostas. Não expandir ambos sem consolidar a decisão arquitetural.
2. `configs/default.yaml` declara `phase: 0`. É metadado legado/ambíguo e precisa de decisão própria; não foi alterado.
3. O validator ainda informa `phase: 0` e usa `phase_0_validation_report.json`. Isso é o gate herdado da Fase 0 e já foi utilizado para validar a Fase 1; não alterar automaticamente como se fosse a fase atual do produto.
4. `requirements.txt` descreve a Fase 0 sem dependências externas. O núcleo atual é independente de framework de ML; preservar essa propriedade.
5. A documentação da Fase 0 ainda tem algumas frases históricas, como a recomendação de avançar à Fase 1. Não são bloqueio de execução da Fase 2, mas podem ser corrigidas em tarefa documental separada.

## 3. Pesquisa documental de fontes candidatas

A pesquisa foi feita somente em páginas e metadados públicos. Nenhum arquivo foi baixado. A licença exibida por um catálogo ou uma distribuição derivada não substitui a verificação da fonte exata e dos arquivos efetivamente utilizados.

| Fonte | Evidência pública | Adequação | Situação |
|---|---|---|---|
| MatchPlant / Zenodo 14856123 | 27 imagens UAV e 8.701 caixas na distribuição AgML; dados associados ao pipeline de detecção de milho; catálogo NLM indica CC BY 4.0 | Melhor correspondência temática inicial para teste de detecção em imagens UAV, mas conjunto pequeno e de domínio limitado | **Candidato prioritário, ainda não aprovado** |
| Bumbaca / Zenodo 15235602 | 3 ortomosaicos, tiles, ground truth e caixas de método manual; aproximadamente 6,5 GB | Forte candidato para avaliar tiles, referência espacial e projeção | **Licença não confirmada na página primária consultada; bloqueado** |
| MaizeHorizon / Zenodo 21775699 | 5.979 frames, 28 clips, rótulos YOLO, split por clip; CC BY 4.0 | Útil para teste complementar de objetos pequenos e avaliação com região ignore; câmera frontal em robô terrestre, não drone | **Complementar; não representa domínio UAV** |
| MSDD / distribuição Hugging Face | 3.152 imagens e 163.921 caixas em três classes; distribuição candidata declara licença `unknown` | Forte adequação para plântulas de milho em UAV | **BLOCKED — manter bloqueado** |
| MTC_UAV / OPIA | 306 imagens UAV de milho e 70.870 anotações pontuais de pendões; uso acadêmico gratuito, uso comercial requer licença | Não é plântula nem bounding-box convencional; não serve como dataset comercial sem negociação | **Não selecionar para o primeiro benchmark** |
| Canola seedling / Zenodo 11055599 | 431 imagens aéreas e 77.059 caixas de plântulas de canola | Pode apoiar avaliação futura de transferência entre culturas | **Licença não confirmada; fora do primeiro benchmark de milho** |

### Referências documentais

- MatchPlant dataset: https://zenodo.org/records/14856123
- MatchPlant dataset catalog record (metadata reports CC BY 4.0): https://datasetcatalog.nlm.nih.gov/dataset?q=0002116933
- MatchPlant AgML dataset card: https://huggingface.co/datasets/Project-AgML/maize_individual_detection
- Bumbaca dataset: https://zenodo.org/records/15235602
- MaizeHorizon dataset and license: https://zenodo.org/records/21775699
- MSDD candidate: https://huggingface.co/datasets/Project-AgML/maize_seedling_msdd_detection
- MTC_UAV source and academic/commercial-use note: https://ngdc.cncb.ac.cn/opia/dataset/datasets?dataId=1
- Canola seedling dataset: https://zenodo.org/records/11055599

## 4. Recomendação de dados

### Candidato prioritário para diligência: MatchPlant

A distribuição associada ao MatchPlant apresenta 27 imagens e 8.701 bounding boxes de milho, derivadas de imagens UAV; a documentação do projeto descreve imagens não distorcidas, anotações COCO e projeção para ortomosaico. O catálogo NLM reporta CC BY 4.0 para o registro de dados.

Limitações:
- amostra pequena para generalização;
- domínio de aquisição restrito;
- licença deve ser confirmada diretamente no registro Zenodo e para cada artefato;
- verificar se a versão Hugging Face é semanticamente idêntica à versão Zenodo;
- confirmar classes, splits, grupos de aquisição e metadados espaciais antes de construir o manifesto;
- modelo pré-treinado é artefato separado e não está aprovado para uso.

**Status: candidato de diligência, não dataset adotado.**

### Candidato espacial secundário: Bumbaca

O registro contém ortomosaicos, tiles, ground truth em shapefiles e bounding boxes de método manual. A página primária consultada não expôs a licença; um índice secundário reporta CC BY, mas isso não basta para liberar uso. Manter bloqueado até confirmar no registro primário e nos arquivos.

### Complementar: MaizeHorizon

A página Zenodo declara dados CC BY 4.0 e descreve splits por clip e uma classe ignore. A câmera é frontal em robô terrestre, não UAV. Pode testar robustez e política de ignore, mas não deve ser usado como evidência de desempenho em ortofotos.

## 5. Contratos que precisam ser aprovados antes de codificar

1. **Image input:** identidade, dimensões, canais, dtype, orientação e acesso aos pixels sem mutar a fonte.
2. **Coordinate frame:** `image` ou `tile`, coordenadas em pixels e convenção explícita.
3. **BoundingBox2D:** valores finitos, dimensões positivas, clipping explícito e referencial identificado.
4. **DetectionPrediction:** imagem/tile, classe, score, caixa, backend/modelo e run ID.
5. **TileRecord:** origem, janela, dimensões, overlap e transformação tile → imagem original.
6. **Evaluation:** ground truth separado de predições; matching one-to-one, IoU, política ignore e suporte por classe.
7. **Run manifest:** checksums, versão de dados, split, configuração, ambiente e artefatos.

Não adicionar dependência de YOLO/Ultralytics/SAHI/PyTorch ao core. O primeiro backend de teste deve ser fake/sintético. Uma implementação de decoder real exigirá escolha e aprovação explícita de uma dependência opcional.

## 6. Protocolo experimental recomendado

- Usar splits por unidade de aquisição (campo, campanha, voo, vídeo ou clip), nunca divisão aleatória de tiles correlacionados.
- Preservar splits originais quando forem confiáveis e documentados; auditar vazamento antes de aceitar.
- Manter imagens, ground truth e predições separados.
- Definir classes apenas após inspecionar a anotação da fonte escolhida.
- Fixar IoU, matching, confidence threshold, política ignore e agregação antes do benchmark.
- Reportar AP por classe, precision/recall e contagens TP/FP/FN; não criar meta de desempenho antes do baseline.
- Não usar resultados de MaizeHorizon como substituto de validação UAV.
- Não misturar caixas de cluster single/double/triple com contagem de plantas individuais sem uma regra agronômica explícita.

## 7. Resultado da etapa 2.0

| Gate | Estado | Motivo |
|---|---|---|
| Auditoria dos módulos existentes | PASS | Contratos e lacunas identificados |
| Reuso sem duplicação | PASS_WITH_ACTIONS | Estender percepção; manter core genérico; evitar duplicar spatial |
| Estratégia de dependências | PASS | Core sem dependências; backend e decoder opcionais |
| Contratos de detecção aprovados | PENDING | Necessitam decisão final de semântica |
| Dataset real com licença aprovada | BLOCKED | Nenhuma fonte foi formalmente adotada |
| Classes e splits finais | BLOCKED | Dependem da fonte aprovada |
| Benchmark real | BLOCKED | Sem dados aprovados |

**Decisão final:** `PARTIAL_READY_FOR_SYNTHETIC_CONTRACTS`. A etapa 2.0 não está totalmente encerrada. É seguro prosseguir para a especificação e implementação de contratos com fixtures sintéticas após revisão; não é seguro iniciar benchmark real, baixar dataset ou usar pesos.

## 8. Próximas ações controladas

1. Confirmar a diligência documental do MatchPlant e, se necessário, solicitar esclarecimentos sobre direitos e redistribuição.
2. Aprovar a semântica dos contratos de imagem, tile e detecção.
3. Implementar contratos e tiling determinístico com fixtures sintéticas, em branch própria.
4. Validar manualmente no Colab com o conjunto completo de testes e validator oficial.
5. Só depois de aprovação explícita de fonte/licença, planejar aquisição local e benchmark.

Nenhuma ação deste relatório autoriza download, adoção, treinamento, inferência real ou merge automático.
