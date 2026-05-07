### set up local, open-source stt model to feel to the local LLM
from tools import open_app, open_url
from wakeword_into_stt import is_awake
from text_agent import chat_with_messages, parse_json, validate_tool_call, run_agent, main
import text_agent
from stt import transcribe_once

class VoiceAgent():
    def __init__(self):
            pass

    def transcribe(self):
        return transcribe_once(2, 0.01)

    def generate_response(self):
        # get transcribed text
        # generate response using LLM
        return "response from LLM"
    
    def voice_response(self):
        # use TTS to speak the response
        pass

    def activate_text_agent(self):
        while True:
            if is_awake():
                text = VoiceAgent.transcribe(self)
                print("Agent:", run_agent(text, 5))


if __name__ == "__main__":
    agent = VoiceAgent()
    agent.activate_text_agent()
