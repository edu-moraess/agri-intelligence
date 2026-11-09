# Plano técnico — Fase 2: Crop Vision Engine

**Status:** execução incremental; 2.0–2.3 integradas; 2.4 em implementação.  
**Branch de planejamento:** `docs/phase-2-vision-plan`  
**Base:** `14a0435a0d28673dd98c6934b66a081bfdf76820`  
**Escopo:** percepção visual em espaço de imagem para plântulas/plantas, com contratos independentes de modelo e dataset.

## 1. Objetivo

Construir um motor de percepção visual reproduzível que receba imagens agrícolas, produza predições tipadas e rastreáveis e permita avaliar o desempenho em um protocolo sem vazamento entre unidades de aquisição.

A primeira entrega será **detecção de objetos em espaço de imagem**. Segmentação, reconstrução de linhas e medições físicas não fazem parte do primeiro incremento: dependem de máscaras ou de validação espacial/geométrica própria.

## 2. Estado conhecido e restrições

- A Fase 0 está concluída e integrada à `main`.
- A Fase 1 (Data Engine) está concluída e integrada à `main` no commit `14a0435a0d28673dd98c6934b66a081bfdf76820`.
- O Data Engine fornece contratos de proveniência, licenças, inventário, manifestos, auditoria de bounding boxes, leakage e metadados espaciais.
- O README da base consultada ainda contém uma descrição antiga da Fase 0; esta documentação corrige o roadmap, sem alterar os contratos existentes.
- O MSDD permanece **BLOCKED**: a distribuição candidata declara licença `unknown`; direitos de redistribuição, uso comercial, atribuição e equivalência da conversão Parquet ainda não foram comprovados.
- Nenhum dataset será baixado, adotado ou redistribuído nesta fase sem aprovação explícita e evidência documental dos direitos.
- Nenhum peso será baixado e nenhum treinamento/inferência será iniciado durante o planejamento.

## 3. Princípios de engenharia

1. **Model-agnostic core:** o núcleo não importa YOLO, Ultralytics, SAHI, PyTorch ou outro framework.
2. **Image-space first:** coordenadas de saída são explicitamente pixels da imagem de origem ou do tile; não são coordenadas geográficas.
3. **Evidence separation:** ground truth, predição, observação derivada e avaliação permanecem objetos distintos.
4. **Provenance:** cada execução identifica imagem, manifesto/dataset, versão do adaptador, configuração e artefato de modelo por identificador/checksum quando aplicável.
5. **No silent assumptions:** classes, convenção de caixa, canais, normalização, limiar e política de tile são declarados.
6. **No fabricated performance:** métricas só podem ser reportadas sobre dados licenciados, splits aprovados e ground truth auditado.
7. **Optional dependencies:** frameworks de modelo e bibliotecas de imagem entram como extras opcionais após um caso de uso aprovado.
8. **Manual validation:** testes e gate executados manualmente no Colab; não criar GitHub Actions.

## 4. Escopo modular proposto

Os nomes abaixo são propostas de organização, não afirmações sobre arquivos já existentes. Antes de implementar, conferir os módulos atuais e estender contratos existentes em vez de duplicá-los.

### 4.1 Image I/O e normalização

Responsabilidades:
- validar formato, dimensões, canais, dtype e orientação;
- preservar identidade e checksum do arquivo original;
- explicitar conversões de cor e normalização;
- rejeitar arquivos truncados/corrompidos com erro tipado;
- não alterar silenciosamente a imagem-fonte.

### 4.2 Tiling

Responsabilidades:
- gerar tiles com tamanho, stride e overlap explícitos;
- registrar índice, origem (x, y), largura e altura de cada tile;
- tratar bordas sem perder pixels nem produzir coordenadas fora da imagem;
- manter transformação tile → imagem original;
- definir política de deduplicação de detecções sobrepostas como configuração explícita.

SAHI pode ser avaliado como adaptador opcional, não como dependência do domínio. Tiling não realiza georreferenciamento.

### 4.3 Detector adapter

Contrato conceitual:
- entrada: imagem/tile validado e configuração declarada;
- saída: zero ou mais detecções com classe, score finito em [0, 1], caixa em convenção declarada e referência à imagem/tile;
- metadados: nome/versão do backend, versão/configuração do modelo, checksum do peso quando aplicável;
- erros: dependência ausente, modelo indisponível, entrada inválida e falha de inferência devem ser distinguíveis.

