# Mesh3D — regras locais de engenharia

Estas regras complementam a referência transversal [Hashzin-0/Rules](https://github.com/Hashzin-0/Rules/blob/main/Rules.md). Em caso de divergência, siga a hierarquia definida na referência, as instruções de maior prioridade e os requisitos explícitos do usuário.

## Classificação baseada em evidências

Estado verificado após as primeiras implementações: o repositório contém uma aplicação React/Vite e uma API FastAPI, com catálogo de motores de reconstrução, execução de jobs, visualizador e endpoints de geração de mídia. A geração local usa workflows ComfyUI configurados pelo servidor; adaptadores opcionais para Pollinations, Cloudflare Workers AI e Gradio Spaces estão implementados, mas só são utilizáveis com configuração válida. A presença dos adaptadores não comprova disponibilidade remota, cota gratuita, licença dos modelos ou geração real bem-sucedida; essas condições devem ser verificadas por provedor.

## Regras gerais obrigatórias

- Inspecione README, regras locais, plano, critérios de aceite e arquivos próximos antes de editar.
- Não declare motores, benchmarks, saídas 3D, métricas ou testes como funcionais sem execução observável.
- Não use modelos 3D, scores, progresso, tempos ou fixtures sintéticos como se fossem resultados reais. Fixtures de teste devem ter origem, direitos e propósito documentados.
- Separe UI, contratos de domínio, API/orquestração, persistência e adaptadores de motores.
- Valide entradas no servidor; não confie em MIME/extensão fornecidos pelo cliente.
- Execute motores nativos/ML em workers isolados, com limites de CPU/GPU/RAM/disco/tempo, sem shell construído com dados do usuário.
- Preserve uploads originais; identifique cada artefato com hash, origem, versão de motor/checkpoint e relatório de validação.
- Mantenha código, pesos, checkpoints e dependências em registros de licença separados. Um motor bloqueado por licença deve permanecer desativado e mostrar a razão.
- Não invente propriedades da malha. Métricas indisponíveis devem ser omitidas ou marcadas como indisponíveis.
- Não exponha imagens, EXIF/GPS, caminhos internos, credenciais, tokens ou URLs assinadas em logs.
- Nunca altere arquivos .env* existentes sem autorização explícita. Documente somente nomes de variáveis em exemplos.
- Prefira mudanças pequenas, reversíveis e testáveis. Registre comandos executados e resultados reais.
- Para recursos visuais, garanta teclado, foco, contraste, estados de erro/vazio/carregamento e respeito a prefers-reduced-motion.

## Regras específicas aplicáveis quando confirmadas

- Edição/transformação de mídia: preservar original, separar processamento e validação, comparar entrada/saída e manter falhas por etapa.
- Editor/experiência 3D: alinhar controles e visualização, liberar geometria/texturas/renderers ao desmontar, limitar custo por frame e oferecer fallback sem WebGL.
- IA/modelos generativos: manter proveniência e licença de pesos; controlar timeout, concorrência, consumo de recursos e erros; nunca transformar indisponibilidade em saída fictícia.

Estas regras especializadas aplicam-se aos fluxos existentes quando confirmados pelo código. A existência de uma rota ou adaptador não comprova que o serviço upstream esteja acessível nem que a geração tenha sido validada.

## Critério de entrega

Toda etapa deve informar arquivos alterados, evidência de execução, testes realmente executados, limitações, bloqueios e próximo critério de aceite. “Implementado”, “validado”, “melhor motor” e “pronto para produção” exigem evidência específica.
