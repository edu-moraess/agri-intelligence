# Arquitetura

## Objetivo

Fornecer contratos estáveis para transformar observações agrícolas visuais, espaciais, temporais e ambientais em inteligência rastreável, sem acoplar o núcleo a um detector, cultura, sensor ou fornecedor.

## Camadas

- `core`: identidade, proveniência, incerteza e tipos fundamentais.
- `data`: auditoria, versionamento e contratos de datasets.
- `perception`: contratos independentes de modelos de visão.
- `crop`: conceitos de cultura e indicadores futuros.
- `geometry`: espaços de coordenadas e medições com escala explícita.
- `geospatial`: metadados de CRS, resolução e transformações futuras.
- `sensors`/`fusion`: pontos de extensão para multimodalidade futura.
- `evaluation`: avaliação futura, sem métricas fabricadas.
- `reporting`: relatórios com proveniência e limitações.
- `interfaces`: protocolos de integração.

## Fluxo de evidência

`observation -> prediction -> derived measurement -> statistical estimate -> agronomic interpretation -> recommendation`

Cada etapa deve preservar a origem e declarar incerteza quando aplicável. Uma saída não pode ser promovida automaticamente a uma conclusão agronômica.

## Limites geoespaciais

O sistema distingue coordenadas de imagem, tile, ortomosaico, projetadas métricas e geográficas. A fundação rejeita distância física calculada diretamente de pixels sem `GroundSamplingDistance` ou transformação espacial validada. Dados sem georreferenciamento continuam úteis em espaço de imagem, mas não recebem coordenadas geográficas inventadas.

## Não implementado nesta fase

YOLO, SAHI, segmentação, Rasterio/GDAL/GeoPandas, armazenamento distribuído, inferência edge, fusão de sensores e recomendações operacionais são extensões futuras.
