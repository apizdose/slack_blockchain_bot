import requests
import json
from datetime import datetime, timedelta
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import re
import csv
import os


TIMEZONE=0 #your timezone in UTC 

tkn={}
if not os.path.isfile("wallets.csv"):
    with open("wallets.csv", "w", newline="", encoding="utf-8"):
        pass
if os.path.isfile("wallets.csv"):
    pass
if not os.path.isfile("tokens.txt"):
    with open("tokens.txt", "w", newline="", encoding="utf-8"):
        pass
if os.path.isfile("tokens.txt"):
    with open("tokens.txt", "r", newline="", encoding="utf-8") as file:
        tokens=file.read().splitlines()
        for i in tokens:
            s=i.split("=")
            tkn[s[0]]=s[1]
SLACK_BOT_TOKEN=tkn["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN=tkn["SLACK_APP_TOKEN"]
print(SLACK_BOT_TOKEN)
print(SLACK_APP_TOKEN)

app = App(token=SLACK_APP_TOKEN, name="BTC Explorer")

wallets = {}

def reader():
    with open("wallets.csv", "r", newline="", encoding="utf-8") as csvfile:
        csvreader=csv.reader(csvfile, delimiter=",")
        for row in csvreader:
            wallets[row[0]]=row[1]

def writer():
    with open("wallets.csv", "w", newline="", encoding="utf-8") as csvfile:
        csvwriter=csv.writer(csvfile, delimiter=",")
        for key, value in wallets.items():
            csvwriter.writerow([key, value])

def calc(value):
    btc=value/100000000
    usd=0
    eur=0
    try:
        with requests.Session() as s:
            r = s.get(f'https://blockchain.info/ticker')

            data = json.loads(r.text)
            usd=data["USD"]["15m"]*btc
            eur=data["EUR"]["15m"]*btc

        #print(f"{btc} {round(usd, 2)} {round(eur, 2)}")
        rate={"btc":btc, "usd":round(usd, 2), "eur":round(eur, 2)}
    except: 
        rate={"btc":btc, "usd":"error", "eur":"error"}
    return rate

def explorer(txid):
    reader()
    message = ""

    with requests.Session() as s:
        r = s.get(f'https://blockchain.info/rawtx/{txid}')

        data = json.loads(r.text)
        try: 
            timetx = datetime.utcfromtimestamp(data["time"])+ timedelta(hours=TIMEZONE)
            timetx=timetx.strftime('%Y-%m-%d %H:%M:%S')
            
            for i in range (data["vout_sz"]):
                for key, value in wallets.items():
                    if data["out"][i]["addr"] == value:
                        rate=calc(data['out'][i]['value']) or {}
                        message+= f"{key}\n{txid}\n\n{rate['btc']}\n$ {rate['usd']}\n{timetx}\n----------------\n"
            if message == "": message = f"{txid}\nNot our transaction or old wallet! :dotted_line_face:\n\n"
            return message

        except: return f"{data['message']} :x:"

def cmdlet(command):
    msg = ""
    
    try:

        if command[1] == "update":
            wallets[command[2].strip()]=command[3].strip()
            writer()
            msg=f"{command[2]} wallet updated to {command[3].strip()}"
        if command[1] == "delete":
            wallets.pop(command[2].strip())
            writer()
            msg=f"{command[2]} wallet deleted"
        if command[1] == "list":
            msg="Actual wallets:\n"
            reader()
            for k,v in wallets.items():
                msg+=f"{k}\n{v}\n----------\n"
        if command[1] == "help":
            msg="""
Help information:
Hi, my name is BTC Explorer, I'm a bot. :robot_face:
I will help you with searching your transactions on blockchain.
To find transaction info for your current wallet, just send me the hash.

To change your current wallets use the following commands:
    :arrows_counterclockwise: For update actual wallet or add new, use command:
        :cmd update "wallet_name" "wallet"

    :negative_squared_cross_mark: For delete wallet from list, use command:
        :cmd delete "wallet_name"

    :spiral_note_pad: To show a list of current wallets, use command:
        :cmd list

            """
            
        #print(wallets)
        return msg
    except: return "Bad command, type 'help'"

@app.message(re.compile("$"))
def trx(message, say):
    
    try:
        msg=explorer(message["text"])
    except: msg="Somenthing went wrong"

    try:
        if message["thread_ts"]:
            return
    except:
        if message["channel_type"] == "channel":
            if ":cmd" in message["text"]:
                command=message["text"].split(" ")
                say(cmdlet(command=command))
            if "help" in message["text"]:
                say(cmdlet(command=[" ", "help"]))
            if not ":cmd" in message["text"] and not "help" in message["text"]:
                say(msg)
    print(message)

def main():
    reader()
    handler = SocketModeHandler(app, SLACK_BOT_TOKEN)
    handler.start()

if __name__ == "__main__":
    main()
