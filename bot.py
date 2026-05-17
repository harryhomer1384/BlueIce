import discord
from discord import app_commands
from discord.ui import View, Button, Select
import asyncio
import os
import traceback
import requests
from datetime import datetime, timedelta, timezone

# ==================== JSONBIN.IO CONFIG ====================

JSONBIN_API_KEY = "$2a$10$oa9N.cjWKW.uDuwPxpK4AOEs.3un2U8/kNH54UU5FqKf3mLUNldh6"
JSONBIN_BIN_ID = "6a0755fbc0954111d82b67ed"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

# ==================== BOT STATE BIN CONFIG ====================

# Create a SECOND bin on jsonbin.io:
# 1. Go to jsonbin.io and sign in
# 2. Click "New Bin"
# 3. Paste this EXACT content: {"verified_accounts":{},"cooldowns":{}}
# 4. Click "Create"
# 5. Copy the Bin ID (the part after /b/ in the URL) and paste it below

BOT_STATE_BIN_ID = "YOUR_BOT_STATE_BIN_ID"  # <-- REPLACE THIS
BOT_STATE_URL = f"https://api.jsonbin.io/v3/b/{BOT_STATE_BIN_ID}"

# ==================== LEADERBOARD FUNCTIONS ====================

def get_leaderboard_data():
    """Fetch current leaderboard from JSONBin."""
    try:
        headers = {"X-Master-Key": JSONBIN_API_KEY}
        response = requests.get(f"{JSONBIN_URL}/latest", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()["record"]
        return []
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return []

def save_leaderboard_data(data):
    """Save leaderboard to JSONBin."""
    try:
        headers = {
            "X-Master-Key": JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.put(JSONBIN_URL, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error saving leaderboard: {e}")
        return False

def add_or_update_player(name, tier):
    """Add new player or update existing player's tier."""
    data = get_leaderboard_data()
    existing = next((p for p in data if p["name"].lower() == name.lower()), None)
    if existing:
        existing["tier"] = tier
        existing["updated"] = datetime.now(timezone.utc).isoformat()
    else:
        new_player = {
            "id": len(data) + 1,
            "name": name,
            "tier": tier,
            "updated": datetime.now(timezone.utc).isoformat()
        }
        data.append(new_player)
    tier_order = {
        'HT1': 1, 'LT1': 2, 'HT2': 3, 'LT2': 4,
        'HT3': 5, 'LT3': 6, 'HT4': 7, 'LT4': 8,
        'HT5': 9, 'LT5': 10
    }
    data.sort(key=lambda x: tier_order.get(x["tier"], 99))
    return save_leaderboard_data(data)

# ==================== BOT STATE FUNCTIONS ====================

def get_bot_state() -> dict:
    """Fetch persistent bot state (cooldowns, verified accounts) from JSONBin."""
    try:
        headers = {"X-Master-Key": JSONBIN_API_KEY}
        response = requests.get(f"{BOT_STATE_URL}/latest", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()["record"]
        return {"verified_accounts": {}, "cooldowns": {}}
    except Exception as e:
        print(f"Error fetching bot state: {e}")
        return {"verified_accounts": {}, "cooldowns": {}}

def save_bot_state(data: dict) -> bool:
    """Save bot state to JSONBin."""
    try:
        headers = {
            "X-Master-Key": JSONBIN_API_KEY,
            "Content-Type": "application/json"
        }
        response = requests.put(BOT_STATE_URL, headers=headers, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error saving bot state: {e}")
        return False

# ==================== CONSTANTS ====================

COOLDOWN_DAYS = 7
RESULTS_CHANNEL_NAME = "results"

REGION_ALIASES = {
    "na": "NA", "north america": "NA", "northamerica": "NA",
    "eu": "EU", "europe": "EU",
    "as": "AS", "asia": "AS",
    "au": "AU", "australia": "AU", "oceania": "AU",
}

WAITLIST_CHANNELS = {
    "NA": "na-waitlist",
    "EU": "eu-waitlist",
    "AS": "as-waitlist",
    "AU": "au-waitlist",
}

WAITLIST_ROLES = {
    "NA": "na-waitlist",
    "EU": "eu-waitlist",
    "AS": "as-waitlist",
    "AU": "au-waitlist",
}

def parse_region(text: str) -> str | None:
    """Return canonical region code (NA/EU/AS/AU) or None if unrecognised."""
    return REGION_ALIASES.get(text.strip().lower())

# ==================== RESULTS EMBED ====================

async def send_results_embed(interaction: discord.Interaction, user: discord.Member,
                             mc_name: str, region: str, tier: str, tester: discord.Member):
    """Send test results embed to the results channel."""
    guild = interaction.guild

    # Try to find existing results channel
    results_channel = discord.utils.get(guild.text_channels, name=RESULTS_CHANNEL_NAME)

    # Create if doesn't exist
    if not results_channel:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            results_channel = await guild.create_text_channel(
                RESULTS_CHANNEL_NAME,
                overwrites=overwrites,
                reason="Test results channel"
            )
        except Exception as e:
            print(f"Failed to create results channel: {e}")
            return

    # Look up previous rank from leaderboard before updating
    leaderboard = get_leaderboard_data()
    prev_entry = next((p for p in leaderboard if p["name"].lower() == mc_name.lower()), None)
    prev_rank = prev_entry["tier"] if prev_entry else "Unranked"

    embed = discord.Embed(
        title=f"🏆 {mc_name}'s Test Results",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Discord", value=user.mention, inline=True)
    embed.add_field(name="Tester", value=tester.mention, inline=True)
    embed.add_field(name="Region", value=region, inline=True)
    embed.add_field(name="MC Username", value=mc_name, inline=True)
    embed.add_field(name="Previous Rank", value=prev_rank, inline=True)
    embed.add_field(name="Rank Earned", value=tier, inline=True)
    embed.set_thumbnail(url=f"https://mc-heads.net/body/{mc_name}/right")

    try:
        await results_channel.send(
            content=f"{user.mention} {tester.mention}",
            embed=embed
        )
    except Exception as e:
        print(f"Error sending results embed: {e}")

# ==================== BOT CLASS ====================

class TicketBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.region_queues: dict[int, dict[str, "RegionQueue"]] = {}
        self.ticket_counter: dict[int, int] = {}
        self.waitlist_cooldowns: dict[int, datetime] = {}
        self.verified_accounts: dict[int, str] = {}
        self.user_regions: dict[int, str] = {}

    async def setup_hook(self):
        """Register all persistent views so buttons survive restarts."""
        self.add_view(RequestTestView(self))
        for region in WAITLIST_CHANNELS:
            self.add_view(WaitlistQueueView(self, region))
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands")
        except Exception as e:
            print(f"Sync failed: {e}")

    async def load_state(self):
        """Load persisted cooldowns and verified accounts from JSONBin."""
        print("Loading bot state...")
        state = get_bot_state()
        self.verified_accounts = {int(k): v for k, v in state.get("verified_accounts", {}).items()}
        self.waitlist_cooldowns = {}
        for uid, ts in state.get("cooldowns", {}).items():
            try:
                self.waitlist_cooldowns[int(uid)] = datetime.fromisoformat(ts)
            except Exception:
                pass
        print(f"  → {len(self.verified_accounts)} verified accounts, {len(self.waitlist_cooldowns)} cooldowns loaded.")

    async def save_state(self):
        """Persist cooldowns and verified accounts to JSONBin."""
        state = {
            "verified_accounts": {str(k): v for k, v in self.verified_accounts.items()},
            "cooldowns": {str(k): v.isoformat() for k, v in self.waitlist_cooldowns.items()}
        }
        save_bot_state(state)

    def get_region_queue(self, guild_id: int, region: str) -> "RegionQueue | None":
        return self.region_queues.get(guild_id, {}).get(region)

    async def update_waitlist_embed(self, guild_id: int, region: str):
        rq = self.get_region_queue(guild_id, region)
        if not rq:
            return
        channel = self.get_channel(rq.channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(rq.message_id)
            embed, view = build_waitlist_embed(rq, region, self)
            await message.edit(embed=embed, view=view)
        except Exception as e:
            print(f"Error updating waitlist embed [{region}]: {e}")

    async def ensure_waitlist_channel(self, guild: discord.Guild, region: str) -> discord.TextChannel:
        """Get or create the waitlist channel and role for a region."""
        channel_name = WAITLIST_CHANNELS[region]
        role_name = WAITLIST_ROLES[region]

        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name, reason=f"Waitlist role for {region}")

        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, manage_channels=True),
                role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            }
            for staff_role_name in ["Staff", "Moderator", "Admin", "Support"]:
                staff_role = discord.utils.get(guild.roles, name=staff_role_name)
                if staff_role:
                    overwrites[staff_role] = discord.PermissionOverwrite(
                        read_messages=True, send_messages=True, manage_channels=True
                    )
            channel = await guild.create_text_channel(
                channel_name,
                overwrites=overwrites,
                reason=f"Waitlist channel for {region}"
            )

        return channel

# ==================== QUEUE MANAGER ====================

class RegionQueue:
    def __init__(self, guild_id: int, region: str, channel_id: int, message_id: int):
        self.guild_id = guild_id
        self.region = region
        self.channel_id = channel_id
        self.message_id = message_id
        self.is_open = False
        self.queue: list[int] = []
        self.active_tickets: dict[int, int] = {}
        self.last_session: datetime | None = None

# ==================== EMBED BUILDER ====================

def build_waitlist_embed(rq: RegionQueue, region: str, bot: TicketBot):
    view = WaitlistQueueView(bot, region)

    if not rq.is_open:
        embed = discord.Embed(
            title=f"🔴 No Testers Online — {region}",
            description=(
                "No testers for your region are available at this time.\n"
                "You will be pinged when a tester is available.\n"
                "Check back later!"
            ),
            color=discord.Color.red()
        )
        if rq.last_session:
            embed.add_field(
                name="Last testing session",
                value=f"<t:{int(rq.last_session.timestamp())}:F>",
                inline=False
            )
    else:
        total = len(rq.queue)
        embed = discord.Embed(
            title=f"🟢 Tester(s) Available! — {region}",
            description=(
                f"⏱️ The queue updates live.\n"
                f"Use **Leave Queue** if you wish to be removed.\n\n"
                f"**Queue** ({total}):"
            ),
            color=discord.Color.green()
        )
        if rq.queue:
            queue_list = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(rq.queue[:20])])
            embed.add_field(name="\u200b", value=queue_list, inline=False)
        else:
            embed.add_field(name="\u200b", value="*No one in queue yet — be the first!*", inline=False)

        if rq.active_tickets:
            active_list = "\n".join([f"{i+1}. <@{uid}>" for i, uid in enumerate(rq.active_tickets.keys())])
            embed.add_field(name="Active Testers", value=active_list, inline=False)

    return embed, view

# ==================== MODALS ====================

class VerifyAccountModal(discord.ui.Modal, title="Verify Account"):
    username = discord.ui.TextInput(
        label="Minecraft Username",
        placeholder="Enter your Minecraft username",
        min_length=3,
        max_length=16
    )

    def __init__(self, bot: TicketBot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.verified_accounts[interaction.user.id] = self.username.value
        asyncio.create_task(self.bot.save_state())
        await interaction.response.send_message(
            f"✅ Account verified as **{self.username.value}**!",
            ephemeral=True
        )

class WaitlistModal(discord.ui.Modal, title="Join Testing Waitlist"):
    region_input = discord.ui.TextInput(
        label="Region",
        placeholder="NA / EU / AS / AU  (or e.g. Asia, Europe)",
        min_length=2,
        max_length=15
    )
    preferred_server = discord.ui.TextInput(
        label="Preferred Server",
        placeholder="e.g. Hypixel, Minemen, etc.",
        min_length=1,
        max_length=64
    )

    def __init__(self, bot: TicketBot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        guild = interaction.guild

        region = parse_region(self.region_input.value)
        if not region:
            await interaction.response.send_message(
                "❌ Invalid region! Please use: `NA`, `EU`, `AS`, or `AU`.\n"
                "You can also type: `North America`, `Europe`, `Asia`, `Australia`, or `Oceania`.",
                ephemeral=True
            )
            return

        now = datetime.now(timezone.utc)
        tested_at = self.bot.waitlist_cooldowns.get(user.id)
        if tested_at:
            elapsed = now - tested_at
            if elapsed < timedelta(days=COOLDOWN_DAYS):
                remaining = timedelta(days=COOLDOWN_DAYS) - elapsed
                days = remaining.days
                hours, remainder = divmod(remaining.seconds, 3600)
                minutes = remainder // 60
                expires_at = tested_at + timedelta(days=COOLDOWN_DAYS)
                await interaction.response.send_message(
                    f"⏳ You're on cooldown after your last test!\n"
                    f"Time remaining: **{days}d {hours}h {minutes}m**\n"
                    f"Cooldown expires: <t:{int(expires_at.timestamp())}:F>",
                    ephemeral=True
                )
                return

        role_name = WAITLIST_ROLES[region]
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(name=role_name, reason=f"Waitlist access for {region}")
            except Exception as e:
                await interaction.response.send_message(f"❌ Could not create waitlist role: {e}", ephemeral=True)
                return

        try:
            await user.add_roles(role, reason=f"Joined {region} waitlist")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to assign roles!", ephemeral=True)
            return

        try:
            channel = await self.bot.ensure_waitlist_channel(guild, region)
        except Exception as e:
            await interaction.response.send_message(f"❌ Could not set up waitlist channel: {e}", ephemeral=True)
            return

        self.bot.user_regions[user.id] = region
        mc_name = self.bot.verified_accounts.get(user.id, "*Not verified*")

        await interaction.response.send_message(
            f"✅ You've been added to the **{region}** waitlist!\n"
            f"**MC Account:** {mc_name}\n"
            f"**Server:** {self.preferred_server.value}\n\n"
            f"You now have access to {channel.mention}.\n"
            f"Head there and click **Join Queue** when testers are online!",
            ephemeral=True
        )

# ==================== REQUEST CHANNEL VIEW ====================

class RequestTestView(View):
    def __init__(self, bot: TicketBot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Verify Account",
        style=discord.ButtonStyle.grey,
        emoji="🔎",
        row=0,
        custom_id="request_verify_account"
    )
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VerifyAccountModal(self.bot))

    @discord.ui.button(
        label="Enter Waitlist",
        style=discord.ButtonStyle.green,
        emoji="🎫",
        row=0,
        custom_id="request_enter_waitlist"
    )
    async def join_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(WaitlistModal(self.bot))

    @discord.ui.button(
        label="View Cooldown",
        style=discord.ButtonStyle.blurple,
        emoji="⏱️",
        row=0,
        custom_id="request_view_cooldown"
    )
    async def cooldown_button(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        tested_at = self.bot.waitlist_cooldowns.get(user.id)

        if not tested_at:
            await interaction.response.send_message(
                "✅ You have no cooldown — you're free to join the waitlist!", ephemeral=True
            )
            return

        now = datetime.now(timezone.utc)
        elapsed = now - tested_at
        if elapsed >= timedelta(days=COOLDOWN_DAYS):
            await interaction.response.send_message(
                "✅ Your cooldown has expired — you can join the waitlist again!", ephemeral=True
            )
        else:
            remaining = timedelta(days=COOLDOWN_DAYS) - elapsed
            days = remaining.days
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes = remainder // 60
            expires_at = tested_at + timedelta(days=COOLDOWN_DAYS)
            await interaction.response.send_message(
                f"⏳ **Cooldown Active**\n"
                f"Time remaining: **{days}d {hours}h {minutes}m**\n"
                f"Expires: <t:{int(expires_at.timestamp())}:F>",
                ephemeral=True
            )

# ==================== WAITLIST CHANNEL VIEW ====================

class WaitlistQueueView(View):
    def __init__(self, bot: TicketBot, region: str):
        super().__init__(timeout=None)
        self.bot = bot
        self.region = region

        join_btn = Button(
            label="Join Queue",
            style=discord.ButtonStyle.green,
            emoji="🎫",
            row=0,
            custom_id=f"join_queue_{region}"
        )
        leave_btn = Button(
            label="Leave Queue",
            style=discord.ButtonStyle.red,
            emoji="🚪",
            row=1,
            custom_id=f"leave_queue_{region}"
        )

        async def join_cb(interaction: discord.Interaction, r=region):
            await self._join(interaction, r)

        async def leave_cb(interaction: discord.Interaction, r=region):
            await self._leave(interaction, r)

        join_btn.callback = join_cb
        leave_btn.callback = leave_cb

        self.add_item(join_btn)
        self.add_item(leave_btn)

    async def _join(self, interaction: discord.Interaction, region: str):
        guild_queues = self.bot.region_queues.get(interaction.guild_id, {})
        rq = guild_queues.get(region)
        user = interaction.user

        if not rq or not rq.is_open:
            await interaction.response.send_message("❌ The queue is currently closed!", ephemeral=True)
            return

        if user.id in rq.active_tickets:
            await interaction.response.send_message("❌ You already have an active ticket!", ephemeral=True)
            return

        if user.id in rq.queue:
            await interaction.response.send_message("⏳ You're already in the queue!", ephemeral=True)
            return

        rq.queue.append(user.id)
        position = len(rq.queue)

        await interaction.response.send_message(
            f"✅ You've joined the **{region}** queue!\n"
            f"**Position:** #{position}\nWait for staff to call `/next`.",
            ephemeral=True
        )
        await self.bot.update_waitlist_embed(interaction.guild_id, region)

    async def _leave(self, interaction: discord.Interaction, region: str):
        guild_queues = self.bot.region_queues.get(interaction.guild_id, {})
        rq = guild_queues.get(region)
        user = interaction.user

        if not rq or user.id not in rq.queue:
            await interaction.response.send_message("❌ You're not in the queue!", ephemeral=True)
            return

        rq.queue.remove(user.id)
        await interaction.response.send_message("👋 You've left the queue.", ephemeral=True)
        await self.bot.update_waitlist_embed(interaction.guild_id, region)

# ==================== TICKET CONTROLS ====================

class TicketControls(View):
    def __init__(self, bot: TicketBot, user_id: int, guild_id: int, region: str, ticket_channel_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.user_id = user_id
        self.guild_id = guild_id
        self.region = region
        self.ticket_channel_id = ticket_channel_id

        close_btn = Button(
            label="Close Ticket",
            style=discord.ButtonStyle.red,
            emoji="🔒",
            row=0,
            custom_id=f"ticket_close_{ticket_channel_id}"
        )
        claim_btn = Button(
            label="Claim Ticket",
            style=discord.ButtonStyle.blurple,
            emoji="👋",
            row=0,
            custom_id=f"ticket_claim_{ticket_channel_id}"
        )

        close_btn.callback = self._close_ticket
        claim_btn.callback = self._claim_ticket

        self.add_item(close_btn)
        self.add_item(claim_btn)

    async def _close_ticket(self, interaction: discord.Interaction):
        guild_queues = self.bot.region_queues.get(self.guild_id, {})
        rq = guild_queues.get(self.region)

        is_staff = interaction.user.guild_permissions.manage_channels
        is_owner = interaction.user.id == self.user_id

        if not (is_staff or is_owner):
            await interaction.response.send_message("❌ No permission!", ephemeral=True)
            return

        if rq and self.user_id in rq.active_tickets:
            del rq.active_tickets[self.user_id]

        await interaction.response.send_message("🔒 Closing ticket...")
        await asyncio.sleep(2)
        await interaction.channel.delete()

    async def _claim_ticket(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Staff only!", ephemeral=True)
            return

        await interaction.response.send_message(
            f"👋 {interaction.user.mention} claimed this ticket!",
            allowed_mentions=discord.AllowedMentions(users=True)
        )

# ==================== RANK SELECT (AUTO-SAVES TO LEADERBOARD) ====================

class RankSelect(Select):
    RANKS = [
        discord.SelectOption(label="LT5", description="Lower Tier 5", emoji="🥉"),
        discord.SelectOption(label="HT5", description="Higher Tier 5", emoji="🥈"),
        discord.SelectOption(label="LT4", description="Lower Tier 4", emoji="🥇"),
        discord.SelectOption(label="HT4", description="Higher Tier 4", emoji="🏅"),
        discord.SelectOption(label="LT3", description="Lower Tier 3", emoji="💎"),
    ]

    def __init__(self, bot: TicketBot, target_user_id: int, guild_id: int, region: str):
        super().__init__(
            placeholder="Select a rank...",
            min_values=1,
            max_values=1,
            options=self.RANKS,
            custom_id=f"rank_select_{region}_{target_user_id}"
        )
        self.bot = bot
        self.target_user_id = target_user_id
        self.guild_id = guild_id
        self.region = region

    async def callback(self, interaction: discord.Interaction):
        rank = self.values[0]
        guild_queues = self.bot.region_queues.get(self.guild_id, {})
        rq = guild_queues.get(self.region)
        guild = interaction.guild

        user = guild.get_member(self.target_user_id)
        if not user:
            try:
                user = await guild.fetch_member(self.target_user_id)
            except Exception:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
                return

        # Give rank role in Discord
        rank_role = discord.utils.get(guild.roles, name=rank)
        if not rank_role:
            try:
                rank_role = await guild.create_role(
                    name=rank, color=discord.Color.gold(), reason=f"Test result: {rank}"
                )
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to create roles!", ephemeral=True)
                return
            except Exception as e:
                await interaction.response.send_message(f"❌ Error creating role: {e}", ephemeral=True)
                return

        try:
            await user.add_roles(rank_role, reason=f"Test result: {rank}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to give roles! My role must be higher than the rank role.",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Error giving role: {e}", ephemeral=True)
            return

        # Send results embed to results channel
        mc_name = self.bot.verified_accounts.get(self.target_user_id, user.name)
        try:
            await send_results_embed(interaction, user, mc_name, self.region, rank, interaction.user)
        except Exception as e:
            print(f"Error sending results embed: {e}")

        # Auto-save to website leaderboard
        success = add_or_update_player(mc_name, rank)
        leaderboard_msg = (
            f"\n🌐 **Leaderboard updated!** {mc_name} is now **{rank}** on the website."
            if success else
            "\n⚠️ Could not update website leaderboard (check JSONBin config)."
        )

        # Remove waitlist role
        waitlist_role_name = WAITLIST_ROLES[self.region]
        waitlist_role = discord.utils.get(guild.roles, name=waitlist_role_name)
        if waitlist_role and waitlist_role in user.roles:
            try:
                await user.remove_roles(waitlist_role, reason="Test completed — cooldown started")
            except Exception as e:
                print(f"Could not remove waitlist role: {e}")

        # Start cooldown and persist it
        self.bot.waitlist_cooldowns[self.target_user_id] = datetime.now(timezone.utc)
        asyncio.create_task(self.bot.save_state())

        # Clean up
        if rq:
            rq.active_tickets.pop(self.target_user_id, None)
            rq.last_session = datetime.now(timezone.utc)

        await interaction.response.send_message(
            f"🎉 **RESULT**\n{user.mention} has been awarded **{rank}**!"
            f"{leaderboard_msg}\n"
            f"Their `{waitlist_role_name}` role has been removed.\n"
            f"They can re-apply in **{COOLDOWN_DAYS} days**.\n\n"
            f"Closing ticket in 5 seconds..."
        )

        await self.bot.update_waitlist_embed(self.guild_id, self.region)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class RankSelectView(View):
    def __init__(self, bot: TicketBot, target_user_id: int, guild_id: int, region: str):
        super().__init__(timeout=60)
        self.add_item(RankSelect(bot, target_user_id, guild_id, region))

# ==================== HIGH RANK SELECT (MANUAL - NO AUTO-SAVE) ====================

class HighRankSelect(Select):
    RANKS = [
        discord.SelectOption(label="HT1", description="Higher Tier 1 — Best", emoji="👑"),
        discord.SelectOption(label="LT1", description="Lower Tier 1", emoji="💠"),
        discord.SelectOption(label="HT2", description="Higher Tier 2", emoji="🔷"),
        discord.SelectOption(label="LT2", description="Lower Tier 2", emoji="🔹"),
        discord.SelectOption(label="HT3", description="Higher Tier 3", emoji="✨"),
    ]

    def __init__(self, bot: TicketBot, target_user_id: int, guild_id: int, region: str):
        super().__init__(
            placeholder="Select a high rank...",
            min_values=1,
            max_values=1,
            options=self.RANKS,
            custom_id=f"high_rank_select_{region}_{target_user_id}"
        )
        self.bot = bot
        self.target_user_id = target_user_id
        self.guild_id = guild_id
        self.region = region

    async def callback(self, interaction: discord.Interaction):
        mod_role = discord.utils.get(interaction.guild.roles, name="Moderator")
        if not mod_role or mod_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Moderator only!", ephemeral=True)
            return

        rank = self.values[0]
        guild_queues = self.bot.region_queues.get(self.guild_id, {})
        rq = guild_queues.get(self.region)
        guild = interaction.guild

        user = guild.get_member(self.target_user_id)
        if not user:
            try:
                user = await guild.fetch_member(self.target_user_id)
            except Exception:
                await interaction.response.send_message("❌ User not found!", ephemeral=True)
                return

        # Give rank role in Discord
        rank_role = discord.utils.get(guild.roles, name=rank)
        if not rank_role:
            try:
                rank_role = await guild.create_role(
                    name=rank, color=discord.Color.purple(), reason=f"High rank result: {rank}"
                )
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to create roles!", ephemeral=True)
                return
            except Exception as e:
                await interaction.response.send_message(f"❌ Error creating role: {e}", ephemeral=True)
                return

        try:
            await user.add_roles(rank_role, reason=f"High rank result: {rank}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to give roles! My role must be higher than the rank role.",
                ephemeral=True
            )
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Error giving role: {e}", ephemeral=True)
            return

        # Send results embed to results channel
        mc_name = self.bot.verified_accounts.get(self.target_user_id, user.name)
        try:
            await send_results_embed(interaction, user, mc_name, self.region, rank, interaction.user)
        except Exception as e:
            print(f"Error sending results embed: {e}")

        # Remove waitlist role and start cooldown
        waitlist_role_name = WAITLIST_ROLES[self.region]
        waitlist_role = discord.utils.get(guild.roles, name=waitlist_role_name)
        if waitlist_role and waitlist_role in user.roles:
            try:
                await user.remove_roles(waitlist_role, reason="High rank test completed — cooldown started")
            except Exception as e:
                print(f"Could not remove waitlist role: {e}")

        self.bot.waitlist_cooldowns[self.target_user_id] = datetime.now(timezone.utc)
        asyncio.create_task(self.bot.save_state())

        if rq:
            rq.active_tickets.pop(self.target_user_id, None)
            rq.last_session = datetime.now(timezone.utc)

        await interaction.response.send_message(
            f"👑 **HIGH RANK RESULT**\n{user.mention} has been awarded **{rank}**!\n"
            f"⚠️ **This rank was NOT auto-saved to the website.**\n"
            f"Use `/add_rank` if you want to add it to the leaderboard.\n"
            f"Their `{waitlist_role_name}` role has been removed.\n"
            f"They can re-apply in **{COOLDOWN_DAYS} days**.\n\n"
            f"Closing ticket in 5 seconds..."
        )

        await self.bot.update_waitlist_embed(self.guild_id, self.region)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class HighRankSelectView(View):
    def __init__(self, bot: TicketBot, target_user_id: int, guild_id: int, region: str):
        super().__init__(timeout=60)
        self.add_item(HighRankSelect(bot, target_user_id, guild_id, region))

# ==================== BOT INSTANCE ====================

bot = TicketBot()

@bot.event
async def on_ready():
    print(f'✅ Bot online: {bot.user}')
    print(f'🌐 In {len(bot.guilds)} guilds')
    await bot.load_state()

# ==================== COMMANDS ====================

@bot.tree.command(name="setup_waitlist", description="Post the Evaluation Testing Waitlist embed in this channel (Staff only)")
@app_commands.checks.has_permissions(manage_channels=True)
async def setup_waitlist(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📝 Evaluation Testing Waitlist",
        description=(
            "Upon applying, you will be added to a waitlist channel.\n"
            "Here you will be pinged when a tester of your region is available.\n\n"
            "• **Region** should be the region of the server you wish to test on\n"
            "• **Username** should be the name of the account you will be testing on\n\n"
            "🔴 **Failure to provide authentic information will result in a denied test.**"
        ),
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=RequestTestView(bot))
    await interaction.response.send_message("✅ Waitlist embed posted!", ephemeral=True)

@bot.tree.command(name="queue_open", description="Open the test queue for a region (Staff only)")
@app_commands.describe(region="Region to open: NA, EU, AS, AU")
@app_commands.checks.has_permissions(manage_channels=True)
async def queue_open(interaction: discord.Interaction, region: str):
    parsed = parse_region(region)
    if not parsed:
        await interaction.response.send_message("❌ Invalid region! Use: NA, EU, AS, AU", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    channel = await bot.ensure_waitlist_channel(guild, parsed)

    guild_queues = bot.region_queues.get(interaction.guild_id, {})
    rq = guild_queues.get(parsed)

    if rq:
        rq.is_open = True
        await bot.update_waitlist_embed(interaction.guild_id, parsed)
        await channel.send(f"@here 🟢 Testers are now available for **{parsed}**!")
        await interaction.followup.send(f"✅ **{parsed}** queue reopened!", ephemeral=True)
        return

    dummy = RegionQueue(interaction.guild_id, parsed, channel.id, 0)
    dummy.is_open = True
    embed, view = build_waitlist_embed(dummy, parsed, bot)
    message = await channel.send(content="@here", embed=embed, view=view)

    rq = RegionQueue(interaction.guild_id, parsed, channel.id, message.id)
    rq.is_open = True

    if interaction.guild_id not in bot.region_queues:
        bot.region_queues[interaction.guild_id] = {}
    bot.region_queues[interaction.guild_id][parsed] = rq

    await interaction.followup.send(f"✅ **{parsed}** queue opened in {channel.mention}!", ephemeral=True)

@bot.tree.command(name="queue_close", description="Close the test queue for a region (Staff only)")
@app_commands.describe(region="Region to close: NA, EU, AS, AU")
@app_commands.checks.has_permissions(manage_channels=True)
async def queue_close(interaction: discord.Interaction, region: str):
    parsed = parse_region(region)
    if not parsed:
        await interaction.response.send_message("❌ Invalid region! Use: NA, EU, AS, AU", ephemeral=True)
        return

    guild_queues = bot.region_queues.get(interaction.guild_id, {})
    rq = guild_queues.get(parsed)

    if not rq:
        await interaction.response.send_message(f"❌ No active queue for **{parsed}**!", ephemeral=True)
        return

    rq.is_open = False
    rq.last_session = datetime.now(timezone.utc)
    await bot.update_waitlist_embed(interaction.guild_id, parsed)
    await interaction.response.send_message(f"🔴 **{parsed}** queue closed!", ephemeral=True)

@bot.tree.command(name="queue_status", description="Check queue status for a region")
@app_commands.describe(region="Region to check: NA, EU, AS, AU")
async def queue_status(interaction: discord.Interaction, region: str):
    parsed = parse_region(region)
    if not parsed:
        await interaction.response.send_message("❌ Invalid region! Use: NA, EU, AS, AU", ephemeral=True)
        return

    guild_queues = bot.region_queues.get(interaction.guild_id, {})
    rq = guild_queues.get(parsed)

    if not rq:
        await interaction.response.send_message(f"❌ No queue found for **{parsed}**!", ephemeral=True)
        return

    status = "🟢 Open" if rq.is_open else "🔴 Closed"
    await interaction.response.send_message(
        f"**Region:** {parsed}\n**Status:** {status}\n"
        f"**Waiting:** {len(rq.queue)}\n**Active:** {len(rq.active_tickets)}",
        ephemeral=True
    )

@bot.tree.command(name="next", description="Open ticket for next person in a region's queue (Staff only)")
@app_commands.describe(region="Region to pull from: NA, EU, AS, AU")
@app_commands.checks.has_permissions(manage_channels=True)
async def next_command(interaction: discord.Interaction, region: str):
    parsed = parse_region(region)
    if not parsed:
        await interaction.response.send_message("❌ Invalid region! Use: NA, EU, AS, AU", ephemeral=True)
        return

    guild_queues = bot.region_queues.get(interaction.guild_id, {})
    rq = guild_queues.get(parsed)

    if not rq:
        await interaction.response.send_message(f"❌ No active queue for **{parsed}**!", ephemeral=True)
        return

    if not rq.queue:
        await interaction.response.send_message(f"❌ **{parsed}** queue is empty!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        guild = interaction.guild
        user_id = rq.queue.pop(0)

        user = guild.get_member(user_id)
        if not user:
            try:
                user = await guild.fetch_member(user_id)
            except Exception:
                await interaction.followup.send("❌ User left the server! Removed from queue.", ephemeral=True)
                await bot.update_waitlist_embed(interaction.guild_id, parsed)
                return

        category = discord.utils.get(guild.categories, name="Test Tickets")
        if not category:
            try:
                category = await guild.create_category("Test Tickets")
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to create category: {e}", ephemeral=True)
                rq.queue.insert(0, user_id)
                return

        if interaction.guild_id not in bot.ticket_counter:
            bot.ticket_counter[interaction.guild_id] = 0
        bot.ticket_counter[interaction.guild_id] += 1
        ticket_num = bot.ticket_counter[interaction.guild_id]

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        for staff_role_name in ["Staff", "Moderator", "Admin", "Support"]:
            staff_role = discord.utils.get(guild.roles, name=staff_role_name)
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_channels=True, manage_messages=True
                )
                break

        try:
            channel = await guild.create_text_channel(
                f"test-{ticket_num:04d}",
                category=category,
                overwrites=overwrites,
                topic=f"Test for {user.name} | Region: {parsed} | ID: {user_id}",
                reason=f"Test ticket for {user.name} [{parsed}]"
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create channel: {e}", ephemeral=True)
            rq.queue.insert(0, user_id)
            return

        rq.active_tickets[user_id] = channel.id

        mc_name = bot.verified_accounts.get(user_id, "*Not verified*")
        embed = discord.Embed(
            title=f"🎫 Test Ticket #{ticket_num:04d}",
            description=(
                f"Welcome {user.mention}!\n\n"
                f"Please wait for staff to review your test.\n\n"
                f"**Staff:** Use `/result` to grade and close."
            ),
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Tester", value=f"{user.name} ({user.id})", inline=True)
        embed.add_field(name="Region", value=parsed, inline=True)
        embed.add_field(name="MC Account", value=mc_name, inline=True)

        try:
            await channel.send(
                content=f"{user.mention}",
                embed=embed,
                view=TicketControls(bot, user_id, interaction.guild_id, parsed, channel.id)
            )
        except Exception as e:
            print(f"Error sending ticket message: {e}")

        try:
            await user.send(f"✅ Your **{parsed}** test ticket is ready: {channel.mention}")
        except Exception:
            pass

        await bot.update_waitlist_embed(interaction.guild_id, parsed)
        await interaction.followup.send(f"✅ Opened ticket for {user.mention}: {channel.mention}", ephemeral=True)

    except Exception as e:
        print(f"Error in /next: {traceback.format_exc()}")
        await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

@bot.tree.command(name="result", description="Give user their rank role and auto-save to leaderboard (Staff only)")
@app_commands.checks.has_permissions(manage_channels=True)
async def result_command(interaction: discord.Interaction):
    current_channel_id = interaction.channel_id

    target_user_id = None
    target_region = None
    for region, rq in bot.region_queues.get(interaction.guild_id, {}).items():
        for uid, cid in rq.active_tickets.items():
            if cid == current_channel_id:
                target_user_id = uid
                target_region = region
                break
        if target_user_id:
            break

    if not target_user_id or not target_region:
        await interaction.response.send_message("❌ This command only works inside a ticket channel!", ephemeral=True)
        return

    await interaction.response.send_message(
        f"🏆 Select the rank to award ({target_region}):",
        view=RankSelectView(bot, target_user_id, interaction.guild_id, target_region),
        ephemeral=True
    )

@bot.tree.command(name="highresults", description="Give user a high rank role and close ticket (Moderator only)")
async def highresults_command(interaction: discord.Interaction):
    mod_role = discord.utils.get(interaction.guild.roles, name="Moderator")
    if not mod_role or mod_role not in interaction.user.roles:
        await interaction.response.send_message("❌ This command is for Moderators only!", ephemeral=True)
        return

    current_channel_id = interaction.channel_id

    target_user_id = None
    target_region = None
    for region, rq in bot.region_queues.get(interaction.guild_id, {}).items():
        for uid, cid in rq.active_tickets.items():
            if cid == current_channel_id:
                target_user_id = uid
                target_region = region
                break
        if target_user_id:
            break

    if not target_user_id or not target_region:
        await interaction.response.send_message("❌ This command only works inside a ticket channel!", ephemeral=True)
        return

    await interaction.response.send_message(
        f"👑 Select the high rank to award ({target_region}):",
        view=HighRankSelectView(bot, target_user_id, interaction.guild_id, target_region),
        ephemeral=True
    )

@bot.tree.command(name="add_rank", description="Manually add/update a player on the website leaderboard (Staff only)")
@app_commands.describe(
    minecraft_username="The player's Minecraft username",
    tier="The tier to assign (HT1, LT1, HT2, LT2, HT3, LT3, HT4, LT4, HT5, LT5)"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def add_rank(interaction: discord.Interaction, minecraft_username: str, tier: str):
    valid_tiers = ['HT1', 'LT1', 'HT2', 'LT2', 'HT3', 'LT3', 'HT4', 'LT4', 'HT5', 'LT5']

    if tier not in valid_tiers:
        await interaction.response.send_message(
            f"❌ Invalid tier! Use one of: {', '.join(valid_tiers)}",
            ephemeral=True
        )
        return

    success = add_or_update_player(minecraft_username, tier)

    if success:
        await interaction.response.send_message(
            f"✅ **{minecraft_username}** has been added/updated to **{tier}** on the website leaderboard!",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ Failed to update leaderboard. Check JSONBin configuration.",
            ephemeral=True
        )

# ==================== ERROR HANDLERS ====================

@result_command.error
@next_command.error
@queue_open.error
@queue_close.error
@setup_waitlist.error
@add_rank.error
async def perm_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Need Manage Channels permission!", ephemeral=True)

# ==================== RUN ====================

token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("❌ ERROR: Set DISCORD_TOKEN environment variable")
    exit(1)

try:
    bot.run(token)
except Exception as e:
    print(f"Fatal error: {e}")
