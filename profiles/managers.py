from django.db import models, transaction
from django.apps import apps

from datetime import datetime
import pytz

from common.osu import apiv1, utils
from common.osu.enums import BeatmapStatus

class BaseOsuUserManager(models.Manager):
    @transaction.atomic
    def create_or_update(self, user_string, gamemode):
        # fetch user data
        data = apiv1.get_user(user_string, user_id_type="string", gamemode=gamemode)
        if not data:
            data = apiv1.get_user(user_string, user_id_type="id", gamemode=gamemode)

        if not data:
            return None  # TODO: replace these type of "return None"s with exception raising

        # get or create OsuUser model
        try:
            osu_user = self.select_for_update().get(id=data["user_id"])
            if not data:
                # user restricted probably
                osu_user.disabled = True
                osu_user.save()
                return None
        except self.model.DoesNotExist:
            osu_user = self.model(id=data["user_id"])

        # update fields
        osu_user.username = data["username"]
        osu_user.country = data["country"]
        osu_user.join_date = datetime.strptime(data["join_date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
        osu_user.disabled = False

        # save and return OsuUser model
        osu_user.save()

        # need to get model via apps to avoid circular import
        user_stats_model = apps.get_model("profiles.UserStats")
        user_stats = user_stats_model.objects.create_or_update_from_data(data, gamemode)
        # osu_user is saved before stats so it can be referenced as a foreign key
        osu_user.stats.add(user_stats, bulk=True)

        return osu_user

class OsuUserQuerySet(models.QuerySet):
    def non_restricted(self):
        return self.filter(disabled=False)

class OsuUserManager(BaseOsuUserManager.from_queryset(OsuUserQuerySet)):
    pass

class BaseUserStatsManager(models.Manager):
    @transaction.atomic
    def create_or_update_from_data(self, user_data, gamemode):
        # add user_data from passed deserialised osu! api response dict
        # gamemode required as parameter because osu! api doesn't return the mode you queried for
        # get or create UserStats model
        try:
            user_stats = self.select_for_update().get(user_id=user_data["user_id"], gamemode=gamemode)
        except self.model.DoesNotExist:
            user_stats = self.model(user_id=user_data["user_id"])
            user_stats.gamemode = gamemode

        # update fields
        user_stats.playcount = int(user_data["playcount"])
        user_stats.playtime = int(user_data["total_seconds_played"])
        user_stats.level = float(user_data["level"])
        user_stats.ranked_score = int(user_data["ranked_score"])
        user_stats.total_score = int(user_data["total_score"])
        user_stats.rank = int(user_data["pp_rank"])
        user_stats.country_rank = int(user_data["pp_country_rank"])
        user_stats.pp = float(user_data["pp_raw"])
        user_stats.accuracy = float(user_data["accuracy"])
        user_stats.count_300 = int(user_data["count300"])
        user_stats.count_100 = int(user_data["count100"])
        user_stats.count_50 = int(user_data["count50"])
        user_stats.count_rank_ss = int(user_data["count_rank_ss"])
        user_stats.count_rank_ssh = int(user_data["count_rank_ssh"])
        user_stats.count_rank_s = int(user_data["count_rank_s"])
        user_stats.count_rank_sh = int(user_data["count_rank_sh"])
        user_stats.count_rank_a = int(user_data["count_rank_a"])

        # need to get model via apps to avoid circular import
        score_model = apps.get_model("profiles.Score")
        scores = score_model.objects.create_or_update_from_data(apiv1.get_user_best(user_stats.user_id, gamemode=gamemode, limit=100), user_stats.id)
        
        # calculate osuchan data, add scores, and save
        user_stats.process_and_add_scores(*scores)

        return user_stats

class UserStatsQuerySet(models.QuerySet):
    def non_restricted(self):
        return self.filter(user__disabled=False)

class UserStatsManager(BaseUserStatsManager.from_queryset(UserStatsQuerySet)):
    pass

class BeatmapManager(models.Manager):
    @transaction.atomic
    def create_or_update(self, beatmap_id):
        # get or create Beatmap model
        try:
            beatmap = self.select_for_update().get(id=beatmap_id)
        except self.model.DoesNotExist:
            beatmap = self.model(id=beatmap_id)
        
        if beatmap.status not in (BeatmapStatus.RANKED, BeatmapStatus.APPROVED):
            # fetch beatmap data if not in database and ranked/approved
            data = apiv1.get_beatmaps(beatmap_id=beatmap_id)[0]
            
            # update fields
            beatmap.set_id = int(data["beatmapset_id"])
            beatmap.artist = data["artist"]
            beatmap.title = data["title"]
            beatmap.difficulty_name = data["version"]
            beatmap.gamemode = int(data["mode"])
            beatmap.status = int(data["approved"])
            beatmap.creator_name = data["creator"]
            beatmap.bpm = float(data["bpm"])
            beatmap.max_combo = int(data["max_combo"]) if data["max_combo"] != None else None
            beatmap.drain_time = int(data["hit_length"])
            beatmap.total_time = int(data["total_length"])
            beatmap.circle_size = float(data["diff_size"])
            beatmap.overall_difficulty = float(data["diff_overall"])
            beatmap.approach_rate = float(data["diff_approach"])
            beatmap.health_drain = float(data["diff_drain"])
            beatmap.star_rating = float(data["difficultyrating"])
            beatmap.last_updated = datetime.strptime(data["last_update"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)
            
            # foreign key ids
            beatmap.creator_id = int(data["creator_id"])

        # save and return Beatmap model
        beatmap.save()
        return beatmap

class BaseScoreManager(models.Manager):
    @transaction.atomic
    def create_or_update(self, beatmap_id, user_id, gamemode):
        # fetch scores for player on a beatmap
        user_stats_model = apps.get_model("profiles.UserStats")
        user_stats = user_stats_model.objects.select_for_update().get(user__id=user_id, gamemode=gamemode)
        
        data = apiv1.get_scores(beatmap_id=beatmap_id, user_id=user_id, gamemode=gamemode)
        scores = self.create_or_update_from_data(data, user_stats.id, beatmap_id=beatmap_id)

        user_stats.process_and_add_scores(*scores)
        return scores

    @transaction.atomic
    def create_or_update_from_data(self, score_data_list, user_stats_id, beatmap_id=None):
        # add list of scores from passed deserialised osu! api response (dicts)
        scores = []

        # need to get model via apps to avoid circular import
        beatmap_model = apps.get_model("profiles.Beatmap")
        
        for score_data in score_data_list:
            score_beatmap_id = beatmap_id or int(score_data["beatmap_id"])
            # get or create Score model
            try:
                # TODO: check if this foreign key lookup for user_id has a large impact (probably doesnt because of indexes)
                score = self.select_for_update().get(user_stats__user_id=int(score_data["user_id"]), beatmap_id=score_beatmap_id, mods=int(score_data["enabled_mods"]))
                # check if we actually need to update this score
                if score.date == datetime.strptime(score_data["date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC):
                    scores.append(score)
                    continue
            except self.model.DoesNotExist:
                score = self.model()
            
            # update fields
            score.score = int(score_data["score"])
            score.count_300 = int(score_data["count300"])
            score.count_100 = int(score_data["count100"])
            score.count_50 = int(score_data["count50"])
            score.count_miss = int(score_data["countmiss"])
            score.count_geki = int(score_data["countgeki"])
            score.count_katu = int(score_data["countkatu"])
            score.best_combo = int(score_data["maxcombo"])
            score.perfect = bool(int(score_data["perfect"]))
            score.mods = int(score_data["enabled_mods"])
            score.rank = score_data["rank"]
            score.pp = float(score_data["pp"])
            score.date = datetime.strptime(score_data["date"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=pytz.UTC)

            # foreign keys
            beatmap = beatmap_model.objects.create_or_update(score_beatmap_id)
            score.beatmap = beatmap
            score.user_stats_id = user_stats_id
            
            # convenience fields
            score.accuracy = utils.get_accuracy(score.count_300, score.count_100, score.count_50, score.count_miss, score.count_katu, score.count_geki)
            score.bpm = utils.get_bpm(beatmap.bpm, score.mods)
            score.length = utils.get_length(beatmap.drain_time, score.mods)
            score.circle_size = utils.get_cs(beatmap.circle_size, score.mods)
            score.approach_rate = utils.get_ar(beatmap.approach_rate, score.mods)
            score.overall_difficulty = utils.get_od(beatmap.overall_difficulty, score.mods)

            # not using bulk queries because they dont call .save() and we need that for oppai calcs
            score.process()
            scores.append(score)

        return scores

class ScoreQuerySet(models.QuerySet):
    def non_restricted(self):
        return self.filter(user_stats__user__disabled=False)

    def unique_maps(self):
        """
        Queryset that returns distinct on beatmap_id prioritising highest pp.
        Remember to use at end of query to not unintentially filter out scores before primary filtering.
        """
        # I do not like this query, but i cannot for the life of me figure out how to get django to SELECT FROM (...subquery...)
        # It seems after testing, the raw sql of these two queries (current one vs select from subquery), they were generally the same speed (on a tiny dataset)
        # I simply want to `return self.order_by("beatmap_id", "-pp").distinct("beatmap_id").order_by("-pp")`, but this doesnt translate to a subquery
        # TODO: figure this out
        return self.filter(
            id__in=models.Subquery(self.all().order_by("beatmap_id", "-pp").distinct("beatmap_id").values("id"))
        ).order_by("-pp")

class ScoreManager(BaseScoreManager.from_queryset(ScoreQuerySet)):
    pass
