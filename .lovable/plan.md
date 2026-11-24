# Conferência completa do pacote AnimeNexus

## O que será feito

- Concluir a correspondência das 37 imagens do RAR com os recortes usados no jogo, sem duplicar animações iguais.
- Adicionar a tela de seleção com Luffy destacado, que está ausente, e usar também a tela com Naruto destacado.
- Trocar a arte da seleção conforme Naruto, Goku ou Luffy é escolhido; manter a tela geral para o Goku.
- Revisar as regras pedidas no texto: cargas e tamanhos do Goku, mortes com destransformação, Rasengan, Rasenshuriken, golpes do Luffy, void, três vidas, revanche, mapa solo e controles móveis.
- Corrigir qualquer divergência encontrada durante os testes, limitada ao escopo do pacote e do pedido original.

## Verificação

- Rodar os testes existentes e acrescentar testes para as regras que forem alteradas.
- Abrir o menu, escolher os três personagens e entrar no modo solo na prévia.
- Conferir as três artes de seleção e os controles em tela horizontal de celular.
- Testar a conexão online com duas janelas automatizadas e, se possível, o fluxo de revanche.

## Detalhes técnicos

- Preservar os metadados gerados e as animações que já funcionam.
- Enviar somente as novas telas como arquivos de mídia com endereços permanentes.
- Manter Phaser fora da renderização do servidor e usar os pontos de apoio compartilhados dos sprites.
