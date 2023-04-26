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
    _t = t()
    return {
        "X-Signature-Version": "app2",
        "X-Claim"            : _t,
        "X-Signature"        : sha256(f"9944822{_t}8{_t}113")
    }

def login(session: httpx.Client, email: str, password: str): # Log into hanime.tv
    session.headers.update(makeXheaders())
    _r = session.post(host+"/rapi/v4/sessions", json={
        "burger": email,
        "fries" : password
    })
    if _r.status_code == 200:
        _r = _r.json()
        _u = _r['user']
        _v = _r['env']['mobile_apps']
        for _ in ['_build_number', 'osts_build_number', 'severilous_build_number']:
            if _ in _v.keys():
                _v = _v[_]
                break
        if type(_v) != int:
            raise exit("[!] Couldn't get build number! Open an issue on github!")
    else:
        raise exit(f"[-] Login failed! Recheck your credentials and/or try again. | Status code: {_r.status_code} | Response: {_r.text}")
    if _u['last_rewarded_ad_clicked_at'] != None:
        _l  = int(tstounix(_u['last_rewarded_ad_clicked_at']))
    else:
        _l  = None
    return {
        "session_token": _r['session_token'],
        "uid"          : _u['id'],
        "build_number" : _v,
        "username"     : f"{_u['name']}#{_u['number']}",
        "coins"        : _u['coins'],
        "last_claimed" : _l
    }

def claim_coins(session: httpx.Client, uid: int, build_number: int):
    session.headers.update(makeXheaders())
    _t = t()
    _r = session.post(host+"/rapi/v4/coins", data={
        "reward_token": sha256("coins%d|%d|%s|coins%d" % (build_number, uid, _t, build_number)) + "|" + _t,
        "version"     : str(build_number)
    })
    if _r.status_code == 200:
        _r = _r.json()
        return True, _r['rewarded_amount'], tstounix(_r['user']['last_rewarded_ad_clicked_at'])
    else:
        return False, _r.text, None

def main():
    cls()
    _s = httpx.Client()
    print("[@] Attempting login...")
    _l = login(_s, email, password)
    _s.headers.update({
        "X-Session-Token": _l["session_token"]
    })
    print(f"[+] Login success! Welcome {_l['username']}")
    while True:
        th = ((60 * 60) * 3)
        cr = int(time.time())
        nx = (_l['last_claimed'] + th)
        if _l['last_claimed'] is not None:
            if cr >= nx+1:
                _c = claim_coins(_s, _l['uid'], _l['build_number'])
                if _c[0] == True:
                    print(f"\n[+] Claimed {_c[1]} coins!")
                    _l['coins'] = _l['coins'] + _c[1]
                    _l['last_claimed'] = _c[2]
                    if webhook_noti == True:
                        webhook(_c[1], _l['coins'], _l['username'])
                else:
                    print("[!] Claim failed! | Response: "+_c[1]+" | Trying again in ~5 minutes...")
                    time.sleep(60 * 5)
            else:
                sys.stdout.write(f"\r[-] Can claim in {unixtohms(nx-cr)}")
                sys.stdout.flush()
                time.sleep(1)
        else:
            raise exit("[!] Never claimed coins before!")
main()