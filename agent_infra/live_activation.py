from pynput import keyboard
import subprocess


TRIGGER = "myai\\"
END = "\\"



def get_next_prompt(trigger_only = False, capture_only = False):
    buffer = ""
    capturing = False
    prompt = ""
    result = None

    def on_press(key):
        nonlocal buffer, capturing, prompt, result

        if key == keyboard.Key.backspace:
            char = "SPECIAL"
        elif key == keyboard.Key.space:
            char = " "
        else:
            try:
                char = key.char
            except AttributeError:
                return
            if char is None:
                return



        if trigger_only:
            if char == "SPECIAL":
                if buffer:
                    buffer = buffer[:-1]
            else:
                buffer += char
                buffer = buffer[-len(TRIGGER):]
            if buffer.endswith(TRIGGER):
                print("Trigger detected!")
                result = True
                return False
        
        
        elif capture_only:
            if char == "SPECIAL":
                prompt = prompt[:-1]
            else:
                prompt += char
            if prompt.endswith(END):
                result = prompt[:-len(END)].strip()
                return False

        else:
            if not capturing:
                # waiting for trigger
                if char == "SPECIAL":
                    if buffer:
                        buffer = buffer[:-1]
                else:
                    buffer += char
                    buffer = buffer[-len(TRIGGER):]
                if buffer.endswith(TRIGGER):
                    capturing = True
                    buffer = ""
                    prompt = ""
            else:
                # capturing prompt
                if char == "SPECIAL":
                    prompt = prompt[:-1]
                else:
                    prompt += char
                if prompt.endswith(END):
                    result = prompt[:-len(END)].strip()
                    return False  # stop listener

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
    prompt = ""
    buffer = ""
    return result