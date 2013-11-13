(function(ADL){
Viewer = function(){ 
    this.firstStored = null;
    this.moreStatementsUrl = null;
    this.auth = null;
    this.endpoint = null;
    this.includeRawData = true;
};

Viewer.prototype.getCallback = function(callback){
    var self = this;
    return function(){ callback.apply(self, arguments); };
};

Viewer.prototype.getAuth = function(){ 
    if(this.auth == null){
        this.auth = 'Basic ' + Base64.encode(Config.user + ':' + Config.password);
    }
    return this.auth;
};

Viewer.prototype.getEndpoint = function(){
    if(this.endpoint == null){
        this.endpoint = Config.endpoint;
    }
    return this.endpoint;
};

Viewer.prototype.XAPIStatementQueryObject = function(){
    this.verb = null;
    this.activity = null;
    this.registration = null;
    this.agent = null;
    this.since = null;
    this.until = null;
    this.limit = 0;
    
    this.toString = function(){
        var qs = new Array();
        for(var key in this){
            if(key == "toString" ||
                key == "toObj" || 
                this[key] == null){
                continue;
            }
            var val = this[key];
            if(typeof val == "object"){
                val = JSON.stringify(val);
            }
            qs.push(key + "=" + encodeURIComponent(val));
        }
        return qs.join("&");
    };

    this.toObj = function(){
        var outObj = new Object();
        for(var key in this){
            if(key == "toString" ||
                key == "toObj" || 
                this[key] == null){
                continue;
            }
            var val = this[key];
            if(typeof val == "object"){
                val = JSON.stringify(val);
            }
            outObj[key] = val;
        }
        return outObj;
    }
};

Viewer.prototype.XAPISearchHelper = function(){
    this.getActor = function(){
        var actor = null;
        var actorJson = this.getSearchVar("actorJson");
        var actorEmail = this.getSearchVar("actorEmail");
        var actorAccount = this.getSearchVar("actorAccount");
        
        if(actorJson != null && actorJson.length > 0){
            actor = JSON.parse(actorJson);
        } 
        else {
            if(actorEmail != null){
                actor = (actor == null) ? new Object() : actor;
                if(actorEmail.indexOf('mailto:') == -1){
                    actorEmail = 'mailto:'+actorEmail;
                }
                actor["mbox"] = actorEmail;
            }
            else if(actorAccount != null){
                actor = (actor == null) ? new Object() : actor;
                var accountParts = actorAccount.split("::");
                actor["account"] = {"accountServiceHomePage":accountParts[0], "accountName":accountParts[1]};
            }
        }
        return actor;
    };
    
    this.getVerb = function(){
        verb = null;
        var id = this.getSearchVar("verb");
        if(id != null){
            // verb = new Object();
            // verb["id"] = id;
            verb = id;
        }
        return verb
    };
    
    this.getObject = function(){
        var obj = null;
        var objectJson = this.getSearchVar("objectJson");
        if(objectJson != null){
            obj = JSON.parse(objectJson);
        } else {
            var activityId = this.getSearchVar("activityId");
            if(activityId != null){
                // obj = {"id":activityId};
                obj = activityId;
            }
        }
        return obj;
    };
    
    this.getRegistration = function(){
        return this.getSearchVar("registration");
    };
    
    this.getSince = function(){
        var since = this.getSearchVar("since");
        return since;
    };
    
    this.getUntil = function(){
        var until = this.getSearchVar("until");
        return until;
    };
    
    this.dateStrIncludesTimeZone = function(str){
        return str != null && (str.indexOf("+") >= 0 || str.indexOf("Z") >= 0); 
    };
    
    this.nonEmptyStringOrNull = function(str){
        return (str != null && str.length > 0) ? str : null;
    };
    
    this.getSearchVar = function(searchVarName, defaultVal){
        var myVar = $("#"+searchVarName).val();
        if(myVar == null || myVar.length < 1){
            return defaultVal;
        }
        return myVar;
    };
    
    this.getSearchVarAsBoolean = function(searchVarName, defaultVal){
        return $("#"+searchVarName).is(":checked");
    };
};

Viewer.prototype.XAPIFormHelper = function(){
    this.copyQueryStringToForm = function(){
        var booleanVals = ["context", "authoritative", "sparse"];
        var qsMap = this.getQueryStringMap();
        for(var key in qsMap){
            var inputType = ($.inArray(key, booleanVals) >= 0) ? "checkbox" : "text";
            this.setInputFromQueryString(key, qsMap[key], inputType);
        }
    };
    
    this.setInputFromQueryString = function(name, val, inputType){
        if(inputType == null){
            inputType = "text";
        }
        if(val != null){
            if(inputType == "text"){
                $("#"+name).val(val);
            }
            else if (inputType == "checkbox"){
                if(val == "true"){
                    $("#"+name).attr('checked', 'checked');
                } else {
                    $("#"+name).removeAttr('checked');
                }
            }
        };
    };
    
    this.getQueryStringMap = function(){
        var qs = window.location.search;
        if(qs == null || qs.length < 1){
            return [];
        }
        if(qs.indexOf("#") > 0){
            qs = qs.substring(0, qs.indexOf("#"));
        }
        qs = qs.substring(1, qs.length);
        var nameVals = qs.split("&");
        var qsMap = {};
        for(var i = 0; i < nameVals.length; i++){
            var keyVal = nameVals[i].split("=");
            qsMap[keyVal[0]] = decodeURIComponent(keyVal[1].replace(/\+/g, " "));
        }
        return qsMap;
    };
};

Viewer.prototype.searchStatements = function(){
    var helper = new this.XAPISearchHelper(); 
    var queryObj = new this.XAPIStatementQueryObject();

    queryObj.agent = helper.getActor();
    queryObj.verb = helper.getVerb();
    queryObj.activity = helper.getObject();
    queryObj.registration = helper.getRegistration();
    queryObj.since = helper.getSince();
    queryObj.until = helper.getUntil();
    queryObj.limit = 25;
    queryObj.format = "exact";

    var url = this.getEndpoint() + "statements?" + queryObj.toString();
    $("#XAPIQueryText").text(url);

    this.getStatements(queryObj.toObj(), this.getCallback(this.renderStatementsHandler));
};

Viewer.prototype.getMoreStatements = function(){
    if (this.moreStatementsUrl !== null){
        $("#statementsLoading").show();
        ADL.XAPIWrapper.getStatements(null, this.moreStatementsUrl, this.getCallback(this.renderStatementsHandler));
    }
};

Viewer.prototype.getStatements = function(queryObj, callback){
    ADL.XAPIWrapper.getStatements(queryObj, null, callback);
};

Viewer.prototype.getActivityProfile = function(activityId, profileKey, callbackFunction) {
    ADL.XAPIWrapper.getActivityProfile(activityId, profileKey, null, callbackFunction);
};

Viewer.prototype.renderStatementsHandler = function(xhr){
    this.renderStatements(JSON.parse(xhr.responseText));
};

Viewer.prototype.renderStatements = function(statementsResult) {
    function getActorName(actor) {
        if (actor === undefined) {
            return "";
        }
        if (actor.name !== undefined) {
            return actor.name;
        }
        if (actor.mbox !== undefined) {
            return actor.mbox;
        }
        if (actor.account !== undefined) {
            return actor.account.name;
        }
        return truncateString(JSON.stringify(actor), 20);
    }

    function getVerb(verb) {
        if (verb === undefined) {
            return "";
        }
        
        if (verb.display !== undefined){
            if (verb.display["en-US"] !== undefined) {
                return verb.display["en-US"];
            }            
        }

        if (verb.id !== undefined) {
            return verb.id;
        }
        return truncateString(JSON.stringify(verb), 20);
    }

    function getTargetDesc(obj) {
        if (obj.objectType !== undefined && obj.objectType !== "Activity") {
            return getActorName(obj);
        }

        if (obj.definition !== undefined) {
            if (obj.definition.name !== undefined) {
                if (obj.definition.name["und"] !== undefined) {
                    return obj.definition.name["und"];
                }
                return obj.definition.name["en-US"];
            }

            if (obj.definition.description !== undefined) {
                if (obj.definition.description["und"] !== undefined) {
                    return truncateString(obj.definition.description["und"], 48);
                }
                return truncateString(obj.definition.description["en-US"], 48);
            }
        }
        return obj.id;
    }

    function truncateString(str, length) {
        if (str == null || str.length < 4 || str.length <= length) {
            return str;
        }
        return str.substr(0, length - 3) + '...';
    };


    var statements = statementsResult.statements;

    this.moreStatementsUrl = statementsResult.more;
    if (this.moreStatementsUrl === undefined || this.moreStatementsUrl === null || this.moreStatementsUrl === "") {
        $("#showAllStatements").hide(); 
    } else {
        $("#showAllStatements").show();
    }

    var stmtStr = new Array();
    stmtStr.push("<table>");

    var i;
    var dt;
    var aDate;

    if (statements.length > 0) {
        if (!this.firstStored) {
            this.firstStored = statements[0].stored;
        }
    }

    if (statements.length == 0) {
        $("#statementsLoading").hide();
        $("#noStatementsMessage").show();
    }

    for (i = 0; i < statements.length; i++) {
        var stmt = statements[i];
        try {
            stmtStr.push("<tr class='statementRow'>");
            stmtStr.push("<td class='date'><div class='statementDate'>" + stmt.stored.replace('Z', '') + "</div></td>");

            stmtStr.push("<td >");
            stmtStr.push("<div class=\"statement unwired\" tcid='" + stmt.id + "'>")
            stmtStr.push("<span class='actor'>" + getActorName(stmt.actor) + "</span>");

            var verb = getVerb(stmt.verb);
            var objDesc = getTargetDesc(stmt.object);
            var answer = null;

            if (stmt.object.definition !== undefined) {
                var activityType = stmt.object.definition.type;
                if (activityType != undefined && (activityType == "question" || activityType == "interaction")) {
                    if (stmt.result != undefined) {
                        if (stmt.result.success != undefined) {
                            verb = ((stmt.result.success) ? "correctly " : "incorrectly ") + verb;
                        }
                        if (stmt.result.response != undefined) {
                            answer = " with response '" + truncateString(stmt.result.response, 12) + "'.";
                        }
                    }

                }
            }

            stmtStr.push(" <span class='verb'>" + verb + "</span>");
            stmtStr.push(" <span class='object'>'" + getTargetDesc(stmt.object) + "'</span>");
            stmtStr.push((answer != "") ? answer : ".");

            if (stmt.result != undefined) {
                if (stmt.result.score != undefined && stmt.result.score.raw != undefined) {
                    stmtStr.push(" with score <span class='score'>" + stmt.result.score.raw + "</span>");
                }
            }

            stmtStr.push("</div>");

            if (this.includeRawData) {
                stmtStr.push("<div class='tc_rawdata' tcid_data='" + stmt.id + "'>");
                stmtStr.push("<pre>" + JSON.stringify(stmt, null, 4) + "</pre>")
                stmtStr.push("</div>");
            }

            stmtStr.push("</td></tr>");
        }
        catch (error) {
            if(console !== undefined)
            {
                console.log("Error occurred while trying to display statement with id " + stmt.id + ": " + error.message);
            }
        }
    }
    stmtStr.push("</table>");

    $("#statementsLoading").hide();

    $("#theStatements").append(stmtStr.join(''));
    var unwiredDivs = $('div[tcid].unwired');
    unwiredDivs.click(function() {
        $('[tcid_data="' + $(this).attr('tcid') + '"]').toggle();
    });
    unwiredDivs.removeClass('unwired');
};

Viewer.prototype.pageInitialize = function()
{
    $.datepicker.setDefaults( {dateFormat: "yy-mm-dd", constrainInput: false} );
    $( "#since" ).datepicker();
    $( "#until" ).datepicker()
    
    $("#statementsLoading").show();
    $("#showAllStatements").hide();
    $("#noStatementsMessage").hide();
    
    $('#refreshStatements').click(function(){
        $("#statementsLoading").show();
        $("#showAllStatements").hide();
        $("#noStatementsMessage").hide();
        $("#theStatements").empty();
        ADL.Viewer.searchStatements();
    });
    $('#showAllStatements').click(function(){
        $("#statementsLoading").show();
        ADL.Viewer.getMoreStatements();
    });
    
    $("#showAdvancedOptions").click(function(){
        $("#advancedSearchTable").toggle('slow', function(){
            var visible = $("#advancedSearchTable").is(":visible");
            var text = (visible ? "Hide" : "Show") + " Advanced Options";
            $("#showAdvancedOptions").html(text);
        });
    });
    
    $("#showQuery").click(function(){
        $("#XAPIQuery").toggle('slow', function(){
            var visible = $("#XAPIQuery").is(":visible");
            var text = (visible ? "Hide" : "Show") + " XAPI Query";
            $("#showQuery").html(text);
        });
    });
    
    (new this.XAPIFormHelper()).copyQueryStringToForm();
};
ADL.Viewer = new Viewer();
}(window.ADL = window.ADL || {}));