O adaptador não deve decidir semântica agronômica nem converter pixels em unidades físicas.

### 4.4 Prediction post-processing

Responsabilidades:
- validar scores, classes e caixas;
- converter coordenadas de tile para imagem original;
- recortar caixas nos limites da imagem conforme política declarada;
- deduplicar predições sobrepostas com método/limiar explícitos;
- preservar a relação entre predição original e predição pós-processada.

### 4.5 Evaluation

Responsabilidades:
- parear predições e ground truth por imagem e classe;
- calcular IoU e métricas de detecção com protocolo documentado;
- reportar precision, recall, AP por classe e agregados quando o volume de dados permitir;
- registrar limiares de confiança, IoU, regra de matching e versão do avaliador;
- produzir resultados reproduzíveis em JSON/CSV sem misturar métricas de treino e teste.

Métricas candidatas: precision, recall, AP@IoU=0.50 e mAP@[0.50:0.95]. A escolha final e a forma de agregação serão congeladas antes da avaliação de benchmark. Não definir metas numéricas de desempenho antes de conhecer dataset, classes, resolução e protocolo.

### 4.6 Run manifest e relatórios

Cada execução deve registrar:
- identificador e checksum das imagens/manifesto;
- split e grupo de aquisição;
- backend, modelo e versão;
- configuração de preprocessing/tiling/post-processing;
- ambiente e versões das dependências;
- métricas, contagens e avisos;
- limitações conhecidas.

## 5. Contratos conceituais mínimos

Os tipos abaixo descrevem semântica requerida; não determinam nomes finais de classes Python:

- `ImageRecord`: ID estável, caminho relativo, checksum, largura, altura, canais e metadados de origem.
- `TileRecord`: ID, imagem-pai, janela em pixels da imagem original e dimensões do tile.
- `BoundingBox2D`: coordenadas numéricas finitas, convenção explícita (`xyxy` ou `xywh`), unidade `pixel` e referencial (`image` ou `tile`).
- `DetectionPrediction`: ID, imagem, classe, score, caixa, backend/modelo e referência à execução.
- `EvaluationConfig`: classes, IoU threshold(s), confidence threshold, matching policy e agregação.
- `EvaluationResult`: contagens TP/FP/FN, métricas por classe, agregados, suporte por classe e configuração utilizada.
- `VisionRunManifest`: entradas, versões, configurações, artefatos e resultados da execução.

Ground truth deve continuar separado de predições. Uma caixa em pixels não pode ser interpretada como posição física.

## 6. Estratégia de dados e protocolo experimental

Antes de qualquer benchmark:
1. selecionar uma fonte candidata e registrar URL/origem, mantenedor, versão e documentação;
2. verificar licença da fonte exata e direitos de uso pretendidos, inclusive uso comercial e redistribuição;
3. confirmar formato original, transformação/conversão, classes, convenção de anotação e integridade;
4. auditar qualidade das caixas e imagens com o Data Engine;
5. identificar grupos de aquisição (fazenda/talhão, campanha, voo, vídeo ou sequência);
6. criar splits por grupos, não por imagens aleatórias correlacionadas;
7. verificar duplicatas e near-duplicates quando houver ferramenta/protocolo aprovado;
8. congelar protocolo e registrar limitações antes de executar avaliação.

**MSDD não é fonte aprovada neste momento.** A análise documental de licença é um bloqueio explícito, não uma tarefa que o código possa contornar.

## 7. Plano de implementação incremental

### 2.0 — Readiness e contratos
- auditar os contratos e módulos existentes da Fase 1;
- fechar fonte de dados/licença e esquema de classes;
- definir protocolo de splits e métricas;
- aprovar os contratos de imagem, tile, detecção e execução.

**Saída:** decisão documentada de prontidão. Nenhum modelo executado.

### 2.1 — Image I/O e tiling determinístico
- implementar leitura/validação sem mutação da fonte;
- implementar tiles e mapeamento de coordenadas;
- cobrir bordas, overlap, dimensões ímpares e imagens menores que o tile.

**Saída:** tiles determinísticos e transformação tile → imagem testada.

### 2.2 — Detector adapter mínimo
- implementar protocolo independente de backend;
- criar fake detector para testes unitários;
- integrar um backend real somente após aprovação de dados, dependências e pesos.

