import requests
from requests.auth import HTTPBasicAuth
import sys
import argparse
import json

# option to hardcode URL & URI
global_url = "http://127.0.0.1:7474"
global_uri = "/db/data/transaction/commit"

# option to hardcode Neo4j database creds, these will be used as the username and password "defaults"
global_username = "neo4j"
global_password = "bloodhound"


def do_test(args):

    try:
        requests.get(args.url + global_uri)
        return True
    except:
        return False


def do_query(args, query):

    data = {"statements":[{"statement":query}]}
    headers = {'Content-type': 'application/json', 'Accept': 'application/json; charset=UTF-8'}
    auth = HTTPBasicAuth(args.username, args.password)

    r = requests.post(args.url + global_uri, auth=auth, headers=headers, json=data)

    if r.status_code == 401:
        print("Authentication error: the supplied credentials are incorrect for the Neo4j database, specify new credentials with -u & -p or hardcode your credentials at the top of the script")
        exit()
    else:
        return r


def get_info(args):

    # key : {query: "", columns: []}
    queries = {
        "users" : {
            "query": "MATCH (n:User) RETURN n.name",
            "columns" : ["UserName"]
            },
        "comps" : {
            "query": "MATCH (n:Computer) RETURN n.name",
            "columns" : ["ComputerName"]
            },
        "groups" : {
            "query": "MATCH (n:Group) RETURN n.name",
            "columns" : ["GroupName"]
            },
        "groups-full" : {
            "query": "MATCH (n),(g:Group) MATCH (n)-[r:MemberOf]->(g) RETURN g.name,n.name",
            "columns" : ["GroupName","MemberName"]
        },
        "das" : {
            "query": "MATCH p =(n:User)-[r:MemberOf*1..]->(g:Group) WHERE g.name=~'DOMAIN ADMINS@.*' RETURN n.name",
            "columns" : ["UserName"]
            },
        "unconstrained" : {
            "query": "MATCH (n) WHERE n.unconstraineddelegation=TRUE RETURN n.name",
            "columns" : ["ObjectName"]
            },
        "nopreauth" : {
            "query": "MATCH (n:User) WHERE n.dontreqpreauth=TRUE RETURN n.name",
            "columns" : ["UserName"]
            },
        "localadmin" : {
            "query": "MATCH p=shortestPath((m:User {{name:\"{uname}\"}})-[r:AdminTo|MemberOf*1..]->(n:Computer)) RETURN n.name",
            "columns" : ["ComputerName"]
            },
        "adminsof" : {
            "query": "MATCH p=shortestPath((m:Computer {{name:\"{comp}\"}})<-[r:AdminTo|MemberOf*1..]-(n:User)) RETURN n.name",
            "columns" : ["UserName"]
            },
        "owned" : {
            "query": "MATCH (n) WHERE n.owned=true RETURN n.name",
            "columns" : ["ObjectName"]
            },
        "hvt" : {
            "query": "MATCH (n) WHERE n.highvalue=true RETURN n.name",
            "columns" : ["ObjectName"]
            },
        "desc" : {
            "query": "MATCH (n:User) WHERE n.description IS NOT NULL RETURN n.name,n.description",
            "columns" : ["UserName","Description"]
            },
        "admincomps" : {
            "query": "MATCH (n:Computer),(m:Computer) MATCH (n)-[r:MemberOf|AdminTo*1..]->(m) return n.name,m.name",
            "columns" : ["AdminCompName","CompName"]
            },
        "nopassreq" : {
            "query": "MATCH (n:User) WHERE n.passwordnotreqd=true RETURN n.name",
            "columns" : ["UserName"]
            }
    }

    query = ""
    cols = []
    if (args.users):
        query = queries["users"]["query"]
        cols = queries["users"]["columns"]
    elif (args.comps):
        query = queries["comps"]["query"]
        cols = queries["comps"]["columns"]
    elif (args.groups):
        query = queries["groups"]["query"]
        cols = queries["groups"]["columns"]
    elif (args.groupsfull):
        query = queries["groups-full"]["query"]
        cols = queries["groups-full"]["columns"]
    elif (args.das):
        query = queries["das"]["query"]
        cols = queries["das"]["columns"]
    elif (args.unconstrained):
        query = queries["unconstrained"]["query"]
        cols = queries["unconstrained"]["columns"]
    elif (args.nopreauth):
        query = queries["nopreauth"]["query"]
        cols = queries["nopreauth"]["columns"]
    elif (args.owned):
        query = queries["owned"]["query"]
        cols = queries["owned"]["columns"]
    elif (args.hvt):
        query = queries["hvt"]["query"]
        cols = queries["hvt"]["columns"]
    elif (args.desc):
        query = queries["desc"]["query"]
        cols = queries["desc"]["columns"]
    elif (args.admincomps):
        query = queries["admincomps"]["query"]
        cols = queries["admincomps"]["columns"]
    elif (args.uname != ""):
        query = queries["localadmin"]["query"].format(uname=args.uname.upper().strip())
        cols = queries["localadmin"]["columns"]
    elif (args.comp != ""):
        query = queries["adminsof"]["query"].format(comp=args.comp.upper().strip())
        cols = queries["adminsof"]["columns"]
    elif (args.nopassreq != ""):
        query = queries["nopassreq"]["query"]
        cols = queries["nopassreq"]["columns"]

    if args.getnote:
        query = query + ",n.notes"
        cols.append("Notes")

    r = do_query(args, query)
    x = json.loads(r.text)
    entry_list = x["results"][0]["data"]


    if args.label:
        print(" - ".join(cols))
    for value in entry_list:
        try:
            print(" - ".join(value["row"]))
        except:
            if len(cols) == 1:
                pass
            else:
                print(" - ".join(map(str,value["row"])))


