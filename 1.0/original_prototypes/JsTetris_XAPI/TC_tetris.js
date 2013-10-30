var TCActive = false;

var actorName = "";
var actorEmail = "";

var gameId = "";

var GAME_ID = "act:adlnet.gov/JsTetris_XAPI";

conf = ADL.XAPIWrapper.lrs;

$(document).ready(function(){

	$('#activateTinCan').change(function(){
		if (!$(this).is(':checked')){
			TCActive = false;
			$('#tc_actorprompt').hide();
		} else {
			TCActive = true;
            if(conf !== undefined && conf.actor !== undefined){
                var actor = JSON.parse(conf.actor);
                actorName = actor.name;
                actorEmail = actor.mbox;
                
			    $('#tc_name').text(actorName);
			    $('#tc_email').text(actorEmail);
            }
			if (actorName == "" || actorEmail == ""){
				$('#tc_actorprompt').show();
			} else {
				$('#tc_actor').show();
			}
		}
	});

	$('#tc_submitActor').click(function(){
		if ($('#tc_nameInput').val() == "" || $('#tc_emailInput').val() == ""){
			alert("Please enter a name and an email.");
			return;
		} else {
			actorName = $('#tc_nameInput').val();
			actorEmail = $('#tc_emailInput').val();
			
			conf.actor = JSON.stringify({"name":actorName, "mbox":"mailto:" + actorEmail})
			
			$('#tc_name').text(actorName);
			$('#tc_email').text(actorEmail);
			
			$('#tc_actorprompt').hide();
			$('#tc_actor').show();
			
			if (tetris.puzzle){
				tc_sendStatment_StartNewGame();
			}
			
		}
		
	});
	
	$('#tc_changeactor').click(function(){
		$('#tc_actor').hide();
		$('#tc_actorprompt').show();
	});


	$('#activateTinCan').click();

});


function tc_getContext(registrationId){
    return {
        "contextActivities":{
            "grouping":{"id":GAME_ID}
        },
        "registration":registrationId
    };
}

function tc_sendStatementWithContext(stmt){
    stmt["context"] = tc_getContext(gameId);
    ADL.XAPIWrapper.sendStatement(stmt);
}

function tc_actor(act){
	if (act === undefined || act === ""){
		return {"name":"unknown","mbox":"mailto:unknown@example.com"};
	}
	a = JSON.parse(act);
	if (a.mbox.slice(0, "mailto:".length) != "mailto:"){
		a.mbox = "mailto:" + a.mbox;
	}
	return a;
}

function tc_sendStatment_StartNewGame(){
	if (TCActive){
		gameId = ADL.ruuid();
		var tcGameObj = {
            'id':GAME_ID,
			"definition":{
				"type":"type:media",
				"name":{"en-US":"Js Tetris - xAPI Prototype"},
				"description":{"en-US":"A game of tetris."}
            }
        };
        var stmt = {
			"actor":tc_actor(conf.actor),
			"verb":{"id":"http://adlnet.gov/xapi/verbs/attempted",
			        "display":{"en-US":"started"}},
			"object":tcGameObj
        };

        tc_sendStatementWithContext(stmt);
	}	
}

function tc_sendStatment_FinishLevel(level,time,apm,lines,score){
	if (TCActive){
		
		var tcGameObj = {
            "id":"act:adlnet.gov/JsTetris_XAPI/level" + level,
			"definition":{
				"type":"type:media",
				"name":{"en-US":"Js Tetris Level" + level},
				"description":{"en-US":"Starting at 1, the higher the level, the harder the game."}
            }
        };

		var resultObj = {
            "extensions":{
                "ext:time":time,
			    "ext:apm":apm,
			    "ext:lines":lines
            },
			"score":{
			    "raw":score,
			    "min":0
            }
        };
			
		var stmt = {
			"actor":tc_actor(conf.actor),
			"verb":{"id":"http://adlnet.gov/xapi/verbs/passed(to_go_beyond)",
		            "display":{"en-US":"passed"}},
			"object":tcGameObj,
			"result":resultObj
        };

        tc_sendStatementWithContext(stmt);
	}	
}

function tc_sendStatment_EndGame(level,time,apm,lines,score){
	if (TCActive){
		
		var tcGameObj = {
            "id":GAME_ID,
			"definition":{
				"type":"type:media",
				"name":{"en-US":"Js Tetris - xAPI Prototype"},
				"description":{"en-US":"A game of tetris."}
            }
        };

		var resultObj = {
            "score":{
				"raw":score,
				"min":0
            },
            "extensions":{
			    "ext:level":level,
			    "ext:time":time,
			    "ext:apm":apm,
			    "ext:lines":lines
            }
        };

		var stmt = {
			"actor":tc_actor(conf.actor),
			"verb":{"id":"http://adlnet.gov/xapi/verbs/completed",
		            "display":{"en-US":"finished"}},
			"object":tcGameObj,
			"result":resultObj
        };

        tc_sendStatementWithContext(stmt);

			
		//update high score
		var newScoreObj = {
            "actor":tc_actor(conf.actor),
			"score":score,
			"date":(new Date()).toISOString()
        };
		
        tc_addScoreToLeaderBoard(newScoreObj, 0);
	}	
}

function tc_addScoreToLeaderBoard(newScoreObj, attemptCount){
    if(attemptCount === undefined || attemptCount === null){
        attemptCount = 0;
    }
    if(attemptCount > 3){
        throw new Error("Could not update leader board");
    }
    
	tc_InitHighScoresObject();
	var highScorePos = tc_findScorePosition(HighScoresArray, 0, HighScoresArray.length-1, newScoreObj.score);
	if (highScorePos < 15){
		HighScoresArray.splice(highScorePos, 0, newScoreObj);
		if (HighScoresArray.length>15) HighScoresArray.pop();

		ADL.XAPIWrapper.sendActivityProfile(
            GAME_ID, "profile:highscores", 
            HighScoresArray,
            ADL.XAPIWrapper.hash(LastHighScoresStr),
            null,
            function(xhr){
                //If we hit a conflict just try this whole thing again...
                if(xhr.status == 409 || xhr.status == 412){
                    tc_addScoreToLeaderBoard(newScoreObj, attemptCount+1);
                }
            });
	}
}

var HighScoresArray;
var LastHighScoresStr = null;

function tc_InitHighScoresObject(){
	HighScoresArray = ADL.XAPIWrapper.getActivityProfile(GAME_ID, "profile:highscores");
	if (HighScoresArray === undefined || HighScoresArray === null || HighScoresArray == ""){
		HighScoresArray = new Array();
	} else {
        LastHighScoresStr = JSON.stringify(HighScoresArray);
	}
}


function tc_findScorePosition(hsArray, start, end ,val){
	if (hsArray.length == 0) return 0;
	
	var insert = 1;
	var keepsearching = true;
	while (keepsearching){
		if (end - start == 0){
			insert = (val <= parseInt(hsArray[start].score))?start+1:start;
			keepsearching = false;
		} else if (end - start == 1) {
			if 	(val > parseInt(hsArray[start].score)){
				insert = start;
			} else if (val > parseInt(hsArray[end].score)){
				insert = end;
			} else {
				insert = end+1;
			}
			keepsearching = false;	
		} else {
			var mid = start + Math.ceil((end - start)/2);
			if (val <= parseInt(hsArray[mid].score)){
				start = mid;
			} else {
				end = mid
			}
		}
	}
	return insert;
}
	
	


