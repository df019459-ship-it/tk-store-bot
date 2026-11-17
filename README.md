# TK STORE — primeira versão

Painel Discord com /start, /pedido e /status. O responsável registra um pedido e confere o Pix antes de clicar em Confirmar pagamento. A mensagem será: “✅ Compra efetuada com sucesso! Aguarde sua ativação.”

## Configurar
1. No https://discord.com/developers/applications crie uma aplicação chamada TK STORE e obtenha seu token na seção Bot. Não compartilhe o token em conversas nem no GitHub.
2. Configure a instalação no servidor com os escopos bot e applications.commands. Conceda somente Ver canal, Enviar mensagens e Inserir links/embeds no canal de pedidos. Não precisa de Administrador nem Message Content Intent.
3. Crie um canal privado acessível somente ao responsável e ao bot. Ative o modo desenvolvedor do Discord para copiar os IDs do servidor, canal e usuário responsável.
4. Use Python 3.11 ou superior e instale: pip install -r requirements.txt
5. Cadastre as variáveis de .env.example no ambiente da hospedagem. O arquivo não é carregado automaticamente. Execute: python bot.py
6. Use um processo de trabalho continuamente ativo e um disco persistente para DATABASE_PATH. Não execute duas instâncias simultâneas. Faça backup do banco, que contém telefones de clientes.
7. No canal configurado execute /start. Depois /pedido telefone:55... produto:... valor:18,00.

## WhatsApp: integração pendente
Este projeto NÃO conecta por pareamento, não abre outra sessão e não altera a Zumy. Não inclui a API da Zumy, pois ela ainda não foi identificada. Para enviar mensagens pelo mesmo número, é necessário adaptar o backend que já mantém a conexão ou confirmar um transporte compatível. Não desconecte nem refaça o pareamento existente para instalar esta base.

WHATSAPP_ADAPTER_URL é um endpoint HTTPS SEU, implementado no backend existente, não uma URL nativa presumida da Zumy. Contrato esperado:
- POST com Authorization: Bearer <segredo> e Idempotency-Key: <id do pedido>.
- JSON: {"order_id":"...", "to":"55...", "text":"..."}.
- Resposta HTTP 200: {"status":"sent", "message_id":"id real retornado pelo transporte"} somente após aceitação pelo WhatsApp.
- O adaptador deve autenticar, validar destinatário e deduplicar duravelmente por order_id antes de enviar. Não redirecionar requisições com credenciais. Ele deve tratar reconexões e eventuais confirmações do provedor.
- Sem adaptador, o botão informa que a integração está pendente e não altera o pedido.
- Em falha ou interrupção durante envio, o pedido fica uncertain, sem nova tentativa automática. Conferir manualmente no provedor antes de reconciliar esse estado; não há promessa de entrega exatamente uma vez entre sistemas.

## Escopo desta versão
Pagamento manual. Sem acesso a banco, sem cobrança Pix, sem ativação automática, sem sincronização com a loja e sem captura automática de compras no WhatsApp. /pedido registra manualmente a compra. Catálogo e entrada automática de pedidos são etapas posteriores, após definir o transporte da Zumy. Não foram incluídos preços com duração ou promoção ainda não confirmadas.

## Validação
Sintaxe Python verificada localmente. A operação real depende de configurar a aplicação Discord e o adaptador WhatsApp. Não testado com contas reais; requer teste completo antes de usar com clientes.
