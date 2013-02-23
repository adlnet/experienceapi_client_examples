Experience API Client Examples
=============================

Experience API (Tin Can API) client examples.

NOTE: 0.95/original_prototypes/index.html references JQuery from Google CDN. Hard coding the scheme to 'http' caused issues when hosting these examples on a server configured for https. The scheme was removed from this url, which allows for the scheme to be decided dynamically. However this causes an issue when the prototypes are not hosted. In this case the prepended scheme is 'file' and prevents JQuery from loading. If you plan to run these example from in an unhosted environment, add the scheme to this url.

```javascript
// change this line in 0.95/original_prototypes/index.html
<script src="//ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js"></script>
// to the following if running the examples unhosted (not on a server)
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js"></script>
```
