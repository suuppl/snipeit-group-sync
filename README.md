# snipeit-ldap-group-sync

This project pulls groups from authentik, adds them to snipeit and subsequently edits the users' (synced via ldap) group memberships

Usage:
```bash
cp auth/authentik.template authentik
# add the base url (line 1) and the api token (line 2)
cp auth/snipeit.template snipeit
# add the base url (line 1) and the api token (line 2)
pip install -r requirements.txt
python src/sync-groups.py
```