var firstStored = null;
var moreStatementsUrl = null;

google.load('visualization', '1.0', {'packages':['corechart']});

$(document).ready(function(){

    ADL.XAPIWrapper.changeConfig(Config);

    GetStatements(25,null,null,RenderStatements);
    $('#refreshStatements').click(function(){
        $("#theStatements").empty();
        GetStatements(25,null,null,RenderStatements);
    });
    $('#showAllStatements').click(function(){
        GetStatements(25,null,null,RenderStatements, true);
    });
    
    GetActivityProfile ("act:adlnet.gov/JsTetris_XAPI", "profile:highscores", RenderHighScores);
    GetStatements(0,"http://adlnet.gov/xapi/verbs/completed","act:adlnet.gov/JsTetris_XAPI",RenderTetrisScoreChart);
    $("#refreshHighScores").click(function(){
        $("#tetrisHighScoreData").empty();
        GetActivityProfile("act:adlnet.gov/JsTetris_XAPI", "profile:highscores", RenderHighScores);
        GetStatements(0,"http://adlnet.gov/xapi/verbs/completed","act:adlnet.gov/JsTetris_XAPI",RenderTetrisScoreChart);
    });
});


function GetStatementsWithinContext (num, verb, activityId, callbackFunction, nextPage) {
    GetStatements(num, verb, activityId, callbackFunction, nextPage, true);
}

function GetStatements (num,verb,activityId,callbackFunction, nextPage, isContextActivity) {
    if (nextPage && moreStatementsUrl !== null && moreStatementsUrl !== undefined)
    {
        ADL.XAPIWrapper.getStatements(null, moreStatementsUrl, callbackFunction);
    } 
    else 
    {
        var params = ADL.XAPIWrapper.searchParams();
        if (num > 0){
            params["limit"] = num;
        }
        if (verb != null){
            params["verb"] = verb;
        }
        if (activityId != null){
            params["activity"] = activityId;
        }
        if(isContextActivity){
            params["related_activities"] = "true";
        }
        // XHR_request(tc_lrs, url, "GET", null, auth, callbackFunction);
        ADL.XAPIWrapper.getStatements(params, null, callbackFunction);
    }
}

function GetActivityProfile (activityId, profileKey, callbackFunction) {
        // var url = endpoint + "activities/profile?activityId=<activity ID>&profileId=<profilekey>";
        
        // url = url.replace('<activity ID>',encodeURIComponent(activityId));
        // url = url.replace('<profilekey>',encodeURIComponent(profileKey));
        
        // XHR_request(tc_lrs, url, "GET", null, auth, callbackFunction, true);
        ADL.XAPIWrapper.getActivityProfile(activityId, profileKey, null, callbackFunction, null, true);
}

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
}

function RenderStatements(xhr){
    var statementsResult = JSON.parse(xhr.responseText);
    var statements = statementsResult.statements;
    moreStatementsUrl = statementsResult.more;
    if(moreStatementsUrl === undefined || moreStatementsUrl === null || moreStatementsUrl === ""){
        $("#showAllStatements").hide();
    }
    else{
        $("#showAllStatements").show();     
    }
    var stmtStr = "<table>";
    var i;
    var dt;
    var aDate;
    if (statements !== undefined && statements !== ""){


        if (statements.length > 0) {
            if (!firstStored) {
                firstStored = statements[0].stored;
            }
        }

        for (i = 0; i < statements.length ; i++){
            stmtStr += "<tr class='statement' tcid='" + statements[i].id + "'>";
            aDate = /^(\d{4})-(\d{2})-(\d{2}).(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)/.exec(statements[i].stored);
            dt = new Date(Date.UTC(aDate[1], aDate[2]-1, aDate[3], aDate[4], aDate[5], aDate[6]));  
            stmtStr += "<td class='date'>"+ dt.toLocaleDateString() + " " + dt.toLocaleTimeString()  +"</td>";

            stmtStr += "<td > <span class='actor'>"+ getActorName(statements[i].actor) +"</span>";
            
            var verb = getVerb(statements[i].verb);
            
            
            var obj = getTargetDesc(statements[i].object);
            if (statements[i].object.definition != undefined){
                var activityType = statements[i].object.definition.type;
                if (activityType != undefined && (activityType == "question" || activityType == "interaction")){
                    obj = (statements[i].object.definition.description != undefined) ? statements[i].object.definition.description["en-US"] : obj;
                    
                    var answer = "";
                    var corrAnswer = "";
                    if (statements[i].result != undefined){
                        if (statements[i].result.success != undefined){
                            stmtStr += " <span class='score'>"+ ((statements[i].result.success)?"correctly":"incorrectly") +"</span>";
                            if (!statements[i].result.success && statements[i].object.definition.correct_responses != undefined){
                                corrAnswer = " The correct response is '" + statements[i].object.definition.correct_responses + "'.";
                            }
                        }
                        if (statements[i].result.response != undefined){
                            answer = " with response '" + statements[i].result.response + "'.";
                        }
                        
                        
                    }

                    stmtStr += " <span class='verb'>"+ verb +"</span>";
                    stmtStr += " <span class='object'>'"+ obj +"'</span>";
                    stmtStr += (answer != "")? answer : ".";
                    stmtStr += corrAnswer;
                    
                } else if (verb == "experienced" && statements[i].object.definition.type != undefined && statements[i].object.definition.type == "Location"){
                    
                    stmtStr += " <span class='verb'>visited</span>";
                    obj = (statements[i].object.definition.name != undefined) ? statements[i].object.definition.name["en-US"] : obj;
                    stmtStr += " <span class='object'>"+ obj +"</span>";
                    
                    if (statements[i].context.extensions.latitude != null && statements[i].context.extensions.longitude != null){
                        stmtStr += " (latitude: "+ 
                                        statements[i].context.extensions.latitude +
                                        ", longitude: " + 
                                        statements[i].context.extensions.longitude + ")";
                    }
                
                
                } else {
                    stmtStr += " <span class='verb'>"+ verb +"</span>";
                    obj = (statements[i].object.definition.name != undefined) ? statements[i].object.definition.name["en-US"] : obj;
                    stmtStr += " <span class='object'>"+ obj +"</span>";
                }
                
                
                
                
            }
            else{
                stmtStr += "&nbsp;<span class='verb'>"+ verb +"</span>&nbsp;<span class='object'>"+ obj +"</span>";
            }
            
            
            
            if (statements[i].result != undefined){
                if (statements[i].result.score != undefined && statements[i].result.score.raw != undefined){
                    stmtStr += " with score <span class='score'>"+ statements[i].result.score.raw +"</span>";
                }
            }
            stmtStr += "<div class='tc_rawdata' tcid_data='" + statements[i].id + "'><pre>" + JSON.stringify(statements[i], null, 4) + "</pre></div>";
            
            stmtStr += "</td></tr>";
            
            
            
        }
    }
    stmtStr += "</table>";
    
    $("#theStatements").append(stmtStr);
    $('tr[tcid]').click(function(){
        $('[tcid_data="' + $(this).attr('tcid') + '"]').toggle();
    })
}



