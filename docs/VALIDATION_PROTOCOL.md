# Protocolo de validação

## Fase 0

A Fase 0 usa verificações determinísticas e locais:

1. Importação do pacote.
2. Compilação sintática de todos os arquivos Python no diretório de trabalho, sem gerar bytecode.
3. Testes unitários e estruturais.
4. Varredura conservadora de indicadores de credenciais.
5. Varredura de artefatos proibidos, como pesos, chaves privadas e arquivos de ambiente.

O compilador em memória verifica sintaxe; não substitui testes de execução ou análise estática. A varredura de segredos por padrões reduz riscos óbvios, mas não substitui uma ferramenta dedicada de secret scanning.

PASS exige que todas as verificações obrigatórias tenham sido executadas e aprovadas. FAIL aplica-se a qualquer falha ou verificação obrigatória não executada. Limitações não bloqueantes devem ser registradas separadamente no relatório.

## Limites

Nenhuma verificação desta fase comprova desempenho agronômico, qualidade de dataset, precisão de detecção ou validade científica de métricas. Esses itens dependem de dados e protocolos próprios nas fases seguintes.
