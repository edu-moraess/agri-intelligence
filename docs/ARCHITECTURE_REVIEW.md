# Architecture Council Review — Fase 0

## Método

Os oito conselhos do mandato foram representados em uma revisão consolidada: Arquitetura; IA e Visão Computacional; Agronomia; Geoespacial e Sensoriamento Remoto; Robótica e Sensores; Dados e Computação Científica; Qualidade, Segurança e Confiabilidade; Produto e Pesquisa. O documento registra decisões, divergências e itens que exigem validação futura.

## Acordos

1. Contratos de evidência devem ser agnósticos ao modelo e preservar proveniência.
2. Geometria física exige escala/transformação explícita e CRS rastreável.
3. Dataset, campanha, sensor, cultura e divisão experimental são metadados de primeira classe.
4. A Fase 0 deve permanecer sem dados, pesos, inferência e métricas.
5. Testes estruturais e documentação são gates obrigatórios.

## Riscos e conflitos

- O conselho agronômico alerta que uma lacuna visual não prova falha de estabelecimento; a visão computacional só pode fornecer evidência observada.
- O conselho geoespacial requer metadados que datasets iniciais podem não possuir; a decisão é permitir análise em espaço de imagem sem fabricar geografia.
- O conselho de plataforma prefere dependências mínimas, enquanto futuras análises exigirão bibliotecas científicas; adiar dependências até haver caso de uso verificável.
- O conselho de produto deseja indicadores de campo, mas o conselho científico rejeita qualquer indicador não calibrado e validado.

## Decisões

- **ADR-0001:** contratos tipados e camadas modulares, sem acoplamento a YOLO/SAHI.
- **ADR-0002:** separação entre observação, predição, medição e interpretação.
- **ADR-0003:** guardas contra medições físicas sem referência espacial.
- **ADR-0004:** validação manual e determinística na Fase 0; sem GitHub Actions.

## Questões em aberto

Qual será o primeiro formato de aquisição aceito? Qual política de licença regerá o MSDD se adotado? Como serão definidas unidades experimentais e splits por campanha? Qual limiar de erro espacial será agronomicamente útil?

## Recomendação do auditor

A fundação é adequada para avançar à Fase 1, condicionada a uma auditoria do MSDD antes de qualquer download ou adoção e à definição de um protocolo de validação com dados reais. Não é produção e não apresenta desempenho de modelo.
