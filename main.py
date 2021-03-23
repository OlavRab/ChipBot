import discord
from discord.ext import commands
import os
import requests
import json
import nacl
from discord import FFmpegPCMAudio
import time
import os.path
from os import path
import json
import datetime
from pytz import timezone
from keep_alive import keep_alive

intens = discord.Intents.default()
intens.members = True
Timezone = timezone('Europe/Amsterdam')

#bot Prefix + Define scared variable
client = commands.Bot(command_prefix = '!', intents=intens)
scared = False

# pfp_path = "cover.png"
# fp = open(pfp_path, 'rb')
# pfp = fp.read()


@client.event
async def on_ready():
  # await client.user.edit(avatar=pfp)
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!sound & !commands"))
  print('Bot logged in as user: {0.user}'.format(client))
  print('-----------------------------------')

#leave when everyone else leaves
@client.event
#get the details of the people in the voice
async def on_voice_state_update(member, before, after):
  voice_state = member.guild.voice_client
  # Checking if the bot is connected to a channel and if there is only 1 member connected to it (the bot itself)
  if voice_state is not None and len(voice_state.channel.members) == 1:
      # You should also check if the song is still playing
      await voice_state.disconnect()


#When a user asks bot to leave
@client.command(pass_context = True)
async def leave(ctx):
  if(scared == True):       #if scarymode is on, leaving is not possible
    await ctx.send("Try to leave? You cannot run")
  else:                     #otherwist, check wether bot hasn't left already
    if(ctx.voice_client):
      await ctx.guild.voice_client.disconnect()
      await ctx.send("I left the channel")
    else:
      await ctx.send("I am not in a voice channel")

#Soundbot Command
@client.command(pass_context= True)
async def sound(ctx, message):
  mp3 = message+'.mp3' #take message (soundname) and add .mp3
  mp3 = 'sounds/'+mp3  #Add /sounds folder
  print(mp3)
  if(path.exists(mp3)):#check if file exists
    source = FFmpegPCMAudio(mp3) #set FFMPEG source
    if(ctx.author.voice is None): #check if author is in voice channel
      await ctx.send("Please join a voice channel first!")
      print("Author not in voicechat") 
    else:               #otherwist, get authors voice channel UID
      print("Author in voicechat") 
      channel = ctx.author.voice.channel
      if(ctx.voice_client is None): #check if bot is already in voicechannel
        print("Bot is not connected, connecting...")
        voice = await channel.connect()   #if not -> Connect
        voice.play(source)                #and Play
      else:                               #if already connected
        voice = ctx.voice_client          #get UID of voice channel
        print("Bot is connected to voicechat")
        voice.play(source)                #play without Reconnecting
  else:
    await ctx.send("Uh Oh, That chip does not exist")#if file doesn't exist
  print("-----------------------------------")

#Activates Scary mode by command !hell
@client.command(pass_context = True)
async def hope(ctx): #CHANGE TO HELL!
  t = datetime.datetime.now(Timezone) #Set time variable
  if(t.hour > 22 and t.minute > 30):  #check if after 22:30
    scared = True
    ss1 = FFmpegPCMAudio("sounds/scarymode/monster.mp3")
    ss3 = FFmpegPCMAudio("sounds/scarymode/laugh.mp3")
    ss4 = FFmpegPCMAudio("sounds/scarymode/geist.mp3")
    ss5 = FFmpegPCMAudio("sounds/scarymode/door.mp3")
    ss6 = FFmpegPCMAudio("sounds/scarymode/heart.mp3")
    print('Scary Mode activated')
    if(ctx.author.voice is None):
      await ctx.send("Please join a voice channel first!")
    else:
      channel = ctx.author.voice.channel
      if(ctx.voice_client is None):
        print("Bot is not connected, connecting...")
        voice = await channel.connect()
        time.sleep(10)
        await ctx.send("**Help!** @everyone @here")
        voice.play(ss1)
      else:
        voice = ctx.voice_client
        print("Bot is connected to voicechat")
        time.sleep(10)
        await ctx.send("**Help!** @everyone @here")
        voice.play(ss1)
    time.sleep(5)
    await ctx.send("**Please, stay with me, this is important**")
    time.sleep(8)
    await ctx.send("**I am all alone here**")
    time.sleep(8)
    await ctx.send("Don't leave, don't disconnect me, DO NOT USE !leave")
    time.sleep(8)
    await ctx.send("_don't you want to help me?_")
    time.sleep(4)
    await ctx.send("**I hear someone**")
    ctx.voice_client.play(ss4)
    time.sleep(21)
    ctx.voice_client.play(ss3)
    await ctx.send("**THEY ARE COMING FOR YOU! Better watch your back!**")
    time.sleep(14)
    ctx.voice_client.play(ss5)
    await ctx.send("Fuck, They are here, HIDE")
    time.sleep(9)
    await ctx.guild.voice_client.disconnect()
    await ctx.send("```Connection to Host Lost, Reconnecting...```")
    time.sleep(8)
    await ctx.send("```Reconnect Failed, Server Error - Debug Code: [666-666-666CR]```")
    time.sleep(10)
    with open('sounds/scarymode/c1.jpg', 'rb') as f:
      picture = discord.File(f)
      await ctx.send(file=picture)
    await ctx.send("```You will not run from us```")
    time.sleep(2)
    await ctx.send("```Service shutting down in 5```")
    time.sleep(1)
    await ctx.send("```4```")
    time.sleep(1)
    await ctx.send("```3```")
    time.sleep(1)
    await ctx.send("```2```")
    time.sleep(1)
    await ctx.send("```1```")
    time.sleep(1)
    await ctx.send("```goodbye for now```")
    time.sleep(15)
    voice = await channel.connect()
    ctx.voice_client.play(ss6)
    time.sleep(51)
    await ctx.guild.voice_client.disconnect()
    await ctx.send("```End of this litte prank, hope u got scared. Good night!```")
    scared = False
  else:
    await ctx.send("That function is not available at this time, try again later")

# !joke command, sends joke upon request
@client.command(pass_context = True)
async def joke(ctx):
  url = "https://v2.jokeapi.dev/joke/Miscellaneous,Dark,Pun?type=single"

  response = requests.get(url).json()

  await ctx.send(str(response['joke']))


@client.command(pass_context = True)
async def commands(ctx):
  await ctx.send("```Hi There, I am ChipBot, your bot for custom sound effects in your Discord server. \n I was created in 2021 by an IT&Management student who likes programming. I am written in Python, the greatest program language (because it was invented by a Dutch man). \n I currently listen to the following commands:\n-----------------------------------------\n!sound [soundname] - To play a sound, uploaded to the bot.\n\n Go to http://chipbot.tk/ to add a sound to the bot \n\n!joke - To get a joke.\n\n !leave - To let the bot leave your voice channel.\n\n !h*ll - Try this after 22:30, if you are brave enough```")

  

#run the bot & keep alive

keep_alive()
client.run(os.getenv("TOKEN"))

