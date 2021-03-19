import discord
from discord.ext import commands
import os
import requests
import json
import nacl
from discord import FFmpegPCMAudio
import time
from mutagen.mp3 import MP3
import os.path
from os import path
import json


intens = discord.Intents.default()
intens.members = True

client = commands.Bot(command_prefix = '!', intents=intens)


def audio_length(audio):
  audio = MP3(audio)
  length = (audio.info.length)
  print(length)
  return length


@client.event
async def on_ready():
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!sound & !help"))
  print('Bot logged in as user: {0.user}'.format(client))
  print('-----------------------------------')


@client.event
async def on_member_join(member):
  channel = client.get_channel(676776081759404043)
  await channel.send("Hello" +str(member))

@client.command(pass_context = True)
async def leave(ctx):
  if(ctx.voice_client):
    await ctx.guild.voice_client.disconnect()
    await ctx.send("I left the channel")
  else:
    await ctx.send("I am not in a voice channel")


@client.command(pass_context= True)
async def sound(ctx, message):
  mp3 = message+'.mp3'
  mp3 = 'sounds/'+mp3
  print(mp3)
  if(path.exists(mp3)):
    source = FFmpegPCMAudio(mp3)
    if(ctx.author.voice is None):
      await ctx.send("Please join a voice channel first!")
      print("Author not in voicechat") 
    else:
      print("Author in voicechat") 
      channel = ctx.author.voice.channel
    if(ctx.voice_client is None):
      print("Bot is not connected, connecting...")
      voice = await channel.connect()
      voice.play(source)
    else:
      voice = ctx.voice_client
      print("Bot is connected to voicechat")
      voice.play(source)
    print("-----------------------------------")
  else:
    # await ctx.send("Uh Oh, That chip does not exist")
    await ctx.send("Da hek nie godverdomme")


@client.command(pass_context = True)
async def choo(ctx):
  await ctx.send("IM A TRAIN, CHOO CHOO MOTHERFUCKERS")

@client.command(pass_context = True)
async def joke(ctx):
  url = "https://v2.jokeapi.dev/joke/Any?type=single"

  response = requests.get(url).json()
  p

  await ctx.send(str(response['joke']) + str(response['category']))


client.run(os.getenv("TOKEN"))

