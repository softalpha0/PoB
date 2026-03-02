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
        
        # FIXED LINE: Added enumerate() to define 'i'
        lb_text = "\n".join([f"**#{i+1+start}** <@{u_id}> — {creds} BC" for i, (u_id, creds) in enumerate(page_data)])
        
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
        print("✅ PoB V2.9.1 Fixed | Leaderboard Restored")

bot = PoBBot()

# --- MODERATOR VIEW ---
class ApprovalView(discord.ui.View):
    def __init__(self, user_id, amount, category):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.amount = amount
        self.category = category

    @discord.ui.button(label="Approve ✅", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        cursor.execute("INSERT OR IGNORE INTO believers (user_id, credits, strikes) VALUES (?, 0, 0)", (str(self.user_id),))
        cursor.execute("UPDATE believers SET credits = credits + ?, strikes = 0 WHERE user_id = ?", (self.amount, str(self.user_id)))
        db.commit()
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(content=f"✅ **Approved!** Credits added.", view=self)

    @discord.ui.button(label="Reject & Penalize ❌", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        cursor.execute("INSERT OR IGNORE INTO believers (user_id, credits, strikes) VALUES (?, 0, 0)", (str(self.user_id),))
        cursor.execute("UPDATE believers SET credits = credits - ?, strikes = strikes + 1 WHERE user_id = ?", (self.amount, str(self.user_id)))
        cursor.execute("SELECT strikes FROM believers WHERE user_id = ?", (str(self.user_id),))
        strikes = cursor.fetchone()[0]
        status = f"❌ **Rejected.** Penalty applied."
        if strikes >= 3:
            cursor.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (str(self.user_id),))
            status += "\n🚫 **User Blacklisted.**"
        db.commit()
        for item in self.children: item.disabled = True
        await interaction.response.edit_message(content=status, view=self)

@bot.tree.command(name="submit", description="Submit proof for Spicenet BC")
@app_commands.choices(category=[
    app_commands.Choice(name="Engagement (5 BC)", value=5),
    app_commands.Choice(name="Bug Report (15 BC)", value=15),
    app_commands.Choice(name="Content (20 BC)", value=20),
    app_commands.Choice(name="Community Spaces (25 BC)", value=25)
])
async def submit(interaction: discord.Interaction, category: app_commands.Choice[int], description: str, proof_link: str = None, attachment: discord.Attachment = None):
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id = ?", (str(interaction.user.id),))
    if cursor.fetchone():
        return await interaction.response.send_message("🚫 You are blacklisted.", ephemeral=True)
    if not proof_link and not attachment:
        return await interaction.response.send_message("❌ Error: You must provide a link OR an attachment.", ephemeral=True)
    channel = bot.get_channel(MOD_CHANNEL_ID)
    embed = discord.Embed(title=f"🌶️ {category.name}", color=0xFF4500)
    embed.add_field(name="User", value=interaction.user.mention)
    embed.add_field(name="Description", value=description, inline=False)
    if proof_link: embed.add_field(name="Link", value=proof_link, inline=False)
    if attachment:
        if any(attachment.filename.lower().endswith(ext) for ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']):
            embed.set_image(url=attachment.url)
        else:
            embed.add_field(name="File", value=f"[View Attachment]({attachment.url})", inline=False)
    await channel.send(embed=embed, view=ApprovalView(interaction.user.id, category.value, category.name))
    await interaction.response.send_message("Submitted! 🌶️", ephemeral=True)

@bot.tree.command(name="leaderboard", description="View the full Spicenet Leaderboard")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT user_id, credits FROM believers ORDER BY credits DESC")
    all_rows = cursor.fetchall()
    if not all_rows:
        return await interaction.response.send_message("The leaderboard is currently empty.", ephemeral=True)
    view = PaginationView(all_rows, "🏆 Spicenet Global Leaderboard")
    await interaction.response.send_message(embed=view.create_embed(), view=view)

@bot.tree.command(name="rank", description="Find the rank of a specific user")
async def rank(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    cursor.execute("SELECT (SELECT COUNT(*) + 1 FROM believers WHERE credits > t.credits) as rank, credits FROM believers t WHERE user_id = ?", (str(target_user.id),))
    result = cursor.fetchone()
    if not result:
        return await interaction.response.send_message(f"**{target_user.display_name}** has 0 BC.", ephemeral=True)
    rank_num, credits = result
    embed = discord.Embed(title="🥇 Rank Search", color=0x3498db)
    embed.add_field(name="User", value=target_user.mention, inline=True)
    embed.add_field(name="Position", value=f"#{rank_num}", inline=True)
    embed.add_field(name="Balance", value=f"{credits} BC", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="profile", description="Check your BC balance and strikes")
async def profile(interaction: discord.Interaction):
    cursor.execute("SELECT credits, strikes FROM believers WHERE user_id = ?", (str(interaction.user.id),))
    row = cursor.fetchone()
    credits, strikes = row if row else (0, 0)
    embed = discord.Embed(title=f"👤 {interaction.user.display_name}", color=0x3498db)
    embed.add_field(name="Belief Credits", value=f"{credits} BC", inline=True)
    embed.add_field(name="Strikes", value=f"{strikes}/3", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="pardon", description="Admin: Un-blacklist a user")
@app_commands.checks.has_permissions(manage_guild=True)
async def pardon(interaction: discord.Interaction, user: discord.User):
    cursor.execute("UPDATE believers SET strikes = 0 WHERE user_id = ?", (str(user.id),))
    cursor.execute("DELETE FROM blacklist WHERE user_id = ?", (str(user.id),))
    db.commit()
    await interaction.response.send_message(f"🔓 <@{user.id}> pardoned.", ephemeral=True)

bot.run(TOKEN)
