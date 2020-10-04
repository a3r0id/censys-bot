
import aiohttp
import discord
import json
import socket
from datetime import datetime, timedelta
import threading
import asyncio
from random import choice

with open('config.json') as f:
  config = json.load(f)

token = config["discord_token"]
prefix = config["prefix"]
rate_limit = config["search_rate_limit_seconds"]
presence_rate_limit = config["presence_change_rate_seconds"]
result_limit_during_reverse_dns = config["result_limit_if_reverse_dns"]
presences = config["presences"]
invite_code = config["invite_code"]
UID = config["CENSYS_UID"]
SECRET = config["CENSYS_SECRET"]
emoji_id = config["request_confirmation_emoji_id"]
embed_color = int(config["embed_color_hash"], 0)

stack = []


def gen_id():
    hash_list = [str(i) for i in range(0, 10)] + ["A", "B", "C", "D", "E", "F"]
    string = ""
    for _ in range(12):
        string += choice(hash_list)
    return string




def rate_limit_polling():
    while True:
        index = 0
        for item in stack:
            diff = datetime.now() > item['expiration']
            if diff:
                #DEBUG# print(f"Deleting {item['user_id']} instance from stack!")
                del stack[index]
            index += 1    
                

API_URL = "https://censys.io/api/v1/search/ipv4"

client = discord.Client()

@client.event
async def on_ready():
    # Start polling thread
    x = threading.Thread(target=rate_limit_polling)
    x.start()
    print("[READY] Started rate-limit-polling thread!")
    index = 0
    while True:
        activity = discord.Activity(name=presences[index], type=discord.ActivityType.watching)
        await client.change_presence(activity=activity)
        await asyncio.sleep(presence_rate_limit)
        index += 1
        if index == len(presences):
            index = 0


