        self._update_buttons()
        embed, file = self.make_page()
        await interaction.response.edit_message(
            embed=embed,
            attachments=[file] if file else [],
            view=self,
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page > 0:
            self.page -= 1
        await self.show_page(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        if self.page < len(self.achievements) - 1:
            self.page += 1
        await self.show_page(interaction)

    async def on_timeout(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.HTTPException, discord.NotFound):
                pass


class AchievementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ballsdex_ball_caught(self, event):
        """Check achievement progress after BallsDex reports a successful catch."""
        from .achievement_service import check_achievements

        spawn_message = getattr(event.view, "message", None)
        channel = getattr(spawn_message, "channel", None)
        await check_achievements(event.player, None, self.bot, channel)

    async def _currency_name(self):
        """Read the currency label configured in BallsDex's settings."""
        try:
            from django.apps import apps

            for model in apps.get_models():
                field_names = {field.name for field in model._meta.get_fields()}
                if "currency_name" not in field_names:
                    continue
                settings = await sync_to_async(model.objects.first)()
                if settings:
                    name = getattr(settings, "currency_name", None)
                    if name:
                        return str(name)
        except (ImportError, AttributeError, RuntimeError):
            pass
        return "currency"

    @app_commands.command(
        name="achievements",
        description="See your achievements!",
    )
    async def achievements(self, interaction: discord.Interaction):
        from .models import Achievement, AchievementCompletion

        achievements = await sync_to_async(list)(
            Achievement.objects.filter(enabled=True)
            .prefetch_related("rewards__ball", "required_balls")
            .order_by("id")
        )

        if not achievements:
            await interaction.response.send_message("out of stock")
            return

        currency_name = await self._currency_name()
        completed_ids = set(await sync_to_async(list)(
            AchievementCompletion.objects.filter(
                discord_id=interaction.user.id,
                achievement__in=achievements,
            ).values_list("achievement_id", flat=True)
        ))
        view = AchievementPages(
            achievements=achievements,
            currency_name=currency_name,
            owner_id=interaction.user.id,
            completed_ids=completed_ids,
        )
        embed, file = view.make_page()

        if file:
            await interaction.response.send_message(
                embed=embed,
                file=file,
                view=view,
            )
        else:
            await interaction.response.send_message(
                embed=embed,
                view=view,
            )

        view.message = await interaction.original_response()


async def setup(bot):
    await bot.add_cog(AchievementCog(bot))
