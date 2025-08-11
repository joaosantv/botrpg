import discord
from discord.commands import SlashCommandGroup, Option
from discord.ext import commands
import database
import asyncio
# NOVOS IMPORTS PARA O COMANDO DE ROLAR DADOS
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

        for item in self.children:
            self.collected_data[item.label.lower()] = item.value

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
                await interaction.followup.send("⏳ Tempo esgotado! A criação da ficha foi cancelada.", ephemeral=True)
                return

        char_name = self.collected_data.get("nome", "Personagem Sem Nome")
        try:
            database.create_character_sheet(
                user_id=interaction.user.id,
                system=self.system_name,
                campaign=self.campaign,
                char_name=char_name,
                attributes=self.collected_data
            )
            embed = discord.Embed(
                title="✅ Ficha Criada com Sucesso!",
                description=f"Sua ficha **{char_name}** para **{self.system_name}** na campanha **{self.campaign}** foi salva com todos os atributos.",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="❌ Erro ao salvar a ficha", description=str(e), color=discord.Color.red())
            await interaction.followup.send(embed=embed, ephemeral=True)


class RPGCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    ficha = SlashCommandGroup("ficha", "Comandos para gerenciar fichas de RPG")

    @ficha.command(name="criar", description="Cria uma nova ficha de personagem para um sistema.")
    async def criar(self, ctx: discord.ApplicationContext,
                    system: Option(str, "Qual o sistema de RPG?", choices=list(RPG_SYSTEMS.keys())),
                    campaign: Option(str, "Qual o nome da campanha?")
                    ):
        system_attributes = RPG_SYSTEMS.get(system.lower(), [])
        if not system_attributes:
            await ctx.respond("❌ Sistema de RPG não encontrado.", ephemeral=True)
            return

        initial_attributes = system_attributes[:5]

        initial_modal = CharacterCreationModal(
            bot=self.bot,
            system_name=system,
            campaign=campaign,
            attributes_to_ask=initial_attributes
        )
        await ctx.send_modal(initial_modal)

    @ficha.command(name="listar", description="Lista todas as suas fichas de um sistema.")
    async def listar(self, ctx: discord.ApplicationContext,
                     system: Option(str, "Listar fichas de qual sistema?", choices=list(RPG_SYSTEMS.keys()))
                     ):
        await ctx.defer(ephemeral=True)
        char_list = database.list_characters(user_id=ctx.author.id, system=system)

        if not char_list:
            embed = discord.Embed(title=f"Nenhuma Ficha Encontrada",
                                  description=f"Você não possui fichas para o sistema **{system}**.",
                                  color=discord.Color.orange())
            await ctx.respond(embed=embed, ephemeral=True)
            return

        embed = discord.Embed(title=f"Fichas de {system.title()}", color=discord.Color.blue())
        description = ""
        for camp, name in char_list:
            description += f"**Campanha:** `{camp}` - **Personagem:** `{name}`\n"
        embed.description = description
        await ctx.respond(embed=embed, ephemeral=True)

    @ficha.command(name="ver", description="Visualiza uma ficha de personagem específica.")
    async def ver(self, ctx: discord.ApplicationContext,
                  system: Option(str, "Sistema da ficha", choices=list(RPG_SYSTEMS.keys())),
                  campaign: Option(str, "Campanha da ficha"),
                  name: Option(str, "Nome do personagem")
                  ):
        await ctx.defer()
        char_id = database.find_character_id(ctx.author.id, system, campaign, name)
        if not char_id:
            await ctx.respond(f"❌ Ficha não encontrada para `{name}` na campanha `{campaign}` de `{system}`.",
                              ephemeral=True)
            return

        sheet = database.get_character_sheet(char_id)

        embed = discord.Embed(title=f"Ficha de {sheet['character_name'].title()}",
                              description=f"Sistema: **{sheet['system'].title()}** | Campanha: **{sheet['campaign'].title()}**",
                              color=discord.Color.purple())
        for attr, value in sheet['attributes'].items():
            embed.add_field(name=attr.title(), value=value or "N/A", inline=True)
        embed.set_footer(text=f"ID do Dono: {sheet['user_id']}")
        await ctx.respond(embed=embed)

    @ficha.command(name="editar", description="Edita um atributo de uma de suas fichas.")
    async def editar(self, ctx: discord.ApplicationContext,
                     system: Option(str, "Sistema da ficha", choices=list(RPG_SYSTEMS.keys())),
                     campaign: Option(str, "Campanha da ficha"),
                     name: Option(str, "Nome do personagem"),
                     atributo: Option(str, "Qual atributo editar?"),
                     novo_valor: Option(str, "Qual o novo valor?")
                     ):
        await ctx.defer(ephemeral=True)
        char_id = database.find_character_id(ctx.author.id, system, campaign, name)
        if not char_id:
            await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
            return

        if database.update_attribute(char_id, atributo, novo_valor):
            await ctx.respond(f"✅ Atributo **{atributo}** de **{name}** atualizado para **{novo_valor}**.",
                              ephemeral=True)
        else:
            await ctx.respond(f"❌ Atributo **{atributo}** não encontrado na ficha de **{name}**.", ephemeral=True)

    @ficha.command(name="modificar",
                   description="Adiciona ou subtrai um valor numérico de um atributo (ex: dano/cura).")
    async def modificar(self, ctx: discord.ApplicationContext,
                        system: Option(str, "Sistema da ficha", choices=list(RPG_SYSTEMS.keys())),
                        campaign: Option(str, "Campanha da ficha"),
                        name: Option(str, "Nome do personagem"),
                        atributo: Option(str, "Qual atributo modificar (ex: PV, Sanidade)?"),
                        valor: Option(int, "Valor a ser adicionado (use negativo para subtrair, ex: -15)")
                        ):
        await ctx.defer()
        char_id = database.find_character_id(ctx.author.id, system, campaign, name)
        if not char_id:
            await ctx.respond(f"❌ Ficha não encontrada.", ephemeral=True)
            return

        sheet = database.get_character_sheet(char_id)

        try:
            current_value_str = sheet['attributes'].get(atributo.lower())
            if current_value_str is None:
                await ctx.respond(f"❌ Atributo **{atributo}** não encontrado na ficha.", ephemeral=True)
                return

            current_value = int(current_value_str)
            new_value = current_value + valor

            database.update_attribute(char_id, atributo, str(new_value))

            operacao = "aumentado" if valor >= 0 else "reduzido"
            sinal = "+" if valor >= 0 else ""
            await ctx.respond(
                f"✅ **{name}**: atributo **{atributo.title()}** foi {operacao} de `{current_value}` para `{new_value}` ({sinal}{valor}).")
        except (ValueError, TypeError):
            await ctx.respond(
                f"❌ O atributo **{atributo}** não parece ser um número e não pode ser modificado matematicamente.",
                ephemeral=True)

    # ===============================================================
    # ================= NOVO COMANDO /rolar =========================
    # ===============================================================
    @commands.slash_command(name="rolar", description="Rola um ou mais dados no formato de RPG (ex: 1d20, 2d6+3).")
    async def rolar(self, ctx: discord.ApplicationContext,
                    notacao: Option(str, "A notação do dado a ser rolado (ex: d20, 2d6+3, 1d12-1)")
                    ):
        pattern = re.compile(r"(\d+)?d(\d+)([+-]\d+)?")
        match = pattern.fullmatch(notacao.lower().strip())

        if not match:
            await ctx.respond(f"❌ Formato inválido: `{notacao}`. Use um formato como `d20`, `2d6` ou `3d8+4`.",
                              ephemeral=True)
            return

        num_dados_str, num_faces_str, modificador_str = match.groups()

        num_dados = int(num_dados_str) if num_dados_str else 1
        num_faces = int(num_faces_str)
        modificador = int(modificador_str) if modificador_str else 0

        if not (1 <= num_dados <= 100):
            await ctx.respond("❌ O número de dados deve estar entre 1 e 100.", ephemeral=True)
            return
        if not (1 <= num_faces <= 1000):
            await ctx.respond("❌ O número de faces deve estar entre 1 e 1000.", ephemeral=True)
            return

        rolagens = [random.randint(1, num_faces) for _ in range(num_dados)]
        total = sum(rolagens) + modificador

        embed = discord.Embed(
            title=f"🎲 Rolagem de Dados: {notacao}",
            color=discord.Color.green() if total > (
                        sum(range(1, num_faces + 1)) / num_faces * num_dados) else discord.Color.red()
        )
        embed.add_field(name="Rolagens Individuais", value=f"`{rolagens}`", inline=False)

        if modificador != 0:
            sinal = "+" if modificador > 0 else ""
            embed.add_field(name="Modificador", value=f"`{sinal}{modificador}`", inline=True)
            embed.add_field(name="Soma Parcial", value=f"`{sum(rolagens)}`", inline=True)

        embed.add_field(name="Total Final", value=f"**`{total}`**", inline=False)
        embed.set_footer(text=f"Rolado por {ctx.author.display_name}")

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(RPGCog(bot))