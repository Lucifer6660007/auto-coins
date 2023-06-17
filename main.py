import httpx, time, hashlib, ciso8601, toml, sys, os

host         = "https://www.universal-cdn.com"
config       = toml.loads(open('config.toml').read())

email        = config['htv']['email']
password     = config['htv']['password']

webhook_noti = config['etc']['webhook_notification']
webhook_url  = config['etc']['webhook_url']

def tstounix(timestamp: str): #Timestamp to unix
    return int(str(time.mktime(ciso8601.parse_datetime(timestamp).timetuple())).split(".")[0])

def unixtohms(unix: int):
    return f"{(unix//3600):02d}:{(unix%3600)//60:02d}:{unix%60:02d}"

def sha256(text): # sha256 hasher
    return hashlib.sha256(str(text).encode()).hexdigest()

def cls():
    if os.name == 'nt':
        os.system('cls')
    elif os.name == 'posix':
        os.system('clear')
    else:
        pass

def t(): # Current time (cuz im lazy)
    return str(int(time.time()))

def webhook(rewarded: int, coins: int, username: str): # Webhook sender
    httpx.post(webhook_url, headers={'Content-Type': 'application/json'}, json={
        "username": username,
        "content": "@everyone",
        "embeds": [
            {
                "description": f"Claimed **{rewarded}** coins!\n_Total: {coins}_ | <t:{t()}:R>"
            }
        ],
    })

def makeXheaders(): # Make X- headers
    time = t()
    return {
        "X-Signature-Version": "app2",
        "X-Claim"            : time,
        "X-Signature"        : sha256(f"9944822{time}8{time}113")
    }

def login(session: httpx.Client, email: str, password: str): # Log into hanime.tv
    session.headers.update(makeXheaders())
    request = session.post(host+"/rapi/v4/sessions", json={
        "burger": email,
        "fries" : password
    })
    if request.status_code == 200:
        response = request.json()
        user = response['user']
        version = response['env']['mobile_apps']
        for i in ['_build_number', 'osts_build_number', 'severilous_build_number']:
            if i in version.keys():
                version = version[i]
                break
        if type(version) != int:
            raise exit("[!] Couldn't get build number! Open an issue on github!")
    else:
        raise exit(f"[-] Login failed! Recheck your credentials and/or try again. | Status code: {request.status_code} | Response: {request.text}")
    if user['last_rewarded_ad_clicked_at'] != None:
        last_claimed  = int(tstounix(user['last_rewarded_ad_clicked_at']))
    else:
        last_claimed  = None
    return {
        "session_token": response['session_token'],
        "uid"          : user['id'],
        "build_number" : version,
        "username"     : f"{user['name']}#{user['number']}",
        "coins"        : user['coins'],
        "last_claimed" : last_claimed
    }

def claim_coins(session: httpx.Client, uid: int, build_number: int):
    session.headers.update(makeXheaders())
    time = t()
    request = session.post(host+"/rapi/v4/coins", data={
        "reward_token": sha256("coins%d|%d|%s|coins%d" % (build_number, uid, time, build_number)) + "|" + time,
        "version"     : str(build_number)
    })
    if request.status_code == 200:
        response = response.json()
        return True, response['rewarded_amount'], tstounix(response['user']['last_rewarded_ad_clicked_at'])
    else:
        return False, request.text, None

def main():
    cls()
    session = httpx.Client()
    print("[@] Attempting login...")
    login = login(session, email, password)
    session.headers.update({
        "X-Session-Token": login["session_token"]
    })
    print(f"[+] Login success! Welcome {_l['username']}")
    while True:
        cooldown = ((60 * 60) * 3)
        current_time = int(time.time())
        next_claim = (login['last_claimed'] + cooldown)
        if login['last_claimed'] is not None:
            if current_time >= next_claim+1:
                claim = claim_coins(session, login['uid'], login['build_number'])
                if claim[0] == True:
                    print(f"\n[+] Claimed {claim[1]} coins!")
                    login['coins'] = login['coins'] + claim[1]
                    login['last_claimed'] = claim[2]
                    if webhook_noti == True:
                        webhook(claim[1], login['coins'], login['username'])
                else:
                    print("[!] Claim failed! | Response: "+claim[1]+" | Trying again in ~5 minutes...")
                    time.sleep(60 * 5)
            else:
                sys.stdout.write(f"\r[-] Can claim in {unixtohms(next_claim-current_time)}")
                sys.stdout.flush()
                time.sleep(1)
        else:
            raise exit("[!] Never claimed coins before!")
main()