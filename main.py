import os
import discord
import sqlite3
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MOD_CHANNEL_ID = int(os.getenv('MOD_CHANNEL_ID'))


db = sqlite3.connect('spicenet_pob.db')
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS believers 
                  (user_id TEXT PRIMARY KEY, credits INTEGER DEFAULT 0, strikes INTEGER DEFAULT 0)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS blacklist 
                  (user_id TEXT PRIMARY KEY)''')
db.commit()

class PoBBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True 
        intents.message_content = True 
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ PoB V2.5 Online | Universal Attachments & Profile Active")

bot = PoBBot()


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
async def submit(
    interaction: discord.Interaction, 
    category: app_commands.Choice[int], 
    description: str, 
    proof_link: str = None, 
    attachment: discord.Attachment = None
):
    cursor.execute("SELECT user_id FROM blacklist WHERE user_id = ?", (str(interaction.user.id),))
    if cursor.fetchone():
        return await interaction.response.send_message("🚫 You are blacklisted.", ephemeral=True)
    
    if not proof_link and not attachment:
        return await interaction.response.send_message("❌ You must provide a link OR an attachment.", ephemeral=True)

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

@bot.tree.command(name="profile", description="Check your BC balance and strikes")
async def profile(interaction: discord.Interaction):
    cursor.execute("SELECT credits, strikes FROM believers WHERE user_id = ?", (str(interaction.user.id),))
    row = cursor.fetchone()
    credits, strikes = row if row else (0, 0)
    
    embed = discord.Embed(title=f"👤 {interaction.user.display_name}'s Profile", color=0x3498db)
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

@bot.tree.command(name="leaderboard", description="Top Believers")
async def leaderboard(interaction: discord.Interaction):
    cursor.execute("SELECT user_id, credits FROM believers ORDER BY credits DESC LIMIT 10")
    rows = cursor.fetchall()
    lb = "\n".join([f"**#{i+1}** <@{r[0]}> — {r[1]} BC" for i, r in enumerate(rows)])
    await interaction.response.send_message(embed=discord.Embed(title="🏆 Leaderboard", description=lb or "Empty"))

bot.run(TOKEN)
