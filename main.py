
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
import re
import logging
import subprocess
from dotenv import load_dotenv
import youtube_dl
from youtube_dl import YoutubeDL
import csv
import matplotlib.pyplot as plt
import numpy as np

#Set logging variables
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

#Set required Discord params
intens = discord.Intents.default()
intens.members = True
Timezone = timezone('Europe/Amsterdam')

#Set .env files
load_dotenv(dotenv_path='keys.env')

#bot Prefix + Define scared variable
client = commands.Bot(command_prefix = '!', intents=intens)
scared = False

#open logfile


#Uncomment th change new icon
# pfp_path = "cover.png"
# fp = open(pfp_path, 'rb')
# pfp = fp.read()

#On Bot Startup
@client.event
async def on_ready():
  # await client.user.edit(avatar=pfp)
  await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="!help"))
  print('Bot logged in as user: {0.user}'.format(client))
  print('-----------------------------------')

#Welcome message upon bot joining
@client.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
          embed=discord.Embed(title="Welcome to Chipbot", url="http://www.chipbot.tk", description="This is a short introduction @everyone", color=0x765e89)
          embed.set_thumbnail(url="http://185.189.182.43/default.png")
          embed.add_field(name="So you just added me", value="Great! I have a lot of cool features, but the most important is being a custom soundboard. You will find a guide on how to upload sounds below! Type !help for all my commands.", inline=False)
          embed.add_field(name="How to upload sounds:", value="Go [www.chipbot.tk](http://185.189.182.43/upload.php) link below and click 'Add Chips'. Select an .mp3 file from your computer, give it a name and add the server id. Not sure what your server-id is? Type !serverinfo. After uploading, join a voicechannel and type !sound [name]", inline=False)
          embed.add_field(name="Need Help?", value="Add me: @OlavRab#5982 or join the ChipBot Support Server: https://discord.gg/KSZYwqyeRV", inline=False)
          await channel.send(embed=embed)
        break

#Clean up leftover sounds when the bot gets removed from the server to free up space
# @client.event
# async def on_guild_remove(guild):
#   print("I Have been kicked")
#   guildid = guild.id
#   for file in os.listdir('/var/chips'+):
#     if file.startswith(str(guildid)):
#       filename = '/var/chips/'+str(file)
#       os.remove(filename)

#Error Handling
@client.event
async def on_command_error(ctx,error):
  if isinstance(error, discord.ext.commands.errors.CommandNotFound):
    await ctx.send("That command was not found, try !help for available commands")


#Remove sound command
@client.command(pass_context = True, help='Remove a sound')
async def rmsound(ctx,message):
  serverid = ctx.message.guild.id
  sound = message
  path = "/var/chips/"+str(serverid)+"/"+str(sound)+".mp3"
  os.remove(path)
  await ctx.send(sound + " has been removed!")


#leave voicechannel when everyone else leaves
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


# @client.command(pass_context=True, help="Play YouTube Sounds")
# async def play(ctx, url: str):
#   # Youtube_DL options
#   # SAVE_PATH = '/'.join(os.getcwd().split('/')[:3]) + '/ftp/upload/ChipBot/youtube'
#   ydl_opts = {
#     'format': 'bestaudio/best',
#     'postprocessors': [{
#         'key': 'FFmpegExtractAudio',
#         'preferredcodec': 'mp3',
#         'preferredquality': '192',
#     }],
#     # 'outtmpl':SAVE_PATH + '/%(title)s.%(ext)s',
#   }
#   if(ctx.author.voice is None):
#     print("User not in voice")
#   else:
#     channel = ctx.author.voice.channel 
#     if(ctx.voice_client is None):
#       print("Bot not in voicechannel")
#       voice = await channel.connect()
#     else:
#       print('Bot was already connected to voice')

#   with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#     await ctx.send("Loading... be patient")
#     song_info = ydl.extract_info(url, download=False)
#     print(song_info)
#     # ydl.download([url])
#   for file in os.listdir("./"):
#     if file.endswith(".mp3"):
#       os.rename(file, "song.mp3")
#   voice.play(discord.FFmpegPCMAudio("song.mp3"))
  

