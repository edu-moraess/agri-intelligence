# Protocolo de validação

## Fase 0

A Fase 0 usa verificações locais, determinísticas e reproduzíveis:

1. Importação do pacote.
2. Compilação sintática em memória de todos os Python elegíveis, sem gerar bytecode.
3. Testes unitários e estruturais por subprocesso com argumentos estruturados, diretório controlado e timeout.
4. Varredura conservadora de indicadores de credenciais, incluindo arquivos ocultos e atribuições suspeitas.
5. Varredura de artefatos proibidos, arquivos de ambiente, certificados/chaves, arquivos grandes e links simbólicos.

O scanner interpreta `configs/validation.yaml` para obter checks obrigatórios, limite de bytes, destino do relatório e exclusões. Percorre somente a raiz autorizada, ignora apenas diretórios de ferramenta explicitamente listados (`.git`, caches Python/teste/lint), não segue symlinks, trata binários sem decodificá-los e transforma erros de leitura em falhas. A leitura do secret scan ocorre em chunks, limitada a `max_scannable_bytes + 1`, detectando crescimento durante a leitura; arquivos maiores que o limite reprovam a verificação sem serem carregados integralmente.

## Estados

- `PASS`: verificação executada e aprovada.
- `FAIL`: verificação executada e reprovada, ou erro operacional detectado.
- `SKIP`: verificação obrigatória não foi executada.
- `WARNING`: limitação não bloqueante identificada.

O gate geral é `FAIL` se qualquer verificação obrigatória estiver em `FAIL` ou `SKIP`; `PASS_WITH_WARNINGS` é permitido apenas quando não houver falha/omissão obrigatória; `PASS` exige aprovação de todas as verificações obrigatórias.

## Relatório e limites

O JSON é gravado atomicamente somente no `report_path` configurado dentro do diretório `artifacts` da raiz autorizada. A raiz e o diretório `artifacts` são validados antes de qualquer arquivo temporário ser criado; destinos fora da raiz ou links simbólicos são recusados. O relatório não inclui valores encontrados, apenas nomes de indicadores e caminhos relativos.

A varredura por padrões reduz riscos óbvios, mas não é uma auditoria completa de secrets, análise profissional de vulnerabilidades ou garantia contra credenciais codificadas de forma não reconhecível. O diretório `.git` é excluído do worktree scan; análise de histórico e objetos Git exige ferramenta dedicada separada. Nenhuma verificação comprova desempenho agronômico, qualidade de dataset ou validade científica de métricas. A validação manual no Google Colab e revisão independente continuam pendentes.
