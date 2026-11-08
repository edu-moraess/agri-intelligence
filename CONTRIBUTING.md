# Contribuindo

Contribuições devem preservar limites de escopo, contratos tipados e rastreabilidade científica. Inclua testes determinísticos para mudanças de comportamento e atualize ADRs quando uma decisão arquitetural mudar.

Antes de abrir um pull request, execute `python3 -m unittest discover -s tests -v` e `PYTHONPATH=src python3 scripts/validate_environment.py`. Não inclua datasets, pesos, tokens ou notebooks com credenciais.