function RenderHighScores(xhr){
    var scores = (xhr.status == 200)?JSON.parse(xhr.responseText):[];

    if (scores.length > 0){
        $("#tetrisHighScoreData").empty();
    }
    
    html = "<table>";

    for (var i = 0; i < scores.length ; i++){
        html += "<tr class='highScoreRow'><td class='scoreRank'>" + (i+1) + "</td>";

        var name = (scores[i].actor.name != undefined) ? scores[i].actor.name : scores[i].actor.mbox;

        html += " <td class='actor'>"+ name +"</td>";

        html += " <td class='score'>"+ scores[i].score +"</td>";
        
        var dt = scores[i].date.substr(0,19).replace("T"," ");//yyyy-MM-ddTHH:mm:ss
        html += " <td class='date'>"+ dt +"</td>";
        
        html += "</tr>";
        
        
    }
    html += "</table>";
    
    $("#tetrisHighScoreData").append(html);
}

function RenderTetrisScoreChart(xhr){
    var statements = JSON.parse(xhr.responseText).statements;
    
    var playerScores = new Object();
    var players = new Array();
    var scores = new Array();
    var emails = new Array();
    var maxScore = 0;
    
    for (var i = 0; i < statements.length ; i++){
        var name = (statements[i].actor.name != undefined) ? statements[i].actor.name : statements[i].actor.mbox;
        var email = statements[i].actor.mbox;
        
        var score = (statements[i].result != undefined 
            && statements[i].result.score != undefined 
            && statements[i].result.score.raw != undefined) ? statements[i].result.score.raw : 0;
        
        if (playerScores[name] !== undefined && emails.indexOf(email) > -1){
            if (score > playerScores[name].score){
                playerScores[name].score = score;
                playerScores[name].count = 1;
                scores[playerScores[name].index] = score;
            }
            else {
                playerScores[name].count++;
            } 
        } else {
            playerScores[name] = new Object();
            playerScores[name].score = score;
            playerScores[name].index = scores.push(score)-1;
            playerScores[name].count = 1;
            players.push(name);
            emails.push(email);
        }
    }
    
    var height = (players.length * 40) + 50;
    
    var data = new google.visualization.DataTable();
    data.addColumn('string', 'Player');
    data.addColumn('number', 'Score');
    data.addRows(players.length);
    for (i = 0; i < players.length;i++){
        data.setCell(i,0,players[i]);
        data.setCell(i,1,scores[i]);
    }

      // Set chart options
      var options = {'title':'Tetris Personal Best Scores',
                     'width':960,'height':height,
                    titleTextStyle: {fontSize: 14} };

      // Instantiate and draw our chart, passing in some options.
      var chart = new google.visualization.BarChart(document.getElementById('tetrisScoresChart'));
      chart.draw(data, options);

    var gamesData = new google.visualization.DataTable();
    gamesData.addColumn('number', 'Games');
    gamesData.addColumn('number', 'Score');
    //gamesData.addColumn('string', 'Player');
    gamesData.addRows(players.length);
    for (i = 0; i < players.length;i++){
        gamesData.setCell(i,0,playerScores[players[i]].count);
        gamesData.setCell(i,1,playerScores[players[i]].score);
        //gamesData.setCell(i,2,players[i]);
    }
    var gamesOptions = {'title':'Tetris Games Played to achieve to High Score',
                    width:432,
                    height:300,
                    hAxis: {title: 'Games'},
                    vAxis: {title: 'Score'},
                    legend: 'none',
                    titleTextStyle: {fontSize: 14} };

      // Instantiate and draw our chart, passing in some options.
      var gamesChart = new google.visualization.ScatterChart(document.getElementById('tetrisGamesScores'));
      gamesChart.draw(gamesData, gamesOptions);
}