**Saída:** predições tipadas e rastreáveis; fake backend não conta como evidência de desempenho.

### 2.3 — Post-processing e avaliação
- mapear caixas para imagem original;
- testar clipping e deduplicação;
- implementar matching e métricas;
- validar métricas em fixtures sintéticas pequenas com resultados calculáveis à mão.

**Saída:** avaliador determinístico com testes de regressão.

### 2.4 — Benchmark controlado
- executar somente sobre dataset aprovado;
- congelar ambiente, split, configuração e artefatos;
- reportar métricas por classe e limitações;
- não promover resultado experimental a capacidade operacional sem validação independente.

**Saída:** relatório reproduzível, ou bloqueio documentado se os dados não forem aprovados.

## 8. Plano de testes

### Unitários
- imagem inválida, dimensões/canais/dtype inesperados;
- caixas degeneradas, negativas, não finitas e fora dos limites;
- scores fora de [0, 1] e classes desconhecidas;
- tiles sem lacunas/duplicação indevida e mapeamento de coordenadas;
- caixas que cruzam bordas e tiles sobrepostos;
- matching one-to-one, IoU limítrofe, classe incompatível;
- casos vazios: sem predições, sem ground truth e classe sem suporte;
- métricas com resultados de referência calculados manualmente;
- serialização determinística e round-trip dos manifests.

### Integração
- fluxo image → tiles → fake detector → post-processing → evaluation;
- preservação de IDs e proveniência;
- compatibilidade com contratos do Data Engine;
- ausência de dependência obrigatória de framework de ML;
- regressão integral dos testes já existentes.

### Adversariais
- imagens muito grandes ou dimensões extremas sob limites configuráveis;
- tile size/stride inválidos;
- NaN/Inf em caixas e scores;
- IDs duplicados e referências ausentes;
- paths externos e symlinks conforme política da Fase 1;
- artefatos ausentes, checksum divergente e versões incompatíveis.

## 9. Quality Gate da Fase 2

A fase só poderá ser considerada concluída quando:
- todos os testes unitários e de integração passarem;
- o validator oficial passar no SHA exato avaliado;
- não houver regressão nos testes da Fase 0/1;
- os contratos forem documentados e independentes do backend;
- dados, licença, classes, splits e protocolo estiverem aprovados;
- a execução real tiver manifesto e artefatos rastreáveis;
- métricas forem reproduzíveis e acompanhadas de limitações;
- nenhuma métrica for apresentada sem ground truth e split válidos.

Se a licença ou os dados permanecerem bloqueados, 2.0–2.3 podem avançar com fixtures sintéticas e fake backend, mas 2.4 fica bloqueada. Testes sintéticos validam software, não desempenho agronômico.

## 10. Não objetivos

- treinamento automático ou fine-tuning;
- download automático de datasets, pesos ou modelos;
- adoção automática do MSDD;
- segmentação sem máscaras licenciadas e auditadas;
- reconstrução de linhas, distância física ou georreferenciamento nesta fase;
- diagnóstico agronômico de falha de emergência;
- recomendação de replantio ou intervenção;
- pipeline em produção, inferência em edge ou fusão multimodal;
- GitHub Actions ou CI novo.

## 11. Riscos e decisões pendentes

| Tema | Situação | Regra |
|---|---|---|
| Licença MSDD | Bloqueada | Não baixar/adotar até comprovação |
| Fonte inicial alternativa | Em aberto | Comparar fontes e direitos antes da escolha |
| Classes iniciais | Dependem da fonte | Não fixar taxonomia sem examinar anotação |
| Resolução/GSD | Pode variar | Avaliar em pixels; não inferir distância física |
| Segmentação | Sem máscaras aprovadas | Fora do primeiro incremento |
| Deduplicação de tiles | Decisão técnica pendente | Comparar NMS/WBF ou regra simples com testes |
| Limiar de desempenho | Não definido | Definir após baseline e protocolo |

## 12. Critério de autorização para implementação

A implementação de código da Fase 2 deve começar em branch própria, após revisão deste plano e confirmação de que:
- o escopo de 2.0–2.3 está aceito;
- os módulos existentes foram auditados para evitar duplicação;
- dependências continuam mínimas e opcionais;
- não haverá downloads, treinamento ou inferência sem autorização específica.

A aprovação deste plano não autoriza adoção de dataset, aquisição de pesos, treinamento, inferência real ou merge na `main`.
