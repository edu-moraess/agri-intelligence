# ADR-0006: Contratos explícitos de percepção em espaço de imagem

- **Status:** proposta implementada em branch para validação.
- **Contexto:** o contrato anterior `ImageFrame` continha apenas ID e dimensões, enquanto `PerceptionModel` retornava o `Prediction` genérico do core. Isso não identificava pixels, caixas, referencial, tile ou execução.
- **Decisão:**
  1. manter `Prediction` genérico e criar `DetectionPrediction` específico;
  2. tornar o payload de pixels opaco (`object`) para não exigir NumPy/Pillow/PyTorch no core;
  3. declarar metadados de imagem (dimensões, canais, dtype, color space e SHA-256 da fonte);
  4. padronizar caixas internas como XYXY em pixels, com frame e espaço (`image` ou `tile`) explícitos;
  5. representar a janela do tile em coordenadas da imagem original e fornecer transformação determinística tile → imagem;
  6. vincular predições a classe, score, modelo, versão e run ID;
  7. exigir checksum de configuração e manifesto de entrada em `VisionRunManifest`;
  8. manter adaptadores e bibliotecas de visão como dependências opcionais.
- **Não objetivos:** decodificação de imagem, geração de tiles, NMS/WBF, inferência real, treinamento, métricas e georreferenciamento.
- **Consequências:** os contratos podem ser testados com payloads sintéticos; adapters futuros devem preservar o payload como somente leitura e respeitar o referencial declarado.
- **Riscos/pendências:** `object` não valida layout de memória nem imutabilidade do buffer; o decoder/adaptador deverá validar shape/dtype real. O contrato de classe continua como identificador string até a fonte de dados e sua taxonomia serem aprovadas.
- **Validação requerida:** testes de contrato, regressão completa e validator oficial executados manualmente no Colab sobre o SHA exato.
