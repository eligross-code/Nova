### here is where the tools will live...
from pathlib import Path
import subprocess 

def write_memory(text):
    path = Path("/Users/eligross/Desktop/local_agent_infra/agent_infra/memory/mem.md")
    with open(path, 'a') as f:
        f.write(text)


def read_memory():
    path = Path("/Users/eligross/Desktop/local_agent_infra/agent_infra/memory/mem.md")
    with open(path) as f:
        ### read the file and return the text 
        return

### general terminal use --> lots of ability

def terminal(line):
    ## implement
    subprocess.run[_]
    return


### subagent spawning capability --> call itself basically

