from discord import Webhook, RequestsWebhookAdapter, Embed # Importing discord.Webhook and discord.RequestsWebhookAdapter
import os
import io
import datetime
import requests
import boto3
import csv


class Message():
    def __init__(self,title,description):
        self.message = Embed(title=title, description=description)

    def addField(self,name,value):
        self.message.add_field(name=name, value=value, inline=False)
    
    def setProfilestring(self,level,rank,rp,before_rp):
        self.profile = "レベル: " + level + "　" + "ランク: " + rank + "　" + "RP: " + rp + " (" + before_rp + ")"

class apexApi():
    def __init__(self):
        self.base_url = "https://public-api.tracker.gg/v2/apex/standard/profile"
        
        API_KEY = os.environ['APEX_API_KEY']
        self.header = {"TRN-Api-Key":API_KEY}

    def getProfile(self,platform,userid):
        url = self.base_url + "/" + platform + "/" + userid
        self.res = requests.get(url, headers=self.header)
        self.res.raise_for_status()
        self.resJson = self.res.json()
        self.result()

    def result(self):
        self.level   = self.resJson['data']['segments'][0]['stats']['level']['displayValue']
        self.rank    = self.resJson['data']['segments'][0]['stats']['rankScore']['metadata']['rankName']
        self.rp      = self.resJson['data']['segments'][0]['stats']['rankScore']['displayValue']
        self.rpvalue = int(self.resJson['data']['segments'][0]['stats']['rankScore']['value'])

class dataControler_aws():
    def __init__(self):
        self.BUCKET_NAME = os.environ['BUCKET_NAME']
        self.filename    = 'data.csv'
        self.local_path  = './tmp/' + self.filename
        self.s3_path     = self.filename

        self.s3 = boto3.resource('s3')
        self.bucket = self.s3.Bucket(self.BUCKET_NAME)
    
    def uploadCsv(self):
        self.bucket.upload_file(self.local_path, self.s3_path)

    def readCsv(self):
        obj = self.s3.Object(self.BUCKET_NAME, self.filename).get()
        self.Csvdict_S3 = csv.DictReader(io.TextIOWrapper(io.BytesIO(obj['Body'].read())))
    
    def savelocalCsv(self, datalist):
        fieldnames = ['Username', 'RP']

        with open(self.local_path, 'w', newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for data in datalist:
                writer.writerow({"Username": data['username'], "RP": data['rp']})


def main():

    tokyo_tz = datetime.timezone(datetime.timedelta(hours=9))
    dt = datetime.datetime.now(tokyo_tz)
    
    embed = Message("",dt.strftime("%Y/%m/%d %a %H:%M:%S"))

    datalist = []
    stats = apexApi()

    dataControler = dataControler_aws()
    dataControler.readCsv()

    for dict in list(dataControler.Csvdict_S3):
        userid = dict['Username']

        stats.getProfile(platform="origin",userid=userid)

        try:
            diffrp = '{:+d}'.format(stats.rpvalue - int(float(dict['RP'])))
        except Exception as e:
            print('Exception')
            print(e.args)
            diffrp = '{:+d}'.format(0)

        datalist.append({'username': userid, 'level': stats.level, 'rank': stats.rank, 'rp': stats.rpvalue, 'diffrp': diffrp})

    for i in range(len(datalist)):
        embed.setProfilestring(datalist[i]['level'],datalist[i]['rank'],str(datalist[i]['rp']),str(datalist[i]['diffrp']))
        embed.addField(datalist[i]['username'],embed.profile)

    dataControler.savelocalCsv(datalist)
    dataControler.uploadCsv()

    WEBHOOK_URL = os.environ['DISCORD_WEBHOOK_URL']
    webhook = Webhook.from_url(WEBHOOK_URL, adapter=RequestsWebhookAdapter())
    webhook.send(embed=embed.message)

if __name__ == '__main__':
    main()
