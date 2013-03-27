Experience API Client Examples
=============================

Experience API (Tin Can API) client examples.
### 0.95/
Contains examples based on the 0.95 version of the Experience API Specification


### 1.0/
Contains examples based on the 1.0 version of the Experience API Specification

### *version*/original_prototypes/
Prototypes created for the original BAA effort, includes a Statement viewer, 
Reporting example, and Tetris game example

### *version*/oauth/
Contains examples using [OAuth 1.0a](https://tools.ietf.org/html/rfc5849) to connect 
to the ADL LRS

NOTE: The [index page](<version>/original_prototypes/index.html) references JQuery from Google CDN. Hard coding the scheme to 'http' caused issues when hosting these examples on a server configured for https. The scheme was removed from this url, which allows for the scheme to be decided dynamically. However this causes an issue when the prototypes are not hosted. In this case the prepended scheme is 'file' and prevents JQuery from loading. If you plan to run these example from in an unhosted environment, add the scheme to this url.

```javascript
// change this line in <version>/original_prototypes/index.html
<script src="//ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js"></script>
// to the following if running the examples unhosted (not on a server)
<script src="http://ajax.googleapis.com/ajax/libs/jquery/1.6.2/jquery.min.js"></script>
```