def mark_owned(args):

    if (args.clear):

        query = 'MATCH (n) WHERE n.owned=true SET n.owned=false'
        r = do_query(args,query)
        print("'Owned' attribute removed from all objects.")

    else:

        note_string = ""
        if args.notes != "":
            note_string = "SET n.notes=\"" + args.notes + "\""

        f = open(args.filename).readlines()

        for line in f:

            query = 'MATCH (n) WHERE n.name="{uname}" SET n.owned=true {notes} RETURN n'.format(uname=line.upper().strip(),notes=note_string)
            r = do_query(args, query)

            fail_resp = '{"results":[{"columns":["n"],"data":[]}],"errors":[]}'
            if r.text == fail_resp:
                print("[-] AD Object: " + line.upper().strip() + " could not be marked as owned")
            else:
                print("[+] AD Object: " + line.upper().strip() + " marked as owned successfully")


def mark_hvt(args):

    if (args.clear):

        query = 'MATCH (n) WHERE n.highvalue=true SET n.highvalue=false'
        r = do_query(args,query)
        print("'High Value' attribute removed from all objects.")

    else:

        note_string = ""
        if args.notes != "":
            note_string = "SET n.notes=\"" + args.notes + "\""

        f = open(args.filename).readlines()

        for line in f:

            query = 'MATCH (n) WHERE n.name="{uname}" SET n.highvalue=true {notes} RETURN n'.format(uname=line.upper().strip(),notes=note_string)
            r = do_query(args, query)

            fail_resp = '{"results":[{"columns":["n"],"data":[]}],"errors":[]}'
            if r.text == fail_resp:
                print("[-] AD Object: " + line.upper().strip() + " could not be marked as HVT")
            else:
                print("[+] AD Object: " + line.upper().strip() + " marked as HVT successfully")


def query_func(args):

    r = do_query(args, args.QUERY)
    x = json.loads(r.text)

    try:
        entry_list = x["results"][0]["data"]

        for value in entry_list:
            try:
                print(" - ".join(value["row"]))
            except:
                if len(value["row"]) == 1:
                    pass
                else:
                    print(" - ".join(map(str,value["row"])))

    except:
        if x['errors'][0]['code'] == "Neo.ClientError.Statement.SyntaxError":
            print("Neo4j syntax error")
            print(x['errors'][0]['message'])
        else:
            print("Uncaught error, sry")


