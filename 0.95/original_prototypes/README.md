Original Prototypes
===================

These are the original client prototypes produced
with the LRS.

###config.js
config.js is used to configure the LRS endpoint and user information. This file needs created. To do this, edit config.js.template

example:
```javascript
Config.endpoint = "http://localhost:8000/";
Config.authUser = "tom";
Config.authPassword = "1234";
Config.actor = { "mbox": "tomcreighton@example.com", "name": "tom creighton" };
```