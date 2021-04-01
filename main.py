
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
from datetime import datetime
from pytz import timezone
from keep_alive import keep_alive
import re
import logging


logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

intens = discord.Intents.default()
intens.members = True
Timezone = timezone('Europe/Amsterdam')

#bot Prefix + Define scared variable
client = commands.Bot(command_prefix = '!', intents=intens)
scared = False

# pfp_path = "cover.png"
# fp = open(pfp_path, 'rb')
# pfp = fp.read()


@client.command(pass_context = True, help='Remove a sound')
async def rmsound(ctx,message):
  serverid = ctx.message.guild.id
  sound = message
  path = "/var/chips/"+str(serverid)+"_"+str(sound)+".mp3"
  os.remove(path)

@client.event
async def on_ready():
  # await client.user.edit(avatar=pfp)
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!help"))
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
@client.command(pass_context = True, help='Make the bot leave the channel it is in')
async def leave(ctx):
  if(scared == True):       #if scarymode is on, leaving is not possible
    await ctx.send("Try to leave? You cannot run")
  else:                     #otherwist, check wether bot hasn't left already
    if(ctx.voice_client):
      await ctx.guild.voice_client.disconnect()
      await ctx.send("I left the channel")
    else:
      await ctx.send("I am not in a voice channel")

#YouTube music player - WIP
@client.command(pass_context=True)
async def play(ctx, message):
	link = message
	await ctx.send(link)

@client.command(pass_context = True)
async def channel(ctx):
  user_channel = ctx.author.voice.channel
  bot_channel = ctx.voice_client.channel
  if(ctx.voice_client is None):
    await ctx.send("Not connected")
  else:
    if(user_channel == bot_channel):
      await ctx.send("Same Channel")
    else:
      await ctx.send("Not the same channel")

#Soundbot Command
@client.command(pass_context= True, help='Play Audio by using !sound [Soundname]')
async def sound(ctx, message):
  serverid = ctx.message.guild.id
  mp3 = "/var/chips/"+str(serverid) + "_" + message + ".mp3"
  print(mp3)
  if(path.exists(mp3)):#check if file exists
    source = FFmpegPCMAudio(mp3)
    if(ctx.author.voice is None):   #is author in a voice channel?
      await ctx.send("Please join a voice channel first!")   #join channel first
    else:    #if author is in voice channel
      channel = ctx.author.voice.channel      #set channel var to author's channel
      if(ctx.voice_client is None):           #Check if bot is not in voice
        voice = await channel.connect()       #If not -> Connect to channel with Author ID
        if(voice.is_playing()):               #If voice is already playing
          voice.stop()                        #Stop talking and start new sound
          voice.play(source)                
        else:                                 #If bot wasn't playing, start new sound
          voice.play(source)            
      else:                                   #If the bot is already connected to A channel
        botchannel = ctx.voice_client.channel #Get the channel that the bot is in
        authorvoice = ctx.author.voice.channel#Get the channel that the author is in
        voice_channel = ctx.voice_client      #Create voice_channel object for the bot
        if(botchannel == authorvoice):        #Check if bot is in same channel as user
          if(voice_channel.is_playing()):     #If it's the same -> Check if sound is playing
            voice_channel.stop()              #Stop playing
            voice_channel.play(source)        #start the new sound
          else:                               #If not playing
            voice_channel.play(source)        #Play the sound
        else:                                 #If bot and author are not in the same channel
          if(voice_channel.is_playing()):     #Check if a sound is playing
            voice_channel.stop()              #Stop the sound
          await voice_channel.disconnect()    #disconnect
          voice2 = await authorvoice.connect()  #create new instance of voicechannel - With author's voice ID
          voice2.play(source)                 #Play the new sound
  else:
    await ctx.send("Uh Oh, That chip does not exist")#if file doesn't exist

#Activates Scary mode by command !hell
@client.command(pass_context = True, help='22:30 GMT+2')
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
@client.command(pass_context = True,help='Get a joke')
async def joke(ctx):
  url = "https://v2.jokeapi.dev/joke/Miscellaneous,Dark,Pun?type=single"

  response = requests.get(url).json()

  await ctx.send(str(response['joke']))


@client.command(pass_context = True, help='Introduction to the soundboard')
async def commands(ctx):
  await ctx.send("```Hi There, I am ChipBot, your bot for custom sound effects in your Discord server. \n I was created in 2021 by an IT&Management student who likes programming. I am written in Python, the greatest program language (because it was invented by a Dutch man). \n I currently listen to the following commands:\n-----------------------------------------\n!sound [soundname] - To play a sound, uploaded to the bot.\n\n Go to http://chipbot.tk/ to add a sound to the bot \n\n!joke - To get a joke.\n\n !leave - To let the bot leave your voice channel.\n\n !h*ll - Try this after 22:30, if you are brave enough```")

@client.command(pass_context = True, help='Show all sounds for your server')
async def soundlist(ctx):
	serverid = str(ctx.message.guild.id)
	list = []
	for f in os.listdir('/var/chips'):
		if re.match(serverid, f):
			x = (f.split('_'))
			y = (x[1].split('.'))
			list.append(y[0])
	b = "  ".join(list)
	await ctx.send("```Available Sounds:\n----------------------------\n" + b + "```")

@client.command(pass_context=True)
async def space(ctx):

	url = 'http://api.open-notify.org/iss-now.json'

	r = requests.get(url).json()

	epoch = r['timestamp']
	timestamp = (datetime.utcfromtimestamp(int(epoch)).strftime('%H:%M:%S - %d-%m-%Y'))

	lat = r['iss_position']['latitude']
	lon = r['iss_position']['longitude']

	await ctx.send("ISS LOCATION AT " + str(timestamp) + "\n Latitude:  " + lat + "\n Longitude: " + lon)	
#run the bot & keep alive

keep_alive()
client.run("Nzg0MTE5NjM1NTM2Mzc5OTE0.X8kqUQ.SnojVfPVu5YEuLz0a5zUOPtR4Jw")


