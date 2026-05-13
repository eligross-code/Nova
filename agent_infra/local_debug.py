### this is a script to locally debug my code, while I am on a plane lol

from use_model import load_model, run


def debug():
    load_model()
    basic = "Here is an issue with a user's code. Explain what is wrong and help fix:" + """
            I want to create an agent memory system....what tools do I give to an agent to write to a file
            in python...also, how is this usually done, .md or .txt? What is most efficenty for reading in/writing
            THINK, but short response. WITH THIS CODE.. it just rewrites the first line, do we have to move on to the
            next time with some short of writer / iterator? ### here is where the tools will live...
                from pathlib import Path

                def write_memory(text):
                    path = Path("/Users/eligross/Desktop/local_agent_infra/agent_infra/memory/mem.md")
                    path.write_text(text)


                write_memory("hellofdf \n")

                  
                                    File "/Users/eligross/Desktop/local_agent_infra/agent_infra/tools.py", line 6, in write_memory
                        path.write_text(text, mode = 'a')
                        ~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
                    TypeError: Path.write_text() got an unexpected keyword argument 'mode'
                    (venv) eligross@Elis-MacBook-Pro agent_infra % 


                """

    run(basic + input("You: "))

while True:
    debug()