#Soundbot Command
@client.command(pass_context= True, help='Play Audio by using !sound [Soundname]')
async def sound(ctx, message):
  try:
    serverid = ctx.message.guild.id
    servername = ctx.message.guild.name
    mp3 = "/var/chips/"+str(serverid)+"/"+ message + ".mp3"
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
            voice.play(source)                  #If bot wasn't playing, start new sound
            logit(serverid, mp3, ctx.author,servername)
          else: 	                       
            voice.play(source)      
            logit(serverid, mp3, ctx.author,servername)      
        else:                                   #If the bot is already connected to A channel
          botchannel = ctx.voice_client.channel #Get the channel that the bot is in
          authorvoice = ctx.author.voice.channel#Get the channel that the author is in
          voice_channel = ctx.voice_client      #Create voice_channel object for the bot
          if(botchannel == authorvoice):        #Check if bot is in same channel as user
            if(voice_channel.is_playing()):     #If it's the same -> Check if sound is playing
              voice_channel.stop()              #Stop playing
              voice_channel.play(source)        #start the new sound
              logit(serverid, mp3, ctx.author,servername)      
            else:                               #If not playing
              voice_channel.play(source)        #Play the sound
              logit(serverid, mp3, ctx.author,servername)  #log the play
          else:                                 #If bot and author are not in the same channel
            if(voice_channel.is_playing()):     #Check if a sound is playing
              voice_channel.stop()              #Stop the sound
            await voice_channel.disconnect()    #disconnect
            voice2 = await authorvoice.connect()  #create new instance of voicechannel - With author's voice ID
            voice2.play(source)                 #Play the new sound
            logit(serverid, mp3, ctx.author,servername) 
    else:
      await ctx.send("Uh Oh, That chip does not exist")#if file doesn't exist
  except Exception as e:
    await ctx.send("__Sorry, something in my internal code broke:__ \n"+str(e))


def logit(serverid, location, user, servername):
  t = datetime.datetime.now()
  date = t.strftime("%Y-%m-%d")
  time = t.strftime("%H:%M:%S")
  y = location.split("/")
  newlocation = "/"+y[1]+"/"+y[2]+"/"+y[3]+"_"+y[4]
  with open('soundboard.csv' , 'a', newline='') as file:
    writer = csv.writer(file)
    writer.writerow([date,time, serverid, newlocation, user, servername])

#Activates Scary mode by command !hell
@client.command(pass_context = True, help='22:30 GMT+2')
async def hell(ctx): #CHANGE TO HELL!
  # t = datetime.datetime.now(Timezone) #Set time variable
  t = datetime.datetime.now()
  if t.strftime('%A') == "Friday" and t.hour > 22 and t.minute > 30:
    scared = True
    ss1 = FFmpegPCMAudio("/var/chips/scary_mode/monster.mp3")
    ss3 = FFmpegPCMAudio("/var/chips/scary_mode/laugh.mp3")
    ss4 = FFmpegPCMAudio("/var/chips/scary_mode/geist.mp3")
    ss5 = FFmpegPCMAudio("/var/chips/scary_mode/door.mp3")
    ss6 = FFmpegPCMAudio("/var/chips/scary_mode/heart.mp3")
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
    with open('/var/chips/scary_mode/c1.jpg', 'rb') as f:
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

@client.command(pass_context=True, help="Find your love")
async def test2 (ctx,message):
  await ctx.send("Error")

@client.command(pass_context=True, help="Add a coin in quotes and get the values")
async def crypto (ctx, coin):
  if coin:
    print('hallo')
    msg = coin.lower()
    msg = msg.replace(" ", "-")
    url_history = "https://api.coincap.io/v2/assets/"+msg+"/history?interval=d1"
    url_name = "https://api.coincap.io/v2/assets/"+msg
    response_history = requests.get(url_history).json()
    response_name = requests.get(url_name).json()
    await ctx.send("URL Called - " + url_history)
    coin_name = response_name['data']['name']
    latest_price = float(response_name['data']['priceUsd'])
    rounded = round(latest_price,2)
    await ctx.send(coin_name+ "/USD = $" + str(rounded))
    time = []
    value = []

    i = 1
    while i < 30:
        time.append(response_history['data'][i]['date'])
        value.append(float(response_history['data'][i]['priceUsd']))
        i = i + 1

    await ctx.send(time)

    plt.plot(time, value)
    ax = plt.gca()
    # ax.axes.xaxis.set_visible(False)  
    plt.xticks([time[0], time[-1]], visible=True, rotation="horizontal")
    # naming the x axis
    plt.xlabel('Time')
    # naming the y axis
    plt.ylabel('Value in $')
      
    # giving a title to my graph
    plt.title(coin_name + " - Last year's performance")

    plt.savefig('test.png')
    with open("test.png", "rb") as fh:
      f = discord.File(fh, filename="test.png")
    await ctx.send(file=f)

    os.remove("test.png")
  else:
    print("Joe")
    await ctx.send("No coin was passed, fill a supported coin in quotes ''")

# !joke command, sends joke upon request
@client.command(pass_context = True,help='Get a joke')
async def joke(ctx):
  url = "https://v2.jokeapi.dev/joke/Miscellaneous,Dark,Pun?type=single"
  response = requests.get(url).json()
  await ctx.send(str(response['joke']))

#Introduction command
@client.command(pass_context = True, help='Introduction to the soundboard')
async def commands(ctx):
  await ctx.send("```Hi There, I am ChipBot, your bot for custom sound effects in your Discord server. \n I was created in 2021 by an IT&Management student who likes programming. I am written in Python, the greatest program language (because it was invented by a Dutch man). \n I currently listen to the following commands:\n-----------------------------------------\n!sound [soundname] - To play a sound, uploaded to the bot.\n\n Go to http://chipbot.tk/ to add a sound to the bot \n\n!joke - To get a joke.\n\n !leave - To let the bot leave your voice channel.\n\n !h*ll - Try this after 22:30, if you are brave enough```")

