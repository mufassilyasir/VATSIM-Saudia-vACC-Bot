import asyncio
from datetime import datetime
import random
import re
import typing as t
from enum import Enum

import discord
import wavelink
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID"))



URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
}


React_Options = {
    "⛔" : 0,
    "1️⃣" : 1,
    "♾️" : 2  
}


class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class QueueIsEmpty(commands.CommandError):
    pass


class NoTracksFound(commands.CommandError):
    pass


class PlayerIsAlreadyPaused(commands.CommandError):
    pass


class NoMoreTracks(commands.CommandError):
    pass


class NoPreviousTracks(commands.CommandError):
    pass


class InvalidRepeatMode(commands.CommandError):
    pass

class AlreadyDisconnectedFromChannel(commands.CommandError):
    pass


class RepeatMode(Enum):
    NONE = 0
    ONE = 1
    ALL = 2


class Queue:
    def __init__(self):
        self._queue = []
        self.position = 0
        self.repeat_mode = RepeatMode.NONE

    @property
    def is_empty(self):
        return not self._queue

    @property
    def current_track(self):
        if not self._queue:
            raise QueueIsEmpty

        if self.position <= len(self._queue) - 1:
            return self._queue[self.position]

    @property
    def upcoming(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[self.position + 1:]

    @property
    def history(self):
        if not self._queue:
            raise QueueIsEmpty

        return self._queue[:self.position]

    @property
    def length(self):
        return len(self._queue)

    def add(self, *args):
        self._queue.extend(args)

    def get_next_track(self):
        if not self._queue:
            raise QueueIsEmpty

        self.position += 1

        if self.position < 0:
            return None
        elif self.position > len(self._queue) - 1:
            if self.repeat_mode == RepeatMode.ALL:
                self.position = 0
            else:
                return None

        return self._queue[self.position]

    def shuffle(self):
        if not self._queue:
            raise QueueIsEmpty

        upcoming = self.upcoming
        random.shuffle(upcoming)
        self._queue = self._queue[:self.position + 1]
        self._queue.extend(upcoming)

    def set_repeat_mode(self, mode):
        if mode == "none":
            self.repeat_mode = RepeatMode.NONE
        elif mode == "1":
            self.repeat_mode = RepeatMode.ONE
        elif mode == "all":
            self.repeat_mode = RepeatMode.ALL

    def empty(self):
        self._queue.clear()
        self.position = 0


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue = Queue()

    async def connect(self, ctx, channel=None):
        if self.is_connected:
            raise AlreadyConnectedToChannel

        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        await super().connect(channel.id)
        return channel

    async def teardown(self):
        try:
            await self.destroy()
        except KeyError:
            pass

    async def add_tracks(self, ctx, tracks):
        if not tracks:
            raise NoTracksFound

        if isinstance(tracks, wavelink.TrackPlaylist):
            self.queue.add(*tracks.tracks)
        elif len(tracks) == 1:
            self.queue.add(tracks[0])
            embed = discord.Embed(title = "Queue", colour = discord.Color.from_rgb(252, 165, 3), timestamp = datetime.utcnow())
            embed.set_footer(text=f"Added by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
            embed.add_field(inline=False, name="Added:", value=f"{tracks[0].title} to the queue.")
            await ctx.send(embed=embed)
        else:
            if (track := await self.choose_track(ctx, tracks)) is not None:
                self.queue.add(track)
                embed = discord.Embed(title = "Queue", colour = discord.Color.from_rgb(252, 165, 3), timestamp = datetime.utcnow())
                embed.set_footer(text=f"Added by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
                embed.add_field(inline=False, name="Added:", value=f"{track.title} to the queue.")
                await ctx.send(embed=embed)

        if not self.is_playing and not self.queue.is_empty:
            await self.start_playback()

    async def choose_track(self, ctx, tracks):
        def _check(r, u):
            return (
                r.emoji in OPTIONS.keys()
                and u == ctx.author
                and r.message.id == msg.id
            )

        embed = discord.Embed(
            title=f"Hey {ctx.message.author.display_name}, I got some results. React to the message below to play/add that song. This message will expire in 30 seconds.",
            description=(
                "\n".join(
                    f"**{i+1}.** {t.title} ({t.length//60000}:{str(t.length%60).zfill(2)})"
                    for i, t in enumerate(tracks[:5])
                )
            ),
            colour=discord.Color.from_rgb(252, 165, 3),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name="Youtube Search Results")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        msg = await ctx.send(embed=embed)
        for emoji in list(OPTIONS.keys())[:min(len(tracks), len(OPTIONS))]:
            await msg.add_reaction(emoji)

        try:
            reaction, _ = await self.bot.wait_for("reaction_add", timeout=30.0, check=_check)
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.message.delete()
        else:
            await msg.delete()
            return tracks[OPTIONS[reaction.emoji]]

    async def start_playback(self):
        await self.play(self.queue.current_track)

    async def advance(self):
        try:
            if (track := self.queue.get_next_track()) is not None:
                await self.play(track)
        except QueueIsEmpty:
            pass

    async def repeat_track(self):
        await self.play(self.queue.current_track)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).teardown()
                

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        #await channel.send(f"LavaLink server `{node.identifier}` initialized. You can play songs now :)")
        print(f" Wavelink node `{node.identifier}` ready.")
    

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node, payload):
        if payload.player.queue.repeat_mode == RepeatMode.ONE:
            await payload.player.repeat_track()
        else:
            await payload.player.advance()

    #sends message in DM(NOT NEEDED!!)
    #async def cog_check(self, ctx):
        #if isinstance(ctx.channel, discord.DMChannel):
            #await ctx.send("Music commands are not available in DMs.")
            #return False

        #return True

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "0.0.0.0",
                "port": 7000,
                "rest_uri": "http://0.0.0.0:7000",
                "password": "makeit",
                "identifier": "MAIN",
                "region": "singapore",
            }
        }

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            return self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            return self.wavelink.get_player(obj.id, cls=Player)

    @commands.command(name="connect", aliases=["join"])
    @commands.guild_only()
    async def connect_command(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
        player = self.get_player(ctx)
        channel = await player.connect(ctx, channel)
        embed = discord.Embed(title = f"I have connected to {channel.name}!", colour = discord.Color.from_rgb(252, 165, 3))
        embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @connect_command.error
    async def connect_command_error(self, ctx, error):
        if isinstance(error, AlreadyConnectedToChannel):
            embed = discord.Embed(title = "I am already connected to a voice channel, join me there. :slight_smile: ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        elif isinstance(error, NoVoiceChannel):
            embed = discord.Embed(title = "Please join a voice channel first.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    @commands.command(name="disconnect", aliases=["leave", "dc"], description = "This command will simply disconnect the bot from the voice channel.")
    @commands.guild_only()
    async def disconnect_command(self, ctx, channel = None):
        player = self.get_player(ctx)
        
        if player.is_connected == False:
            raise AlreadyDisconnectedFromChannel

        elif (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            embed = discord.Embed(title = "You are not in a voice channel. To use that command join a voice channel.",colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

        else:
            player.queue.empty()
            await player.stop()
            await player.teardown()
            embed = discord.Embed(title = "Disconnected!", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
    
    @disconnect_command.error
    async def disconnect_command_error(self, ctx, error):
        if isinstance(error, AlreadyDisconnectedFromChannel):
            embed = discord.Embed(title = "I am already disconnected!", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text= f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            


    @commands.command(name="play", aliases = ["p"], description = "To use Music bot you simply need to join any voice channel, run the command `!join` or simply use `!p` followed by any song to search or a direct link. Supported commands are `!play`, `!stop`, `!queue`, `!next`, `!previous`, `!repeat` and `!disconnect`. Run them to know what they do." )
    @commands.guild_only()
    async def play_command(self, ctx, *, query: t.Optional[str]):
        player = self.get_player(ctx)

        if not player.is_connected:
            await player.connect(ctx)
        

        if query is None:
            if player.queue.is_empty:
                raise QueueIsEmpty

            await player.set_pause(False)
            embed = discord.Embed(title = "Resuming song :arrow_forward: ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

        else:
            query = query.strip("<>")
            if not re.match(URL_REGEX, query):
                query = f"ytsearch:{query}"

            await player.add_tracks(ctx, await self.wavelink.get_tracks(query))

    @play_command.error
    async def play_command_error(self, ctx, error):
        if isinstance(error, QueueIsEmpty):
            embed = discord.Embed(title = "Add some songs to play music.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        elif isinstance(error, NoVoiceChannel):
            embed = discord.Embed(title = "Join a voice channel to run this command.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
    

    @commands.command(name="pause")
    @commands.guild_only()
    async def pause_command(self, ctx):
        player = self.get_player(ctx)

        if player.is_paused:
            raise PlayerIsAlreadyPaused

        await player.set_pause(True)
        
        embed = discord.Embed(title = "Song Paused :pause_button: ", colour = discord.Color.from_rgb(252, 165, 3))
        embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @pause_command.error
    async def pause_command_error(self, ctx, exc):
        if isinstance(exc, PlayerIsAlreadyPaused):
            embed = discord.Embed(title = "The music is already paused.", colour = discord.Color.from_rgb(252, 165, 3) )
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            

    @commands.command(name="stop", aliases = ["clear", "empty"], description = "This command will clear all current songs in queue and stop playing music.")
    @commands.guild_only()
    async def stop_command(self, ctx, channel=None):
        player = self.get_player(ctx)

        if player.is_connected == False:
            raise AlreadyDisconnectedFromChannel

        elif (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            embed = discord.Embed(title = "You are not in a voice channel. To use that command join a voice channel.",colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        else:
            player.queue.empty()
            await player.stop()
            embed = discord.Embed(title = "Clearing up queue..... And stopped the current song. You may now add songs again. ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
    
    @stop_command.error
    async def stop_command_error(self, ctx, error):
        if isinstance(error, AlreadyDisconnectedFromChannel):
            embed = discord.Embed(title = "I am not in a voice channel.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    @commands.command(name="next", aliases=["skip", "n"], description = "This command will skip the current playing song and play the next track in queue if there is any.")
    @commands.guild_only()
    async def next_command(self, ctx, channel = None):
        player = self.get_player(ctx)

        if player.is_connected == False:
            raise AlreadyDisconnectedFromChannel

        elif (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            embed = discord.Embed(title = "You are not in a voice channel. To use that command join a voice channel.",colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        elif not player.queue.upcoming:
            raise NoMoreTracks

        else:
            await player.stop()
        
            embed = discord.Embed(title = "Skipping the song... :track_next: ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        

    @next_command.error
    async def next_command_error(self, ctx, error):
        if isinstance(error, AlreadyDisconnectedFromChannel):
            embed = discord.Embed(title = "Invite me to a voice channel first.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        elif isinstance(error, QueueIsEmpty):
            embed = discord.Embed(title = "The queue is empty.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            
        elif isinstance(error, NoMoreTracks):
            embed = discord.Embed(title = "There isn't any song in the queue to skip to. ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
    
            
            

    @commands.command(name="previous", description = "This command will play the previous song in the queue (the one which was already played) if there was any.")
    @commands.guild_only()
    async def previous_command(self, ctx, channel = None):
        player = self.get_player(ctx)
        
        if player.is_connected == False:
            raise AlreadyDisconnectedFromChannel

        elif (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            embed = discord.Embed(title = "You are not in a voice channel. To use that command join a voice channel.",colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

        elif not player.queue.history:
            raise NoPreviousTracks
        
        else:
            player.queue.position -= 2
            await player.stop()
            embed = discord.Embed(title = "Going back to the previous media. ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    @previous_command.error
    async def previous_command_error(self, ctx, error):
        if isinstance(error, AlreadyDisconnectedFromChannel):
            embed = discord.Embed(title = "Invite me to a voice channel first.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

        elif isinstance(error, QueueIsEmpty):
            embed = discord.Embed(title = "The queue is empty ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
            
        elif isinstance(error, NoPreviousTracks):
            embed = discord.Embed(title = "No previous songs found.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

    # @commands.command(name="shuffle")
    # async def shuffle_command(self, ctx):
    #     player = self.get_player(ctx)
    #     player.queue.shuffle()
    #     await ctx.send("Queue shuffled.")

    #@shuffle_command.error
    #async def shuffle_command_error(self, ctx, exc):
        #if isinstance(exc, QueueIsEmpty):
            #await ctx.send("The queue could not be shuffled as it is currently empty.")


    @commands.command(name="repeat", aliases = ["r"], description = "This command will allow you to repeat the song/queue. Run the command for more information on repeat modes.")
    @commands.guild_only()
    async def repeat_command(self, ctx,channel = None):
        player = self.get_player(ctx)
        def _check(r, u):
            return (
                r.emoji in React_Options.keys()
                and u == ctx.author
                and r.message.id == msg.id
            )
        
        if player.is_connected == False:
            raise AlreadyDisconnectedFromChannel

        elif (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            embed = discord.Embed(title = "You are not in a voice channel. To use that command join a voice channel.",colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        else:
            embed = discord.Embed(title = "Set Repeat Mode", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            embed.add_field(inline=False,name="\u200b", value= "⛔ - React to this emoji to set repeat mode to NONE. It will not repeat any track.")
            embed.add_field(inline=False,name="\u200b", value= "1️⃣ - React to this emoji to set repeat mode to ONE. It will repeat current track forever.")
            embed.add_field(inline=False,name="\u200b",value=  "♾️ - React to this emoji to set repeat mode to ALL. It will repeat all tracks in queue forever.")
            msg = await ctx.send(embed=embed)

            for emoji in list(React_Options.keys()):
                await msg.add_reaction(emoji)
            
            try:
                reactions, _= await self.bot.wait_for("reaction_add", timeout = 10.0, check=_check)
            except asyncio.TimeoutError:
                await msg.delete()
                await ctx.message.delete()
            else:
                await msg.delete()
                mode =  React_Options[reactions.emoji]

                if mode == 0:
                    mode = "none"

                elif mode == 1:
                    mode = "one"

                elif mode == 2:
                    mode = "all"

                player.queue.set_repeat_mode(mode)
                if mode == "none":
                    embed = discord.Embed(title = "Repeat Mode set to None :no_entry:", colour = discord.Color.from_rgb(252, 165, 3))
                    embed.set_footer(text=f"Repeat mode set by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed)
                elif mode == "one":
                    embed = discord.Embed(title = "Repeat Mode set to repeat current track :one:", colour = discord.Color.from_rgb(252, 165, 3))
                    embed.set_footer(text=f"Repeat mode set by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed)
                elif mode == "all":
                    embed = discord.Embed(title = "Repeat Mode set to repeat all tracks in queue :repeat:", colour = discord.Color.from_rgb(252, 165, 3))
                    embed.set_footer(text=f"Repeat mode set by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed)

    @repeat_command.error
    async def repeat_command_error(self, ctx, error):
        if isinstance(error, AlreadyDisconnectedFromChannel):
            embed = discord.Embed(title = "Invite me to a voice channel first.", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)


    @commands.command(name="queue", aliases = ["q"], description = "This command shows the queue as already guessed. Shows upto 10 tracks that are in queue with current track being played.")
    @commands.guild_only()
    async def queue_command(self, ctx, show: t.Optional[int] = 10, channel = None):
        player = self.get_player(ctx)

        
        if player.is_connected == False:
            raise AlreadyDisconnectedFromChannel

        elif (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            embed = discord.Embed(title = "You are not in a voice channel. To use that command join a voice channel.",colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        elif player.queue.is_empty:
            raise QueueIsEmpty
        
        else:
            embed = discord.Embed(
                title="Queue",
                description=f"Displaying songs up to next {show} tracks:",
                colour = discord.Color.from_rgb(252, 165, 3),
                timestamp=datetime.utcnow()
            )
            embed.set_author(name="Query Results")
            embed.set_footer(text=f"Requested by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            embed.add_field(
                name="Currently playing song:",
                value=getattr(player.queue.current_track, "title", "No tracks currently playing."),
                inline=False
            )
            if upcoming := player.queue.upcoming:
                embed.add_field(
                    name="Songs in Queue:",
                    value="\n".join(t.title for t in upcoming[:show]),
                    inline=False
                )

            msg = await ctx.send(embed=embed)

    @queue_command.error
    async def queue_command_error(self, ctx, error):
        if isinstance(error, AlreadyDisconnectedFromChannel):
            embed = discord.Embed(title = "Invite me to a voice channel first. ", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)
        
        elif isinstance(error, QueueIsEmpty):
            embed = discord.Embed(title = "Hmmm, I could not find a song in the queue. Why don't you try command `!p` and search for the song or paste the link?", colour = discord.Color.from_rgb(252, 165, 3))
            embed.set_footer(text=f"Error caused by {ctx.message.author.display_name}", icon_url=ctx.author.avatar_url)
            await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Music(bot))