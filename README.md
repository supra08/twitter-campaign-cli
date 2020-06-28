<p align="center">
  <img src="https://i.imgur.com/SKDEUxo.png" height="200px"><br />
  Run your Campaigns on Twitter from your terminal<br /><br /><br />
  <img src="https://i.imgur.com/X2QHI9L.gif">
</p>

## Installation

1. This application needs MongoDB to be installed. You can install it with Brew

```
    brew tap mongodb/brew
    brew install mongodb-community@4.2
```

2. Clone this repository

```
    git clone https://github.com/supra08/twitter-campaign-cli
    cd twitter-campaign-cli
```

3. For the first run, run command

```
    ./tc-cli config
```

and configure your API keys. First run will take time because it installs all the dependencies.

4. Run this command to get a list of all possible commands

```
    ./tc-cli --help
```

### List of commands

    add                 Add New Campaign
    start               Start a Campaign
    status              Status of a Campaign
    delete              Delete a (or all) Campaign(s)
    dm                  Direct message for a campaign
    list                List all campaigns
    reset               Reset a campaign
    followers           get followers of a campaign
    stop                Stop a campaign
    edit                Edit a campaign
    continue            continue all started campaigns

## Authors

* Supratik Das ([@supra08](https://github.com/supra08))  
* Palak Goenka ([@palakg11](https://github.com/palakg11))  
* Kanav Gupta ([@kanav99](https://github.com/kanav99))

Created with :heart: by [SDSLabs](https://sdslabs.co)

Icon Credits: Freepik