@client.event
async def on_message(message):
    ##################################################

    if message.author == client.user:
        return

    m = message
    c = m.content
    ##################################################

    if prefix + "prune" in c:
        total, succ, failed = 0, 0, 0
        async for elem in m.channel.history(limit=999):
            if elem.author == client.user:
                try:
                    await elem.delete()
                    succ += 1
                except:
                    failed += 1
                    pass    
            total += 1    
        #
        
        
        init_embed = discord.Embed(
            title=f"System Message",
            description=f"Deleted `{succ}` out of {total} messages.\nFailed to delete {failed} messages.", url='https://host-info.net', color=embed_color
            )

        mm = await m.channel.send(embed=init_embed)     

        await asyncio.sleep(10)
        await mm.delete()

    ##################################################    

    if prefix + "stop" in c:
        for emoji in client.emojis:
            if emoji.id == emoji_id:
                await m.add_reaction(emoji)
        
        Flushed = []
        count = 0
        stack_pointer = 0
        for item in stack:
            if item['user_id']:
                count += 1
                Flushed.append(item)
                del stack[stack_pointer]
            stack_pointer += 1  
        
        description = f"Flushed {str(len(Flushed))} Jobs From Memory!\nFlushed:\n"

        t_embed = discord.Embed(
            title=f"Flushed `{count}` from memory!",
            description=description, url='https://host-info.net', color=embed_color
            )
        x = 0
        for this in Flushed:
            cha = client.get_channel(this['channel'])
            t_embed.add_field(
                name=f"[{str(x+1)}] Flushed Job",
                value= f"Job ID: `{this['query_id']}`\nQuery: `{this['query']}`\nServer: `{cha.guild}`\nChannel: `{cha}`\n",
                inline=False
            )                        

        await m.channel.send(embed=t_embed)               

    ##################################################

    if prefix + "help" in c:
        for emoji in client.emojis:
            if emoji.id == emoji_id:
                await m.add_reaction(emoji)
        embed = discord.Embed(
            title=f"Censys Bot | Usage",
            description="Q = your query", url='https://host-info.net', color=embed_color
        )
        embed.set_thumbnail(url="https://host-info.net/app/img/mag.gif")
        embed.set_image(url="https://censys.io/assets/censys-logo-white.png")
        embed.set_author(name=str(m.author), url='https://host-info.net', icon_url=m.author.avatar_url)
        
        embed.add_field(
            name="Basic Usage",
            value= "`<Q>`\n*Max 100 Results",
            inline=False
        )        
        embed.add_field(
            name="Advanced Usage",
            value= f"`<Q> --reversedns`\n*Max {result_limit_during_reverse_dns} Results",
            inline=False
        )     
        embed.add_field(
            name="Stop Current Query",
            value= f"`{prefix}stop`\n",
            inline=False
        )         
        embed.add_field(
            name="Prune Censys Messages",
            value= f"`{prefix}prune`\n",
            inline=False
        )                   
        embed.add_field(
            name="What is a Censys Query? Learn more below!",
            value= "[Query Syntax](https://censys.io/ipv4/help)\n[Examples](https://censys.io/ipv4/help/examples)\n[Data Types](https://censys.io/ipv4/help/examples/definitions)",
            inline=False
        )     
        embed.add_field(
            name="Invite Censys Bot",
            value= f"[Invite]({invite_code})",
            inline=False
        )     

        embed.set_footer(text=f"A bot by Aero@host-info.net | Request by {m.author} in #{message.channel}.")  
        await m.channel.send(embed=embed)
    ##################################################

    if "<" in c and ">" in c and "<!" not in c and "<@" not in c and "<:" not in c:
        for emoji in client.emojis:
            if emoji.id == emoji_id:
                await m.add_reaction(emoji)
        for item in stack:

            if item['user_id'] == m.author.id:
                diff_in_seconds = item['expiration'] - datetime.now()
                diff_in_seconds = diff_in_seconds.total_seconds()
                try:
                    chan = client.get_channel(item['channel'])
                    chan_name = chan.name
                    Server_name = chan.guild.name
                except:
                    chan_name = "N/A"
                    Server_name = "N/A"

                this = discord.Embed(
                    title=f"System Message",
                    description=f"""
                    **You are being rate-limited.**

                    Please wait {rate_limit} seconds between searches!

                    Time Remaining:
                    `{str(round(diff_in_seconds))}`

                    Last Search - Server:
                    `{Server_name}`

                    Last Search - Channel:
                    `{chan_name}`

                    Last Search - Query:
                    `{item['query']}`

                    """, url='https://host-info.net', color=embed_color
                    )
                await m.channel.send(embed=this)  
                return                

        query = c.lower().split("<")[1].split(">")[0]   
        this_id = gen_id()      

        stack.append(
            {
                'user_id': m.author.id,
                'query_id': this_id,
                'time': datetime.now(),
                'expiration': datetime.now() + timedelta(seconds=rate_limit),
                'used_query': True,
                'channel': m.channel.id,
                'query': query,
                'active': True
            })

        if "--reversedns" in c.lower():
            reverse = True
        else:
            reverse = False

        

        init_embed = discord.Embed(
            title=f"Sending Request | Query: {query}",
            description="Please Wait...", url='https://host-info.net', color=embed_color
            )
        await m.channel.send(embed=init_embed)

        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL,auth=aiohttp.BasicAuth(UID,SECRET),json=json.dumps({"query": query,"page":1,"flatten":True})) as resp:
                js = await resp.json()
                #DEBUG# print(js)

        if js["status"] == "ok":
            res = js["results"]
            res_len = len(res)

            if res_len == 0:
                embed = discord.Embed(
                    title=f"0 Results Found...",
                    description="Query: " + "`" + query + "`", url='https://host-info.net', color=embed_color
                    )

                embed.set_image(url="https://censys.io/assets/censys-logo-white.png")    
                await m.channel.send(embed=embed)
                return            
            
            index = 1

            if reverse and res_len > result_limit_during_reverse_dns:
                res_len = result_limit_during_reverse_dns

            for result in res:
                this_embed = discord.Embed(
                    title=f"Result #{index} / {res_len} | Query: {query}",
                    description=" ", url='https://host-info.net', color=embed_color
                    )

                this_embed.set_author(name=str(m.author), url='https://host-info.net', icon_url=m.author.avatar_url)

                try:
                    cc = f'https://www.countryflags.io/{result["location.country_code"].lower()}/shiny/64.png'
                except:
                    cc = "https://s.clipartkey.com/mpngs/s/73-734603_picture-freeuse-explosion-like-text-bubbles-transprent-oops.png"

                if reverse:
                    try:
                        hostname = socket.gethostbyaddr(result["ip"])[0]
                    except Exception as f:
                        hostname = str(f)

                    if hostname == "":
                        hostname = "blank"
                        
                this_embed.set_thumbnail(url=cc)
                this_embed.set_image(url="https://censys.io/assets/censys-logo-white.png")

                this_embed.add_field(
                    name="IP",
                    value=result["ip"],
                    inline=False
                    )  
                
                if reverse:
                    this_embed.add_field(
                        name="Hostname",
                        value=hostname,
                        inline=False
                        )                        

                this_embed.add_field(
                    name="Protocols",
                    value= ", ".join(result["protocols"]),
                    inline=False
                    )           

                try:
                    con = result["location.continent"]
                except:
                    con = "N/A"    

                this_embed.add_field(
                    name="Continent",
                    value=con,
                    inline=True
                    )   

                try:
                    co = result["location.country"]
                except:
                    co = "N/A"         
                try:
                    co1 = result["location.country_code"]
                except:
                    co1 = "N/A"                                     

                this_embed.add_field(
                    name="Country",
                    value=co + " | " + co1,
                    inline=True
                    )      
                
                try:
                    cor = result["location.registered_country"]
                except:
                    cor = "N/A"    

                this_embed.add_field(
                    name="Country Of Registration",
                    value=cor,
                    inline=True
                    )

                try:
                    tz = result["location.timezone"]
                except:
                    tz = "N/A"    

                this_embed.add_field(
                    name="Timezone",
                    value=tz,
                    inline=True
                    )              

                try:
                    prov = result["location.providence"]
                except:
                    prov = "N/A"    

                this_embed.add_field(
                    name="State/Providence",
                    value=prov,
                    inline=True
                    )      

                try:
                    lat_lon = str(result["location.latitude"]) + "," + str(result["location.longitude"])
                except:
                    lat_lon = "N/A"    

                this_embed.add_field(
                    name="Latitude, Longitude",
                    value=lat_lon,
                    inline=True
                    )     

                this_embed.set_footer(text=f"A bot by Aero@host-info.net | Request by {m.author} in #{message.channel}.")        

                await m.channel.send(embed=this_embed)

                ### POST-MESSAGE CHECK-IN
                
                #    
                if index == res_len:
                    if reverse:
                        description=f"Reached end of query. Max {result_limit_during_reverse_dns} results with use of \"--reversedns\", leave this out for max 100 results."
                    else:
                        description="Reached end of query."    

                    ##
                    pointer = 0
                    for item in stack:
                        if item['query_id'] == this_id:
                            del stack[pointer]
                            break
                        pointer += 1    
                    ##    

                    rev_embed = discord.Embed(
                        title=f"End of Query",
                        description=description, url='https://host-info.net', color=embed_color
                        )

                    await m.channel.send(embed=rev_embed)   
                    return

                # CHECK IF JOB HAS BEEN FLUSHED
                stack_pointer = 0
                loop = False
                for item in stack:
                    if this_id == item['query_id']:
                        loop = True
                    stack_pointer += 1   

                if loop == False:
                    return
                
                #
                index += 1

        elif js["status"] == "error":
            await m.channel.send("**ERROR**")   

        else:
            await m.channel.send(f"**UNKNOWN ERROR:** `{js['status']}`")     
    ##################################################

client.run(token)