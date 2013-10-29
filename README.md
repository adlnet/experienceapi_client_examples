Experience API Client Examples
=============================

## Contributing to the project
We welcome contributions to this project. Fork this repository, 
make changes and submit pull requests. If you're not comfortable 
with editing the code, please submit an issue and we'll be happy 
to address it.

xAPI client examples built from the original Tin Can examples from Rustici Software that now implement ADL's [xAPIWrapper](https://github.com/adlnet/xAPIWrapper). 
The examples are split into two folders, .95 for data compliant to the .95 xAPI specification and 1.0 for data compliant to the current 1.0.1 spec. Read more about the Experience API Spec here.](https://github.com/adlnet/xAPI-Spec/blob/master/xAPI.md)

## config.js
config.js is used to configure the LRS endpoint and user information. This file needs created. To do this, edit config.js.template

example:
```javascript
Config.endpoint = "https://lrs.adlnet.gov/xapi/";
Config.user = "username";
Config.password = "password";
Config.actor = { "mbox": "name@example.com", "name": "my name" };
```

Each folder contains three examples, a Report Sample, Statement Viewer, and JavaScript Tetris.

## Report Sample

The Statements tab displays all of the statements in the LRS in a human-readable form (I did this.). When each statement is clicked, it is expanded to show the full JSON representation of the statement that is stored inside of the LRS.

The Tetris Reporting tab contains a high score chart of the tetris scores from the JavaScript Tetris example, as well as a bar graph and scatter plot on how many times it took each user to achieve their high score.

## Statement Viewer

The Statement Viewer also displays all of the statements in the LRS in a collapsable human-readable format. This time however, you can query the statements based on the actor's email, verb ID, activity ID, since, until, registration, and actor JSON parameters.  When the query is made, the full query is also visible.

## JS Tetris

The tetris game is a fully playable tetris game that sends playing statements to the LRS. It will send statements once you begin a game, complete a level, and when you inevitably lose. If you don't want to submit data to the LRS, you can uncheck the box below the game, and you can also change the actors name by giving it your name and email address. There is also another tetris leaderboard on the left side of the game.

