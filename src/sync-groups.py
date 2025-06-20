#!python3

import time
import requests
import json
import functools

def get_rate_limit(url, headers=None, params=None, json_val=None):
    response = requests.get(url, headers=headers, params=params, json=json_val)
    response = json.loads(response.text)
    if response.get("status_code", -1) == 429:
        print(f"rate limit: sleeping for {response['retryAfter']+1} s")
        time.sleep(response["retryAfter"]+1)
        response = requests.get(url, headers=headers, params=params, json=json_val)
        response = json.loads(response.text)
    return response

def post_rate_limit(url, headers=None, params=None, json_val=None):
    response = requests.post(url, headers=headers, params=params, json=json_val)
    response = json.loads(response.text)
    if response.get("status_code", -1) == 429:
        print(f"rate limit: sleeping for {response['retryAfter']+1} s")
        time.sleep(response["retryAfter"]+1)
        response = requests.post(url, headers=headers, params=params, json=json_val)
        response = json.loads(response.text)
    return response

def patch_rate_limit(url, headers=None, params=None, json_val=None):
    response = requests.patch(url, headers=headers, params=params, json=json_val)
    response = json.loads(response.text)
    if response.get("status_code", -1) == 429:
        print(f"rate limit: sleeping for {response['retryAfter']+1} s")
        time.sleep(response["retryAfter"]+1)
        response = requests.patch(url, headers=headers, params=params, json=json_val)
        response = json.loads(response.text)
    return response

def get_url_and_token(authentication_file):
    with open(authentication_file, "r") as f:
        url = f.readline().strip()
        token = f.readline().strip()
    return url, token

def get_groups_from_authentik(authentication_file):
    base_url, token = get_url_and_token(authentication_file)
    url = f"{base_url}/api/v3/core/groups/"

    params = {"search": "::", "include_users": "true", "page": 1, "page_size": 10000}
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    response = requests.request("GET", url, headers=headers, params=params)
    response = json.loads(response.text)
    groups = response["results"]
    groups = [{"name":group["name"],"users":group["users_obj"]} for group in groups]

    for i, group in enumerate(groups):
        users = group["users"]
        users = [user['username'] for user in users if user["is_active"]]
        groups[i]['users'] = users
    # groups = sorted(groups)
    return groups

def get_users_from_groups(groups):
    users = {}
    for group in groups:
        gname = group["name"]
        gusers = group["users"]
        for user in gusers:
            if user not in users:
                users[user] = [gname]
            else:
                users[user].append(gname)
    userlist = []
    for k,v in users.items():
        userlist.append({k:v})
    return userlist

def create_group_in_snipeit(authentication_file, group_name, verbose=False):
    group_mapping = get_snipeit_group_id_mapping(authentication_file)
    base_url, token = get_url_and_token(authentication_file)
    url = f"{base_url}/api/v1/groups"

    params = {"name": group_name}
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "content-type": "application/json",
    }

    # print(f"checking for group {group_name}")

    if group_name in group_mapping:
        return

    print(f"creating group {group_name}")
    response = post_rate_limit(url, headers=headers, params=params)
    if verbose:
        print(response)

@functools.cache
def get_snipeit_group_id_mapping(authentication_file):
    base_url, token = get_url_and_token(authentication_file)
    url = f"{base_url}/api/v1/groups"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "content-type": "application/json",
    }

    params = {
        "limit": 500,
        "offset": 0
    }

    # print(group_name)
    response = get_rate_limit(url, headers=headers, params=params)
    num_groups = response["total"]
    groups = response["rows"]
    # current = len(response["rows"])
    while len(groups) < num_groups:
        params["offset"] = len(groups)-1
        params["limit"] = min(500, num_groups-len(groups))
        response = get_rate_limit(url, headers=headers, params=params)
        groups.extend(response["rows"])

    mapping = {
        group["name"]:group["id"] for group in groups
    }
    return mapping

@functools.cache
def get_snipeit_users(authentication_file):
    base_url, token = get_url_and_token(authentication_file)
    url = f"{base_url}/api/v1/users"

    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "content-type": "application/json",
    }

    params = {
        "limit": 500,
        "offset": 0
    }

    # print(group_name)
    response = get_rate_limit(url, headers=headers, params=params)

    num_users = response["total"]
    users = response["rows"]
    # current = len(response["rows"])
    while len(users) <= num_users:
        params["offset"] = len(users)-1
        params["limit"] = min(500, num_users-len(users)+1)
        response = get_rate_limit(url, headers=headers, params=params)
        users.extend(response["rows"])
        # current += len(response["rows"])
    return users

@functools.cache
def get_snipeit_user(authentication_file, username):
    users = get_snipeit_users(authentication_file)
    for user in users:
        if user["username"] == username:
            return user
    
@functools.cache
def get_snipeit_user_id_mapping(authentication_file):
    users = get_snipeit_users(authentication_file)
    mapping = {
        user["username"]:user["id"] for user in users
    }
    return mapping

def set_snipeit_user_groups(authentication_file, user, write_skipped=True):
    group_id_mapping = get_snipeit_group_id_mapping(authentication_file)
    user_id_mapping = get_snipeit_user_id_mapping(authentication_file)

    username = list(user.keys())[0]
    try:
        user_id = user_id_mapping[username]
    except KeyError:
        print(f"user {username} not found, skipping")
        if write_skipped:
            with open("skipped", "a+") as f:
                f.write(username+"\n")
        return
    groups = user[username]
    group_ids = [group_id_mapping[group] for group in groups]
    group_ids = sorted(group_ids)

    base_url, token = get_url_and_token(authentication_file)
    url = f"{base_url}/api/v1/users/{user_id}"
    
    headers = {
        "accept": "application/json",
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "content-type": "application/json",
    }

    params = {
        "id": user_id,
    }

    # print(f"checking {username}")
    current_user = get_snipeit_user(authentication_file, username)
    if current_user is not None:
        current_groups = current_user["groups"]
        if current_groups is not None:
            current_groups = sorted([group["id"] for group in current_groups["rows"]])
            if group_ids == current_groups:
                return

    print(f"updating {username}")
    payload = {
        "groups": group_ids
    }
    response = patch_rate_limit(url, headers=headers, params=params, json_val=payload)

    if response["status"] != "success":
        raise Exception(response)
    pass

if __name__ == "__main__":
    write_skipped = False

    if write_skipped:
        with open("skipped", "w") as f:
            pass

    authentik_groups = get_groups_from_authentik("auth/authentik")
    authentik_users = get_users_from_groups(authentik_groups)

    for group in authentik_groups:
        create_group_in_snipeit("auth/snipeit", group["name"])

    for user in authentik_users:
        set_snipeit_user_groups("auth/snipeit", user, write_skipped)
