### this is where the agent logic will live

### two approachs
#  orchesrator into harnessed terminal-subagents with shared memory
#  single agent approach for easier actions 
#  in this implementation, we define the harness as a instance of memory created by the orchestrator, the shared memory with with orchestrator, and the set of tools / permissions
### 

### main novelties of this system --> graph computer state, efficent and fast context windows


### we will build this all in classes ...
import use_model
from use_model import load_model, unload_model, run


### this is our general agent class
class Model():
    def __init__(self, level, sys_prompt, prompt):
        self.level = level 
    
    def loadup(self):
        use_model.load()
    
    def call(self, sys_prompt, prompt):
        use_model.run(sys_prompt + prompt)

    def tools(self):
        ### implement tool access for the model
        return
    
    def memory(self):
        ### set up memory system
        return

    def display_creds(self):
        print(self.level)


