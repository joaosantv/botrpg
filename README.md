# 🎲 BOT RPG - Bot de RPG para Discord

## 📖 Sobre o Projeto

O **Guardião das Fichas** é um bot para Discord criado em Python, projetado para ser um assistente completo para mesas de RPG de mesa. Este foi meu primeiro grande projeto de desenvolvimento, nascido da minha paixão por RPG e da necessidade de uma ferramenta integrada ao Discord para gerenciar o caos de fichas de personagem, rolagens de dados e o andamento do combate.

O objetivo é centralizar as informações mais importantes do jogo, permitindo que mestres e jogadores foquem no que realmente importa: a história.

## ✨ Funcionalidades Principais

* **Fichas de Personagem:** Sistema completo para criar, visualizar e modificar fichas de personagem.
* **Suporte a Múltiplos Sistemas:** Facilmente extensível, atualmente configurado para Ordem Paranormal, Tormenta20, Pokémon TTRPG e Alice in Borderland.
* **Gerenciamento de Atributos:** Comandos para aplicar dano, cura ou editar qualquer status da ficha em tempo real.
* **Rolador de Dados:** Um rolador de dados inteligente que entende a notação padrão de RPG (ex: `2d6+3`, `1d20-1`).
* **Gerenciador de Iniciativa:** Ferramenta para o mestre organizar e acompanhar a ordem dos turnos em combate.
* **Inventário e Dinheiro:** Cada personagem possui uma "mochila" para guardar itens e um contador de dinheiro.
* **NPCs Rápidos:** O mestre pode criar e gerenciar fichas simplificadas para NPCs.
* **Efeitos de Status:** Aplique condições como "Envenenado" ou "Atordoado" e controle sua duração em turnos.

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3
* **Biblioteca Discord:** Py-cord
* **Banco de Dados:** SQLite 3
* **Controle de Versão:** Git & GitHub
* **IDE:** PyCharm

## 🚀 Como Usar o Bot

O bot funciona inteiramente com comandos de barra (`/`). Aqui estão os principais:

* `/ficha criar` - Inicia o processo de criação de uma nova ficha.
* `/ficha ver` - Mostra uma ficha de personagem completa.
* `/rolar <notacao>` - Rola dados. Ex: `/rolar notacao:3d8+4`.
* `/iniciativa adicionar` - Adiciona um combatente à ordem de turnos.
* `/iniciativa proximo` - Avança para o próximo turno.
* `/inventario ver` - Mostra seu inventário e dinheiro.
* `/npc criar` - Permite ao mestre criar um NPC rapidamente.

## 🔧 Como Rodar o Projeto Localmente

Se você quiser rodar sua própria instância do bot, siga estes passos:

1.  **Clone o repositório:**
    ```bash
    git clone [https://github.com/joaosantv/botrpg.git](https://github.com/joaosantv/botrpg.git)
    ```
2.  **Navegue até a pasta do projeto:**
    ```bash
    cd rpg-discord-bot 
    ```
3.  **Crie e ative um ambiente virtual:**
    ```bash
    python -m venv .venv
    # No Windows
    .venv\Scripts\activate
    ```
4.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Configure suas credenciais:**
    * Crie um arquivo chamado `.env` na raiz do projeto.
    * Dentro dele, adicione a linha: `DISCORD_TOKEN=SEU_TOKEN_DO_DISCORD_AQUI`
6.  **Execute o bot:**
    ```bash
    python bot.py
    ```

## ✒️ Autor

* **João Victor** - [joaosantv](https://github.com/joaosantv)

## 📄 Licença

Este projeto está sob a Licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.
