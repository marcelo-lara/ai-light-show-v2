# AI Light Show

## Overview

An intelligent DMX lighting control system that uses AI to analyze music and create synchronized light shows. The system combines audio analysis, and natural language processing to automatically generate lighting performances that match the musical content.


## Components

The project has 3 main components:

- DMX Canvas : The light show that will be performed when the song is played.

- Actions sheet : A list with the commands to "draw" Fixture effects into the DMX Canvas.

- Song Metadata : The information of the song that will be usefull to create the light show. This information comes fron (a) audio analysis from essentia and other models, and (b) user provided information, like key_moments.

- AI Assistant : A conversational model that receive the song metadata to create and update the [Actions sheet]

- Web UI : A web frontend to (a) play song and start the light show. (b) interact with the AI Assistant to manage the [Actions Sheet] (c) Request, review and edit Song Metadata.

### DMX Related

#### DMX Canvas

Responsible of mataining the Universe Canvas: an object representing { time: 0.0, universe: {byteArray}}

### Fixture

- Definition: [Fixtures](fixtures/fixtures.md) are the available installed DMX Lights and fixtures. This file will not change during runtime.

The Fixture 


### Song

The "Song" is an MP3 file from the `/songs` folder with an associated [SongMetadata](File_SongMetadata.md)

The SongMetadata contains the results of Audio Analysis (such as Beats, Chords, Patterns) and User definitions (such as Arrangement, Key Moments).

The purpose of this file is to build prompts for the "Light Designer Agent"