#Soundlist command
@client.command(pass_context=True, help="Show all sounds in your server!")
async def soundlist(ctx):
  serverid = str(ctx.message.guild.id)
  path = "/var/chips/"+serverid
  list = []
  for f in os.listdir(path):
    list.append(f.split(".")[0])
  b = "  ".join(list)
  await ctx.send("```Available Sounds:\n----------------------------\n" + b + "```")
    

#ISS Command
@client.command(pass_context=True, help='Get the current coordinates of the ISS')
async def space(ctx):
	url = 'http://api.open-notify.org/iss-now.json'
	r = requests.get(url).json()
	epoch = r['timestamp']
	timestamp = (datetime.utcfromtimestamp(int(epoch)).strftime('%H:%M:%S - %d-%m-%Y'))
	lat = r['iss_position']['latitude']
	lon = r['iss_position']['longitude']
	await ctx.send("ISS LOCATION AT " + str(timestamp) + "\n Latitude:  " + lat + "\n Longitude: " + lon)	

#Get Latency to bot
@client.command(pass_context= True, help='Get your latency(ping)')
async def ping(ctx):
  clientltc = client.latency * 1000
  await ctx.send(f'Pong! - Your latency to the bot is: {round(clientltc)} ms')
  
#Serverinfo  
@client.command(pass_context=True, help="Get information about the server")
async def serverinfo(ctx):
  name = str(ctx.guild.name)
  if(ctx.guild.description is None):
    description = "No description set"
  else:
    description = str(ctx.guild.description)
  owner = str(ctx.guild.owner)
  id = str(ctx.guild.id)
  region = str(ctx.guild.region)
  memberCount = str(ctx.guild.member_count)
  icon = str(ctx.guild.icon_url)
  embed = discord.Embed(
      title=name + "Server Information",
      description=description,
      color=discord.Color.blue()
    )
  embed.set_thumbnail(url=icon)
  embed.add_field(name="Owner", value=owner, inline=True)
  embed.add_field(name="Server ID", value=id, inline=True)
  embed.add_field(name="Region", value=region, inline=True)
  embed.add_field(name="Member Count", value=memberCount, inline=True)
  await ctx.send(embed=embed)


#Love Command
@client.command(pass_context=True, help="Find your love")
async def love(ctx,message):
  url = "https://love-calculator.p.rapidapi.com/getPercentage"

  querystring = {"fname":"John","sname":"Alice"}

  headers = {
    'x-rapidapi-key': "2df44f8855msh8680922143f6a75p1c535ejsnf3df2dee558c",
    'x-rapidapi-host': "love-calculator.p.rapidapi.com"
    }

  response = requests.request("GET", url, headers=headers, params=querystring)

  print(response.text)

#Admin Command
@client.command(pass_context=True, help="Admin purposes only")
async def admin(ctx, message):
  if(message == "s1"):
    if(ctx.author.id == int(os.environ.get("ADMIN-ID"))):
      servers = []
      output = set()
      for f in os.listdir('/var/chips'):
        x = (f.split('_'))
        y = x[0]
        servers.append(y)
      unique_numbers = list(set(servers)) 
      b = "  ".join(unique_numbers)
      await ctx.send(b)   
    else:
      await ctx.send("It seems that you are not an admin, sorry")

@client.command(pass_context=True, help="Some very interesting things here")
async def sexytime(ctx):
  await ctx.send("You dirty man")

@client.command(pass_context=True, help="See available space on server")
async def storage(ctx):
  x = subprocess.run(['df -h /home --output=avail,used,size'], shell=True, capture_output=True)
  output = str(x.stdout)
  split_output = output.split(" ")
  available = split_output[6]
  used = split_output[8]
  total = split_output[11]
  available_memory = int(available.split("G")[0])
  used_memory = float(used.split("G")[0])
  total_memory = int(total.split("G")[0])
  await ctx.send("**Memory Status on the ChipBot VPS: **" + "\n Used Space:" + str(used_memory) + " Gigabytes\n Free Space: " + str(total_memory)+ " Gigabytes\n Note that this storage is shared with all ChipBot users!")

@client.command(pass_context=True, help="See the available RAM on the server")
async def ram(ctx):
  x = subprocess.run(['free -m'], shell=True, capture_output=True)
  output = str(x.stdout)
  split_output = output.split(" ")
  print(split_output)


@client.command(pass_context=True, help="Get the latest currency")
async def coin(ctx,message):
  if not message:
    await ctx.send("Please supply a coin name within brackets")
  else:
    msg = message.lower()
    msg = msg.replace(" ", "-")
    url = "https://api.coincap.io/v2/assets/"+msg
    response = requests.get(url).json()
    latest_price = float(response['data']['priceUsd'])
    rounded = round(latest_price,2)
    coin_name = response['data']['name']
    await ctx.send(coin_name+ "/USD = $" + str(rounded))

keep_alive()
client.run(os.environ.get("TOKEN"))