def main():

    parser = argparse.ArgumentParser(description="Maximizing Bloodhound. Max is a good boy.")

    general = parser.add_argument_group("global arguments")

    # generic function parameters
    general.add_argument("-u",dest="username",default=global_username,help="Neo4j database username (Default: {})".format(global_username))
    general.add_argument("-p",dest="password",default=global_password,help="Neo4j database password (Default: {})".format(global_password))
    general.add_argument("--url",dest="url",default=global_url,help="Neo4j database URL (Default: {})".format(global_url))

    # three options for the function
    parser._positionals.title = "available modules"
    switch = parser.add_subparsers(dest='command')
    getinfo = switch.add_parser("get-info",help="Get info for users, computers, etc")
    markowned = switch.add_parser("mark-owned",help="Mark objects as Owned")
    markhvt = switch.add_parser("mark-hvt",help="Mark items as High Value Targets (HVTs)")
    query = switch.add_parser("query",help="Run a raw query & return results (must return node attributes like n.name or n.description)")

    # GETINFO function parameters
    getinfo_switch = getinfo.add_mutually_exclusive_group(required=True)
    getinfo_switch.add_argument("--users",dest="users",default=False,action="store_true",help="Return a list of all domain users")
    getinfo_switch.add_argument("--comps",dest="comps",default=False,action="store_true",help="Return a list of all domain computers")
    getinfo_switch.add_argument("--groups",dest="groups",default=False,action="store_true",help="Return a list of all domain groups")
    getinfo_switch.add_argument("--groups-full",dest="groupsfull",default=False,action="store_true",help="Return a list of all domain groups with all respective group members")
    getinfo_switch.add_argument("--das",dest="das",default=False,action="store_true",help="Return a list of all Domain Admins")
    getinfo_switch.add_argument("--unconst",dest="unconstrained",default=False,action="store_true",help="Return a list of all objects configured with Unconstrained Delegation")
    getinfo_switch.add_argument("--npusers",dest="nopreauth",default=False,action="store_true",help="Return a list of all users that don't require Kerberos Pre-Auth (AS-REP roastable)")
    getinfo_switch.add_argument("--adminto",dest="uname",default="",help="Return a list of computers that UNAME is a local administrator to")
    getinfo_switch.add_argument("--adminsof",dest="comp",default="",help="Return a list of users that are administrators to COMP")
    getinfo_switch.add_argument("--owned",dest="owned",default=False,action="store_true",help="Return all objects that are marked as owned")
    getinfo_switch.add_argument("--hvt",dest="hvt",default=False,action="store_true",help="Return all objects that are marked as High Value Targets")
    getinfo_switch.add_argument("--desc",dest="desc",default=False,action="store_true",help="Return all users with the description field populated (also returns description)")
    getinfo_switch.add_argument("--admincomps",dest="admincomps",default=False,action="store_true",help="Return all computers with admin privileges to another computer [Comp1-AdminTo->Comp2]")
    getinfo_switch.add_argument("--nopassreq",dest="nopassreq",default=False,action="store_true",help="Returns all users that don't require passwords on login")
    getinfo.add_argument("--get-note",dest="getnote",default=False,action="store_true",help="Optional, return the \"notes\" attribute for whatever objects are returned")
    
    getinfo.add_argument("-l",dest="label",action="store_true",default=False,help="Optional, apply labels to the columns returned")

    # MARKOWNED function paramters
    markowned.add_argument("-f","--file",dest="filename",default="",required=False,help="Filename containing AD objects (must have FQDN attached)")
    markowned.add_argument("--add-note",dest="notes",default="",help="Notes to add to all marked objects (method of compromise)")
    markowned.add_argument("--clear",dest="clear",action="store_true",help="Remove owned marker from all objects")

    # MARKHVT function parameters
    markhvt.add_argument("-f","--file",dest="filename",default="",required=False,help="Filename containing AD objects (must have FQDN attached)")
    markhvt.add_argument("--add-note",dest="notes",default="",help="Notes to add to all marked objects (reason for HVT status)")
    markhvt.add_argument("--clear",dest="clear",action="store_true",help="Remove HVT marker from all objects")

    # QUERY function arguments
    query.add_argument("QUERY",help="Query designation")

    args = parser.parse_args()


    if not do_test(args):
        print("Connection error: restart Neo4j console or verify the the following URL is available: http://127.0.0.1:7474")
        exit()

    if args.command == "get-info":
        get_info(args)
    elif args.command == "mark-owned":
        if args.filename == "" and args.clear == False:
            print("Module mark-owned requires either -f filename or --clear options")
        else:
            mark_owned(args)
    elif args.command == "mark-hvt":
        if args.filename == "" and args.clear == False:
            print("Module mark-hvt requires either -f filename or --clear options")
        else:
            mark_hvt(args)
    elif args.command == "query":
        query_func(args)
    else:
        print("Error: use a module or use -h/--help to see help")


if __name__ == "__main__":
    main()
