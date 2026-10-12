"""Connect successful countryball catches to Verity Achievements."""

import logging
from functools import wraps

log = logging.getLogger("ballsdex.packages.achievements")


def install_catch_integration(bot) -> None:
    """Check achievements after catches without modifying BallsDex's messages."""
    from ballsdex.packages.countryballs.countryball import BallSpawnView

    catch_ball = BallSpawnView.catch_ball
    if getattr(catch_ball, "_verity_achievements_wrapped", False):
        return

    @wraps(catch_ball)
    async def catch_ball_with_achievements(self, user, *, player=None, guild=None):
        result = await catch_ball(self, user, player=player, guild=guild)

        try:
            from bd_models.models import Player
            from .achievement_service import check_achievements

            achievement_player = player
            if achievement_player is None:
                achievement_player, _ = await Player.objects.aget_or_create(
                    discord_id=user.id
                )

            message = getattr(self, "message", None)
            channel = getattr(message, "channel", None)
            await check_achievements(
                achievement_player,
                bot=bot,
                channel=channel,
            )
        except Exception:
            log.exception("Could not check achievements after a catch")

        return result

    catch_ball_with_achievements._verity_achievements_wrapped = True
    BallSpawnView.catch_ball = catch_ball_with_achievements
    log.info("Installed Verity Achievements catch integration")
