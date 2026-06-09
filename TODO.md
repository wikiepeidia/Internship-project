Recommendation to add to slide and report

- slide: add Reference slide
- Report+slide: Research about Chatgpt/cloud api leaking user daata .

Urgent fix according to supervisor, require to rerun the model and evaluate the model again.

# slides 1

- Localized: not quite correxct, supervisor said "making clear: only training model not making app"-->fix the title
- Explainable AI: he said not too clear due to project is only give like clue and stuffs
-

# slide2

- Agenda-->replace by table of content
- Fix slide alignment : Why local -->after the motivation

# slide 3 ok

# slide 4

- just pipleine model training not system so do not put name stystem architecture
- synthethise data?where
do you use it for val /test (model can be overfit)at least for val
require to say no (no one use synthethise data to train test)
- Versioned spilts--> change to data spilts
-

# slide 5

- pydantic need to explain a bit, gemini+ judje manually-->need to apply t test-->
# slide 6:
- content in this slide not good (jaikbreak cases cant have shit )
- api leak recommended + privacy issue, require researching for chatgpt leaked data problem

# slide 7 ok

# slide 8: 
- training result 1,733s is 1 second or 1733 second require fix
- why Quantization 4 bit, but cpu deployed to GGUF 8? no sense. 

# slide 9:
- evaluation has to be fixed, we need eval on all stats, but dont need to eval 4 of these classes, instead quickly run on Scam+non scam messages 
- terrible chart, can convert to table 

# slide 10: 
- the same as slidee 9 where you just need scam+non scam 

# report:
- after fixing slide, required to f