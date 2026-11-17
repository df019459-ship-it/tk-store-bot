"""TK STORE: painel Discord; transporte WhatsApp depende de adaptador existente."""
import asyncio
import os
import re
import sqlite3
import uuid
from decimal import Decimal, InvalidOperation
import aiohttp
import discord
from discord import app_commands

DB = os.getenv('DATABASE_PATH', 'orders.sqlite3')
GUILD = int(os.environ['DISCORD_GUILD_ID'])
CHANNEL = int(os.environ['DISCORD_CHANNEL_ID'])
ADMIN = int(os.environ['DISCORD_ADMIN_USER_ID'])
MESSAGE = '✅ Compra efetuada com sucesso!\nAguarde sua ativação.'

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

with connect() as db:
    db.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, phone TEXT NOT NULL, product TEXT NOT NULL, cents INTEGER NOT NULL, state TEXT NOT NULL DEFAULT "pending", actor TEXT)')
    # Envios interrompidos exigem conferência: não repetir automaticamente.
    db.execute("UPDATE orders SET state='uncertain' WHERE state='sending'")

def authorized(i):
    return i.guild_id == GUILD and i.channel_id == CHANNEL and i.user.id == ADMIN

async def guard(i):
    if authorized(i):
        return True
    await i.response.send_message('Use o canal privado configurado e a conta do responsável.', ephemeral=True)
    return False

class Store(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.none(), allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)
    async def setup_hook(self):
        self.add_view(ConfirmView())
        self.tree.copy_global_to(guild=discord.Object(id=GUILD))
        await self.tree.sync(guild=discord.Object(id=GUILD))

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label='Confirmar pagamento', style=discord.ButtonStyle.green, custom_id='tkstore:confirm:v1')
    async def confirm(self, i: discord.Interaction, button: discord.ui.Button):
        if not await guard(i):
            return
        if not i.message.embeds or not i.message.embeds[0].footer.text:
            await i.response.send_message('Pedido inválido.', ephemeral=True)
            return
        order_id = i.message.embeds[0].footer.text
        url, token = os.getenv('WHATSAPP_ADAPTER_URL'), os.getenv('WHATSAPP_ADAPTER_TOKEN')
        if not url or not token or not url.startswith('https://'):
            await i.response.send_message('WhatsApp ainda não integrado. Nenhum envio realizado; pedido permanece pendente.', ephemeral=True)
            return
        await i.response.defer(ephemeral=True, thinking=True)
        with connect() as db:
            changed = db.execute("UPDATE orders SET state='sending',actor=? WHERE id=? AND state='pending'", (str(i.user.id), order_id)).rowcount
            row = db.execute('SELECT * FROM orders WHERE id=?', (order_id,)).fetchone()
        if not changed:
            await i.followup.send('Pedido já processado ou aguardando conferência. Não houve novo envio.', ephemeral=True)
            return
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
                async with session.post(url, headers={'Authorization': f'Bearer {token}', 'Idempotency-Key': order_id}, json={'order_id': order_id, 'to': row['phone'], 'text': MESSAGE}, allow_redirects=False) as response:
                    if response.status != 200:
                        raise ValueError('Resposta sem confirmação')
                    result = await response.json()
                    if result.get('status') != 'sent' or not result.get('message_id'):
                        raise ValueError('Resposta sem confirmação')
            state, notice = 'sent', 'Pagamento confirmado e mensagem aceita pelo WhatsApp. A entrega ao aparelho depende do serviço.'
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            state, notice = 'uncertain', 'Envio sem confirmação. Confira o WhatsApp antes de qualquer reenvio; o bot não repetirá automaticamente.'
        with connect() as db:
            db.execute('UPDATE orders SET state=? WHERE id=?', (state, order_id))
        await i.followup.send(notice, ephemeral=True)

bot = Store()

@bot.tree.command(name='start', description='Abrir o painel TK STORE')
async def start(i: discord.Interaction):
    if await guard(i):
        await i.response.send_message('🛍️ **TK STORE**\nUse `/pedido` para registrar uma compra. Após conferir o Pix, clique em **Confirmar pagamento**.\nUse `/status` para consultar um pedido. A conexão da Zumy não é alterada por este programa.', ephemeral=True)

@bot.tree.command(name='pedido', description='Registrar pedido para confirmação manual')
@app_commands.describe(telefone='DDI + DDD + número, somente dígitos', produto='Produto e condições combinadas', valor='Valor em reais, ex.: 18,00')
async def pedido(i: discord.Interaction, telefone: str, produto: str, valor: str):
    if not await guard(i):
        return
    try:
        amount = Decimal(valor.replace(',', '.'))
        if not amount.is_finite() or amount <= 0 or amount > 100000 or amount.as_tuple().exponent < -2:
            raise ValueError()
        if not re.fullmatch(r'[1-9][0-9]{9,14}', telefone) or not 1 <= len(produto.strip()) <= 200:
            raise ValueError()
    except (InvalidOperation, ValueError):
        await i.response.send_message('Confira telefone com DDI, produto e valor positivo com até duas casas decimais.', ephemeral=True)
        return
    order_id = uuid.uuid4().hex
    with connect() as db:
        db.execute('INSERT INTO orders (id,phone,product,cents) VALUES (?,?,?,?)', (order_id, telefone, produto.strip(), int(amount * 100)))
    embed = discord.Embed(title='TK STORE — conferir Pix', description=discord.utils.escape_markdown(produto.strip()))
    embed.add_field(name='Valor', value=f'R$ {amount:.2f}')
    embed.add_field(name='WhatsApp', value='••••' + telefone[-4:])
    embed.set_footer(text=order_id)
    await i.response.send_message(embed=embed, view=ConfirmView())

@bot.tree.command(name='status', description='Consultar o estado do pedido')
async def status(i: discord.Interaction, pedido_id: str):
    if await guard(i):
        with connect() as db:
            row = db.execute('SELECT state FROM orders WHERE id=?', (pedido_id,)).fetchone()
        await i.response.send_message(f"Estado: {row['state'] if row else 'não encontrado'}", ephemeral=True)

if __name__ == '__main__':
    bot.run(os.environ['DISCORD_TOKEN'], log_handler=None)
