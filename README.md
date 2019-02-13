# NAIL agent
Navigate Acquire Interact Learn

NAIL is a general game-playing agent designed for parser-based interactive fiction games 
([Hausknecht et al. 2019](https://arxiv.org/abs/1902.04259)).
NAIL employs a simple heuristic: examine the current location to identify relevant objects,
interact with the identified objects, navigate to a new location, and repeat.
Though simple, this loop proves effective across a wide variety of games.

NAIL won first place in the 2018 Text-Based Adventure AI Competition
([Atkinson et al. 2018](https://arxiv.org/abs/1808.01262)),
where it was evaluated on a set of twenty unknown parser-based IF games.

## Requirements
* Linux
* Python 3

## Installation
* Install basic build tools.
    * sudo apt-get update
    * sudo apt-get install build-essential
    * sudo apt-get install python3-dev

* Install [fastText](https://github.com/facebookresearch/fastText#building-fasttext-for-python)
    * pip3 install pybind11
    * git clone https://github.com/facebookresearch/fastText.git
    * cd fastText
    * pip3 install .
    * cd ..

* Install [Jericho](https://github.com/Microsoft/jericho)
    * pip3 install jericho
* Clone this nail_agent repository to your Linux machine.
* Download the NAIL agent's language model to the nail_agent/agent/affordance_extractors/language_model directory:
    * wget http://download.microsoft.com/download/B/8/8/B88DDDC1-F316-412A-94B3-025788436054/nail_agent_lm.zip
* unzip nail_agent_lm.zip
    * The unzipped directory should contain 1028 files.

* pip3 install numpy
* pip3 install fuzzywuzzy
* pip3 install spacy
* python3 -m spacy download en
* pip3 install python-Levenshtein

## Usage
* Obtain a z-machine game (like zork1.z5)
* cd nail_agent
* python3 run_nail_agent.py <path_to_game>

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
