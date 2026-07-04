# usage
should work via `uv run bot.py`. well add your `.env` vars first

# AI (openai compatible api)
ai is uesd for two task. first usage is too humanize output as the rulebook encouraged. second is to detect user message as command. so that boss doesnt have to write "!usage", or "!room work2". he can just say "update me on 2nd room".

oh and it also suggest me keyword for gif. which then fetched randomly from **giphy** (thanks for free api lol).

## local stack
used local open source llm via ollama. my laptop has no gpu, so not a great model chosen. the model with system prompt is written in `Modelfile`. change model if you have better pc. then run 
```zsh
ollama create discord-intent -f ./Modelfile.intent
ollama create discord-respond -f ./Modelfile.respond
```

the system prompt is also written by another ai (hail lord *claude*). also i have zero interest on fine tuning this system prompt. its a one day hackathon. not my dream project. you get the basic idea of how thing works. best of luck.

why two model running? well, i tried on 1 model. but then i have to take of prompts in weird way that i do not like. so seperate task, seperate model. this is not efficient, neither you should do on real life. **but i am testing this on a laptop with no gpu, so i had to do this, otherwise the output was wrong sometimes.**

## remote api model
just change `.env` var for the ai api. example value is given for local api. read ollama doc for local tuning.

