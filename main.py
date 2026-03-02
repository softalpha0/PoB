import os
import discord
import sqlite3
import math
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOD_CHANNEL_ID = int(os.getenv('MOD_CHANNEL_ID'))

# --- CLOUD PERSISTENCE ---
if not os.path.exists('data'):
    os.makedirs('data')

db = sqlite3.connect('data/spicenet_pob.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS believers 
                  (user_id TEXT PRIMARY KEY, credits INTEGER DEFAULT 0, strikes INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS blacklist 
                  (user_id TEXT PRIMARY KEY)''')
db.commit()

# --- LEADERBOARD PAGINATION ---
class PaginationView(discord.ui.View):
    def __init__(self, data, title):
        super().__init__(timeout=60)
        self.data = data
        self.title = title
        self.per_page = 10
        self.current_page = 0
        self.max_pages = math.ceil(len(data) / self.per_page)

    def create_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        page_data = self.data[start:end]
        
        lb_text = "\n".join([f"**#{i+1+start}** <@{u_id}> — {creds} BC" for u_id, creds in page_data])
        embed = discord.Embed(title=self.title, description=lb_text or "No data.", color=0xFFD700)
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.max_pages}")
        return embed

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

class PoBBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ PoB V2.9 Online | Infinite Leaderboard & Rank Search Active")

bot = PoBBot()

# ... (Include ApprovalView, submit, profile, and pardon commands from previous versions) ...

@bot.tree.command(name="leaderboard", description="View the full Spicenet Leaderboard")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT user_id, credits FROM believers ORDER BY credits DESC")
    all_rows = cursor.fetchall()
    
    if not all_rows:
        return await interaction.response.send_message("The leaderboard is currently empty.", ephemeral=True)

    view = PaginationView(all_rows, "🏆 Spicenet Global Leaderboard")
    await interaction.response.send_message(embed=view.create_embed(), view=view)

@bot.tree.command(name="rank", description="Find the rank of a specific user")
@app_commands.describe(user="The user you want to check (defaults to you)")
async def rank(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    
    # SQL to find rank: Count how many users have MORE credits than this user
    cursor.execute("""
        SELECT (SELECT COUNT(*) + 1 FROM believers WHERE credits > t.credits) as rank, credits
        FROM believers t WHERE user_id = ?
    """, (str(target_user.id),))
    
    result = cursor.fetchone()
    if not result:
        return await interaction.response.send_message(f"**{target_user.display_name}** hasn't earned any BC yet.", ephemeral=True)
    
    rank_num, credits = result
    embed = discord.Embed(title=f"🥇 Rank Search", color=0x3498db)
    embed.add_field(name="User", value=target_user.mention, inline=True)
    embed.add_field(name="Position", value=f"#{rank_num}", inline=True)
    embed.add_field(name="Balance", value=f"{credits} BC", inline=True)
    
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)
