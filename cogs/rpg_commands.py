import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands
import database
import asyncio
import random
import re

RPG_SYSTEMS = {
    "ordem paranormal": ["Nome", "Classe", "Origem", "PV", "Sanidade", "PE", "Força", "Agilidade", "Intelecto",
                         "Presença", "Vigor"],
    "tormenta20": ["Nome", "Raça", "Classe", "PV", "Mana", "Força", "Destreza", "Constituição", "Inteligência",
                   "Sabedoria", "Carisma"],
    "pokemon ttrpg": ["Nome", "Treinador", "PV", "Energia", "Ataque", "Defesa", "Ataque Especial", "Defesa Especial",
                      "Velocidade"],
    "alice in borderland": ["Nome", "Vida", "Sanidade", "Stamina", "Visto", "Popularidade", "Sangue", "Agilidade",
                            "Vontade", "Raciocínio", "Engano"]
}


class CharacterCreationModal(discord.ui.Modal):
    def __init__(self, bot, system_name: str, campaign: str, attributes_to_ask: list):
        self.bot = bot
        self.system_name = system_name
        self.campaign = campaign
        self.attributes_to_ask = attributes_to_ask
        self.collected_data = {}
        super().__init__(title=f"Criar Ficha ({system_name}) - Parte 1")
        for attr in self.attributes_to_ask:
            self.add_item(discord.ui.InputText(label=attr.title(), placeholder=f"Digite o valor para {attr}"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Parte 1 recebida! Vamos continuar no chat...", ephemeral=True)
        for item in self.children: self.collected_data[item.label.lower()] = item.value
        all_attributes = RPG_SYSTEMS.get(self.system_name.lower())
        remaining_attributes = [attr for attr in all_attributes if attr.lower() not in self.collected_data]

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        for attr in remaining_attributes:
            await interaction.followup.send(f"Qual o valor para **{attr.title()}**?", ephemeral=True)
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=60.0)
                self.collected_data[attr.lower()] = msg.content
                await msg.delete()
            except asyncio.TimeoutError:
                return await interaction.followup.send("⏳ Tempo esgotado! Criação cancelada.", ephemeral=True)
        char_name = self.collected_data.get("nome", "Personagem Sem Nome")
        try:
            database.create_character_sheet(user_id=interaction.user.id, system=self.system_name,
                                            campaign=self.campaign, char_name=char_name, attributes=self.collected_data)
            embed = discord.Embed(title="✅ Ficha Criada com Sucesso!",
                                  description=f"Sua ficha **{char_name}** para **{self.system_name}** foi salva.",
                                  color=discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao salvar: {e}", ephemeral=True)


class RPGCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.initiative_trackers = {}

    ficha = SlashCommandGroup("ficha", "Comandos para gerenciar fichas de RPG")

    @ficha.command(name="criar", description="Cria uma nova ficha de personagem.")
    async def criar(self, ctx: discord.ApplicationContext,
                    system: Option(str, "Sistema", choices=list(RPG_SYSTEMS.keys())),
                    campaign: Option(str, "Campanha")):
        attributes = RPG_SYSTEMS.get(system.lower(), [])
        modal = CharacterCreationModal(bot=self.bot, system_name=system, campaign=campaign,
                                       attributes_to_ask=attributes[:5])
        await ctx.send_modal(modal)

    @ficha.command(name="ver", description="Visualiza uma ficha de personagem.")
    async def ver(self, ctx: discord.ApplicationContext,
                  system: Option(str, "Sistema", choices=list(RPG_SYSTEMS.keys())), campaign: Option(str, "Campanha"),
                  name: Option(str, "Nome do Personagem")):
        await ctx.defer()
        char_id = database.find_character_id(ctx.author.id, system, campaign, name)
        if not char_id: return await ctx.followup.send("❌ Ficha não encontrada.", ephemeral=True)
        sheet = database.get_character_sheet(char_id)
        embed = discord.Embed(title=f"Ficha de {sheet['character_name'].title()}",
                              description=f"Sistema: {sheet['system'].title()} | Campanha: {sheet['campaign'].title()}",
                              color=discord.Color.purple())
        embed.add_field(name="💰 Dinheiro", value=sheet.get('money', 0), inline=True)
        for attr, value in sheet['attributes'].items():
            embed.add_field(name=attr.title(), value=value or "N/A", inline=True)
        await ctx.followup.send(embed=embed)

    inventario = SlashCommandGroup("inventario", "Comandos para gerenciar o inventário.")
    dinheiro = SlashCommandGroup("dinheiro", "Comandos para gerenciar o dinheiro.")

    @dinheiro.command(name="adicionar", description="[MESTRE] Adiciona dinheiro a um personagem.")
    @commands.has_permissions(manage_guild=True)
    async def money_add(self, ctx: discord.ApplicationContext, jogador: Option(discord.Member, "Jogador"),
                        sistema: Option(str, "Sistema"), campanha: Option(str, "Campanha"),
                        personagem: Option(str, "Personagem"), quantidade: Option(float, "Quantidade")):
        char_id = database.find_character_id(jogador.id, sistema, campanha, personagem)
        if not char_id: return await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
        database.modify_money(char_id, quantidade)
        await ctx.respond(f"✅ Adicionado **{quantidade}** de dinheiro para **{personagem}**.", ephemeral=True)

    @inventario.command(name="adicionar", description="[MESTRE] Adiciona um item a um personagem.")
    @commands.has_permissions(manage_guild=True)
    async def inv_add(self, ctx: discord.ApplicationContext, jogador: Option(discord.Member, "Jogador"),
                      sistema: Option(str, "Sistema"), campanha: Option(str, "Campanha"),
                      personagem: Option(str, "Personagem"), item: Option(str, "Item"),
                      quantidade: Option(int, "Qtd", default=1), descricao: Option(str, "Descrição", default="")):
        char_id = database.find_character_id(jogador.id, sistema, campanha, personagem)
        if not char_id: return await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
        database.add_item(char_id, item, quantidade, descricao)
        await ctx.respond(f"✅ **{quantidade}x {item}** adicionado ao inventário de **{personagem}**.", ephemeral=True)

    @inventario.command(name="remover", description="Remove um item do seu inventário.")
    async def inv_remove(self, ctx: discord.ApplicationContext, sistema: Option(str, "Sistema"),
                         campanha: Option(str, "Campanha"), personagem: Option(str, "Personagem"),
                         item: Option(str, "Item"), quantidade: Option(int, "Qtd", default=1)):
        char_id = database.find_character_id(ctx.author.id, sistema, campanha, personagem)
        if not char_id: return await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
        try:
            database.remove_item(char_id, item, quantidade)
            await ctx.respond(f"✅ **{quantidade}x {item}** removido do inventário de **{personagem}**.", ephemeral=True)
        except ValueError as e:
            await ctx.respond(f"❌ {e}", ephemeral=True)

    @inventario.command(name="ver", description="Mostra seu inventário e dinheiro.")
    async def inv_view(self, ctx: discord.ApplicationContext, sistema: Option(str, "Sistema"),
                       campanha: Option(str, "Campanha"), personagem: Option(str, "Personagem")):
        char_id = database.find_character_id(ctx.author.id, sistema, campanha, personagem)
        if not char_id: return await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
        sheet = database.get_character_sheet(char_id)
        inventory = database.get_inventory(char_id)
        embed = discord.Embed(title=f"🎒 Inventário de {personagem}", color=discord.Color.dark_orange())
        embed.add_field(name="💰 Dinheiro", value=f"{sheet.get('money', 0):.2f}", inline=False)
        if not inventory:
            embed.description = "O inventário está vazio."
        else:
            for item in inventory:
                embed.add_field(name=f"{item['item_name']} (x{item['quantity']})",
                                value=item['description'] or "Sem descrição.", inline=False)
        await ctx.respond(embed=embed, ephemeral=True)

    efeito = SlashCommandGroup("efeito", "Comandos para gerenciar efeitos de status.")

    @efeito.command(name="aplicar", description="[MESTRE] Aplica um efeito de status em um personagem.")
    @commands.has_permissions(manage_guild=True)
    async def effect_apply(self, ctx: discord.ApplicationContext, jogador: Option(discord.Member, "Jogador"),
                           sistema: Option(str, "Sistema"), campanha: Option(str, "Campanha"),
                           personagem: Option(str, "Personagem"), efeito: Option(str, "Efeito"),
                           duracao: Option(int, "Duração em turnos")):
        char_id = database.find_character_id(jogador.id, sistema, campanha, personagem)
        if not char_id: return await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
        database.apply_effect(char_id, efeito, duracao, ctx.author.id)
        await ctx.respond(f"✅ Efeito **{efeito}** aplicado em **{personagem}** por **{duracao}** turnos.",
                          ephemeral=True)

    iniciativa = SlashCommandGroup("iniciativa", "Comandos para gerenciar a ordem de combate.")

    @iniciativa.command(name="adicionar", description="Adiciona um personagem à iniciativa.")
    async def iniciativa_add(self, ctx: discord.ApplicationContext, nome: Option(str, "Nome"),
                             valor: Option(int, "Iniciativa"),
                             jogador: Option(discord.Member, "Mencione o jogador (opcional)", default=None)):
        server_id = ctx.guild.id
        if server_id not in self.initiative_trackers: self.initiative_trackers[server_id] = {"combatants": [],
                                                                                             "turn_index": -1}
        tracker = self.initiative_trackers[server_id]
        tracker["combatants"].append({"name": nome, "value": valor, "user_id": jogador.id if jogador else None})
        tracker["combatants"].sort(key=lambda x: x["value"], reverse=True)
        await ctx.respond(f"✅ **{nome}** adicionado à iniciativa com valor **{valor}**.", ephemeral=True)

    @iniciativa.command(name="ver", description="Mostra a ordem de iniciativa atual.")
    async def iniciativa_ver(self, ctx: discord.ApplicationContext):
        server_id = ctx.guild.id
        if server_id not in self.initiative_trackers or not self.initiative_trackers[server_id]["combatants"]:
            return await ctx.respond("⚔️ A lista de iniciativa está vazia.", ephemeral=True)
        tracker = self.initiative_trackers[server_id]
        embed = discord.Embed(title="⚔️ Ordem de Iniciativa ⚔️", color=discord.Color.gold())
        description = ""
        for i, combatant in enumerate(tracker["combatants"]):
            arrow = "▶️ " if i == tracker["turn_index"] else ""
            description += f"**{i + 1}.** {arrow}`{combatant['value']:<2}` - {combatant['name']}\n"
        embed.description = description
        await ctx.respond(embed=embed)

    @iniciativa.command(name="proximo", description="Avança para o próximo turno e aplica efeitos.")
    async def iniciativa_next(self, ctx: discord.ApplicationContext):
        server_id = ctx.guild.id
        if server_id not in self.initiative_trackers or not self.initiative_trackers[server_id]["combatants"]:
            return await ctx.respond("⚔️ Lista de iniciativa vazia.", ephemeral=True)
        tracker = self.initiative_trackers[server_id]
        tracker["turn_index"] = (tracker["turn_index"] + 1) % len(tracker["combatants"])
        await self.iniciativa_ver(ctx)

    @iniciativa.command(name="zerar", description="Limpa a lista de iniciativa.")
    async def iniciativa_clear(self, ctx: discord.ApplicationContext):
        server_id = ctx.guild.id
        if server_id in self.initiative_trackers:
            self.initiative_trackers.pop(server_id)
        await ctx.respond("✅ A lista de iniciativa foi zerada!", ephemeral=True)

    npc = SlashCommandGroup("npc", "Comandos para gerenciar NPCs rápidos.")

    @commands.slash_command(name="rolar", description="Rola dados (ex: 1d20, 2d6+3).")
    async def rolar(self, ctx: discord.ApplicationContext, notacao: Option(str, "A notação do dado")):
        pattern = re.compile(r"(\d+)?d(\d+)([+-]\d+)?")
        match = pattern.fullmatch(notacao.lower().strip())
        if not match: return await ctx.respond(f"❌ Formato inválido: `{notacao}`.", ephemeral=True)
        num_dados_str, num_faces_str, mod_str = match.groups()
        num_dados = int(num_dados_str) if num_dados_str else 1
        num_faces = int(num_faces_str)
        modificador = int(mod_str) if mod_str else 0
        rolagens = [random.randint(1, num_faces) for _ in range(num_dados)]
        total = sum(rolagens) + modificador
        embed = discord.Embed(title=f"🎲 Rolagem de Dados: {notacao}", color=discord.Color.blurple())
        embed.add_field(name="Total Final", value=f"**` {total} `**", inline=False)
        if num_dados > 1 or modificador != 0:
            embed.add_field(name="Rolagens", value=f"`{rolagens} + ({modificador})`", inline=True)
        embed.set_footer(text=f"Rolado por {ctx.author.display_name}")
        await ctx.respond(embed=embed)

    @commands.slash_command(name="ping", description="Verifica a latência do bot.")
    async def ping(self, ctx: discord.ApplicationContext):
        latency = self.bot.latency * 1000
        await ctx.respond(f"Pong! 🏓 Latência: {latency:.2f}ms")


def setup(bot):
    bot.add_cog(RPGCog(bot))